# Keil Map 文件分析

> 编译后生成的 `.map` 文件包含符号表、调用栈分析、内存布局等关键信息。

## 查找函数引用关系

```powershell
Get-Content "*.map" | Select-String "mbSafeguardParse_m|eMBMasterPoll|u32_SafeguardCRC32"
```

## 查找变量地址

```powershell
Get-Content "*.map" | Select-String "ErrorCode|sa_MetaQueue"
```

## 查找调用栈深度

```powershell
Get-Content "*.map" | Select-String "Call Chain" -Context 0,2
```

## 信息类型参考

| 信息类型 | map 文件位置 | 用途 |
|----------|-------------|------|
| 函数地址 | `Global Symbols` | 调试器断点设置 |
| 调用栈 | `Call Chain` | 检查最大栈深度是否溢出 |
| 内存占用 | `Memory Map` | 确认 RAM/Flash 使用率 |
| 移除的符号 | `Removing` | 检查代码是否被优化掉 |
