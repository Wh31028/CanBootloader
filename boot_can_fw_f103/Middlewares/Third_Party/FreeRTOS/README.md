# FreeRTOS kernel source

This directory contains the minimal FreeRTOS kernel sources used by the
STM32F103RB application.

- Kernel version: FreeRTOS V10.3.1
- Source package: STM32Cube_FW_F1_V1.8.6
- Port: `portable/GCC/ARM_CM3`
- License: MIT; see `Source/LICENSE`

The source was copied from the locally installed STM32Cube F1 firmware package.
Only `tasks.c`, `list.c`, the public headers, and the GCC Cortex-M3 port are
included. Dynamic allocation, queues, event groups, stream buffers, and the
software timer service are not part of this application build.
