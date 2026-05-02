#include "ap.h"
#include "boot_can.h"

// RTC Backup Register DR0에서 Magic Number 확인 후 플래그 초기화
static bool checkFotaRequest(void)
{
  __HAL_RCC_PWR_CLK_ENABLE();
  HAL_PWR_EnableBkUpAccess();

  if (RTC->BKP0R == FOTA_MAGIC_NUMBER)
  {
    // 플래그 즉시 초기화 (다음 리셋 시 재진입 방지)
    RTC->BKP0R = 0x00000000;
    return true;
  }
  return false;
}

void apInit(void)
{
  cliOpen(_DEF_UART1, 115200);
  cliLogo();

#ifdef _USE_HW_CLI
  cliPrintf("[BOOT] Checking FOTA request flag...\n\r");
#endif

  // FOTA 요청이 없으면 바로 App으로 점프
  if (!checkFotaRequest())
  {
    // App FW의 유효성 확인 후 점프
    uint32_t *app_reset_vector = (uint32_t *)(FLASH_ADDR_START + 4);
    if (*app_reset_vector >= FLASH_ADDR_START && *app_reset_vector < FLASH_ADDR_END)
    {
#ifdef _USE_HW_CLI
      cliPrintf("[BOOT] No FOTA request. Jumping to App...\n\r");
#endif
      delay(50);

      // App으로 점프
      void (**jump_func)(void) = (void (**)(void))(FLASH_ADDR_START + 4);
      __disable_irq();
      SCB->VTOR = FLASH_ADDR_START;
      __set_MSP(*(__IO uint32_t *)FLASH_ADDR_START);
      (*jump_func)();
    }
    else
    {
#ifdef _USE_HW_CLI
      cliPrintf("[BOOT] No valid App found. Entering FOTA mode.\n\r");
#endif
    }
  }
  else
  {
#ifdef _USE_HW_CLI
    cliPrintf("[BOOT] FOTA request detected! Entering FOTA mode.\n\r");
#endif
  }

  // FOTA 모드: 부트로더 초기화
  bootInit();

#ifdef _USE_HW_CLI
  cliPrintf("[BOOT] Waiting for firmware from host...\n\r");
#endif
}

void apMain(void)
{
  uint32_t pre_time;

  pre_time = millis();
  while (1)
  {
    bootProcess();
    if (millis() - pre_time >= 500)
    {
      pre_time = millis();
      ledToggle(_DEF_LED1);
    }
    cliMain();
  }
}