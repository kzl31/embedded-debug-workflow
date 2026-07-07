// ============================================================
// 嵌入式调试打印模板合集
// 使用方式：在 Keil 工程 Define 中添加 CHESHI 或 DEBUG_LEVEL=N
// ============================================================

// ------------------------------------------------------------
// 模板 1: 基础调试打印（#ifdef CHESHI 模式）
// 在 Keil 工程 → Options → C/C++ → Define 中添加 CHESHI
// ------------------------------------------------------------
#ifdef CHESHI
    printf("[TAG] key1=%d key2=%02X\r\n", var1, var2);
#endif

// ------------------------------------------------------------
// 模板 2: 带 HEX dump 的调试打印
// ------------------------------------------------------------
#ifdef CHESHI
    printf("[MY_TAG] addr=%d cnt=%d usLen=%d PDU:", usRegAddress, usRegCount, *usLen);
    for(int _i=0; _i<8 && _i<*usLen; _i++) printf(" %02X", pucFrame[_i]);
    printf("\r\n");
#endif

// ------------------------------------------------------------
// 模板 3: 条件编译分层（DEBUG_LEVEL）
// 在 Keil 工程 Define 中添加 DEBUG_LEVEL=1/2/3
// ------------------------------------------------------------
#if DEBUG_LEVEL >= 1
    printf("[ERR] func=0x%02X except=%d\r\n", func, except);
#endif

#if DEBUG_LEVEL >= 2
    printf("[EXEC] addr=%d cnt=%d len=%d\r\n", addr, cnt, len);
#endif

#if DEBUG_LEVEL >= 3
    printf("[HEX] ");
    for(int i=0; i<len && i<32; i++) printf("%02X ", buf[i]);
    printf("\r\n");
#endif

// ------------------------------------------------------------
// 模板 4: 中断保护打印（环形缓冲区）
// 在 ISR 中写入环形缓冲区，主循环中统一输出
// ------------------------------------------------------------
#define DBG_BUF_SIZE 256

// 中断中写入
void USART3_IRQHandler(void) {
    // ...中断处理...
#ifdef CHESHI
    g_dbg_buf[g_dbg_wr++ % DBG_BUF_SIZE] = rx_byte;  // 只记关键字节
#endif
}

// 主循环中输出
void Debug_Flush(void) {
#ifdef CHESHI
    while (g_dbg_rd != g_dbg_wr) {
        printf("%02X ", g_dbg_buf[g_dbg_rd++ % DBG_BUF_SIZE]);
    }
#endif
}

// ------------------------------------------------------------
// 模板 5: 函数入口/出口跟踪
// ------------------------------------------------------------
#ifdef CHESHI
    printf("[TRACE] >> %s (line=%d)\r\n", __FUNCTION__, __LINE__);
#endif

// ... 函数体 ...

#ifdef CHESHI
    printf("[TRACE] << %s (ret=%d)\r\n", __FUNCTION__, ret_val);
#endif
