#include "can.h"

#ifdef _USE_HW_CAN
#include "cli.h"
#include "qbuffer.h"

#define CAN_RX_QUEUE_LEN  64U
#define CAN_STD_ID_MAX    0x7FFU
#define CAN_MAX_DLC_BYTES 8U

static bool is_init = false;

// Diagnostic counters, read over SWD (no UART/CLI output in the bootloader).
volatile uint32_t g_can_rx_queue_drop_count   = 0; // software queue full
volatile uint32_t g_can_rx_fifo_overrun_count = 0; // bxCAN RX FIFO1 overrun
volatile uint32_t g_can_busoff_count          = 0; // bus-off entries

//-- CAN 핸들 선언
//
extern CAN_HandleTypeDef hcan;
static qbuffer_t q_rx;
static can_msg_t q_rx_msg[CAN_RX_QUEUE_LEN];

//-- 함수 선언
//
static void canFifoCallback(CAN_HandleTypeDef *_hcan);
static void canErrorCallback(CAN_HandleTypeDef *p_hcan);
static bool canInitFilter(void);

#ifdef _USE_HW_CLI
static void cliCmd(cli_args_t *args);
#endif

bool canInit(void)
{
  bool ret = true;

  qbufferCreateBySize(&q_rx, (uint8_t *)&q_rx_msg[0], sizeof(can_msg_t),
                      CAN_RX_QUEUE_LEN);

  //-- Callback 등록
  //

  HAL_StatusTypeDef status;

  status = HAL_CAN_RegisterCallback(&hcan, HAL_CAN_RX_FIFO1_MSG_PENDING_CB_ID,
                                    canFifoCallback);
  if (status != HAL_OK)
  {
    ret = false;
  }

  status =
      HAL_CAN_RegisterCallback(&hcan, HAL_CAN_ERROR_CB_ID, canErrorCallback);
  if (status != HAL_OK)
  {
    ret = false;
  }

  //-- 인터럽트 활성화
  //
  if (HAL_CAN_ActivateNotification(
          &hcan, CAN_IT_RX_FIFO1_MSG_PENDING | CAN_IT_RX_FIFO1_OVERRUN |
                     CAN_IT_BUSOFF | CAN_IT_ERROR) != HAL_OK)
  {
    ret = false;
  }

  //-- 필터 함수 호출
  //
  if (!canInitFilter())
  {
    ret = false;
  }

  //-- CAN 하드웨어 시작
  //
  if (ret && HAL_CAN_Start(&hcan) != HAL_OK)
  {
    ret = false;
  }

  is_init = ret;

  logPrintf("[%s] canInit()\n", is_init ? "OK" : "E_");

#ifdef _USE_HW_CLI
  cliAdd("can", cliCmd);
#endif
  return is_init;
}

bool canIsInit(void) { return is_init; }

//-- 필터 함수 구현
//
bool canInitFilter(void)
{
  bool ret = false;
  CAN_FilterTypeDef sFilterConfig;

  sFilterConfig.FilterBank           = 0;
  sFilterConfig.FilterScale          = CAN_FILTERSCALE_32BIT;
  sFilterConfig.FilterFIFOAssignment = CAN_RX_FIFO1;
  sFilterConfig.FilterActivation     = ENABLE;
  sFilterConfig.SlaveStartFilterBank = 14;

  sFilterConfig.FilterIdHigh     = ((0 >> 13) & 0xFFFF);
  sFilterConfig.FilterIdLow      = ((0 << 3) & 0xFFF8);
  sFilterConfig.FilterMaskIdHigh = ((0 >> 13) & 0xFFFF);
  sFilterConfig.FilterMaskIdLow  = ((0 << 3) & 0xFFF8);

  sFilterConfig.FilterMode = CAN_FILTERMODE_IDMASK;

  if (HAL_CAN_ConfigFilter(&hcan, &sFilterConfig) == HAL_OK)
  {
    ret = true;
  }

  return ret;
}

// --- [API 구현] AP 폴더에서 사용할 함수들 ---

// 수신된 메시지 개수 확인
uint32_t canAvailable(void) { return qbufferAvailable(&q_rx); }

// 메시지 읽기 (꺼내오기)
bool canMsgRead(can_msg_t *p_msg)
{
  return qbufferRead(&q_rx, (uint8_t *)p_msg, 1);
}

