# J-Link Commander 调试

> 当串口不可用或需要直接查看内存/寄存器时使用。

## 启动 J-Link Commander

```powershell
& "C:\Program Files\SEGGER\JLink\JLink.exe" -device STM32H753ZI -if SWD -speed 4000 -autoconnect 1
```

## 常用命令

| 命令 | 功能 | 示例 |
|------|------|------|
| `mem32 <addr>, <n>` | 读取 32 位内存 | `mem32 0x24000000, 16` |
| `mem8 <addr>, <n>` | 读取 8 位内存 | `mem8 0x24000000, 64` |
| `h` | 暂停 CPU | 暂停后查看寄存器 |
| `g` | 继续运行 | 恢复执行 |
| `r` | 复位 | 复位目标板 |
| `w4 <addr>, <val>` | 写入 32 位值 | `w4 0x24000000, 0x1234` |

## 适用场景

- 变量值直接验证
- 内存越界排查
- 寄存器状态检查
