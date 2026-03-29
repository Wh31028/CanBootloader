#include "boot_can.h"
#include "can.h" // 작성하신 CAN 드라이버 포함
#include "flash.h"
#include <stdbool.h>
#include <string.h>

// 펌웨어 데이터 버퍼 (256바이트 페이지 단위)
#define BOOT_BUF_SIZE 256
static uint8_t boot_buf[BOOT_BUF_SIZE];
static uint32_t fw_addr = FLASH_ADDR_FW;  // App 시작 주소 (모델에 따라 다름)
static uint32_t original_fw_size     = 0; // 원본 파일 크기 저장용 (CRC 계산용)
static uint32_t total_received_bytes = 0;

// 블록별 수신 상태 관리
static uint64_t rx_block_map            = 0;
static uint8_t expected_frames_in_block = 37; // 256/7 = 36.57 -> 37프레임

static void SendResponse(uint8_t cmd, uint8_t result_or_seq);
static void bootProcessStart(can_msg_t *msg);
static void bootProcessData(can_msg_t *msg, uint8_t seq);
static void bootProcessEnd(can_msg_t *msg);
static void bootProcessJump(can_msg_t *msg);
static bool bootVerifyFw(void);
static void JumpToFw(void);
static uint32_t calculate_crc32(uint32_t start_addr, uint32_t length);

void bootInit(void)
{
  rx_block_map         = 0;
  total_received_bytes = 0;
}

void bootProcess(void)
{
  while (canAvailable() > 0)
  {
    can_msg_t msg;
    canMsgRead(&msg);

    // Host -> Target ID: 0x100
    if (msg.id == 0x100 && msg.dlc > 0)
    {
      uint8_t header = msg.data[0];
      uint8_t cmd    = GET_CMD(header);
      uint8_t seq    = GET_SEQ(header);

      switch (cmd)
      {
      case CMD_RX_START:
        bootProcessStart(&msg);
        break;
      case CMD_RX_DATA:
        bootProcessData(&msg, seq);
        break;
      case CMD_RX_END:
        bootProcessEnd(&msg);
        break;
      case CMD_RX_JUMP:
        bootProcessJump(&msg);
        break;
      }
    }
  }
}

static void bootProcessStart(can_msg_t *msg)
{
  fw_addr          = FLASH_ADDR_FW;
  uint8_t status   = BOOT_OK;
  uint32_t rx_size = 0;

  memset(boot_buf, 0xFF, BOOT_BUF_SIZE);
  rx_block_map         = 0;
  total_received_bytes = 0;

  if (msg->dlc >= 5)
  {
    rx_size = (uint32_t)msg->data[1] << 0;
    rx_size |= (uint32_t)msg->data[2] << 8;
    rx_size |= (uint32_t)msg->data[3] << 16;
    rx_size |= (uint32_t)msg->data[4] << 24;
  }

  original_fw_size = rx_size;

  if (rx_size == 0 || rx_size > FLASH_ADDR_FW_MAX_LEN)
  {
    rx_size = FLASH_ADDR_FW_MAX_LEN;
  }

  if (flashErase(FLASH_ADDR_FW, rx_size) == true)
  {
    status = BOOT_OK;
  }
  else
  {
    status = BOOT_ERR_FLASH_ERASE;
  }

  if (status == BOOT_OK)
  {
    SendResponse(CMD_TX_ACK, 0);
  }
  else
  {
    SendResponse(CMD_TX_ERR, status);
  }
}

