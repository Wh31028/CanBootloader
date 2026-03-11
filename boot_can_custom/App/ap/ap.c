#include "ap.h"
#include "uart.h"
#include "boot_can.h"

void apInit(void)
{
  cliOpen(_DEF_UART1, 115200);
  cliLogo();
  // 1. 부트로더 로직 초기화
  bootInit();

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
    bootProcess();
    if (millis()-pre_time >= 500)
    {
      pre_time = millis();
      ledToggle(_DEF_LED1);
    }
    cliMain();
  }
} 