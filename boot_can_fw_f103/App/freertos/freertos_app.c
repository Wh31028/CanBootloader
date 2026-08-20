#include "freertos_app.h"

#include "FreeRTOS.h"
#include "ap.h"
#include "ecu_ready.h"
#include "task.h"

#define APP_TASK_STACK_WORDS 256U
#define APP_TASK_PRIORITY    (tskIDLE_PRIORITY + 1U)

static StaticTask_t app_task_tcb;
static StackType_t app_task_stack[APP_TASK_STACK_WORDS];
static StaticTask_t idle_task_tcb;
static StackType_t idle_task_stack[configMINIMAL_STACK_SIZE];

static void AppTask(void *argument)
{
  (void)argument;

  ecuReadySetReady();
  apMain();

  freertosAssertFailed();
}

void freertosAppStart(void)
{
  TaskHandle_t app_task;

  app_task = xTaskCreateStatic(AppTask, "AppTask", APP_TASK_STACK_WORDS, NULL,
                               APP_TASK_PRIORITY, app_task_stack, &app_task_tcb);
  if (app_task == NULL)
  {
    freertosAssertFailed();
  }

  vTaskStartScheduler();
  freertosAssertFailed();
}

void vApplicationGetIdleTaskMemory(StaticTask_t **idle_tcb,
                                   StackType_t **idle_stack,
                                   uint32_t *idle_stack_size)
{
  *idle_tcb        = &idle_task_tcb;
  *idle_stack      = idle_task_stack;
  *idle_stack_size = configMINIMAL_STACK_SIZE;
}

void vApplicationStackOverflowHook(TaskHandle_t task, char *task_name)
{
  (void)task;
  (void)task_name;
  freertosAssertFailed();
}

void freertosAssertFailed(void)
{
  taskDISABLE_INTERRUPTS();
  for (;;)
  {
  }
}
