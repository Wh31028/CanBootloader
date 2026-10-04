#include "boot_can.h"
#include "can.h" // 작성하신 CAN 드라이버 포함
#include "flash.h"
#include <stdbool.h>
#include <string.h>

// 펌웨어 데이터 버퍼 (256바이트 페이지 단위)
#define BOOT_BUF_SIZE 256
#define BOOT_FRAME_PAYLOAD_SIZE 7
#define STM32F103RB_SRAM_START 0x20000000UL
#define STM32F103RB_SRAM_END   0x20005000UL
static uint8_t boot_buf[BOOT_BUF_SIZE];
static uint32_t fw_addr = FLASH_ADDR_DOWN;  // 다운로드 구역 주소
static uint32_t original_fw_size     = 0; // 원본 파일 크기 저장용 (CRC 계산용)
static uint32_t total_received_bytes = 0;

// 블록별 수신 상태 관리
static uint64_t rx_block_map            = 0;
static uint8_t expected_frames_in_block = 37; // 256/7 = 36.57 -> 37프레임
static uint32_t boot_last_rx_time       = 0;

typedef enum
{
  BOOT_STATE_IDLE = 0,
  BOOT_STATE_RECEIVING,
  BOOT_STATE_IMAGE_VERIFIED,
  BOOT_STATE_FAILED,
} boot_state_t;

static boot_state_t boot_state = BOOT_STATE_IDLE;

static void SendResponse(uint8_t cmd, uint8_t result_or_seq);
static void SendNackMap(uint64_t map);
static void bootProcessStart(can_msg_t *msg);
static void bootProcessData(can_msg_t *msg, uint8_t seq);
static void bootProcessEnd(can_msg_t *msg);
static void bootProcessJump(can_msg_t *msg);
static void bootResetReceiveContext(void);
static bool bootVerifyImageAt(uint32_t image_addr);
static bool bootWritePadded(uint32_t addr, const uint8_t *data, uint32_t length);
bool bootVerifyFw(void);
void JumpToFw(void);
static uint32_t calculate_crc32(uint32_t start_addr, uint32_t length);
bool bootCopyFw(uint32_t fw_size, uint32_t expected_crc);

void bootInit(void)
{
  bootResetReceiveContext();
  boot_state            = BOOT_STATE_IDLE;
  boot_last_rx_time    = millis();
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
      boot_last_rx_time = millis(); // 통신 수신 시간 갱신

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
  if (msg->dlc != 5)
  {
    SendResponse(CMD_TX_ERR, BOOT_ERR_INVALID_DLC);
    return;
  }

  if (GET_SEQ(msg->data[0]) != 0)
  {
    SendResponse(CMD_TX_ERR, BOOT_ERR_INVALID_SEQUENCE);
    return;
  }

  uint32_t rx_size = (uint32_t)msg->data[1] << 0;
  rx_size |= (uint32_t)msg->data[2] << 8;
  rx_size |= (uint32_t)msg->data[3] << 16;
  rx_size |= (uint32_t)msg->data[4] << 24;

  if (rx_size == 0 || rx_size > FLASH_ADDR_FW_MAX_LEN)
  {
    SendResponse(CMD_TX_ERR, BOOT_ERR_INVALID_SIZE);
    return;
  }

  if (flashErase(FLASH_ADDR_DOWN, 1024 * 56) == true)
  {
    bootResetReceiveContext();
    original_fw_size = rx_size;
    boot_state = BOOT_STATE_RECEIVING;
    SendResponse(CMD_TX_ACK, 0);
  }
  else
  {
    boot_state = BOOT_STATE_FAILED;
    SendResponse(CMD_TX_ERR, BOOT_ERR_FLASH_ERASE);
  }
}

