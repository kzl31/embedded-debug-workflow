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

流程定义集中在单一文件 **`flow.yaml`**（线性序号步骤表），引擎逻辑位于 `scripts/engine/` 包（查表 + 序号跳转解析器，零硬编码步骤），`scripts/workflow_engine.py` 仅作为 CLI 入口转发到该包。引擎按单一职责拆分为如下模块，全部文件均可在 `scripts/engine/` 下查看：

| 模块文件 | 职责 |
|:---|:---|
| `engine/__init__.py` | 包导出，对外暴露 `WorkflowEngine` 与 `main` |
| `engine/constants.py` | 引擎常量与路径（Skill 目录推导、`flow.yaml` 路径、动作类型分类 AUTO/AI/TERMINATE、状态加密密钥） |
| `engine/utils.py` | 纯工具函数：JSON/YAML 读取、模板路径替换、时间/值解析、XOR+base64 轻量加密解密、配置内容指纹 |
| `engine/state.py` | 流程状态 `flow-gate.json` 读写与默认结构：路径推导、进度展示开关、加密读 / 原子写 / 并发保护 |
| `engine/conditions.py` | 条件求值与状态写入：点号路径读取、AI 参数占位符展开、条件表达式比较、状态字段写入/自增 |
| `engine/executors.py` | 具体执行器：定位脚本绝对路径、运行外部 Python 脚本并回收逐项目结果、检查文件存在性 |
| `engine/auto_steps.py` | 自动步骤驱动与流向控制：链式推进、单步执行（断言→动作→分支）、动作分发、goto/exit/wait/log 原语 |
| `engine/ai_instructions.py` | AI 步骤指令与终止态：生成 AI 工作指令、最小进度展示载荷、暂停态/完成态输出 |
| `engine/config_sync.py` | 配置与项目模式同步：响应 `--set`、重载校验配置、按逐项目模式生成运行状态、派生执行能力 |
| `engine/core.py` | 引擎核心：加载 `flow.yaml`/`flow-gate`、基础查询、序号推进、对外主入口 `run/ack/wake/show_status/reset/init`、统一结果构造 |
| `engine/workflow.py` | `WorkflowEngine` 组合类：多继承聚合各 Mixin，对外接口与行为与原单文件引擎完全一致 |
| `engine/cli.py` | 命令行入口 `argparse`/`main`：`--init/--mode/--ack/--wake/--reset/--set/--reload-config`，行为与原引擎完全一致 |
运行参数和工作区文件路径集中在 `scripts/skill-config.json`，Python 通过
`scripts/path_config.py` 统一读取，避免多个脚本重复拼接路径。

## 🎯 适用场景

| 场景 | 说明 |
|:---|:---|
| 有线通信协议异常 | Modbus/CAN/SPI/TTL 通信故障 |
| 数据解析错误 | 长度/偏移/CRC校验失效 |
| 状态机异常 | 卡状态、跳转逻辑错误 |
| 基础外设驱动问题 | Flash/传感器读取超时 |

## 📥 安装

本仓库只包含一个 Skill，公开地址统一使用：

<https://github.com/kzl31/embedded-debug-workflow>

需要 Node.js 和 `npx`。以下命令均为**全局、免确认安装**，可以直接复制执行。

### GitHub Copilot

```powershell
npx skills add https://github.com/kzl31/embedded-debug-workflow --skill embedded-debug-workflow --agent github-copilot --global --yes
```

安装到 GitHub Copilot 的全局 Skills 目录。

### Claude Code

```powershell
npx skills add https://github.com/kzl31/embedded-debug-workflow --skill embedded-debug-workflow --agent claude-code --global --yes
```

安装到 Claude Code 的全局 Skills 目录。

### Codex

```powershell
npx skills add https://github.com/kzl31/embedded-debug-workflow --skill embedded-debug-workflow --agent codex --global --yes
```

安装到 Codex 的全局 Skills 目录。

### Cursor

```powershell
npx skills add https://github.com/kzl31/embedded-debug-workflow --skill embedded-debug-workflow --agent cursor --global --yes
```

安装到 Cursor 的全局 Skills 目录。

### 常用管理命令

查看已安装的全局 Skill：

```powershell
npx skills list --global
```

更新全部全局 Skill：

```powershell
npx skills update --global --yes
```

卸载本 Skill：

```powershell
npx skills remove embedded-debug-workflow --global --yes
```

安装完成后，重新加载对应 Agent 或重启编辑器。如果自动检测不到 Agent，可确认命令中的
`--agent` 名称与上述示例完全一致。

## 📁 目录结构

