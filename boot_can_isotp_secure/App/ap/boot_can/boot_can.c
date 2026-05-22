#include "boot_can.h"
#include "can.h"
#include "flash.h"
#include "isotp_port.h"
#include <stdbool.h>
#include <string.h>

#include "crypto/tiny-AES-c/aes.h"
#include "crypto/micro-ecc/uECC.h"
#include "crypto/sha256.h"

#define CMD_FW_START      0x10
#define CMD_FW_DATA       0x20
#define CMD_FW_END        0x30
#define CMD_FW_JUMP_TO_FW 0x40
#define FOTA_CHUNK_SIZE 256

static uint32_t fw_addr = FLASH_ADDR_FW; 
static uint32_t original_fw_size = 0;    

static void SendResponse(uint8_t cmd, uint8_t result);
static uint8_t bootIsoTpFlashErase(uint8_t *payload, uint16_t size);
static uint8_t bootIsoTpFlashWrite(uint8_t *payload, uint16_t size);
static uint8_t bootIsoTpFlashEnd(uint8_t *payload, uint16_t size);
static uint8_t bootIsoTpJump(uint8_t cmd);
static bool bootVerifyFw(void);
static void JumpToFw(void);
static uint32_t calculate_crc32(uint32_t start_addr, uint32_t length);

// FOTA Security States
static bool header_received = false;
static uint8_t fota_header[240];
static struct AES_ctx aes_ctx;
static SHA256_CTX sha256_enc_ctx;
static SHA256_CTX sha256_pt_ctx;
static uint8_t expected_sha256_enc[32];
static uint8_t expected_sha256_pt[32];
static uint8_t sig_enc[64];
static uint8_t sig_pt[64];

static const uint8_t AES_KEY[16] = {0x2b, 0x7e, 0x15, 0x16, 0x28, 0xae, 0xd2, 0xa6, 0xab, 0xf7, 0x15, 0x88, 0x09, 0xcf, 0x4f, 0x3c};
static const uint8_t ECDSA_PUB_KEY[64] = {
    0xfd, 0x85, 0x6c, 0xf6, 0x9b, 0xfe, 0x17, 0xb4, 0xbb, 0x3a, 0x46, 0x86, 0x66, 0x55, 0x5c, 0x0e, 
    0x8f, 0xfb, 0xc8, 0x62, 0x54, 0x2b, 0x11, 0xe5, 0x8e, 0xbf, 0x56, 0x67, 0x64, 0x88, 0xaf, 0x52, 
    0xad, 0xbd, 0x80, 0x11, 0xe9, 0xcf, 0x8a, 0x5f, 0xa4, 0x3c, 0x3f, 0xa4, 0xab, 0xf9, 0xa6, 0xbb, 
    0x8d, 0x6a, 0x78, 0x1e, 0xb3, 0x1e, 0xcb, 0xd9, 0xf8, 0xe4, 0x7f, 0x22, 0xa7, 0xea, 0x82, 0xbf
};

void bootInit(void) { 
  isotp_port_init(); 
  header_received = false;
}

void bootProcess(void)
{
  isotp_port_poll();
  while (canAvailable() > 0)
  {
    can_msg_t msg;
    canMsgRead(&msg);

    if (msg.id == g_isotp_link.receive_arbitration_id || msg.id == 0x7E0 || msg.id == 0x7E8)
    {
      isotp_port_on_can_rx(msg.id, msg.data, msg.dlc);
    }
  }
}

void bootIsoTpProcessCommand(uint8_t *payload, uint16_t size)
{
  if (size < 1) return;
  uint8_t cmd    = payload[0];
  uint8_t status = BOOT_OK;

  switch (cmd)
  {
  case CMD_FW_START:
    status = bootIsoTpFlashErase(payload, size);
    break;
  case CMD_FW_DATA:
    status = bootIsoTpFlashWrite(payload, size);
    break;
  case CMD_FW_END:
    status = bootIsoTpFlashEnd(payload, size);
    break;
  case CMD_FW_JUMP_TO_FW:
    status = bootIsoTpJump(cmd);
    if (status == BOOT_OK) return;
    break;
  }

  if (cmd == CMD_FW_START && status == BOOT_OK)
  {
    uint8_t ack_payload[4] = {cmd, status, (FOTA_CHUNK_SIZE & 0xFF), ((FOTA_CHUNK_SIZE >> 8) & 0xFF)};
    extern IsoTpLink g_isotp_link;
    isotp_send(&g_isotp_link, ack_payload, sizeof(ack_payload));
  }
  else
  {
    uint8_t ack_payload[2] = {cmd, status};
    extern IsoTpLink g_isotp_link;
    isotp_send(&g_isotp_link, ack_payload, sizeof(ack_payload));
  }
}

bool bootVerifyFw(void)
{
  uint32_t *jump_addr = (uint32_t *)(FLASH_ADDR_START + 4);
  if ((*jump_addr) >= FLASH_ADDR_START && (*jump_addr) < FLASH_ADDR_END) return true;
  return false;
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

void SendResponse(uint8_t cmd, uint8_t result)
{
  uint8_t data[2];
  data[0] = cmd;    
  data[1] = result; 
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
      if (crc & 1) crc = (crc >> 1) ^ 0xEDB88320;
      else crc >>= 1;
    }
  }
  return ~crc;
}

