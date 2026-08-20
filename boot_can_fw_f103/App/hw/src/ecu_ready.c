#include "ecu_ready.h"

#include "main.h"

bool ecuReadyInit(void)
{
  ecuReadySetNotReady();
  return true;
}

void ecuReadySetReady(void)
{
  HAL_GPIO_WritePin(ECU_READY_GPIO_Port, ECU_READY_Pin, GPIO_PIN_SET);
}

void ecuReadySetNotReady(void)
{
  HAL_GPIO_WritePin(ECU_READY_GPIO_Port, ECU_READY_Pin, GPIO_PIN_RESET);
}
