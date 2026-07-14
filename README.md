# 嵌入式固件调试工作流 Skill

> 一个面向嵌入式开发的自动化调试助手 Skill，基于 VS Code Copilot Agent 实现（当然这个可以在其他Agent中使用）。

<p align="center">
  <a href="README_EN.md"><strong>🇺🇸 English README</strong></a>
</p>

## 📖 概述

本 Skill 定义了一套完整的嵌入式固件调试自动化工作流，覆盖从问题发现到标准化报告输出的全链路：

```
问题发现 → 故障分类诊断 → CHESHI调试打印迭代 → 自动编译下载
→ 串口日志解析 → 业务代码修复 → 回归验证 → 标准化报告
```

流程定义集中在单一文件 **`flow.yaml`**（线性序号步骤表），引擎 `workflow_engine.py` 是零硬编码的纯查表+序号跳转解析器。

## 🎯 适用场景

| 场景 | 说明 |
|:---|:---|
| 有线通信协议异常 | Modbus/CAN/SPI/TTL 通信故障 |
| 数据解析错误 | 长度/偏移/CRC校验失效 |
| 状态机异常 | 卡状态、跳转逻辑错误 |
| 基础外设驱动问题 | Flash/传感器读取超时 |

## 📁 目录结构

```
embedded-debug-workflow/
├── README.md              # 本文件
├── SKILL.md               # AI 核心入口（铁律 + 引擎调用方式 + flow.yaml 格式速查）
├── flow.yaml              # 🔑 流程唯一真相源（线性序号步骤表，含 phase 分组）
├── commands/              # /kzl 快捷命令入口
│   ├── help.md            #   /kzl 帮助（帮助）
│   ├── init.md            #   /kzl 初始化（初始化配置）
│   ├── build.md           #   /kzl 编译（仅编译）/ /kzl 编译下载（编译下载）
│   └── add-flow.md        #   /kzl 新增流程（新增步骤/阶段 → 编辑 flow.yaml）
├── scripts/               # Python 自动化脚本
│   ├── config_reader.py   #   配置文件读写 (Python)
│   ├── keil_build.py      #   Keil 编译 (Python)
│   ├── keil_flash.py      #   固件下载 (Python)
│   ├── build_and_flash.py #   一键编译+下载 (Python)
│   ├── serial_read.py     #   串口单次读取 (Python)
│   ├── serial_monitor.py  #   串口持续监听 (Python)
│   ├── batch_build.py     #   多工程批量操作 (Python)
│   ├── multi_project_runner.py # 按逐项目模式执行编译/下载/串口监听
│   └── workflow_engine.py #   🔑 流程引擎（查表 + 序号跳转，零硬编码步骤）
├── refs/                  # AI 按需加载的详细规范
│   ├── core-rules.md      #   强制规则（AI 行为约束）
│   ├── script-commands.md #   脚本命令参考
│   ├── config-format.md   #   配置文件格式说明
│   ├── debug-loop.md      #   核心调试循环（8轮迭代）
│   ├── git-rules.md       #   Git 本地版本管理
│   ├── cheshi-macro.md    #   CHESHI 宏规范（含 ISR 安全打印）
│   ├── pause-scenarios.md #   人工暂停规范
│   ├── common-faults.md   #   常见故障速查 & JLink/Map 分析
│   ├── add-flow-guide.md  #   新增步骤/阶段指南（编辑 flow.yaml）
│   └── workflow-diagram.md#   完整流程图（交互模式 + 序号流程）
├── templates/             # 模板文件
│   ├── checklist.md       #   迭代检查清单（含验证方法与常见问题速查）
│   ├── report.md          #   故障报告模板
│   ├── abort-report.md    #   🛑 流程违规退出标准格式
│   ├── flow-gate.json     #   状态文件模板（currentSeq 等）
│   └── cheshi_snippet.c   #   CHESHI 宏代码模板
└── data/                  # 运行时数据（自动生成）
    └── debug-history.yaml #   调试历史索引
```

## 🔧 环境要求

