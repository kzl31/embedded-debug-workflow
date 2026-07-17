# 嵌入式调试工作流 — 完整运行流程图

> 本文件描述 **AI 与引擎的交互模式** 与 **flow.yaml 的三大阶段序号流程**。
> 所有步骤、跳转、条件都在 `flow.yaml` 中定义，引擎只是按 `seq` 查表执行。

## 1. AI 与引擎交互模式

```mermaid
flowchart TD
    Start(["新对话开始 👤"]) --> Step0["⚡ 第零步: --init
        python workflow_engine.py --init --project <dir>"]
    Step0 --> InitOk{"引擎返回
        status='initialized'?"}
    InitOk -->|✅ 是| Step1["🔍 读状态 / 执行:
        python ... --mode 0 (只读快照)
        python ... --mode 1 (执行当前步骤)"]
    InitOk -->|❌ 否| Step0

    Step1 --> RunOk{"--mode 1 返回 status?"}

    RunOk -->|"awaiting_ai"| AiDo["🤖 AI 按 what/params 执行
        (ask_user / edit_source / analyze / report / check_regression)
        完成后: python ... --ack success (或 --ack failure)"]
    AiDo --> Step1

    RunOk -->|"auto_pending"| AutoDone["⚙️ 引擎已自动执行
        (run_script / check_file / ...) 并按 on_success/on_failure 自动跳转"]
    AutoDone --> Step1

    RunOk -->|"awaiting_user"| Wait["⏸ 人工暂停 (wait_user)
        处理完: python ... --wake 恢复"]
    Wait --> Step1

    RunOk -->|"completed"| AllDone["✅ 全部完成
        → 使用 --reset 开始新任务"]
```

> 提示：`--done` 是 `--ack success` 的别名；自动步骤无需 `--ack`，引擎已自动推进。

## 2. 三大阶段序号流程（对应 flow.yaml）

```mermaid
flowchart TD
    S2["seq 2：逐项目询问模式<br/>AI 自动判断跳过参数"] --> Skip{"AI 判断执行意图"}
    Skip -->|两者都跳过| R19["seq 19：回归检查"]
    Skip -->|skipBuild| D8["seq 8：直接下载已有固件"]
    Skip -->|skipFlash| Mode{"项目聚合模式（仅编译）"}
    Skip -->|均不跳过| Mode
    Mode -->|none| D7["seq 7：跳过编译"]
    Mode -->|compile_only| D7
    Mode -->|compile_flash| D7
    Mode -->|full| D6["seq 6：添加 CHESHI 观测"]
    D6 --> D7

    D7 -->|none| R19["seq 19：回归检查"]
    D7 -->|compile_only 且编译成功| R19
    D7 -->|compile_flash/full 且编译成功| D8["seq 8：下载固件"]
    D8 -->|compile_flash 且下载成功| R19
    D8 -->|full 且下载成功| D9["seq 9：串口监听"]
    D9 --> D10["seq 10：分析监听结果"]

    R19 --> R20["seq 20：生成报告"]
    R20 --> R21["seq 21：完成"]
```

> 四种模式必须对 `projects` 中每一个项目分别询问，并分别确认全局参数 `skipBuild`、
> `skipFlash`。`none` 不编译不下载，
> `compile_only` 仅编译，`compile_flash` 编译下载但不监听，`full` 编译下载并监听。

## 3. 整体阶段流转

```mermaid
stateDiagram-v2
    [*] --> STARTUP: --init
    STARTUP --> DEBUG_LOOP: seq 4 衔接到 seq 5
    DEBUG_LOOP --> VERIFY_AND_REPORT: seq 7/8 按模式跳到 seq 19
    DEBUG_LOOP --> VERIFY_AND_REPORT: seq 10 找到根因后进入修复验证
    VERIFY_AND_REPORT --> DEBUG_LOOP: 验证失败回到 seq 5
    VERIFY_AND_REPORT --> COMPLETED: seq 21 完成

    COMPLETED --> STARTUP: --reset（新任务）
    COMPLETED --> STARTUP: --init（新对话）

    note right of DEBUG_LOOP
        最多 8 轮迭代
        full: 分析→CHESHI→编译→下载→监听→分析
        compile_flash: 编译→下载→回归
        compile_only: 编译→回归
        none: 直接回归
    end note
```
