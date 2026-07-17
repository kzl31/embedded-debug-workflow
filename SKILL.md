---
name: embedded-debug-workflow
description: >-
  嵌入式固件调试自动化工作流。用于 Keil MDK 工程串口日志抓取分析、CHESHI 调试宏迭代注入、故障定位与代码修复。检测到用户描述故障现象时自动激活。
argument-hint: '描述故障现象 / 输入 debug help 查看帮助'
---

# 嵌入式固件调试工作流 Skill

> 自动化调试引擎：问题发现 → 初始化 → CHESHI 迭代 → 编译下载 → 日志分析 → 代码修复 → 回归验证 → 标准化报告。
> 流程定义全部集中在 `flow.yaml`（线性序号驱动），AI 行为强制规则见 `refs/core-rules.md`。

你接收到的参数：`$ARGUMENTS`

---

## 强制规则（铁律，违反即流程违规）

1. **按步骤执行，不可直接跳转** —— 流程顺序由引擎按 `seq` 强制，所有跳转都在 `flow.yaml` 内声明。
2. **任何判断以引擎 JSON 输出为准** —— 禁止直接读取*终端*或者*其他的任何形式文件*确定当前状态。
4. **只有到达流程完成步骤才可以停止** ——禁止在流程中途停止。



---

## 执行流程

### 第一步：检查是否已初始化（任何操作前必做，不可跳过）

- 本节只适用于用户进入嵌入式调试**流程**，不适用于下方 `/kzl` 独立快捷命令。
- 如果**无可见对话历史** 或者对话中没有 **--init**或者你不确定有没有 **--init** --→ 必须 `--init`
- 启动预检细节见 `refs/core-rules.md` 规则 1

### 第二步：初始化引擎（发现未初始化时执行）

```
python "{{SKILL_DIR}}\scripts\workflow_engine.py" --init --project "<VS Code 工作区根目录>"
```

> `{{SKILL_DIR}}` 为 skill 实际绝对路径，AI 执行时替换（如 `c:\Users\xxxxx\.copilot\skills\embedded-debug-workflow`）。
> `--project` 是历史兼容参数名，实际必须传入当前 **VS Code 工作区根目录**，不是
> Skill 仓库目录，也不是配置中某个 Keil 工程的 `projects[*].dir`。例如工作区为
> `E:\文件\代码\ai\自动化流程`、Skill 项目位于其子目录
> `embedded-debug-workflow` 时，必须传前者。运行状态和工作区级配置写入
> `{工作区根目录}/.copilot/`；源码、工程日志和报告目标则依据配置中的实际工程路径确定。

引擎会：创建干净内部状态 → 当前步骤置 `seq=1` → 输出初始化 JSON → 返回 `next_action`。

### 第三步：运行流程引擎（唯一流程入口）

```
python "{{SKILL_DIR}}\scripts\workflow_engine.py" --project "<VS Code 工作区根目录>" --mode 1
```

引擎返回两种状态：

- `status = "awaiting_ai"` → 当前是 **AI 步骤**（问用户 / 改源码 / 分析 / 报告 / 回归）。按 `what` / `params` 执行，完成后提交结果：
  ```
  python "...workflow_engine.py" --project "<VS Code 工作区根目录>" --ack success   # 目标达成
  python "...workflow_engine.py" --project "<VS Code 工作区根目录>" --ack failure   # 未达成（走 on_failure 分支）
  # 等价于 --done = --ack success
  ```
- `status = "auto_pending"` → 当前是 **自动步骤**（编译/下载/检查文件等），引擎已自动执行并按 `flow.yaml` 的 `on_success` / `on_failure` **链式推进**。AI 无需 `--ack`，直接再跑 `--mode 1` 即可，引擎会持续自动推进直到遇到 `awaiting_ai` / `awaiting_user` / `completed`。
- `status = "awaiting_user"` → 触发人工暂停（`wait_user`），处理用户后 `--wake` 恢复。
- `status = "completed"` → 全部流程结束，可用 `--reset` 开始新任务。