static void bootProcessData(can_msg_t *msg, uint8_t seq)
{
  if (boot_state != BOOT_STATE_RECEIVING)
  {
    SendResponse(CMD_TX_ERR, BOOT_ERR_INVALID_STATE);
    return;
  }

  if (total_received_bytes >= original_fw_size)
  {
    SendResponse(CMD_TX_ERR, BOOT_ERR_INCOMPLETE_IMAGE);
    return;
  }

  uint32_t remaining_bytes = original_fw_size - total_received_bytes;
  uint32_t block_expected_bytes =
      (remaining_bytes > BOOT_BUF_SIZE) ? BOOT_BUF_SIZE : remaining_bytes;
  expected_frames_in_block =
      (uint8_t)((block_expected_bytes + BOOT_FRAME_PAYLOAD_SIZE - 1) /
                BOOT_FRAME_PAYLOAD_SIZE);

  if (seq >= expected_frames_in_block)
  {
    SendResponse(CMD_TX_ERR, BOOT_ERR_INVALID_SEQUENCE);
    return;
  }

  uint32_t offset = (uint32_t)seq * BOOT_FRAME_PAYLOAD_SIZE;
  uint32_t frame_remaining = block_expected_bytes - offset;
  uint8_t expected_payload_len =
      (frame_remaining > BOOT_FRAME_PAYLOAD_SIZE) ? BOOT_FRAME_PAYLOAD_SIZE : frame_remaining;

  if (msg->dlc != expected_payload_len + 1)
  {
    SendResponse(CMD_TX_ERR, BOOT_ERR_INVALID_DLC);
    return;
  }

  uint64_t sequence_bit = 1ULL << seq;
  if ((rx_block_map & sequence_bit) != 0)
  {
    if (seq == (expected_frames_in_block - 1))
    {
      SendNackMap(rx_block_map);
    }
    return;
  }

  memcpy(&boot_buf[offset], &msg->data[1], expected_payload_len);
  rx_block_map |= sequence_bit;

  uint64_t target_map = (1ULL << expected_frames_in_block) - 1;

  if ((rx_block_map & target_map) == target_map)
  {
    // 모두 정상 수신됨 -> 플래시 기록
    if (flashWrite(fw_addr, boot_buf, BOOT_BUF_SIZE) == true)
    {
      fw_addr              += BOOT_BUF_SIZE;
      total_received_bytes += block_expected_bytes;
      rx_block_map         = 0;
      
      memset(boot_buf, 0xFF, BOOT_BUF_SIZE);
      SendResponse(CMD_TX_ACK, 0); // 블록 완료 ACK
    }
    else
    {
      boot_state = BOOT_STATE_FAILED;
      SendResponse(CMD_TX_ERR, BOOT_ERR_FLASH_WRITE);
    }
  }
  // 만약 마지막 프레임이 도착했는데도 전체 출석부가 덜 찼다면
  else if (seq == (expected_frames_in_block - 1))
  {
    // 출석부(비트맵) 전체를 8바이트에 담아 1개의 NACK으로 한 방에 묶어서 보고합니다!
    SendNackMap(rx_block_map);
  }
}

static void bootProcessEnd(can_msg_t *msg)
{
  if (boot_state != BOOT_STATE_RECEIVING)
  {
    SendResponse(CMD_TX_ERR, BOOT_ERR_INVALID_STATE);
    return;
  }

  if (msg->dlc != 5)
  {
    SendResponse(CMD_TX_ERR, BOOT_ERR_INVALID_DLC);
    return;
  }

  if (GET_SEQ(msg->data[0]) != 0)
  {
    SendResponse(CMD_TX_ERR, BOOT_ERR_INVALID_SEQUENCE);
    return;
  }

  if (total_received_bytes != original_fw_size || rx_block_map != 0)
  {
    SendResponse(CMD_TX_ERR, BOOT_ERR_INCOMPLETE_IMAGE);
    return;
  }

  uint32_t received_crc = (uint32_t)msg->data[1] << 0 | (uint32_t)msg->data[2] << 8 |
                          (uint32_t)msg->data[3] << 16 | (uint32_t)msg->data[4] << 24;

  uint32_t calculated_crc = calculate_crc32(FLASH_ADDR_DOWN, original_fw_size);

  if (calculated_crc == received_crc)
  {
    if (bootVerifyImageAt(FLASH_ADDR_DOWN) == false)
    {
      boot_state = BOOT_STATE_FAILED;
      SendResponse(CMD_TX_ERR, BOOT_ERR_FLASH_JUMP);
      return;
    }

    // 검증 성공 -> 1. 메타 헤더(Size, CRC) 기록
    if (flashWrite(FLASH_ADDR_META_SIZE, (uint8_t *)&original_fw_size, 4) == false ||
        flashWrite(FLASH_ADDR_META_CRC, (uint8_t *)&received_crc, 4) == false)
    {
      boot_state = BOOT_STATE_FAILED;
      SendResponse(CMD_TX_ERR, BOOT_ERR_FLASH_WRITE);
      return;
    }

    // 2. 실행 구역으로 복사
    bool copy_success = bootCopyFw(original_fw_size, received_crc);

    if (copy_success)
    {
      boot_state = BOOT_STATE_IMAGE_VERIFIED;
      SendResponse(CMD_TX_ACK, 0);
    }
    else
    {
      boot_state = BOOT_STATE_FAILED;
      SendResponse(CMD_TX_ERR, BOOT_ERR_FLASH_WRITE);
    }
  }
  else
  {
    boot_state = BOOT_STATE_FAILED;
    SendResponse(CMD_TX_ERR, BOOT_ERR_CRC);
  }
}

