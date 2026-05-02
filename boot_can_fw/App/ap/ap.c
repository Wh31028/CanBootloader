#include "ap.h"
#include "can.h"
#include "hw_def.h"
#include "stm32f4xx_hal.h"

// RTC Backup Register에 Magic Number를 기록하고 소프트 리셋
static void enterFotaMode(void)
{
  // PWR + RTC 클록 활성화 (이미 SystemClock_Config에서 됐지만 안전하게 재호출)
  __HAL_RCC_PWR_CLK_ENABLE();
  HAL_PWR_EnableBkUpAccess();

  // Backup Register DR0에 Magic Number 저장
  // 부트로더가 시작 시 이 값을 확인해 FOTA 모드 진입 여부 결정
  RTC->BKP0R = FOTA_MAGIC_NUMBER;

#ifdef _USE_HW_CLI
  cliPrintf("[AP] FOTA request received! Rebooting to bootloader...\n\r");
#endif

  // 100ms 후 소프트 리셋 (UART TX 완료 대기)
  delay(100);
  NVIC_SystemReset();
}

void apInit(void)
{
  cliOpen(_DEF_UART1, 115200);
  cliLogo();

#ifdef _USE_HW_CLI
  cliPrintf("[AP] Firmware Running. Waiting for FOTA request on CAN ID 0x200...\n\r");
#endif
}

void apMain(void)
{
  uint32_t pre_time;

  pre_time = millis();
  while (1)
  {
    // LED 토글 (동작 확인용)
    if (millis() - pre_time >= 500)
    {
      pre_time = millis();
      ledToggle(_DEF_LED1);
      ledToggle(_DEF_LED2);
      ledToggle(_DEF_LED3);
      ledToggle(_DEF_LED4);
    }

    // CAN 메시지 폴링 - FOTA 진입 신호 감지
#ifdef _USE_HW_CAN
    while (canAvailable() > 0)
    {
      can_msg_t msg;
      canMsgRead(&msg);

      // BBB에서 CAN ID 0x200으로 0xDE 0xAD를 보내면 FOTA 진입
      if (msg.id == CAN_ID_FOTA_REQUEST && msg.dlc >= 2 &&
          msg.data[0] == 0xDE && msg.data[1] == 0xAD)
      {
        enterFotaMode();
      }
    }
#endif

    cliMain();
  }
}