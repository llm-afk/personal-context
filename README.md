# Personal Context

用 Markdown 和 Git 维护可携带、可查询、可纠正的个人上下文。你正常聊天和做事，AI 在权限允许时顺手保存有长期价值的信息。

这是规则与文件组成的工作区，适用于能够读取、编辑本地文件的 AI 客户端。它没有后台服务、数据库、自动抓取或持续监控，也不是一套能强制所有模型遵从规则的软件。

## 开始使用

1. 在 AI 客户端中打开本仓库文件夹 `personal-context`，不要把桌面根目录当作此系统的工作区。
2. 首次接入时确认客户端已加载 [AGENTS.md](AGENTS.md)。规则无法自动加载时，在开头说：

   > 请先读取本工作区根目录的 AGENTS.md，按其中约定正常与我对话，并在授权范围内维护个人上下文；如果无法读取或写入，请说明实际限制，不要声称完成了保存。

3. 直接开始普通对话，例如讨论一个问题、说明项目目标，或告诉 AI 某个以后也适用的协作偏好。

已经加载规则后，无需每轮粘贴接入句或填写表格。普通记忆维护成功通常不另外汇报；明确要求保存、更正、删除或改变开关时会简短说明结果。

首次初始化没有导入既有聊天、其他项目或个人档案。分类文件在第一次有合适内容时创建，不用填满空模板。

## 用自然语言控制

| 你说的话 | 效果 |
| --- | --- |
| “这件事别记” | 当前指代内容不写入任何记忆、证据、索引、临时队列或提交说明 |
| “暂停记录” | 停止自动新增记忆，仍可调用旧记忆 |
| “恢复记录” | 恢复之后的自动记录，不补录暂停期间内容 |
| “关闭记忆” | 同时停止自动记录和调用旧记忆 |
| “恢复记忆” | 同时恢复记录和调用 |
| “本轮别用以前的记忆” | 只在本轮停止使用个人历史，不改持久开关 |
| “记住这一条” | 在其他边界允许时保存指定内容；即使暂停，也只授权这一条 |
| “纠正一下……” | 修正指定记录和相关引用，不改变暂停状态 |
| “忘记这条” | 清理工作树内的相关记录、摘要、证据、归档和衍生副本 |
| “你记住了我什么？依据是什么？” | 查询相关记录、来源和不确定性 |
| “关闭自动提交” | 将 `local_commits` 设为 `off`，仍可保存文件 |

控制状态只保存在 [memory/control.md](memory/control.md)：`recording`、`recall` 和 `local_commits` 互相独立。规则和配置无法读取时，自动记忆功能暂停，普通对话仍可继续。

“别记”约束这次保存；需要删除已经保存的内容时说“忘记”。工作树删除不等于清除 Git 历史、聊天平台日志、其他备份或客户端自身记忆。

## 文件如何分工

| 位置 | 职责 |
| --- | --- |
| [AGENTS.md](AGENTS.md) | 所有客户端共同遵循的日常主规则 |
| [CLAUDE.md](CLAUDE.md)、[GEMINI.md](GEMINI.md) | 只导入主规则的客户端入口 |
| [memory/control.md](memory/control.md) | 控制开关，不存放个人背景 |
| [memory/INDEX.md](memory/INDEX.md) | 导航到已经存在的权威记录 |
| `memory/profile.md`、`preferences.md` | 按需创建的稳定事实、范围明确的偏好 |
| `memory/current.md`、`decisions.md` | 跨项目的当前目标与重要决定 |
| `memory/understanding.md`、`hypotheses.md` | 理解证据、未解决问题和少量暂定推断 |
| `memory/projects/` | 项目自己的状态、约束、决定和下一步 |
| `memory/evidence/`、`archive/` | 必要的最少证据和有保留价值的历史 |
| [spec/schema.md](spec/schema.md) | 开关、记录格式、来源和状态语义；写入时按需读取 |
| [spec/acceptance.md](spec/acceptance.md) | 行为验收场景与实际检查范围 |
| [scripts/check.py](scripts/check.py) | 只读、无第三方依赖的基础结构检查 |
| `.private/` | 按明确授权使用的本地私密区，不默认读取、不进入 Git |