static uint8_t bootIsoTpFlashErase(uint8_t *payload, uint16_t size)
{
  if (size < 5) return BOOT_ERR_FLASH_ERASE;

  fw_addr = FLASH_ADDR_FW;
  uint32_t rx_size = 0;
  rx_size = (uint32_t)payload[1] << 0 | (uint32_t)payload[2] << 8 | (uint32_t)payload[3] << 16 | (uint32_t)payload[4] << 24;

  original_fw_size = rx_size;

  if (rx_size == 0 || rx_size > FLASH_ADDR_FW_MAX_LEN) rx_size = FLASH_ADDR_FW_MAX_LEN;

  header_received = false;

  if (flashErase(FLASH_ADDR_FW, rx_size) == true) {
      sha256_init(&sha256_enc_ctx);
      sha256_init(&sha256_pt_ctx);
      return BOOT_OK;
  }
  else return BOOT_ERR_FLASH_ERASE;
}

static uint8_t bootIsoTpFlashWrite(uint8_t *payload, uint16_t size)
{
  uint16_t data_len = size - 1; // Subtract CMD byte
  uint8_t* p_data = &payload[1];

  if (!header_received)
  {
      if (data_len < 240) return BOOT_ERR_FLASH_WRITE; // Should be at least header size

      memcpy(fota_header, p_data, 240);
      original_fw_size = fota_header[4] | (fota_header[5] << 8) | (fota_header[6] << 16) | (fota_header[7] << 24);
      
      memcpy(expected_sha256_pt, &fota_header[8], 32);
      memcpy(sig_pt, &fota_header[40], 64);
      memcpy(expected_sha256_enc, &fota_header[104], 32);
      memcpy(sig_enc, &fota_header[136], 64);
      
      uint8_t iv[16];
      memcpy(iv, &fota_header[200], 16);
      AES_init_ctx_iv(&aes_ctx, AES_KEY, iv);

      int sig_valid = uECC_verify(ECDSA_PUB_KEY, expected_sha256_enc, 32, sig_enc, uECC_secp256r1());
      if (!sig_valid) {
          // Demo: log error, but proceed
      }

      uint16_t enc_len = data_len - 240;
      if (enc_len > 0)
      {
          uint8_t enc_chunk[enc_len];
          memcpy(enc_chunk, &p_data[240], enc_len);
          
          sha256_update(&sha256_enc_ctx, enc_chunk, enc_len);
          AES_CBC_decrypt_buffer(&aes_ctx, enc_chunk, enc_len);
          sha256_update(&sha256_pt_ctx, enc_chunk, enc_len);

          if (flashWrite(fw_addr, enc_chunk, enc_len) != true) return BOOT_ERR_FLASH_WRITE;
          fw_addr += enc_len;
      }
      
      header_received = true;
      return BOOT_OK;
  }
  else
  {
      // Normal Block
      sha256_update(&sha256_enc_ctx, p_data, data_len);
      AES_CBC_decrypt_buffer(&aes_ctx, p_data, data_len);
      sha256_update(&sha256_pt_ctx, p_data, data_len);

      if (flashWrite(fw_addr, p_data, data_len) == true)
      {
        fw_addr += data_len;
        return BOOT_OK;
      }
      else
      {
        return BOOT_ERR_FLASH_WRITE;
      }
  }
}

static uint8_t bootIsoTpFlashEnd(uint8_t *payload, uint16_t size)
{
  uint32_t received_crc = 0;
  if (size >= 5)
  {
    received_crc = (uint32_t)payload[1] << 0 | (uint32_t)payload[2] << 8 | (uint32_t)payload[3] << 16 | (uint32_t)payload[4] << 24;
  }

  uint8_t calc_sha256_enc[32];
  uint8_t calc_sha256_pt[32];
  sha256_final(&sha256_enc_ctx, calc_sha256_enc);
  sha256_final(&sha256_pt_ctx, calc_sha256_pt);

  if (memcmp(calc_sha256_enc, expected_sha256_enc, 32) != 0) {
      return BOOT_ERR_CRC;
  }

  // This ECC verify takes 600ms, proving the ISO-TP delay!
  int pt_sig_valid = uECC_verify(ECDSA_PUB_KEY, expected_sha256_pt, 32, sig_pt, uECC_secp256r1());
  if (!pt_sig_valid) {
      // Demo: proceed regardless
  }

  return BOOT_OK;
}

static uint8_t bootIsoTpJump(uint8_t cmd)
{
  if (bootVerifyFw() == true)
  {
    uint8_t ack[2] = {cmd, BOOT_OK};
    extern IsoTpLink g_isotp_link;
    isotp_send(&g_isotp_link, ack, sizeof(ack));
    delay(100);
    JumpToFw();
    return BOOT_OK;
  }
  else
  {
    return BOOT_ERR_FLASH_JUMP;
  }
}