```
embedded-debug-workflow/
├── README.md              # 本文件
├── SKILL.md               # AI 核心入口（触发条件、执行边界和文档路由）
├── flow.yaml              # 🔑 流程唯一真相源（线性序号步骤表，含 phase 分组）
├── commands/              # /kzl 快捷命令入口
│   ├── help.md            #   /kzl 帮助（帮助）
│   ├── init.md            #   /kzl 初始化（初始化配置）
│   ├── build.md           #   /kzl 编译（仅编译）/ /kzl 编译下载（编译下载）
│   ├── print.md           #   /kzl 打印（按 CHESHI 规范独立添加调试打印）
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
│   ├── path_config.py     #   集中路径和运行参数接口
│   ├── skill-config.json  #   可变路径、默认值和超时的唯一配置源
│   ├── engine/            #   🔑 流程引擎模块化实现（查表 + 序号跳转，零硬编码步骤）
│   │   ├── __init__.py    #   包导出（暴露 WorkflowEngine、main）
│   │   ├── constants.py   #   引擎常量与路径、动作类型分类、加密密钥
│   │   ├── utils.py       #   纯工具函数（IO / 加密 / 解析 / 指纹）
│   │   ├── state.py       #   流程状态 flow-gate 读写与默认结构
│   │   ├── conditions.py  #   条件求值与状态写入
│   │   ├── executors.py   #   外部脚本与文件检查执行器
│   │   ├── auto_steps.py  #   自动步骤驱动与流向控制
│   │   ├── ai_instructions.py # AI 步骤指令与终止态
│   │   ├── config_sync.py #   配置与项目模式同步
│   │   ├── core.py        #   初始化 / 查询 / 主入口 / 结果构造
│   │   ├── workflow.py    #   WorkflowEngine 组合类（聚合各 Mixin）
│   │   └── cli.py         #   argparse 入口 main()
│   └── workflow_engine.py #   引擎 CLI 入口（转发到 engine/ 包）
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
│   ├── runtime-config.md  #   集中运行配置规则
│   └── workflow-diagram.md#   完整流程图（交互模式 + 序号流程）
├── templates/             # 模板文件
│   ├── checklist.md       #   迭代检查清单（含验证方法与常见问题速查）
│   ├── report.md          #   故障报告模板
│   ├── flow-gate.json     #   状态文件模板（currentSeq 等）
│   └── cheshi_snippet.c   #   CHESHI 宏代码模板
└── data/                  # Skill 自身的历史索引（自动生成/按配置使用）
    └── debug-history.yaml #   调试历史索引
```

### 工作区文件位置

工作区级配置、流程状态、编译/下载/串口日志和报告不写入 Skill 仓库目录，
实际位置由 `scripts/skill-config.json` 的 `paths` 配置和
`scripts/path_config.py` 解析。默认使用工作区下的 Skill 专属数据目录：

- 配置：`embedded-debug-config.json`
- 加密状态：`flow-gate.json`
- 项目日志：`build_log_p<下标>_<项目名>.txt`、`flash_log_p<下标>_<项目名>.txt`、
  `debug_log_p<下标>_<项目名>.txt`、`verify_log_p<下标>_<项目名>.txt`
- 报告：工作区 Skill 专属报告目录

修改工作区目录名、日志目录名、报告目录名或状态文件名时，只修改
`scripts/skill-config.json`，不要在 Python、YAML 或 Markdown 中重复拼接路径。

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

Skill 激活后，先初始化当前 VS Code 工作区，再由流程引擎按 `flow.yaml` 推进。AI 只执行引擎明确交给
AI 的故障采集、源码调整、证据分析、回归核对和报告整理；编译、下载、状态更新和流程跳转由引擎完成。
完整的 AI 行为规则见 `SKILL.md` 和 `refs/core-rules.md`，具体命令见 `commands/init.md` 与
`refs/script-commands.md`。

> `/kzl 初始化` 每次都会递归扫描当前工作区的 Keil 工程并显示结果。已有配置会保留人工参数并增量追加新工程；Keil、串口和下载器使用通用默认值。也可使用 `config_reader.py --scan <工作区>` 只查看扫描结果而不修改配置。路径由 `skill-config.json` 集中解析。
> 所有流程逻辑（步骤顺序、跳转、条件）都写在 `flow.yaml`，引擎只是按 `seq` 查表执行。

### 独立快捷命令

`/kzl 初始化`、`/kzl 编译`、`/kzl 编译下载`、`/kzl 打印`、`/kzl 报告` 与调试流程相互独立，
不运行或推进 `workflow_engine.py`。其中编译命令只直接调用 Python 脚本；配置不存在时
提示先执行 `/kzl 初始化`，不会自行初始化。独立命令可为后续流程准备配置、调试观测点和固件。

`/kzl 报告 [标题/要求]` 会基于当前可见对话及实际工具输出生成包含完整排查过程、证据链、
修复原理、验证边界和回归风险的详细 Markdown 报告，并同步更新集中配置定义的历史索引
与持久记忆。缺失信息会标记为“未提供”或“未验证”，不会补造结论。

### 典型调试流程

`STARTUP` 负责配置和故障信息采集，`DEBUG_LOOP` 负责观测、验证和根因收敛，
`VERIFY_AND_REPORT` 负责清理临时代码、回归验证和报告输出。具体步骤和分支以 `flow.yaml` 为准，
不要在 README 中维护步骤编号。

## 📝 规范要点

- **CHESHI 宏**：Bit 位掩码或数值分级；并非每轮都必须插入调试日志，只有当 AI 判断当前阶段、故障类型和可观测性确实值得引入新证据时才加观测点。凡调试结束需删除的依赖、声明、变量、参数、辅助实现及调用路径均完整受 CHESHI 包裹，不得只包裹打印；通信层仅采集快照，main 主循环统一输出，结束时整段删除并恢复临时工程配置
- **Git 管控**：仅本地操作，禁止 git push；调试分支命名 `debug/故障简述_YYYYMMDD`
- **8 轮上限**：自动加打印满 8 轮仍无法定位 → 触发人工求助（`wait_user`）
- **三类暂停**：设备断电重启 / Keil 断点调试 / 迭代上限求助


## 📄 报告模板

故障解决后自动输出标准化报告，包含问题描述、根因分析、修改文件清单、验证结果和影响范围。

