#ifndef ECU_READY_H_
#define ECU_READY_H_

#include <stdbool.h>

bool ecuReadyInit(void);
void ecuReadySetReady(void);
void ecuReadySetNotReady(void);

#endif