// 메시지 보내기 (비글본으로 ACK 보낼 때 사용)
bool canMsgWrite(uint32_t id, uint8_t *p_data, uint8_t len)
{
  CAN_TxHeaderTypeDef tx_header;
  uint32_t tx_mailbox;

  if (!is_init || p_data == NULL || id > CAN_STD_ID_MAX ||
      len > CAN_MAX_DLC_BYTES)
    return false;

  // All Custom/FOTA IDs are 11-bit; send Standard frames to match the host.
  tx_header.StdId              = id;
  tx_header.ExtId              = 0;
  tx_header.IDE                = CAN_ID_STD;
  tx_header.RTR                = CAN_RTR_DATA;
  tx_header.DLC                = len;
  tx_header.TransmitGlobalTime = DISABLE;

  if (HAL_CAN_GetTxMailboxesFreeLevel(&hcan) > 0)
  {
    if (HAL_CAN_AddTxMessage(&hcan, &tx_header, p_data, &tx_mailbox) == HAL_OK)
    {
      return true;
    }
  }
  return false;
}
// -------------------------------------------

//-- Fifo 콜백 함수
//

void canFifoCallback(CAN_HandleTypeDef *hcan)
{
  CAN_RxHeaderTypeDef rx_header;
  can_msg_t can_msg;

  if (hcan->Instance == CAN1)
  {
    if (HAL_CAN_GetRxMessage(hcan, CAN_RX_FIFO1, &rx_header, can_msg.data) == HAL_OK)
    {
      can_msg.id =
          rx_header.IDE == CAN_ID_STD ? rx_header.StdId : rx_header.ExtId;
      can_msg.id_type = rx_header.IDE == CAN_ID_STD ? CAN_STD : CAN_EXT;
      can_msg.dlc     = rx_header.DLC;

      if (!qbufferWrite(&q_rx, (uint8_t *)&can_msg, 1))
      {
        g_can_rx_queue_drop_count++;
      }
    }
  }
}

// HAL accumulates error bits in ErrorCode; reset after each callback so every
// event is counted once.
static void canErrorCallback(CAN_HandleTypeDef *p_hcan)
{
  uint32_t err = HAL_CAN_GetError(p_hcan);

  if ((err & HAL_CAN_ERROR_RX_FOV1) != 0U)
  {
    g_can_rx_fifo_overrun_count++;
  }
  if ((err & HAL_CAN_ERROR_BOF) != 0U)
  {
    g_can_busoff_count++;
  }
  (void)HAL_CAN_ResetError(p_hcan);
}
#ifdef _USE_HW_CLI
void cliCmd(cli_args_t *args)
{
  bool ret = false;

  if (args->argc == 1 && args->isStr(0, "info"))
  {
    cliPrintf("is_init : %s\n\r", is_init ? "true" : "false");
    cliPrintf("q_avail : %d\n\r", canAvailable());
    cliPrintf("rx_drop : %lu\n\r", (unsigned long)g_can_rx_queue_drop_count);
    cliPrintf("rx_ovr  : %lu\n\r", (unsigned long)g_can_rx_fifo_overrun_count);
    cliPrintf("bus_off : %lu\n\r", (unsigned long)g_can_busoff_count);
    ret = true;
  }

  // send 0x100 1 2 3 ...
  if (args->argc >= 3 && args->isStr(0, "send"))
  {
    uint32_t id = (uint32_t)args->getData(1);
    uint8_t len = 0;
    uint8_t data[8];

    for (int i = 0; i < 8; i++)
    {
      if (args->argc > (2 + i))
      {
        data[i] = (uint8_t)args->getData(2 + i);
        len++;
      }
    }

    if (canMsgWrite(id, data, len))
      cliPrintf("Send OK\n\r");
    else
      cliPrintf("Send Fail\n\r");

    ret = true;
  }

  if (args->argc == 1 && args->isStr(0, "read"))
  {
    while (canAvailable() > 0)
    {
      can_msg_t msg;
      canMsgRead(&msg);

      cliPrintf("Rx ID:0x%X Type:%s DLC:%d Data:", msg.id,
                msg.id_type == CAN_STD ? "STD" : "EXT", msg.dlc);

      for (int i = 0; i < msg.dlc; i++)
      {
        cliPrintf("0x%02X ", msg.data[i]);
      }
      cliPrintf("\n\r");
    }
    ret = true;
  }

  if (ret == false)
  {
    cliPrintf("can info\n\r");
    cliPrintf("can send [id] [data1] ...\n\r");
    cliPrintf("can read\n\r");
  }
}
#endif

#endif
