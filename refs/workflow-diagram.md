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
    subgraph STARTUP["■ STARTUP 阶段 (seq 1~3)"]
        S1["seq1 step_check_config
            action: check_file
            检查 embedded-debug-config.json"]
        S1 --> S1C{"存在?"}
        S1C -->|✅| S1OK["on_success: read_config
            → goto 2"]
        S1C -->|❌| S1M["on_failure: config_reader --init
            → goto 2"]
        S1OK --> S2
        S1M --> S2
        S2["seq2 step_collect_params
            action: ask_user
            采集故障现象 + 确认工程配置"]
        S2 --> S2D["AI 提问 → --ack success
            → goto 3"]
        S2D --> S3["seq3 step_to_debug
            action: noop → goto 4"]
    end
    S3 --> D4

    subgraph DEBUG_LOOP["■ DEBUG_LOOP 阶段 (seq 4~9)"]
        D4["seq4 step_analyze
            action: analyze (locate)"]
        D4 --> D5["seq5 step_add_cheshi
            action: edit_source (insert_cheshi)"]
        D5 --> D6["seq6 step_compile
            action: run_script (keil_build.py)"]
        D6 --> D6C{"编译?"}
        D6C -->|✅| D6S["goto 7"]
        D6C -->|❌| D6F["goto 5 🔄"]
        D6S --> D7["seq7 step_flash
            action: run_script (keil_flash.py)
            precheck: retryCount<2, buildMode==full"]
        D7 --> D7C{"下载?"}
        D7C -->|✅| D7S["retryCount=0 → goto 8"]
        D7C -->|❌ retry<2| D7F["goto 7 🔄"]
        D7C -->|❌ retry≥2| D7B["exit → COMPLETED ⛔"]
        D7S --> D8["seq8 step_capture_log
            action: run_script (serial_monitor.py)
            precheck: retryCount<2"]
        D8 --> D8C{"串口?"}
        D8C -->|✅| D8S["retryCount=0 → goto 9"]
        D8C -->|❌ retry<2| D8F["goto 8 🔄"]
        D8C -->|❌ retry≥2| D8B["exit → COMPLETED ⛔"]
        D8S --> D9["seq9 step_analyze_result
            action: analyze (root_cause)"]
        D9 --> D9C{"根因找到?"}
        D9C -->|✅| D9F["goto 10"]
        D9C -->|❌| D9I{"迭代<8?"}
        D9I -->|✅| D9R["iterationCount++ → goto 5 🔄"]
        D9I -->|❌| D9W["wait_user → --wake 回到 seq9"]
    end
    D9F --> V10

    subgraph VERIFY["■ VERIFY_AND_REPORT 阶段 (seq 10~16)"]
        V10["seq10 step_clean_cheshi
            action: edit_source (remove_cheshi)"]
        V10 --> V11["seq11 step_fix_code
            action: edit_source (fix_bug)"]
        V11 --> V12["seq12 step_verify_build
            action: run_script (keil_build.py)
            precheck: buildMode!=none"]
        V12 --> V12C{"验证?"}
        V12C -->|✅| V12S["goto 13"]
        V12C -->|❌| V12F["goto 4 🔄 退回调试"]
        V12S --> V13["seq13 step_verify_flash
            action: run_script (keil_flash.py)
            precheck: buildMode==full"]
        V13 --> V13C{"验证?"}
        V13C -->|✅| V13S["goto 14"]
        V13C -->|❌| V13F["goto 4 🔄 退回调试"]
        V13S --> V14["seq14 step_regression
            action: check_regression"]
        V14 --> V15["seq15 step_report
            action: report → goto 16"]
        V15 --> V16["seq16 step_complete
            action: exit → COMPLETED ✅"]
    end
```

## 3. 整体阶段流转

```mermaid
stateDiagram-v2
    [*] --> STARTUP: --init
    STARTUP --> DEBUG_LOOP: seq3 衔接 (goto 4)
    DEBUG_LOOP --> VERIFY_AND_REPORT: seq9 找到根因 (goto 10)
    DEBUG_LOOP --> COMPLETED: 下载失败2次 / 串口失败2次
    VERIFY_AND_REPORT --> DEBUG_LOOP: 验证失败 (goto 4)
    VERIFY_AND_REPORT --> COMPLETED: seq16 完成

    COMPLETED --> STARTUP: --reset（新任务）
    COMPLETED --> STARTUP: --init（新对话）

    note right of DEBUG_LOOP
        最多 8 轮迭代
        每轮: 分析→CHESHI→编译→下载→串口→分析结果
    end note
```
