#ifndef HW_DEF_H
#define HW_DEF_H


#include "main.h"
#include "def.h"

#define _USE_HW_LED
#define      HW_LED_MAX_CH          4

#define _USE_HW_UART
#define      HW_UART_MAX_CH         1

#define logPrintf printf

void delay(uint32_t ms);
uint32_t millis(void);


#endif