# 脚本一键执行（AI 自动调用）

使用 Python 运行自动化脚本：

```bash
# ── 常用示例 ──

# 增量编译（默认，只编译当前文档所属项目中修改过的文件）
python scripts/keil_build.py --project "RU3.uvprojx"

# 全编译（首次调试或宏变化时使用）
python scripts/keil_build.py --project "RU3.uvprojx" --rebuild

# 编译+下载（仅在用户明确确认 full 模式后使用；自动先增量编译，成功后下载）
python scripts/build_and_flash.py

# 按逐项目模式执行编译/下载/串口（flow.yaml 主力脚本，多工程）
python scripts/multi_project_runner.py --action build  --config-dir "<工作区>" --modes "full,compile_only"
python scripts/multi_project_runner.py --action serial --config-dir "<工作区>" --modes "full,none" --delay 10 --duration 30 --save "debug_log.txt"
```

> `--save` 是基础文件名；日志目录和项目后缀由集中配置及 `path_config.py` 自动生成。

## 脚本索引

| 脚本 | 用途 | 依赖 |
|------|------|------|
| `scripts/config_reader.py` | 读取/校验/初始化配置，逐项目模式选择 | 无 |
| `scripts/multi_project_runner.py` | 按逐项目模式批量执行编译/下载/串口（flow.yaml 主力） | pyserial（serial 动作） |
| `scripts/keil_build.py` | Keil 编译（单工程） | 无 |
| `scripts/keil_flash.py` | Keil 下载固件（单工程） | 无 |
| `scripts/build_and_flash.py` | 一键编译+下载（单工程） | 无 |
| `scripts/batch_build.py` | 多工程批量编译下载 | 无 |
| `scripts/serial_read.py` | 串口单次读取 | pyserial |
| `scripts/serial_monitor.py` | 串口持续监听 | pyserial |
| `scripts/remove_cheshi.py` | 清理本次调试新增的全部 CHESHI 临时代码（flow.yaml seq17 调用） | 无 |
| `scripts/regression_check.py` | 回归核对清单：编译/下载/验证日志与 CHESHI 残留检查（flow.yaml seq19 调用） | 无 |

## 各脚本参数

### `config_reader.py`（配置管理）

| 参数 | 说明 |
|------|------|
| `--init <工作区目录>` | 扫描工作区并生成/增量更新 Keil 工程配置 |
| `--interactive` | 初始化后用数字选项确认配置并逐项目选择执行模式 |
| `--scan <工作区目录>` | 只扫描并输出 Keil 工程，不修改配置 |
| `--read` | 读取并打印当前配置（默认行为） |
| `--validate` | 校验配置完整性 |
| `--get {keil,serial,projects,debugger}` | 获取指定字段值（JSON 输出） |
| `--set-port COMx` | 快速修改指定工程的串口号 |
| `--set-baud <波特率>` | 快速修改指定工程的波特率 |
| `--project-index <N>` | 指定工程下标（多工程时用，默认 0） |
| `--path <文件>` | 指定配置文件路径（默认自动查找） |
| `--project-count <N>` | 兼容旧调用，初始化时忽略 |

### `multi_project_runner.py`（逐项目批量执行）

| 参数 | 说明 |
|------|------|
| `--action {build,flash,serial}` | **必填**，执行的动作 |
| `--config-dir <路径>` | **必填**，工作区或配置文件路径 |
| `--modes <逗号分隔>` | **必填**，与 projects 顺序一致的逐项目模式（如 `full,compile_only,none`） |
| `--stage <标识>` | 写入逐项目状态时使用的流程阶段标识（默认取 action 名） |
| `--duration <秒>` | 串口监听时长，默认 30 |
| `--delay <秒>` | 串口监听开始前的等待时间，默认 0（不等待） |
| `--save <路径>` | 串口日志基础路径；多项目自动附加项目标识 |

### `keil_build.py`（单工程编译）