同一信息只有一个权威位置。项目状态保存在项目文件中，全局导航只引用它。记录包含稳定 ID、来源、范围、状态和时间；推断不会因反复引用自动变成已确认事实。

## 客户端接入

- **Codex** 使用根目录 `AGENTS.md`。具体加载会受到工作目录、覆盖文件和配置影响；修改规则后确认新版本已生效，必要时新开会话。[官方说明](https://learn.chatgpt.com/docs/agent-configuration/agents-md)
- **Claude Code** 通过 `CLAUDE.md` 中独立的一行 `@AGENTS.md` 导入共同规则。[官方说明](https://code.claude.com/docs/en/memory)
- **Gemini CLI** 通过 `GEMINI.md` 中独立的一行 `@./AGENTS.md` 导入共同规则。[官方说明](https://geminicli.com/docs/reference/memport/)

导入行不能放在代码块或反引号中。入口仅导入主规则，个人记录按当前问题读取。其他工具先确认自己的加载机制；无文件访问能力的聊天工具，仅靠接入句无法维护本仓库。

这些规则不修改全局客户端设置，也不控制客户端自己的自动记忆、后台提取和日志保留。官方入口文档于 2026-10-10 核对；实际客户端行为的验证状态见验收文件。

## Git 和公开范围

本仓库按所有者要求作为公开仓库发布，目标为 [llm-afk/personal-context](https://github.com/llm-afk/personal-context)。首次发布的个人记忆为空。

日常记录默认可以创建低敏内容的**本地提交**，不会自动 push。后续若要求推送，必须检查所有待推送提交的内容；即使工作树已经删除某条记录，旧提交也可能仍含它。明确要求发布当前版本，不代表授权以后持续公开新的个人内容。

不应把凭据、敏感原文、公司机密或第三方隐私写入可版本管理的文件。`.private/`、本地运行目录、日志和常见凭据文件已排除；Git 排除不是加密，也不会自动清除此前已跟踪的文件。云端 AI 读取本地文件不代表数据始终留在本机。

查看当前修改和暂存内容：

```powershell
git status --short
git diff
git diff --cached
```

需要手动提交时，先确认暂存区没有不明修改，再使用本轮实际修改的明确路径。下面只是第一次创建偏好记录时的路径示例，文件存在且确为本轮改动时才执行：

```powershell
git add -- memory/preferences.md memory/INDEX.md
git diff --cached
git commit -m "Update context records"
```

不要使用 `git add .` 或 `git add -A` 夹带其他改动。提交失败不代表文件没有保存；不编造 Git 身份、不改全局配置、不清理他人暂存内容。

在另一台设备使用已经发布的版本：

```powershell
git clone https://github.com/llm-afk/personal-context.git
cd personal-context
```

同步前先检查本地修改。用户要求同步时可以 `git fetch origin` 后比较双方提交，确认可快进再 `git merge --ff-only origin/main`。需要发布已经审阅的本地提交时才执行 `git push origin main`。出现分歧时保留双方内容并处理冲突，不用 `reset --hard` 或强推代替判断。

如果要连接另一个由你指定的私有仓库，先在 GitHub 创建空的私有仓库，再显式添加它的真实地址为一个新 remote，例如 `git remote add private <你提供的真实仓库地址>`；核对 `git remote -v` 后再决定推送哪些提交。不会猜测账号、创建远程或自动迁移内容。

第一版按“不同 AI 交替使用，同一时刻一个写入者”设计。Git 能保留版本，但不能自动理解和解决语义冲突。

## 检查与能力边界

安装有 Python 3.10 或更新版本时，在仓库根目录运行：

```powershell
python scripts/check.py
```

检查器不写文件，不访问网络，不读取 `.private/`。它检查入口、控制值、导航、记录结构、ID 和记录引用，以及 Git 忽略与跟踪状态；有问题时返回非零退出码。它只接受 schema 中约定的简化 YAML 格式，不是通用 YAML 解析器。

通过结构检查不代表事实正确，也不证明模型会完整遵守每项规则。25 个对话场景保留在验收文件中，静态检查、实际执行和未测试的情况分别标注。
