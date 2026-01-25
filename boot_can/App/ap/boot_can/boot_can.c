#include "boot_can.h"
#include "can.h"   // 작성하신 CAN 드라이버 포함
#include "flash.h" 
#include <stdbool.h>

// 비글본 파이썬 코드와 맞춘 명령어
#define CMD_FW_START      0x10
#define CMD_FW_DATA       0x20
#define CMD_FW_END        0x30
#define CMD_FW_JUMP_TO_FW 0x40



// 펌웨어 데이터 버퍼 (256바이트 페이지 단위)
#define BOOT_BUF_SIZE 256
static uint8_t  boot_buf[BOOT_BUF_SIZE];
static uint16_t boot_idx = 0;
static uint32_t fw_addr = FLASH_ADDR_FW; // App 시작 주소 (모델에 따라 다름)


static void SendResponse(uint8_t cmd, uint8_t result);
static void bootFlashErase(can_msg_t *msg);
static void bootFlashWrite(can_msg_t *msg);
static void bootFlashEnd(can_msg_t *msg);
static void bootJumpToFw(can_msg_t *msg);
static bool bootVerifyFw(void);
static void JumpToFw(void);

void bootInit(void)
{
  boot_idx = 0;
}

void bootProcess(void)
{
  // 1. CAN 메시지가 왔는지 확인 (qbuffer 덕분에 안전함)
  while (canAvailable() > 0)
  {
    can_msg_t msg;
    canMsgRead(&msg); // 큐에서 하나 꺼냄

    // FOTA용 ID인지 확인
    if (msg.id == 0x100)
    {
      uint8_t cmd = msg.data[0];
      switch(cmd)
      {
        case CMD_FW_START:
          bootFlashErase(&msg);
          break;
        case CMD_FW_DATA:
          bootFlashWrite(&msg);
          break;
        case CMD_FW_END:
          bootFlashEnd(&msg);
          break;
        case CMD_FW_JUMP_TO_FW:
          bootJumpToFw(&msg);
          break;

      }
    }
  }
}

void bootFlashErase(can_msg_t *msg)
{
  fw_addr = FLASH_ADDR_FW;
  uint8_t status = BOOT_OK;
  uint32_t rx_size = 0;
  // [시작] 플래시 지우기 & 초기화
  boot_idx = 0;

  rx_size = (uint32_t)msg->data[4] << 0;
  rx_size |= (uint32_t)msg->data[5] << 8;
  rx_size |= (uint32_t)msg->data[6] << 16;
  rx_size |= (uint32_t)msg->data[7] << 24;

  // 안전장치: 크기가 0이거나 너무 크면 기본값 사용 (선택 사항)
  if (rx_size == 0 || rx_size > FLASH_ADDR_FW_MAX_LEN) 
  {
    rx_size = FLASH_ADDR_FW_MAX_LEN; // 그냥 다 지워버림 (안전빵)
  }
  if (flashErase(FLASH_ADDR_FW, rx_size) == true) status = BOOT_OK;
  else status = BOOT_ERR_FLASH_ERASE;

  SendResponse(CMD_FW_START, status);
  // LED 켜기 (진행 중 표시)

}

void bootFlashWrite(can_msg_t *msg)
{
  uint8_t status = BOOT_OK;
  for(int i=1;i<msg->dlc;i++)
  {
    boot_buf[boot_idx++] = msg->data[i];
    
    if(boot_idx >= BOOT_BUF_SIZE)
    {
      if(flashWrite(fw_addr, boot_buf, BOOT_BUF_SIZE) == true)
      {
        status = BOOT_OK;
        fw_addr+=BOOT_BUF_SIZE;
        boot_idx = 0;

        SendResponse(CMD_FW_DATA, status);
      }
      else 
      {
        status = BOOT_ERR_FLASH_WRITE;
        SendResponse(CMD_FW_DATA, status);
        return;
      }
      
    }
  }
  
}

void bootFlashEnd(can_msg_t *msg)
{
  uint8_t status = BOOT_OK;

  // 버퍼에 남은 데이터가 있다면
  if (boot_idx > 0)
  {
    // [핵심] 4바이트 정렬 맞추기 (나머지 공간을 0xFF로 채움)
    // 예: 데이터가 1바이트 남았으면 3바이트를 0xFF로 채워서 4바이트로 만듦
    while((boot_idx % 4) != 0)
    {
      boot_buf[boot_idx++] = 0xFF;
    }

    // 이제 boot_idx는 무조건 4의 배수임
    if(flashWrite(fw_addr, boot_buf, boot_idx) == true)
    {
      status = BOOT_OK;
    }
    else
    {
      status = BOOT_ERR_FLASH_WRITE;
    }
  }

  SendResponse(CMD_FW_END, status);
}

static void bootJumpToFw(can_msg_t *msg)
{
  uint8_t status = BOOT_OK;
  if(bootVerifyFw() == true)
  {
    SendResponse(CMD_FW_JUMP_TO_FW, status);
    delay(100);
    JumpToFw();
  }
  else 
  {
    status=BOOT_ERR_FLASH_JUMP;
    SendResponse(CMD_FW_JUMP_TO_FW, status);
  }

}

bool bootVerifyFw(void)
{
  uint32_t *jump_addr= (uint32_t *)(FLASH_ADDR_START + 4);

  if ((*jump_addr) >= FLASH_ADDR_START && 
      (*jump_addr) < FLASH_ADDR_END)
  {
    return true;
  }
  else 
  {
    return false;
  }
}

void JumpToFw(void)
{
  void (**jump_func)(void) = (void(**)(void))(FLASH_ADDR_START + 4);

  bspDeInit();

  __disable_irq();

  //벡터 테이블 위치를 앱의 시작 주소로 변경
  // 이걸 안 하면 앱에서 인터럽트 켜는 순간 죽습니다.
  SCB->VTOR = FLASH_ADDR_START;

  //  메인 스택 포인터(MSP)를 앱의 스택 시작점으로 변경
  //    (FLASH_ADDR_START 번지에는 스택 주소가 들어있음)
  __set_MSP(*(__IO uint32_t*)FLASH_ADDR_START);
  
  (*jump_func)();
}



// 응답을 보내는 함수 추가
void SendResponse(uint8_t cmd, uint8_t result)
{
    uint8_t data[2];
    data[0] = cmd;    // 어떤 명령에 대한 응답인지
    data[1] = result; // 0:성공, 1:실패

    // ID 0x101로 응답 전송
    canMsgWrite(0x101, data, 2);
}