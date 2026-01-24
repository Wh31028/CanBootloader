#include "boot_can.h"
#include "can.h"   // 작성하신 CAN 드라이버 포함
#include "flash.h" 

// 비글본 파이썬 코드와 맞춘 명령어
#define CMD_FW_START  0x10
#define CMD_FW_DATA   0x20
#define CMD_FW_END    0x30



// 펌웨어 데이터 버퍼 (256바이트 페이지 단위)
#define BOOT_BUF_SIZE 256
static uint8_t  boot_buf[BOOT_BUF_SIZE];
static uint16_t boot_idx = 0;
static uint32_t fw_addr = FLASH_ADDR_FW; // App 시작 주소 (모델에 따라 다름)


static void SendResponse(uint8_t cmd, uint8_t result);
static void bootFlashErase(can_msg_t *msg);

void bootInit(void)
{
  boot_idx = 0;
}

void bootProcess(void)
{
  // 1. CAN 메시지가 왔는지 확인 (qbuffer 덕분에 안전함)
  if (canAvailable() > 0)
  {
    can_msg_t msg;
    canMsgRead(&msg); // 큐에서 하나 꺼냄

    // FOTA용 ID인지 확인 (예: 0x100)
    if (msg.id == 0x100)
    {
      uint8_t cmd = msg.data[0];
      switch(cmd)
      {
        case CMD_FW_START:
          bootFlashErase(&msg);
          break;
      }
    }
  }
}

void bootFlashErase(can_msg_t *msg)
{
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


// 응답을 보내는 함수 추가
void SendResponse(uint8_t cmd, uint8_t result)
{
    uint8_t data[2];
    data[0] = cmd;    // 어떤 명령에 대한 응답인지
    data[1] = result; // 0:성공, 1:실패

    // ID 0x101로 응답 전송
    canMsgWrite(0x101, data, 2);
}