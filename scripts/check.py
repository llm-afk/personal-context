#!/usr/bin/env python3
"""Read-only checks for this workspace's deliberately small Markdown/YAML format."""
import argparse
import datetime as dt
import json
import os
from pathlib import Path
import re
import stat
import subprocess
import sys
import uuid

REQUIRED = ("AGENTS.md", "CLAUDE.md", "GEMINI.md", "README.md", ".gitignore",
            "memory/control.md", "memory/INDEX.md", "spec/schema.md", "spec/acceptance.md")
KINDS = {"fact", "preference", "goal", "state", "understanding", "hypothesis", "decision"}
STATES = {"active", "tentative", "disputed", "superseded", "expired"}
SOURCES = {"user_statement", "user_confirmation", "artifact", "inference"}
FIELDS = {"kind", "content", "scope", "status", "sources", "recorded_at", "updated_at"}
OPTIONAL = {"valid_from", "valid_until", "review_after", "related_ids", "supersedes"}
ID_RE = re.compile(r"m-[0-9a-f]{8}(?:-[0-9a-f]{4}){3}-[0-9a-f]{12}")


def scalar(raw):
    if not raw:
        raise ValueError("empty scalar")
    if raw.startswith(('"', '[')) or raw == "null" or re.fullmatch(r"[0-9]+", raw):
        return json.loads(raw)
    if re.fullmatch(r"[a-z_]+", raw):
        return raw
    raise ValueError("unsupported scalar; follow the documented YAML subset")


def mapping(block):
    result, source = {}, None
    for line in block.splitlines():
        if not line.strip() or line.lstrip().startswith("#"):
            continue
        top = re.fullmatch(r"([a-z_]+):[ ]?(.*)", line)
        if top:
            key, raw = top.groups()
            if key in result:
                raise ValueError("duplicate field")
            source = None
            if key == "sources" and not raw:
                result[key] = []
            else:
                result[key] = scalar(raw)
            continue
        item = re.fullmatch(r"  - ([a-z_]+):[ ]?(.*)", line)
        entry = re.fullmatch(r"    ([a-z_]+):[ ]?(.*)", line)
        if item and isinstance(result.get("sources"), list):
            key, raw = item.groups()
            source = {key: scalar(raw)}
            result["sources"].append(source)
        elif entry and source is not None:
            key, raw = entry.groups()
            if key in source:
                raise ValueError("duplicate source field")
            source[key] = scalar(raw)
        else:
            raise ValueError("unsupported YAML layout")
    return result


def nonempty(value):
    return isinstance(value, str) and bool(value.strip())


def valid_time(value):
    if not isinstance(value, str):
        return False
    try:
        if re.fullmatch(r"\d{4}-\d{2}-\d{2}", value):
            dt.date.fromisoformat(value)
            return True
        parsed = dt.datetime.fromisoformat(value.replace("Z", "+00:00"))
        return "T" in value and parsed.tzinfo is not None
    except ValueError:
        return False


