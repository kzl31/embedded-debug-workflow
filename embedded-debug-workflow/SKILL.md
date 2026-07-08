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
| `/kzl 编译` 或 `/kzl build` | 编译当前工程并下载固件到设备 | `commands/build.md` |

> 以上命令是辅助入口，仍可通过直接描述故障现象触发完整调试流程。
> **所有操作（包括 `/kzl` 命令）必须先执行下方的 Flow Gate 门禁预检。**
> 原始 Flow Gate 门禁机制保持不变，所有流程仍需遵循门禁规则。

---

## 📑 目录

| 章节 | 说明 | 位置 |
|------|------|------|
| 📋 待办事项管理规则 | 按三阶段模板生成 Todo List，严格匹配门禁步骤 | 本文件下方 |
| 🆕 新任务重置机制 | COMPLETED 后新任务自动重置 flow-gate.json | 本文件下方 |
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

## 📋 待办事项管理规则

### 待办事项模板（AI 必须严格按此模板生成）

每次创建待办事项时，必须严格按照以下模板，按顺序生成 `- [ ] 步骤名` 格式的列表。
**待办项名称必须与当前阶段门禁步骤的 description 保持一致**，不可自行编造。

```
■ 第一阶段：STARTUP（启动阶段）
  - [ ] Flow Gate 预检           ← 步骤0-4（读 registry → flow-gate.json）
  - [ ] 检查配置文件              ← STARTUP Step 1
  - [ ] 采集参数                  ← STARTUP Step 2（串口/下载器/故障描述）
  - [ ] 确认硬件                  ← STARTUP Step 2（用户确认就绪）
  └── 完成后 currentPhase → DEBUG_LOOP

■ 第二阶段：DEBUG_LOOP（调试循环，可多轮迭代，上限8轮）
  每轮迭代包含以下步骤：
  - [ ] 分析日志/定位代码          ← DEBUG_LOOP Step 1
  - [ ] 添加CHESHI调试打印         ← DEBUG_LOOP Step 2（可选）
  - [ ] 编译                      ← DEBUG_LOOP Step 3（用 keil_build.py）
  - [ ] 下载固件                  ← DEBUG_LOOP Step 4（用 keil_flash.py）
  - [ ] 串口监听+复位目标板        ← DEBUG_LOOP Step 5（用 serial_monitor.py）
  - [ ] 分析日志结果              ← DEBUG_LOOP Step 6
  └── 根因未找到 → 返回"分析日志/定位代码"开始下一轮
  └── 根因已找到 → currentPhase → VERIFY_AND_REPORT

■ 第三阶段：VERIFY_AND_REPORT（验证与报告）
  - [ ] 清理CHESHI宏              ← VERIFY Step 1
  - [ ] 修改业务代码修复           ← VERIFY Step 2
  - [ ] 下载验证                  ← VERIFY Step 3（build_and_flash.py + serial_monitor）
  - [ ] 回归验证                  ← VERIFY Step 4
  - [ ] 生成报告                  ← VERIFY Step 5
  └── 完成后 currentPhase → COMPLETED
```

### 执行规则