| 依赖 | 说明 |
|:---|:---|
| **Python 3.8+** | 运行 Python 自动化脚本（推荐） |
| **pyserial**（Python 用） | 串口通信（`pip install pyserial`） |
| **PyYAML**（Python 用） | 解析 `flow.yaml`（`pip install pyyaml`） |
| **Keil MDK** | ARM 编译环境（UV4.exe，路径固定为 `C:\Keil_v5\UV4\UV4.exe`） |
| **J-Link / ST-Link** | 调试下载器 |

## 🚀 快速开始

### 启动初始化流程

Skill 激活后，AI 按以下模式驱动引擎（**唯一流程入口**）：

```
① 新对话 → 运行引擎 --init 初始化状态，不询问用户
② 若配置不存在，固定在工作区 .copilot 下生成两个带通用默认值的项目配置
③ 读取配置中的实际 projects 数组，逐项目询问独立模式（编译下载/仅编译/不执行）
④ 运行引擎 --mode 0 读取当前状态（当前 seq / phase / 待办）
⑤ 运行引擎 --mode 1 执行/推进当前步骤：
   - 自动步骤（run_script/check_file/...）：引擎直接执行并按 flow.yaml 的
     on_success / on_failure 自动跳转，直到遇到 AI 步骤或完成
   - AI 步骤（ask_user/edit_source/analyze/report/...）：引擎输出指令（status=awaiting_ai），
     AI 执行后提交 --ack success（或 --ack failure）
   - 人工暂停（wait_user）：status=awaiting_user，处理完 --wake 恢复
⑥ 重复 ④~⑤，直至 status=completed
```

> 初始化不扫描工作区；生成 Keil、串口和下载器通用默认值，工程路径及实际端口由用户编辑配置文件。
> 所有流程逻辑（步骤顺序、跳转、条件）都写在 `flow.yaml`，引擎只是按 `seq` 查表执行。

### 典型调试流程

```
1. STARTUP 自动确保双项目默认配置存在，全程不询问
2. AI 读取 embedded-debug-config.json，以 projects 数组为唯一项目列表，并逐项目询问执行模式
3. AI 注入 CHESHI 调试宏，自动编译下载并抓取日志（seq 5~9）
4. AI 分析日志并迭代定位根因（seq 10，必要时回到 seq 6）
5. 定位根因后先修复业务代码，保留 CHESHI 观测点
6. 重新编译下载并持续读取串口日志，确认故障彻底解决；失败则退回调试循环
7. 确认成功后清理 CHESHI，再编译、回归验证并输出报告
```

## 📝 规范要点

- **CHESHI 宏**：Bit 位掩码或数值分级，所有调试内容受 CHESHI 包裹；通信层仅采集快照，main 主循环统一输出，调试结束整段删除
- **Git 管控**：仅本地操作，禁止 git push；调试分支命名 `debug/故障简述_YYYYMMDD`
- **8 轮上限**：自动加打印满 8 轮仍无法定位 → 触发人工求助（`wait_user`）
- **三类暂停**：设备断电重启 / Keil 断点调试 / 迭代上限求助

## 🛑 流程违规退出

由 **AI 在对话中自行判定**：只要发现当前情形不符合流程（用户强制跳过步骤、要求阶段禁止的操作、
未初始化就操作、跳跃步骤、直接读状态文件等），AI 必须**立即退出执行**，并输出标准格式中止通告。

- **判定方是 AI 自己，不依赖脚本**：AI 在对话中识别违规情形（含用户要求跳过流程），随即停止一切后续动作。
- **违规即退出执行**：AI 立即停止编译/下载/分析/读状态文件/报告等所有操作，按 `templates/abort-report.md`
  的**标准格式**输出 `⛔ 流程中止通告（FLOW ABORT）`，等待用户重新 `--init`。
- 违规类型（AI 据情形自行选填）：`user_skip_step` / `user_forbidden_op` / `not_initialized` /
  `out_of_order` / `read_state_file` / `phase_mismatch`。

## 📄 报告模板

故障解决后自动输出标准化报告，包含问题描述、根因分析、修改文件清单、验证结果和影响范围。

