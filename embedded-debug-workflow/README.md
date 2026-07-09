# 嵌入式固件调试工作流 Skill

> 一个面向嵌入式开发的自动化调试助手 Skill，基于 VS Code Copilot Agent 实现。

## 📖 概述

本 Skill 定义了一套完整的嵌入式固件调试自动化工作流，覆盖从问题发现到标准化报告输出的全链路：

```
问题发现 → 故障分类诊断 → CHESHI调试打印迭代 → 自动编译下载 
→ 串口日志解析 → 业务代码修复 → 回归验证 → 标准化报告
```

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
├── SKILL.md               # AI 核心入口（精简：元数据 + 目录索引 + Flow Gate 预检）
├── registry.json           # 🔑 阶段注册中心（唯一权威：阶段名→门禁文件映射）
├── gates/                 # Flow Gate 门禁文件（结构化的 YAML 步骤）
│   ├── FLOW_GATE_RULES.md #   门禁总规则（引用 registry，不硬编码）
│   ├── STARTUP.yaml       #   启动阶段（采集故障现象+确认工程配置）
│   ├── DEBUG_LOOP.yaml    #   调试循环（8轮迭代）
│   └── VERIFY_AND_REPORT.yaml # 验证与报告阶段（末步自动生成报告+写记忆）
├── commands/              # /kzl 快捷命令入口
│   ├── help.md            #   /kzl bz（帮助）
│   ├── init.md            #   /kzl csh（初始化）
│   ├── build.md           #   /kzl by（仅编译）/ /kzl byxz（编译下载）
│   └── add-flow.md        #   /kzl zjlc（增加流程）
├── scripts/               # Python 自动化脚本
│   ├── skill-config.json  #   脚本默认配置（Keil路径/串口/JLink参数）
│   ├── config_reader.py   #   配置文件读写 (Python)
│   ├── keil_build.py      #   Keil 编译 (Python)
│   ├── keil_flash.py      #   固件下载 (Python)
│   ├── build_and_flash.py #   一键编译+下载 (Python)
│   ├── serial_read.py     #   串口单次读取 (Python)
│   ├── serial_monitor.py  #   串口持续监听 (Python)
│   ├── batch_build.py     #   多工程批量操作 (Python)
│   └── workflow_engine.py #   流程引擎（纯解析器）
├── refs/                 # AI 按需加载的详细规范
│   ├── core-rules.md      #   5 条强制规则
│   ├── script-commands.md #   脚本命令参考
│   ├── config-format.md   #   配置文件格式说明
│   ├── debug-loop.md      #   核心调试循环（8轮迭代）
│   ├── git-rules.md       #   Git 本地版本管理
│   ├── cheshi-macro.md    #   CHESHI 宏规范（含 ISR 安全打印）
│   ├── pause-scenarios.md #   人工暂停规范
│   ├── common-faults.md   #   常见故障速查 & JLink/Map 分析
│   └── add-flow-guide.md  #   新增步骤/阶段指南
├── templates/             # 模板文件
│   ├── checklist.md       #   迭代检查清单（含验证方法与常见问题速查）
│   ├── report.md          #   故障报告模板
│   ├── abort-report.md    #   🛑 流程违规退出标准格式
│   └── cheshi_snippet.c   #   CHESHI 宏代码模板
└── data/                 # 运行时数据（自动生成）
    └── debug-history.yaml #   调试历史索引
```

## 🔧 环境要求

| 依赖 | 说明 |
|:---|:---|
| **Python 3.8+** | 运行 Python 自动化脚本（推荐） |
| **pyserial**（Python 用） | 串口通信（`pip install pyserial`） |
| **Keil MDK** | ARM 编译环境（UV4.exe，路径固定为 `C:\Keil_v5\UV4\UV4.exe`） |
| **J-Link / ST-Link** | 调试下载器 |

## 🚀 快速开始

### 启动初始化流程

Skill 激活后，AI 自动执行 Flow Gate 门禁流程：

```
① 运行引擎（--mode 0）读取当前状态 → 检查 currentPhase
   ├─ STARTUP     → 读取 gates/STARTUP.yaml，采集故障现象并确认工程配置
   ├─ DEBUG_LOOP  → 读取 gates/DEBUG_LOOP.yaml，进入调试循环
   ├─ VERIFY_...  → 读取 gates/VERIFY_AND_REPORT.yaml，验证与报告
   └─ COMPLETED   → 允许重新开始
② 若无 embedded-debug-config.json → 自动执行 --init 初始化
③ 按门禁文件 Step 1..N 顺序执行，引擎自动维护内部状态
```

> `uv4_path`（`C:\Keil_v5\UV4\UV4.exe`）为固定系统路径，自动填入，不询问用户。

### 典型调试流程

```
1. AI 读取 data/config.json 获取环境参数
2. STARTUP 阶段采集故障现象并确认工程配置
3. AI 注入 CHESHI 调试宏，自动编译下载
4. AI 抓取串口日志，迭代分析
5. 定位根因后修复业务代码
6. 回归验证，输出报告


```

## 📝 规范要点

- **CHESHI 宏**：Bit 位掩码或数值分级，集中写在 main.c 头部，调试结束整段删除
- **Git 管控**：仅本地操作，禁止 git push；调试分支命名 `debug/故障简述_YYYYMMDD`
- **8 轮上限**：自动加打印满 8 轮仍无法定位 → 触发人工求助
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

## 🤝 参考

本 Skill 的蓝图来源于 `sad.md`（嵌入式固件调试工作流指南），架构参考了 `EM-SKILL` 和 `git-workflow` 的设计模式。