def check(root):
    errors, records, texts = [], {}, {}

    def require(condition, message):
        if not condition:
            errors.append(message)

    def read(relative):
        path = root / relative
        if not path.resolve().is_relative_to(root):
            raise ValueError("path resolves outside the workspace")
        return path.read_text(encoding="utf-8-sig")

    for relative in REQUIRED:
        try:
            texts[relative] = read(relative)
        except (OSError, UnicodeError, ValueError):
            errors.append(f"{relative}: missing, unreadable, or outside workspace")
    if errors:
        return errors, 0

    agents = texts["AGENTS.md"]
    require(len(agents.splitlines()) <= 150 and len(agents.encode("utf-8")) <= 16384,
            "AGENTS.md: exceeds the project's size target")
    for name, expected in (("CLAUDE.md", "@AGENTS.md"), ("GEMINI.md", "@./AGENTS.md")):
        require(texts[name].strip() == expected, f"{name}: expected one plain import line")

    def frontmatter(text):
        match = re.match(r"\A---\n(.*?)\n---(?:\n|$)", text, re.S)
        if not match:
            raise ValueError("missing front matter")
        fields = mapping(match[1])
        if type(fields.get("schema_version")) is not int or fields["schema_version"] != 1:
            raise ValueError("unsupported schema version")
        return fields

    try:
        control = frontmatter(texts["memory/control.md"])
        require(set(control) == {"schema_version", "recording", "recall", "local_commits", "updated_at"},
                "memory/control.md: missing or unknown fields")
        for field, values in (("recording", {"auto", "paused"}), ("recall", {"on", "off"}),
                              ("local_commits", {"on", "off"})):
            require(control.get(field) in values, f"memory/control.md: invalid {field}")
        require(valid_time(control.get("updated_at")), "memory/control.md: invalid updated_at")
    except (ValueError, TypeError):
        errors.append("memory/control.md: invalid format or schema version")

    def linked(path):
        return path.is_symlink() or bool(getattr(path.lstat(), "st_file_attributes", 0)
                                        & getattr(stat, "FILE_ATTRIBUTE_REPARSE_POINT", 1024))

    memory_files = []
    memory_root = root / "memory"
    if linked(memory_root) or not memory_root.resolve().is_relative_to(root):
        errors.append("memory/: linked or external directory is not supported")
        return errors, 0
    for directory, dirs, names in os.walk(memory_root, followlinks=False):
        for name in list(dirs):
            path = Path(directory) / name
            if name.startswith(".") or linked(path) or not path.resolve().is_relative_to(memory_root):
                errors.append("memory/: linked or external directory is not supported")
                dirs.remove(name)
        for name in names:
            if name.endswith(".md"):
                path = Path(directory) / name
                if linked(path):
                    errors.append("memory/: linked files are not supported")
                else:
                    memory_files.append(path)
    for path in sorted(memory_files):
        relative = path.relative_to(root).as_posix()
        if relative == "memory/control.md":
            continue
        try:
            text = read(relative)
            frontmatter(text)
            if relative == "memory/INDEX.md" or relative.startswith("memory/evidence/"):
                continue
            headings = list(re.finditer(r"^## (.+)$", text, re.M))
            if not headings:
                errors.append(f"{relative}: no records; omit unused categories")
            for index, heading in enumerate(headings):
                record_id = heading[1]
                if not ID_RE.fullmatch(record_id):
                    raise ValueError("invalid record heading")
                uuid.UUID(record_id[2:])
                end = headings[index + 1].start() if index + 1 < len(headings) else len(text)
                body = text[heading.end():end]
                match = re.fullmatch(r"\s*```yaml\n(.*?)\n```\s*", body, re.S)
                if not match:
                    raise ValueError("record must contain exactly one YAML block")
                data = mapping(match[1])
                require(record_id not in records, f"{relative}: duplicate record ID {record_id}")
                records[record_id] = (relative, data)
                require(FIELDS <= data.keys() <= FIELDS | OPTIONAL, f"{relative}: missing or unknown record fields")
                require(data.get("kind") in KINDS and data.get("status") in STATES, f"{relative}: invalid kind or status")
                require(nonempty(data.get("content")) and nonempty(data.get("scope")), f"{relative}: empty content or scope")
                for field in ("recorded_at", "updated_at"):
                    require(valid_time(data.get(field)), f"{relative}: invalid {field}")
                for field in ("valid_from", "valid_until", "review_after"):
                    require(data.get(field) is None or valid_time(data[field]), f"{relative}: invalid {field}")
                sources = data.get("sources")
                if not isinstance(sources, list) or not sources:
                    errors.append(f"{relative}: sources must be a nonempty list")
                    continue
                for source in sources:
                    require(isinstance(source, dict), f"{relative}: invalid source")
                    if not isinstance(source, dict):
                        continue
                    require({"type", "basis"} <= source.keys() <= {"type", "basis", "locator", "limitation"},
                            f"{relative}: missing or unknown source fields")
                    require(source.get("type") in SOURCES and nonempty(source.get("basis")), f"{relative}: invalid source type or basis")
                    locator = source.get("locator")
                    require(locator is None or nonempty(locator), f"{relative}: invalid source locator")
                    require(nonempty(locator) or nonempty(source.get("limitation")), f"{relative}: unlocated source needs limitation")
                if all(isinstance(source, dict) and source.get("type") == "inference" for source in sources):
                    require(data.get("status") != "active", f"{relative}: inference alone cannot be active")
        except (OSError, UnicodeError, ValueError, TypeError):
            errors.append(f"{relative}: invalid record format; follow spec/schema.md")

    for record_id, (relative, data) in records.items():
        related = data.get("related_ids", [])
        require(isinstance(related, list) and all(isinstance(item, str) for item in related),
                f"{relative}: related_ids must be a string array")
        refs = related if isinstance(related, list) else []
        previous = data.get("supersedes")
        if previous is not None:
            require(isinstance(previous, str), f"{relative}: supersedes must be one ID")
            refs = refs + [previous]
        for ref in refs:
            require(isinstance(ref, str) and ref in records and ref != record_id,
                    f"{relative}: missing or self-referencing record ID")
        if isinstance(previous, str) and previous in records:
            require(records[previous][1].get("status") == "superseded", f"{relative}: replaced record must be superseded")
        seen, current = set(), record_id
        while isinstance(current, str) and current in records:
            if current in seen:
                errors.append(f"{relative}: supersedes cycle")
                break
            seen.add(current)
            current = records[current][1].get("supersedes")

    for target in re.findall(r"\[[^\]]+\]\(([^)]+)\)", texts["memory/INDEX.md"]):
        if "://" in target:
            errors.append("memory/INDEX.md: use workspace links for record navigation")
            continue
        file_part, _, anchor = target.partition("#")
        path = (root / "memory" / file_part).resolve()
        require(path.is_relative_to(root) and path.is_file() and ".private" not in path.parts,
                "memory/INDEX.md: missing or disallowed link target")
        if anchor.startswith("m-"):
            require(anchor in records and (root / records[anchor][0]).resolve() == path,
                    "memory/INDEX.md: record anchor does not match its target file")

    try:
        top = subprocess.run(["git", "rev-parse", "--show-toplevel"], cwd=root, capture_output=True, text=True)
        require(top.returncode == 0 and Path(top.stdout.strip()).resolve() == root,
                "Git root must be this workspace, not a parent repository")
        for probe in (".private/check.txt", ".tmp/check.txt", ".env", "check.key", ".codex-log/check.log"):
            result = subprocess.run(["git", "check-ignore", "--no-index", "-q", "--", probe], cwd=root, capture_output=True)
            require(result.returncode == 0, f".gitignore: missing exclusion for {probe}")
        tracked = subprocess.run(["git", "ls-files", "-ci", "--exclude-standard", "-z"], cwd=root, capture_output=True)
        require(tracked.returncode == 0 and not tracked.stdout, "Git already tracks ignored files; review index and history")
        unresolved = subprocess.run(["git", "ls-files", "-u"], cwd=root, capture_output=True)
        require(unresolved.returncode == 0 and not unresolved.stdout, "Git contains unresolved merge entries")
    except OSError:
        errors.append("Git is unavailable; ignore and index checks were not completed")
    return errors, len(records)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=Path(__file__).resolve().parents[1])
    args = parser.parse_args()
    errors, count = check(args.root.resolve())
    for error in errors:
        print("FAIL " + error)
    if errors:
        print(f"FAILED: {len(errors)} structural issue(s). No files were changed.")
        return 1
    print(f"PASS: workspace structure, controls, links, {count} record(s), and Git exclusions.")
    print("This does not verify facts, privacy of prose, or AI conversational behavior.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
