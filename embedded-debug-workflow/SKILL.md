---
name: embedded-debug-workflow
description: >-
  嵌入式固件调试自动化工作流。用于 Keil MDK 工程编译烧录、串口日志抓取分析、CHESHI 调试宏迭代注入、Git 本地版本管理、故障定位与代码修复、标准化报告输出。检测到 .uvprojx/.uvproj/main.c 或用户描述故障现象时自动激活。
argument-hint: '描述故障现象 / 输入 debug help 查看帮助'
---

# 嵌入式固件调试工作流 Skill

> 自动化调试引擎：问题发现 → 初始化 → CHESHI 迭代 → 编译下载 → 日志分析 → 代码修复 → 回归验证 → 标准化报告。
> 详细门禁纪律见 `gates/FLOW_GATE_RULES.md`，AI 行为约束见 `refs/core-rules.md`。

你接收到的参数：`$ARGUMENTS`

---

## 强制规则（铁律，违反即流程违规）

1. **按步骤执行，不可直接跳转** —— 流程顺序由门禁强制。
2. **任何判断以引擎 JSON 输出为准** —— 禁止直接读取内部状态文件。
3. **流程违规必须立即退出执行** —— 见下方「流程违规退出机制」。

### AI 自检清单（每次操作前必查）

- [ ] **新对话？** → 会话无可见历史即新对话，必须先 `--init`
- [ ] **用户要求跳过流程 / 阶段禁止的操作？** → 判定违规，立即退出执行
- [ ] **要改代码/编译/下载/分析/出报告？** → 先跑引擎，看当前阶段是否允许
- [ ] **在走捷径？**（"这次小事直接搞"）→ 没有小事，规则就是规则

> 一旦判定违规，**任何情况下都不得继续操作**，只能按 `templates/abort-report.md` 输出标准格式中止通告。

---

## 流程违规退出机制

由 **AI 在对话中自行判定**（不依赖脚本）：只要发现当前情形不符合流程，立即退出执行。

**触发条件（任一即违规）**：用户强制跳过步骤 / 用户要求阶段禁止的操作 / 未初始化就操作 / 跳跃步骤 / 直接读状态文件 / 阶段与操作不匹配。

**退出动作**：
1. **立即停止**一切工具调用与脚本执行（编译、下载、读状态文件、分析代码、生成报告一律禁止）；
2. 按 `templates/abort-report.md` 的**标准格式**输出 `⛔ 流程中止通告（FLOW ABORT）`，据情形填入 `violation_type` / `violation_reason` / `当前阶段` / `本次已执行步骤`；
3. 不再尝试 `--mode 1` / `--done`，仅提示用户重新 `--init`。

> 违规类型速查与格式模板见 `templates/abort-report.md`。

---

## 执行流程

### 第一步：检查是否已初始化（任何操作前必做，不可跳过）

- 当前会话**无可见对话历史** → 新对话 → 必须 `--init`
- ❌ 不得依据「状态文件存在 / 报告文件存在 / 持久记忆」判断（可能来自上一次会话残留，且 AI 不得自行读状态文件）
- 启动预检细节见 `gates/FLOW_GATE_RULES.md` 规则 1

### 第二步：初始化引擎（发现未初始化时执行）

```
python "{{SKILL_DIR}}\scripts\workflow_engine.py" --init --project "<项目根目录>"
```

> `{{SKILL_DIR}}` 为 skill 实际绝对路径，AI 执行时替换（如 `c:\Users\xxxxx\.copilot\skills\embedded-debug-workflow`）。

引擎会：创建干净内部状态 → 阶段置 `STARTUP` → 输出初始化 JSON → 返回 `next_action`。

### 第三步：运行流程引擎（唯一流程入口）

```
python "{{SKILL_DIR}}\scripts\workflow_engine.py" --project "<项目根目录>" --mode 1
```

> `--mode 0` 只读当前状态不推进；`--mode 1` 执行/推进当前步骤；完成后 `--done` 推进。

**你的职责**：
1. 以引擎 JSON 的 `status` / `next_action` 为唯一判据（**不读状态文件**）
2. `status = "awaiting_ai"` → 按 `message`/`details` 执行，完成后 `--done`
3. `status = "auto_executed"` → 引擎已自动完成，跑 `--done` 推进
4. **禁止跳过引擎直接操作**（编译/下载/分析等）
5. **用户要求跳过流程 / 阶段禁止操作 / 未初始化就操作** → 流程违规，按 `templates/abort-report.md` 退出执行

### 快捷命令

| 命令 | 用途 |
|------|------|
| `/kzl bz` | 显示帮助 → 读 `commands/help.md` |
| `/kzl csh [目录]` | 初始化配置 → 读 `commands/init.md` |
| `/kzl by` | 仅编译（不下载）→ 读 `commands/build.md` |
| `/kzl byxz` | 编译+下载 → 读 `commands/build.md` |
| `/kzl zjlc` | 新增步骤/阶段 → 读 `commands/add-flow.md` |

> `/kzl` 命令也必须先跑引擎检查当前阶段是否允许。

---

## 参考文档（按需加载）

| 主题 | 文件 |
|------|------|
| 完整流程图 | `refs/workflow-diagram.md` |
| 强制规则 | `refs/core-rules.md` |
| CHESHI 宏规范 | `refs/cheshi-macro.md` |
| Git 版本管理 | `refs/git-rules.md` |
| 脚本命令 | `refs/script-commands.md` |
| 配置文件格式 | `refs/config-format.md` |
| 新增流程指南 | `refs/add-flow-guide.md` |
| 检查清单 | `templates/checklist.md` |
| 调试循环 | `refs/debug-loop.md` |
| 人工暂停 | `refs/pause-scenarios.md` |
| 常见故障 | `refs/common-faults.md` |
| 流程违规退出 | `templates/abort-report.md` |

## 流程定义（由引擎自动读取，勿手动解析）

| 文件 | 说明 |
|------|------|
| `registry.json` | 阶段注册中心 |
| `gates/FLOW_GATE_RULES.md` | 门禁总规则 |
| `gates/STARTUP.yaml` | 启动阶段 |
| `gates/DEBUG_LOOP.yaml` | 调试循环 |
| `gates/VERIFY_AND_REPORT.yaml` | 验证与报告 |
