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
 * 3. 凡调试结束需删除的 include、宏、类型、声明、变量、参数、
 *    辅助函数、缓冲区、初始化及调用点，都必须放入对应 CHESHI 块
 * 4. 调试完成后删除全部临时代码，并恢复临时工程配置
 *****************************************/

/* ========== 使用示例 ========== */

/* 临时依赖、声明、数据和辅助函数必须完整受控，不能只包裹 printf */
#if (CHESHI & 0x02)
#include "debug_capture.h"

#define DBG_BUF_SIZE 256U

static uint8_t g_debug_buffer[DBG_BUF_SIZE];
static void Debug_CaptureFrame(const uint8_t *data, uint16_t length);
static void Debug_Flush(void);
#endif

/* 通用流程打印 Bit0 */
#if (CHESHI & 0x01)
    printf("[COMMON] func=%s line=%d\r\n", __FUNCTION__, __LINE__);
#endif

/* 通信层只采集快照；禁止在通信回调/ISR中直接 printf */
#if (CHESHI & 0x02)
    debug_capture_frame(pbuf, len);
#endif

/* main 主循环统一输出通信快照 Bit1 */
#if (CHESHI & 0x02)
    Debug_Flush();
#endif

/* 外设驱动状态打印 Bit2 */
#if (CHESHI & 0x04)
    printf("[DRV] reg=%d val=%d\r\n", reg_addr, reg_val);
#endif

/* 状态机跳转打印 Bit3 */
#if (CHESHI & 0x08)
    printf("[FSM] %s -> %s (evt=%d)\r\n", state_cur, state_next, event);
#endif
