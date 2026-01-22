#ifndef HW_DEF_H
#define HW_DEF_H


#include "main.h"
#include "def.h"

#define _USE_HW_LED
#define      HW_LED_MAX_CH          4

#define _USE_HW_UART
#define      HW_UART_MAX_CH         1

#define _USE_HW_CLI
#define      HW_CLI_CMD_LIST_MAX    32
#define      HW_CLI_CMD_NAME_MAX    16
#define      HW_CLI_LINE_HIS_MAX    8
#define      HW_CLI_LINE_BUF_MAX    64

#define _USE_HW_FLASH
#define _USE_MAC

#define logPrintf printf

void delay(uint32_t ms);
uint32_t millis(void);


#endif