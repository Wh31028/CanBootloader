#include "ap.h"

void apInit(void)
{
  cliOpen(_DEF_UART1, 115200);
  cliLogo();

  // (선택) 시작 메시지 출력
  #ifdef _USE_HW_CLI
  cliPrintf("[AP] Bootloader Ready...\n");
  #endif
}

void apMain(void)
{
  uint32_t pre_time;

  pre_time = millis();
  while(1)
  {
    if (millis()-pre_time >= 500)
    {
      pre_time = millis();
      ledToggle(_DEF_LED1);
      ledToggle(_DEF_LED2);
      ledToggle(_DEF_LED3);
      ledToggle(_DEF_LED4);
    }
    cliMain();
  }
} 