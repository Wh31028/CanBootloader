#include "hw.h"
#include "stm32f4xx_hal.h"
#include <stdint.h>



bool hwInit(void)
{
  ledInit();
  
  return true;
}


void delay(uint32_t ms)
{
  HAL_Delay(ms);
}

uint32_t millis(void)
{
  return HAL_GetTick();
}