static void bootProcessJump(can_msg_t *msg)
{
  if (msg->dlc != 1)
  {
    SendResponse(CMD_TX_ERR, BOOT_ERR_INVALID_DLC);
    return;
  }

  if (GET_SEQ(msg->data[0]) != 0)
  {
    SendResponse(CMD_TX_ERR, BOOT_ERR_INVALID_SEQUENCE);
    return;
  }

  if (boot_state != BOOT_STATE_IMAGE_VERIFIED)
  {
    SendResponse(CMD_TX_ERR, BOOT_ERR_INVALID_STATE);
    return;
  }

  if (bootVerifyFw() == true)
  {
    SendResponse(CMD_TX_ACK, 0);
    delay(100);
    JumpToFw();
  }
  else
  {
    boot_state = BOOT_STATE_FAILED;
    SendResponse(CMD_TX_ERR, BOOT_ERR_FLASH_JUMP);
  }
}

static void bootResetReceiveContext(void)
{
  fw_addr = FLASH_ADDR_DOWN;
  original_fw_size = 0;
  total_received_bytes = 0;
  rx_block_map = 0;
  expected_frames_in_block = 0;
  memset(boot_buf, 0xFF, BOOT_BUF_SIZE);
}

bool bootVerifyFw(void)
{
  return bootVerifyImageAt(FLASH_ADDR_START);
}

static bool bootVerifyImageAt(uint32_t image_addr)
{
  uint32_t initial_sp = *(uint32_t *)image_addr;
  uint32_t reset_handler = *(uint32_t *)(image_addr + 4);
  uint32_t reset_addr = reset_handler & ~1UL;
  uint32_t active_image_end = FLASH_ADDR_START + FLASH_ADDR_FW_MAX_LEN;

  if (initial_sp < STM32F103RB_SRAM_START || initial_sp > STM32F103RB_SRAM_END ||
      (initial_sp & 0x3UL) != 0 || (reset_handler & 1UL) == 0 ||
      reset_addr < FLASH_ADDR_START || reset_addr >= active_image_end)
  {
    return false;
  }

  return true;
}

// 컴파일러의 스택 메모리 해제(pop) 오작동을 원천 차단하기 위해 naked(어셈블리) 함수로 점프를 구현합니다.
__attribute__((naked)) void bootJump(uint32_t sp, uint32_t pc)
{
  __asm volatile (
    "msr msp, r0\n" // r0에 담긴 sp 값으로 스택 포인터 변경
    "bx r1\n"       // r1에 담긴 pc 값으로 점프 (절대 돌아오지 않음)
  );
}

void JumpToFw(void)
{
  delay(50);
  
  // HAL 레벨의 CAN/UART 인터럽트만 안전하게 비활성화
  HAL_NVIC_DisableIRQ(USB_LP_CAN1_RX0_IRQn);
  HAL_NVIC_DisableIRQ(USB_HP_CAN1_TX_IRQn);
  HAL_NVIC_DisableIRQ(CAN1_RX1_IRQn);
  HAL_NVIC_DisableIRQ(CAN1_SCE_IRQn);
  HAL_NVIC_DisableIRQ(USART1_IRQn);

  __disable_irq();

  SCB->VTOR = FLASH_ADDR_START;

  uint32_t sp = *(__IO uint32_t *)FLASH_ADDR_START;
  uint32_t pc = *(__IO uint32_t *)(FLASH_ADDR_START + 4);

  // 어셈블리 점프 함수 호출 (이후 컴파일러의 불필요한 pop 동작 원천 차단)
  bootJump(sp, pc);
}

uint32_t bootGetLastRxTime(void)
{
  return boot_last_rx_time;
}

// 응답 헤더 구성 후 전송
void SendResponse(uint8_t cmd, uint8_t result_or_seq)
{
  uint8_t data[2];
  data[0] = PACK_HEADER(cmd, result_or_seq);
  data[1] = 0x00;

  canMsgWrite(0x101, data, 2);
}