```
1. 创建时只列出**当前阶段及之后的待办项**
   例：在 STARTUP 阶段 → 列出 STARTUP + DEBUG_LOOP + VERIFY 的全部项

2. 每完成一项，立即用 manage_todo_list 标记为 [x]
   每开始一项，立即标记为 in-progress
   ⛔ 严禁一次性标记多个项为 completed

3. 待办项名称必须从模板中选用，如需新增必须与当前门禁步骤 description 一致
   例：在 Step 2 可能需要 "采集参数" 和 "确认硬件" 两个待办
   ✅ "[ ] 采集参数"    ← 正确，来自模板
   ❌ "[ ] 查看串口"    ← 错误，无此模板项
   ❌ "[ ] 分析代码"    ← 错误，模板中是"分析日志/定位代码"

4. 每轮 DEBUG_LOOP 迭代完成后，如果根因未找到：
   - flow-gate.json 中 iterationCount +1
   - 待办列表新增一轮 DEBUG_LOOP 项（从"分析日志/定位代码"重新开始）
   - 最多 8 轮，超限则等待用户指示

5. ⛔ 完整闭环铁律：
   每次 DEBUG_LOOP 迭代必须完整执行，不可中途停止：
   编译 → 下载 → 串口监听+复位 → 分析日志
   ├─ 缺少任何一环 = 流程违规
   ├─ 即使编译成功也不能跳过下载和串口验证
   └─ 即使"看起来修复了"也必须走完串口验证再进入下一轮

5. **⛔ 强制自动延续规则（阶段转换时不得中断）**
   ```
   根因找到（rootCauseFound=true）后，AI 必须立即自动执行以下操作，
   不得停顿、不得向用户展示阶段性成果、不得等待用户确认：
   
   ├─ 1. 更新 flow-gate.json → currentPhase=VERIFY_AND_REPORT
   ├─ 2. 读取 gates/VERIFY_AND_REPORT.yaml
   ├─ 3. 立即执行 VERIFY Step 1（清理CHESHI）  ← 不中断
   ├─ 4. 按顺序执行 VERIFY Step 2~5 直至 COMPLETED
   └─ 唯一的合法暂停：终端命令（编译/下载/串口）等待输出时
   
   同理，从 STARTUP 进入 DEBUG_LOOP 时也必须自动延续。
   ```
```

---

## 🆕 新任务重置机制

### 什么时候需要重置

当以下条件**同时满足**时，表示这是一个**新调试任务**，需要重置 flow-gate.json：

1. `flow-gate.json` 中的 `currentPhase` 为 `COMPLETED`
2. 用户描述的故障现象**不同于** `debugSession.faultSummary` 中记录的内容

### 重置规则

```
满足重置条件 → AI 自动执行以下操作：

1. 读取当前 flow-gate.json，保留项目路径等基本信息
2. 将以下字段重置为 STARTUP 初始状态：
   ├─ currentPhase: "STARTUP"
   ├─ completedPhases: []
   ├─ currentGateFile: "gates/STARTUP.yaml"
   ├─ debugLoopInfo.iterationCount: 0
   ├─ debugLoopInfo.cheshiAdded: false
   ├─ debugLoopInfo.lastBuildStatus: null
   ├─ debugLoopInfo.lastFlashStatus: null
   ├─ debugLoopInfo.rootCauseFound: false
   ├─ debugSession.startTime: 当前时间
   ├─ debugSession.endTime: null
   ├─ debugSession.faultSummary: 用户描述的新故障
   ├─ debugSession.reportFile: ""
   └─ debugSession.memorySaved: false
3. 写入 .copilot/flow-gate.json
4. 按"待办事项模板"创建待办列表（从 STARTUP 阶段开始全部列出）
5. 第一条"Flow Gate 预检"标记为 in-progress → 开始执行
```

### 不重置的情况

如果 `currentPhase = COMPLETED` 但用户描述的是**同一故障的延续**（相同的 faultSummary），则无需重置，直接进入 DEBUG_LOOP 继续迭代。

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

步骤 4: 先更新状态，再执行操作（无条件执行，无论用户打开什么文件）
  ├─ 每次执行任何操作前 → 先更新 flow-gate.json
  │  中的 currentPhase 和当前步骤状态
  ├─ 每次操作完成后 → 再次更新 flow-gate.json 记录结果
  ├─ 必须严格按照门禁文件中的 Step 1..N 顺序执行完整闭环
  │  编译 → 下载 → 串口监听 → 分析 → 下一轮迭代
  │  ⛔ 禁止在任意一环停下
  ├─ 严禁跳过中间步骤
  └─ 每完成一步，立即更新 .copilot/flow-gate.json 对应字段

  ⛔ 特别禁止：
    ├─ 禁止直接调用 UV4.exe / keil_flash.py 下载固件
    ├─ 必须经过 step_flash 门禁（含 flashRetryCount 强制检查）
    └─ 每次下载前必须读 flow-gate.json 检查 flashRetryCount
       └─ flashRetryCount ≥ 2 → 禁止下载，直接结束流程
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
