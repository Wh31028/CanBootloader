#ifndef AP_INCLUDE_FOTA_H_
#define AP_INCLUDE_FOTA_H_

#include "ap_def.h"


#define BOOT_OK                  0x00
#define BOOT_ERR_FLASH_ERASE    0x03


void bootInit(void);
void bootProcess(void); // 메인 루프에서 계속 돌릴 함수

#endif