| 参数 | 说明 |
|------|------|
| `--project <文件>` | 工程文件名（默认读取配置第一个工程） |
| `--dir <目录>` | 工程目录（默认读取配置） |
| `--target <名称>` | 指定 Target 名称 |
| `--rebuild` | 重新编译（Clean + Build） |
| `--log <路径>` | 编译日志保存路径 |
| `--find-uv4` | 仅探测 UV4 路径并退出 |
| `--config-dir <目录>` | 配置文件所在目录（默认自动查找） |
| `--project-index <N>` | 指定工程下标（默认 0） |

### `keil_flash.py`（单工程下载）

| 参数 | 说明 |
|------|------|
| `--project <文件>` | 工程文件名（默认读取配置第一个工程） |
| `--dir <目录>` | 工程目录（默认读取配置） |
| `--log <路径>` | 下载日志保存路径 |
| `--config-dir <目录>` | 配置文件所在目录（默认自动查找） |
| `--project-index <N>` | 指定工程下标（默认 0） |

### `build_and_flash.py`（一键编译+下载）

| 参数 | 说明 |
|------|------|
| `--project <文件>` | 工程文件名 |
| `--dir <目录>` | 工程目录 |
| `--target <名称>` | 指定 Target 名称 |
| `--rebuild` | 先 Clean 再编译 |
| `--skip-build` | 跳过编译，直接下载已有固件 |
| `--skip-flash` | 只编译，不下载 |
| `--build-log <路径>` | 编译日志路径 |
| `--flash-log <路径>` | 下载日志路径 |
| `--config-dir <目录>` | 配置文件所在目录（默认自动查找） |
| `--project-index <N>` | 指定工程下标（默认 0） |

### `batch_build.py`（多工程批量）

| 参数 | 说明 |
|------|------|
| `--build-only` | 仅编译，不下载 |
| `--flash-only` | 仅下载，不编译 |
| `--index <N>` | 仅处理指定索引的工程（从 0 开始） |
| `--target <名称>` | 指定 Target 名称 |
| `--config-dir <目录>` | 配置文件所在目录（默认自动查找） |

### `serial_read.py`（串口单次读取）

| 参数 | 说明 |
|------|------|
| `--port <COMx>` | 串口号（默认读取配置） |
| `--baud <波特率>` | 波特率（默认读取配置） |
| `--data-bits <N>` | 数据位，默认 8 |
| `--stop-bits <N>` | 停止位，默认 1 |
| `--parity <值>` | 校验位，默认 None |
| `--timeout <秒>` | 读取超时，默认 3 |
| `--config-dir <目录>` | 配置文件所在目录（默认自动查找） |

### `serial_monitor.py`（串口持续监听）

| 参数 | 说明 |
|------|------|
| `--port <COMx>` | 串口号（默认读取配置） |
| `--baud <波特率>` | 波特率（默认读取配置） |
| `--data-bits <N>` | 数据位，默认 8 |
| `--stop-bits <N>` | 停止位，默认 1 |
| `--parity <值>` | 校验位，默认 None |
| `--duration <秒>` | 监听时长，默认 10 |
| `--continuous` | 持续监听模式 |
| `--save <路径>` | 日志保存路径 |
| `--wait <关键字>` | 等待关键字后停止 |
| `--config-dir <目录>` | 配置文件所在目录（默认自动查找） |
| `--project-index <N>` | 指定工程下标 |
| `--project-dir <目录>` | 指定工程目录，用于匹配对应工程的串口参数 |

### `remove_cheshi.py`（CHESHI 临时代码清理）

| 参数 | 说明 |
|------|------|
| `--config-dir <路径>` | **必填**，工作区或配置文件路径；脚本据此读取各工程源码目录，扫描并移除 CHESHI 条件编译块、宏定义与横幅注释，清理前自动 `git commit` 建立回退基线 |

### `regression_check.py`（回归核对清单）

| 参数 | 说明 |
|------|------|
| `--config-dir <路径>` | **必填**，工作区或配置文件路径；脚本据此读取配置与各工程日志，做确定性检查（配置完整性、构建 0 Error、下载成功标志、验证日志生成、CHESHI 无残留），并输出需 AI 复核项 |