**你的职责**：
1. 以引擎 JSON 的 `status` / `next_action` / `seq` / `phase` 为唯一判据（**不读状态文件**）
2. AI 步骤执行后必须 `--ack success` 或 `--ack failure`
3. **禁止跳过引擎直接操作**（编译/下载/分析等）
4. **只有到达流程完成步骤才可以停止**
5. 每次到达新步骤时，将 `user_display.current_step` 简短展示给用户；这只是进度展示，不是分析汇报
6. `user_display.loop` 存在时，同时简述调试循环次数和原因，不展开日志、根因或结论，使用“> 内容描述”告知用户

### 快捷命令

| 命令 | 用途 |
|------|------|
| `/kzl 帮助` | 显示帮助 → 读 `commands/help.md` |
| `/kzl 初始化 [目录]` | 初始化配置 → 读 `commands/init.md` |
| `/kzl 编译` | 仅编译（不下载）→ 读 `commands/build.md` |
| `/kzl 编译下载` | 编译+下载 → 读 `commands/build.md` |
| `/kzl 打印 <要求>` | 按 CHESHI 规范添加调试打印 → 读 `commands/print.md` |
| `/kzl 报告 [标题/要求]` | 根据当前对话生成详细报告并保存记忆 → 读 `commands/report.md` |
| `/kzl 新增流程` | 新增步骤/阶段 → 读 `commands/add-flow.md` |

> **命令与流程严格分离**：识别到上表命令后，直接读取对应 `commands/*.md` 执行并停止，
> 不得先运行 `workflow_engine.py`，不得初始化或推进流程。命令可为流程准备配置、打印和固件，
> 但不受 `flow.yaml` 当前 `seq` 约束。`/klz 打印` 作为 `/kzl 打印` 的兼容拼写处理。
> 所有 `report` 动作必须使用完整报告模板，明确证据与验证边界，并同时更新
> `data/debug-history.yaml` 和 `/memories/embedded-debug-workflow.md` 持久记忆；任何一项失败均不得宣称报告完成。

---

## 参考文档（按需加载）

| 主题 | 文件 |
|------|------|
| **流程定义（唯一真相源）** | `flow.yaml` |
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

> 注：`gates/*.yaml` 与 `registry.json` 为旧版多文件引擎遗留，已被 `flow.yaml` 取代，请勿再手动解析。新增/修改步骤请直接编辑 `flow.yaml`。

---

## flow.yaml 步骤格式速查

每个步骤**格式完全相同**：

```yaml
- seq: 1                       # 连续唯一的全局序号（线性编号）
  id: step_xxx                 # 语义化 id（goto 也可写 goto: step_xxx）
  phase: STARTUP               # 阶段分组标签（仅用于报告分组 + AI 自检 forbidden）
  what: "这一步做什么"         # 给 AI 读的一句话
  action: run_script           # 动作类型枚举（见下）
  call: 'python scripts/xxx.py --config-dir "{project_dir}"'  # 脚本命令（action=run_script 时）
  precheck: [ { assert: "条件", on_fail: [ ... ] } ]   # 执行前断言
  pre_action: [ ... ]                                # 执行前动作（如 retryCount+1）
  on_success: [ ... ]          # 成功后的「动作列表」
  on_failure: [ ... ]          # 失败后的「动作列表」
```

**动作类型（action 枚举）**
- 自动：`run_script` / `check_file` / `read_config` / `update_state` / `log` / `exit` / `noop`
- AI：`ask_user` / `edit_source` / `analyze` / `report` / `check_regression` / `wait_user`

**on_success / on_failure 是「动作列表」**，元素为单键对象：
- `update_state: { 点号路径: 值 }`（`"+1"` 表示自增）
- `run_script: "命令"`
- `log: "msg"` 或 `log: { level: info|warning|error, msg: "..." }`
- `read_config: {}`
- `goto: <seq | id | next | done | wait>`（序号 / id / 下一步 / 结束 / 暂停）
- `exit: COMPLETED`
- `wait_user: "msg"`
- `when: "条件"`（同级 `then: [...]` / `else: [...]`）

> 列表里出现 `goto` / `exit` / `wait_user` 即终止；若没有跳转动作，引擎默认推进到 `seq+1`。

**条件语法**：`section.field <op> 值`，如 `debugLoopInfo.retryCount < 2`、`projectInfo.hasSerialProjects == true`；
支持 `== != < > <= >=`，数值/字符串自动判断。

新增/修改步骤详见 `refs/add-flow-guide.md`，完整流程图见 `refs/workflow-diagram.md`。
