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

## 强制规则（AI 外部执行纪律）

1. **唯一入口** —— 流程顺序、跳转、自动步骤和状态由引擎控制；AI 不得绕过引擎直接编译、下载、分析、
  修改流程状态或自行跳转。
2. **唯一判据** —— 仅依据引擎 JSON 的 `status`、`next_action`、`seq`、`phase` 和 `what` 执行当前动作，
  不读取状态文件或终端输出来判断流程状态。
3. **完成条件** —— 只有引擎返回 `status = "completed"` 时才可结束流程。
4. **修改前先建立回退基线** —— 每轮修改前先提交当前状态，具体规则见 `refs/git-rules.md`。

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
> 工作区级配置、状态、日志和报告的路径由 `scripts/path_config.py` 根据
> `scripts/skill-config.json` 集中生成；源码由配置中的实际工程路径确定。

初始化参数由引擎步骤 1 的脚本完成并保存。AI 不得重复询问或介入参数选择，初始化后按引擎返回的
`next_action` 继续执行。

### 第三步：运行流程引擎（唯一流程入口）

```
python "{{SKILL_DIR}}\scripts\workflow_engine.py" --project "<VS Code 工作区根目录>" --mode 1
```

引擎会在 JSON 的 `status` 和 `next_action` 中返回下一步动作。AI 只处理引擎明确交给 AI 的步骤；
编译、下载、检查、状态更新和流程跳转由引擎完成。AI 步骤主要包括故障信息采集、源码调整、证据分析、
回归核对和报告整理。

具体的 AI 步骤执行、回执、进度展示、暂停和持续推进规则统一见 `refs/core-rules.md`；进入流程前必须
按需读取该文件。不要在本入口文档中重复维护这些细节。

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
| 集中运行参数 | `refs/runtime-config.md` |
| 新增流程指南 | `refs/add-flow-guide.md` |
| 检查清单 | `templates/checklist.md` |
| 调试循环 | `refs/debug-loop.md` |
| 人工暂停 | `refs/pause-scenarios.md` |
| 常见故障 | `refs/common-faults.md` |

> 注：`gates/*.yaml` 与 `registry.json` 为旧版多文件引擎遗留，已被 `flow.yaml` 取代，请勿再手动解析。新增/修改步骤请直接编辑 `flow.yaml`。

---

流程步骤、动作类型、条件和跳转格式均由 `flow.yaml` 与引擎实现定义；修改流程时直接查阅
`flow.yaml` 和 `refs/add-flow-guide.md`，无需在本 Skill 中重复维护格式速查。各参考文档只补充
对应领域的执行规范，不重复描述引擎内部状态和自动步骤。