// 출석부 전체 비트맵 정보 한 번에 전송
static void SendNackMap(uint64_t map)
{
  uint8_t data[8];
  data[0] = PACK_HEADER(CMD_TX_NACK, 0); // 명령어: NACK
  // 37개의 출석부 비트를 7바이트(56비트) 공간에 여유 있게 꽉 눌러 담음
  data[1] = (map >> 0)  & 0xFF;
  data[2] = (map >> 8)  & 0xFF;
  data[3] = (map >> 16) & 0xFF;
  data[4] = (map >> 24) & 0xFF;
  data[5] = (map >> 32) & 0xFF;
  data[6] = (map >> 40) & 0xFF;
  data[7] = (map >> 48) & 0xFF;

  canMsgWrite(0x101, data, 8); // 8바이트 꽉꽉 채워서 송신
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

static bool bootWritePadded(uint32_t addr, const uint8_t *data, uint32_t length)
{
  uint8_t padded_word[4] = {0xFF, 0xFF, 0xFF, 0xFF};
  uint32_t aligned_length = length & ~0x3UL;

  if (aligned_length > 0 && flashWrite(addr, (uint8_t *)data, aligned_length) == false)
  {
    return false;
  }

  if (aligned_length == length)
  {
    return true;
  }

  memcpy(padded_word, data + aligned_length, length - aligned_length);
  return flashWrite(addr + aligned_length, padded_word, sizeof(padded_word));
}

bool bootCopyFw(uint32_t fw_size, uint32_t expected_crc)
{
  bool copy_success = false;

  if (fw_size == 0 || fw_size > FLASH_ADDR_FW_MAX_LEN)
  {
    return false;
  }

  if (flashErase(FLASH_ADDR_START, fw_size) == true)
  {
    copy_success = true;

    // 안전장치: 전원이 끊겼을 때를 대비해, 부팅 여부를 결정하는 '첫 번째 블록'을 가장 마지막에 복사합니다.
    uint32_t offset = BOOT_BUF_SIZE;
    while (offset < fw_size)
    {
      uint32_t copy_len = (fw_size - offset > BOOT_BUF_SIZE) ? BOOT_BUF_SIZE : (fw_size - offset);
      if (bootWritePadded(FLASH_ADDR_START + offset,
                          (const uint8_t *)(FLASH_ADDR_DOWN + offset), copy_len) == false)
      {
        copy_success = false;
        break;
      }
      offset += copy_len;
    }

    // 나머지 펌웨어가 모두 정상 복사되었을 때만 마지막으로 첫 번째 블록(인터럽트 벡터 테이블)을 복사!
    if (copy_success)
    {
      uint32_t first_len = (fw_size > BOOT_BUF_SIZE) ? BOOT_BUF_SIZE : fw_size;
      
      // 1. 오프셋 8부터 나머지 벡터 테이블(예: 8 ~ 255)을 먼저 복사
      if (first_len > 8)
      {
        if (bootWritePadded(FLASH_ADDR_START + 8,
                            ((const uint8_t *)FLASH_ADDR_DOWN) + 8, first_len - 8) == false)
        {
          copy_success = false;
        }
      }

      // 2. 가장 마지막 순간에 오프셋 0~7 (Initial SP 및 Reset Vector) 복사!!
      // 이렇게 하면 SP와 Reset Vector가 온전히 적히기 전까지는 부트로더가 절대 점프하지 않음.
      if (copy_success)
      {
        if (flashWrite(FLASH_ADDR_START, (uint8_t *)FLASH_ADDR_DOWN, 8) != true)
        {
          copy_success = false;
        }
      }
    }

    if (copy_success &&
        (calculate_crc32(FLASH_ADDR_START, fw_size) != expected_crc || bootVerifyFw() == false))
    {
      copy_success = false;
    }
  }
  else
  {
    copy_success = false;
  }
  return copy_success;
}

bool bootAutoRecover(void)
{
  // 1. 읽어온 메타 헤더
  uint32_t meta_size = *(uint32_t *)FLASH_ADDR_META_SIZE;
  uint32_t meta_crc  = *(uint32_t *)FLASH_ADDR_META_CRC;

  // 2. 유효한 사이즈인지 검사
  if (meta_size == 0 || meta_size > FLASH_ADDR_FW_MAX_LEN || meta_size == 0xFFFFFFFF)
  {
    return false; // 복구 불가
  }

  // 3. 다운로드 구역의 CRC 계산
  uint32_t calc_crc = calculate_crc32(FLASH_ADDR_DOWN, meta_size);

  // 4. CRC가 일치하면 다운로드 구역이 온전하다는 뜻! 복사 재개!
  if (calc_crc == meta_crc)
  {
    // 다운로드 구역이 온전하므로 다시 복사를 시도합니다.
    if (bootVerifyImageAt(FLASH_ADDR_DOWN) == true &&
        bootCopyFw(meta_size, meta_crc) == true)
    {
      return true; // 복구 성공
    }
  }

  return false;
}
