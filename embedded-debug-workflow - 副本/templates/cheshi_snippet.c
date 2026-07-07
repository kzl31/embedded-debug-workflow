/*****************************************
 * 【临时调试宏 - 仅调试阶段启用，正式版本完整删除本段】
 *
 * 方案A：Bit 位掩码（推荐）
 * Bit0(0x01)：通用流程函数入口打印
 * Bit1(0x02)：通信原始帧HEX打印
 * Bit2(0x04)：外设驱动状态打印
 * Bit3(0x08)：业务状态机跳转打印
 *****************************************/
#define CHESHI  0x0F   // 00001111 开启全部模块调试打印

/*****************************************
 * 使用说明：
 * 1. 将本段代码粘贴到 main.c 文件头部
 * 2. 根据需要调整 CHESHI 值控制打印模块
 * 3. 调试完成后删除本整段代码
 *****************************************/

/* ========== 使用示例 ========== */

/* 通用流程打印 Bit0 */
#if (CHESHI & 0x01)
    printf("[COMMON] func=%s line=%d\r\n", __FUNCTION__, __LINE__);
#endif

/* 通信原始帧打印 Bit1 */
#if (CHESHI & 0x02)
    printf("[COMM_RAW] len=%d data:", len);
    for (int _i = 0; _i < len && _i < 16; _i++) printf(" %02X", pbuf[_i]);
    printf("\r\n");
#endif

/* 外设驱动状态打印 Bit2 */
#if (CHESHI & 0x04)
    printf("[DRV] reg=%d val=%d\r\n", reg_addr, reg_val);
#endif

/* 状态机跳转打印 Bit3 */
#if (CHESHI & 0x08)
    printf("[FSM] %s -> %s (evt=%d)\r\n", state_cur, state_next, event);
#endif
