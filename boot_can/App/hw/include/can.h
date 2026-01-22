#ifndef CAN_H_
#define CAN_H_

#ifdef __cplusplus
extern "C" {
#endif

#include "hw_def.h"

#ifdef _USE_HW_CAN

#define CAN_MAX_CH  HW_CAN_MAX_CH



bool canInit(void);


#endif

#ifdef __cplusplus
}
#endif

#endif