static void bootProcessData(can_msg_t *msg, uint8_t seq)
{
  if (seq > 36)
  {
    return; // Ignore invalid sequences (max 37 frames for 256 bytes)
  }

  // 1. 버퍼 복사 (7바이트 단위, 마지막 프레임은 남은 바이트만큼)
  uint32_t offset     = seq * 7;
  uint8_t payload_len = msg->dlc - 1;

  if (offset + payload_len <= BOOT_BUF_SIZE)
  {
    memcpy(&boot_buf[offset], &msg->data[1], payload_len);
  }

  // 2. 해당 시퀀스 비트 마킹
  rx_block_map |= (1ULL << seq);

  // 현재 받아야 할 프레임 개수 계산
  uint32_t rem_bytes = original_fw_size - total_received_bytes;
  uint32_t block_expected_bytes =
      (rem_bytes > BOOT_BUF_SIZE) ? BOOT_BUF_SIZE : rem_bytes;
  expected_frames_in_block = (block_expected_bytes + 6) / 7;

  // 3. 기대하는 모든 프레임을 수신했는지 확인
  uint64_t target_map = (1ULL << expected_frames_in_block) - 1;

  // 마지막 시퀀스 번호 체크
  if (seq == (expected_frames_in_block - 1))
  {
    if ((rx_block_map & target_map) == target_map)
    {
      // 모두 정상 수신됨 -> 플래시 기록
      if (flashWrite(fw_addr, boot_buf, BOOT_BUF_SIZE) == true)
      {
        fw_addr += BOOT_BUF_SIZE;
        total_received_bytes += block_expected_bytes;
        rx_block_map = 0;

        memset(boot_buf, 0xFF, BOOT_BUF_SIZE);
        SendResponse(CMD_TX_ACK, 0); // 블록 완료 ACK
      }
      else
      {
        SendResponse(CMD_TX_ERR, BOOT_ERR_FLASH_WRITE);
      }
    }
    else
    {
      // 중간 이빨 빠짐 탐지 (Selective NACK)
      for (uint8_t i = 0; i < expected_frames_in_block; i++)
      {
        if ((rx_block_map & (1ULL << i)) == 0)
        {
          SendResponse(CMD_TX_NACK, i); // 누락된 첫 번째 seq 요청
          return;
        }
      }
    }
  }
}

static void bootProcessEnd(can_msg_t *msg)
{
  uint8_t status        = BOOT_OK;
  uint32_t received_crc = 0;

  if (msg->dlc >= 5)
  {
    received_crc = (uint32_t)msg->data[1] << 0 | (uint32_t)msg->data[2] << 8 |
                   (uint32_t)msg->data[3] << 16 | (uint32_t)msg->data[4] << 24;
  }

  uint32_t calculated_crc = calculate_crc32(FLASH_ADDR_FW, original_fw_size);

  if (calculated_crc == received_crc)
  {
    status = BOOT_OK;
    SendResponse(CMD_TX_ACK, 0);

    // Auto Jump
    if (bootVerifyFw() == true)
    {
      delay(100);
      JumpToFw();
    }
  }
  else
  {
    status = BOOT_ERR_CRC;
    SendResponse(CMD_TX_ERR, status);
  }
}

static void bootProcessJump(can_msg_t *msg)
{
  (void)msg;
  if (bootVerifyFw() == true)
  {
    SendResponse(CMD_TX_ACK, 0);
    delay(100);
    JumpToFw();
  }
  else
  {
    SendResponse(CMD_TX_ERR, BOOT_ERR_FLASH_JUMP);
  }
}

bool bootVerifyFw(void)
{
  uint32_t *jump_addr = (uint32_t *)(FLASH_ADDR_START + 4);

  if ((*jump_addr) >= FLASH_ADDR_START && (*jump_addr) < FLASH_ADDR_END)
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
  void (**jump_func)(void) = (void (**)(void))(FLASH_ADDR_START + 4);

  bspDeInit();

  __disable_irq();

  SCB->VTOR = FLASH_ADDR_START;

  __set_MSP(*(__IO uint32_t *)FLASH_ADDR_START);

  (*jump_func)();
}

// 응답 헤더 구성 후 전송
void SendResponse(uint8_t cmd, uint8_t result_or_seq)
{
  uint8_t data[2];
  data[0] = PACK_HEADER(cmd, result_or_seq);
  data[1] = 0x00;

  canMsgWrite(0x101, data, 2);
}

static uint32_t calculate_crc32(uint32_t start_addr, uint32_t length)
{
  uint32_t crc  = 0xFFFFFFFF;
  uint8_t *data = (uint8_t *)start_addr;

  for (uint32_t i = 0; i < length; i++)
  {
    crc ^= data[i];
    for (int j = 0; j < 8; j++)
    {
      if (crc & 1)
      {
        crc = (crc >> 1) ^ 0xEDB88320;
      }
      else
      {
        crc >>= 1;
      }
    }
  }
  return ~crc;
}