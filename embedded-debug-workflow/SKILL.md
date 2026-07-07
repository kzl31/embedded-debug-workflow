---
name: embedded-debug-workflow
description: >-
  嵌入式固件调试自动化工作流。用于 Keil MDK 工程编译烧录、串口日志抓取分析、
  CHESHI 调试宏迭代注入、Git 本地版本管理、故障定位与代码修复、标准化报告输出。
  检测到 .uvprojx/.uvproj/main.c 或用户描述故障现象时自动激活。
argument-hint: '描述故障现象 / 输入 debug help 查看帮助'
---

# 嵌入式固件调试工作流 Skill

> 实现的自动化调试引擎，覆盖：问题发现 → CHESHI 迭代 → 编译下载 → 日志分析 → 代码修复 → 回归验证 → 标准化报告。

你接收到的参数：`$ARGUMENTS`

---

## 🎮 快捷命令

| 命令 | 用途 | 执行前必须读取 |
|------|------|:---:|
| `/kzl 帮助` 或 `/kzl help` | 显示调试工作流帮助和可用命令 | `commands/help.md` |
| `/kzl 初始化` 或 `/kzl init [项目目录]` | 初始化调试配置（扫描工程→采集参数→生成配置） | `commands/init.md` |

> 以上命令是辅助入口，仍可通过直接描述故障现象触发完整调试流程。
> 原始 Flow Gate 门禁机制保持不变，所有流程仍需遵循门禁规则。

---

## 📑 目录

| 章节 | 说明 | 位置 |
|------|------|------|
| ⛔ Flow Gate 门禁预检 | **优先级最高，每次操作前必执行** | 本文件下方 |
| 强制规则 | 5 条核心规则 | `refs/core-rules.md` |
| 启动流程 | STARTUP 门禁（参数采集+初始化） | `gates/STARTUP.yaml` |
| 调试循环 | DEBUG_LOOP 门禁（8轮迭代） | `gates/DEBUG_LOOP.yaml` |
| 验证报告 | VERIFY_AND_REPORT 门禁 | `gates/VERIFY_AND_REPORT.yaml` |
| 工作流总览 | 10 步完整流程示意图 | `refs/workflow-overview.md` |
| 项目设置 | 快速开始 + 配置存放位置 | `refs/project-setup.md` |
| 脚本命令 | Python/PowerShell 命令参考 | `refs/script-commands.md` |
| 配置文件格式 | embedded-debug-config.json 说明 | `refs/config-format.md` |
| 迭代检查清单 | 每次迭代完成后的校验项 | `refs/checklist.md` |
| 核心调试循环 | 8 轮迭代详细说明 | `refs/debug-loop.md` |
| Git 版本管理 | 本地分支/提交/回退规范 | `refs/git-rules.md` |
| CHESHI 宏规范 | 调试宏编写标准 | `refs/cheshi-macro.md` |
| 人工暂停规范 | 🛑 三类暂停场景 | `refs/pause-scenarios.md` |
| 常见故障速查 | 故障分类 & Map 分析 | `refs/common-faults.md` |
| JLink 调试 | JLink Commander 命令行调试 | `refs/jlink-debug.md` |
| Map 文件分析 | 查函数地址、栈深度、内存占用 | `refs/map-analysis.md` |
| 中断安全打印 | 环形缓冲区 ISR 调试方案 | `refs/isr-debug.md` |

---

## ⛔ Flow Gate 门禁预检（优先级最高，必须首先执行）

> **此机制参照 EM-SKILL 的路由-门禁-状态 三位一体架构设计。**
> **违反此节 = 流程违规。** 

### 操作前强制预检步骤

```
步骤 0: 读取 registry.json，获取所有阶段定义和门禁文件列表
       检查 gates/ 目录中所有注册的 gateFile 是否存在
       缺失任一文件 → 报错并停止

步骤 1: 读取项目工作区 .copilot/ 下的 flow-gate.json（必须存在）
  不存在 → 创建默认 .copilot/flow-gate.json 并继续

步骤 2: 检查 flow-gate.json 中的 currentPhase 字段

步骤 3: 在 registry.json 中查找 currentPhase → 读取对应的 gateFile
  ├─ 找到 gateFile → 只能读取该文件
  ├─ null / 未找到 → 只能读 gates/STARTUP.yaml
  └─ "COMPLETED"   → 允许任意门禁（继续或新任务）

步骤 4: 严格按照门禁文件中的 Step 1..N 顺序执行
  严禁跳过中间步骤
  每完成一步，更新 .copilot/flow-gate.json 对应字段
```

### ⛔ 禁止规则（定义于 registry.json）

```
各阶段的 forbiddenOperations 在 registry.json 中定义。
新增阶段只需注册 forbiddenOperations，无需修改 SKILL.md。
常见禁止操作参考 gates/FLOW_GATE_RULES.md 规则 5。
```

> **用户描述故障 ≠ 可以跳过 STARTUP 门禁**

### 注册中心

当前已注册的阶段和门禁文件见 `registry.json`。新增阶段只需：
1. 在 `registry.json` 注册 phase + gateFile
2. 在 `gates/` 下创建对应的门禁文件
3. 无需修改 SKILL.md 或 FLOW_GATE_RULES.md
