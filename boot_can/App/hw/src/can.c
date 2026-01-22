#include "can.h"



#ifdef _USE_HW_CAN
#include "cli.h"



static bool is_init = false;


//-- CAN 핸들 선언
//
extern CAN_HandleTypeDef hcan1;

//-- 함수 선언
//
static void canFifoCallback(CAN_HandleTypeDef *_hcan);
static bool canInitFilter(void);


#ifdef _USE_HW_CLI
static void cliCmd(cli_args_t *args);
#endif






bool canInit(void)
{
  bool ret = true;


  //-- Callback 등록
  //

  HAL_StatusTypeDef status;

  status = HAL_CAN_RegisterCallback(&hcan1, HAL_CAN_RX_FIFO0_MSG_PENDING_CB_ID, canFifoCallback);
  if (status != HAL_OK)
  {
    ret &= false;
  }

  //-- 인터럽트 활성화
  //
  uint32_t enable_int;
  
  enable_int = CAN_IT_RX_FIFO0_MSG_PENDING |
               CAN_IT_BUSOFF |
               CAN_IT_ERROR_WARNING |
               CAN_IT_ERROR_PASSIVE |
               CAN_IT_LAST_ERROR_CODE |
               CAN_IT_ERROR;
  status = HAL_CAN_ActivateNotification(&hcan1, enable_int);
  if (status != HAL_OK)
  {
    ret &= false;
  }

  //-- 필터 함수 호출
  //
  canInitFilter();

  //-- CAN 하드웨어 시작
  //
    if (HAL_CAN_Start(&hcan1) != HAL_OK)
  {
    ret &= false;
  }

  is_init = ret;

  logPrintf("[%s] canInit()\n", is_init ? "OK":"E_");

#ifdef _USE_HW_CLI
  cliAdd("can", cliCmd);
#endif
  return true;
}

//-- 필터 함수 구현
//
bool canInitFilter(void)
{
  bool              ret = false;
  CAN_FilterTypeDef sFilterConfig;


  sFilterConfig.FilterBank           = 0;
  sFilterConfig.FilterScale          = CAN_FILTERSCALE_32BIT;
  sFilterConfig.FilterFIFOAssignment = CAN_RX_FIFO0;
  sFilterConfig.FilterActivation     = ENABLE;
  sFilterConfig.SlaveStartFilterBank = 14;

  sFilterConfig.FilterIdHigh     = ((0 >> 13) & 0xFFFF);
  sFilterConfig.FilterIdLow      = ((0 << 3) & 0xFFF8);
  sFilterConfig.FilterMaskIdHigh = ((0 >> 13) & 0xFFFF);
  sFilterConfig.FilterMaskIdLow  = ((0 << 3) & 0xFFF8);

  sFilterConfig.FilterMode = CAN_FILTERMODE_IDMASK;

  if (HAL_CAN_ConfigFilter(&hcan1, &sFilterConfig) == HAL_OK)
  {
    ret = true;
  }

  return ret;
}

//-- Fifo 콜백 함수
//
static bool is_received = false;
static CAN_RxHeaderTypeDef rx_header;
static uint8_t rx_buf[8];

void canFifoCallback(CAN_HandleTypeDef *p_hcan)
{
  if (HAL_CAN_GetRxMessage(p_hcan, CAN_RX_FIFO0, &rx_header, rx_buf) == HAL_OK)
  {
    is_received = true;
  }
}

#ifdef _USE_HW_CLI
void cliCmd(cli_args_t *args)
{
  bool ret = false;


  if (args->argc == 1 && args->isStr(0, "info"))
  {
    cliPrintf("is_init : %s\n", is_init ? "true":"false");
    ret = true;
  }

  //-- Send 명령 시험
  //
  if (args->argc == 1 && args->isStr(0, "send"))
  {
    CAN_TxHeaderTypeDef tx_header;
    uint32_t tx_mailbox;
    uint8_t tx_buf[8];

    tx_header.ExtId = 100 & 0x1FFFFFFF;
    tx_header.IDE   = CAN_ID_EXT;
    tx_header.DLC   = 1;
    tx_header.RTR   = CAN_RTR_DATA;
    tx_header.TransmitGlobalTime = DISABLE;

    tx_buf[0] = 1;

    is_received = false;
    if (HAL_CAN_GetTxMailboxesFreeLevel(&hcan1) > 0)
    {
      if(HAL_CAN_AddTxMessage(&hcan1, &tx_header, tx_buf, &tx_mailbox) == HAL_OK)
      {
        cliPrintf("send ok\n");
      }
    }
    ret = true;
  }

  //-- Read 명령 시험
  //
  if (args->argc == 1 && args->isStr(0, "read"))
  {
    if (is_received)
    {
      is_received = false;
      cliPrintf("type %s id %d,  dlc %d, data[0]=%d\n",
               rx_header.IDE == CAN_ID_STD ? "STD":"EXT",
               rx_header.IDE == CAN_ID_STD ? rx_header.StdId:rx_header.ExtId,
               rx_header.DLC,
               rx_buf[0]);
    }
    else
    {
      cliPrintf("No Message\n");
    }
    ret = true;
  }

  if (ret == false)
  {
    cliPrintf("can info\n\r");
    //-- Send/Read 명령
    //
    cliPrintf("can send\n\r");
    cliPrintf("can read\n\r");
  }
}
#endif

#endif
