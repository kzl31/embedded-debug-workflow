# 常见故障速查表 & 辅助工具

> 本文件由 SKILL.md 按需加载。

---

## 常见故障速查表

| 故障现象 | 可能根因 | 解决方式 |
|:---|:---|:---|
| COM 端口拒绝访问 | 串口被其他工具占用（SecureCRT、串口助手等） | 关闭多余串口监听程序后重试 |
| 串口输出乱码 | 波特率不匹配 / 系统时钟配置错误 | 核对 config.json 波特率参数，校验芯片时钟配置 |
| 修改代码编译无变化 | 目标文件未重新构建 | 删除工程 `.o` 中间文件重新编译（`--rebuild`） |
| CHESHI 打印无输出 | Keil 工程未配置 CHESHI 宏定义 | 在工程 C/C++ Define 中添加 `CHESHI` |
| 下载后设备无响应 | 启动代码异常 / 中断向量表偏移错误 | 检查 `SystemInit` 和 `SCB->VTOR` 配置 |
| 通信超时 | 缓冲区溢出 / 中断优先级配置错误 | 检查 DMA 配置和 NVIC 优先级分组 |
| HardFault | 栈溢出 / 野指针 / 数组越界 | 使用 Map 文件分析栈使用量 |
| 变量值不符合预期 | 编译器优化 / 缓存未刷新 | 添加 `volatile` 关键字或使用断点调试 |

---

## J-Link Commander 底层调试

串口失效时使用 J-Link 直接读写内存。

### 自动化调用

```bash
# 从 config.json 读取芯片型号
& "C:\Program Files\SEGGER\JLink\JLink.exe" -device STM32H753ZI -if SWD -speed 4000 -autoconnect 1
```

### 常用命令

| 命令 | 功能 | 使用示例 |
|:---|:---|:---|
| `mem32 地址,长度` | 读取 32 位内存数据 | `mem32 0x24000000, 16` |
| `mem8 地址,长度` | 读取单字节内存 | `mem8 0x24000000, 64` |
| `h` | 暂停 CPU 查看寄存器 | `h` |
| `g` | 恢复设备运行 | `g` |
| `r` | 硬件复位设备 | `r` |
| `w4 地址,数值` | 写入 32 位测试值 | `w4 0x24000000, 0x1234` |

### 读取芯片型号

```bash
& "C:\Program Files\SEGGER\JLink\JLink.exe" -device ? -if SWD -speed 4000 -autoconnect 1 -CommanderScript show_devices.jlink
```

---

## Keil Map 文件自动化分析

Map 文件是排查栈溢出、内存使用、函数符号的关键工具。

### 常用检索命令

```powershell
# PowerShell 检索（在工程目录下执行）
# 检索目标函数符号
Select-String -Path "*.map" -Pattern "mbSafeguardParse_m|eMBMasterPoll"

# 检索全局变量地址
Select-String -Path "*.map" -Pattern "ErrorCode|sa_MetaQueue"

# 检索调用栈深度
Select-String -Path "*.map" -Pattern "Call Chain" -Context 0,2
```

### Map 文件关键信息

| 信息区域 | 作用 | 检索关键词 |
|:---|:---|:---|
| Global Symbols | 定位函数/变量地址，设置断点 | `Global Symbols` |
| Call Chain | 校验最大栈深度，规避 HardFault | `Call Chain` |
| Memory Map | 统计 RAM/Flash 占用率 | `Memory Map` |
| Removing | 确认变量是否被编译器优化 | `Removing` |
| Image Entry | 镜像入口点 | `Image Entry` |

### 栈深度分析

检索 `Call Chain` 章节，查找调用树中的最大栈使用量：

```
Call Chain of: mbSafeguardParse_m
   Stack Usage: 128 bytes
   Called by: eMBMasterPoll (64 bytes)
   Calls: CRC16 (32 bytes)
   Max Chain: 224 bytes
```

若最大栈链接近或超过启动文件中的栈大小配置（通常 `Stack_Size` 在 `startup_*.s` 中定义），则有栈溢出风险。
