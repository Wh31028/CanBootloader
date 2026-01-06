#include "ap.h"




void apInit(void)
{

}

void apMain(void)
{
  uint32_t pre_time;ledOn(_DEF_LED3);

  ledOn(_DEF_LED3);
  ledOn(_DEF_LED4);
  ledOn(_DEF_LED2);
  pre_time = millis();
  while(1)
  {
    if (millis()-pre_time >= 500)
    {
      pre_time = millis();
      ledToggle(_DEF_LED1);
    }
  }
}