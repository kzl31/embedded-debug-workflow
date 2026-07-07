# 添加调试打印

## 推荐模式：`#ifdef CHESHI`

```c
#ifdef CHESHI
    printf("[TAG] key1=%d key2=%02X\r\n", var1, var2);
#endif
```

使用 `CHESHI` 宏统一控制调试代码的开关：
- 在 Keil 工程 → `Options → C/C++ → Define` 中添加 `CHESHI`
- 正式发布时移除即可，无需改动代码

## 打印内容建议

| 标签 | 含义 | 示例 |
|------|------|------|
| `[TAG]` | 唯一标识，方便过滤搜索 | `[SAFE_PARSE]` |
| 关键变量 | 数值、指针、长度 | `len=19 offset=10` |
| 原始数据 | HEX dump（前 N 字节） | `raw[0..15]` |
| 函数入口/出口 | 确认代码路径 | `func=0x03 except=0` |

## 典型模板

```c
#ifdef CHESHI
    printf("[MY_TAG] addr=%d cnt=%d usLen=%d PDU:", usRegAddress, usRegCount, *usLen);
    for(int _i=0; _i<8 && _i<*usLen; _i++) printf(" %02X", pucFrame[_i]);
    printf("\r\n");
#endif
```

更多代码模板见 `assets/debug-templates.c`。
