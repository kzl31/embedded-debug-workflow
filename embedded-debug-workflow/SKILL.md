---
name: embedded-debug-workflow
description: >-
  嵌入式固件调试自动化工作流。用于 Keil MDK 工程编译烧录、串口日志抓取分析、
  CHESHI 调试宏迭代注入、Git 本地版本管理、故障定位与代码修复、标准化报告输出。
  检测到 .uvprojx/.uvproj/main.c 或用户描述故障现象时自动激活。
argument-hint: '描述故障现象 / 输入 debug help 查看帮助'
---

# 嵌入式固件调试工作流 Skill

> 自动化调试引擎，覆盖：问题发现 → CHESHI 迭代 → 编译下载 → 日志分析 → 代码修复 → 回归验证 → 标准化报告。

你接收到的参数：`$ARGUMENTS`

---
## 强制规则，不可违背，否则会有国际领导人去世

1.*按步骤执行，不可以直接跳转，否则就是流程违规*
2.*任何判断都必须以引擎输出 JSON 为准，禁止直接读取状态文件，否则就是流程违规，*

### 🔴 AI 自检清单（每次推理前必须逐条核查）

> **在调用任何工具之前，先逐条问自己：**

- [ ] **这是新对话吗？** — 会话记忆为空 / 第一条消息 → 必须先 `--init`
- [ ] **我想改代码/编译/下载/分析？** — ⛔ 必须先跑引擎，看当前阶段是否允许
- [ ] **我在走捷径吗？** — "这次是小事，直接搞吧" → ⛔ 没有小事，规则就是规则

> 以上四条只要有一条是 ❌，就**必须优先跑引擎**，否则就是流程违规，等于有人去世。

## 🔴 第零步：检查是否已初始化（任何操作前必须先执行，不能跳过这个步骤）

### 判断规则（严格按以下优先级检查）

1. ✅ **会话记忆（Session Memory）为空** → **新对话** → 必须 `--init`
2. ✅ **这是当前会话的第一条用户消息** → **新对话** → 必须 `--init`
3. ❌ **持久记忆（User Memory）有历史记录** → **不是判断依据**（跨会话存储，无关）
4. ❌ **引擎状态文件存在** → **不是判断依据**（可能来自上一次会话残留，且 AI 不得自行读取该文件）
5. ❌ **调试报告文件存在** → **不是判断依据**（同上）

**一句话规则：只要当前会话无可见对话历史 → 就是新对话 → 必须 `--init`。**

> ⛔ **AI 不得自行假设"是否已初始化"。** 必须严格按上述规则判断。
> ⛔ **禁止跳过此步骤直接操作。**

## ⚡ 初始化引擎（检查发现未初始化时执行）

```
python "{{SKILL_DIR}}\scripts\workflow_engine.py" --init --project "<项目根目录>"
```

> ⚠️ `{{SKILL_DIR}}` 为本 skill 所在目录，AI 执行时需替换为 skill 的实际绝对路径（例如 `c:\Users\xxxxx\.copilot\skills\embedded-debug-workflow`）。

引擎会：
- 创建干净的内部状态文件（路径由引擎自身管理，无需 AI 关心）
- 设置初始阶段为 STARTUP
- 输出初始化完成 JSON
- 返回 `next_action` 告诉你下一步跑引擎

## ⛔ 第一步：运行流程引擎（是否运行了第0步）

```
python "{{SKILL_DIR}}\scripts\workflow_engine.py" --project "<项目根目录>" --mode 1
```
> 💡 只想看当前进度、不推进？用 `--mode 0`（只读状态）；要执行/推进当前步骤用 `--mode 1`。

**这是唯一的流程入口。** 引擎会：
- 自动读取 `registry.json` + `gates/*.yaml` 获取流程定义
- 自动读取自身维护的内部状态获取当前进度
- 自动执行编译/下载/串口等步骤
- 输出 JSON 指令告诉你下一步做什么

**你的职责：**
1. *先跑引擎*，以 JSON 输出的 `status` / `next_action` 作为下一步唯一判据（**不要去读状态文件**），不然就是*流程违规*
2. 如果 `status = "awaiting_ai"` → 按 `message` 和 `details` 执行，完成后跑 `--done`
3. 如果 `status = "auto_executed"` → 引擎已自动完成，跑 `--done` 推进
4. **禁止跳过引擎直接操作**（编译/下载/分析代码等）

### 快捷命令

| 命令 | 用途 |
|------|------|
| `/kzl 帮助` | 显示帮助 → 读 `commands/help.md` |
| `/kzl 初始化 [目录]` | 初始化配置 → 读 `commands/init.md` |
| `/kzl 编译` | 编译下载 → 读 `commands/build.md` |
| `/kzl 增加流程` | 新增步骤/阶段 → 读 `commands/add-flow.md` |

> `/kzl` 命令也必须先跑引擎检查当前阶段是否允许。

---

## 📑 参考文档（按需加载）

| 主题 | 文件 |
|------|------|
| 完整流程图 | `refs/workflow-diagram.md` |
| 强制规则 | `refs/core-rules.md` |
| CHESHI 宏规范 | `refs/cheshi-macro.md` |
| Git 版本管理 | `refs/git-rules.md` |
| 工作流总览 | `refs/workflow-overview.md` |
| 脚本命令 | `refs/script-commands.md` |
| 配置文件格式 | `refs/config-format.md` |
| 检查清单 | `refs/checklist.md` |
| 调试循环 | `refs/debug-loop.md` |
| 人工暂停 | `refs/pause-scenarios.md` |
| 常见故障 | `refs/common-faults.md` |
| JLink 调试 | `refs/jlink-debug.md` |
| Map 分析 | `refs/map-analysis.md` |
| ISR 调试 | `refs/isr-debug.md` |

## 🔧 流程定义（由引擎自动读取，勿手动解析）

| 文件 | 说明 |
|------|------|
| `registry.json` | 阶段注册中心 |
| `gates/FLOW_GATE_RULES.md` | 门禁总规则 |
| `gates/STARTUP.yaml` | 启动阶段 |
| `gates/DEBUG_LOOP.yaml` | 调试循环 |
| `gates/VERIFY_AND_REPORT.yaml` | 验证与报告 |
