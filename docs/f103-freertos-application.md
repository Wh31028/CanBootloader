# STM32F103RB FreeRTOS Application Milestone

## Scope and design decision

The first milestone wraps the existing Custom FOTA application behavior in one
FreeRTOS task. The Custom CAN protocol, bootloader, staging/copy flow, and Flash
layout are unchanged.

Startup is:

1. `HAL_Init()` and the existing clock/peripheral initialization.
2. `hwInit()` and `apInit()`.
3. Static creation of `AppTask`.
4. `vTaskStartScheduler()`.
5. `AppTask` runs the existing `apMain()` LED and CAN polling loop.

The CAN RX interrupt callback still writes received frames to the existing
64-entry ring buffer. `AppTask` polls that buffer every 1 ms. CAN ID `0x200`
with payload `DE AD` still writes `0xDEADBEEF` to BKP DR1/DR2 and resets into
the Custom bootloader.

## FreeRTOS source

- FreeRTOS kernel: V10.3.1
- STM32 package: STM32Cube_FW_F1_V1.8.6
- Compiler port: `portable/GCC/ARM_CM3`
- Included kernel sources: `tasks.c`, `list.c`, and `port.c`
- Allocation: static only
- Software timer service: disabled

The source came from the locally installed STM32Cube F1 firmware repository;
no external download was used.

## SysTick and HAL tick

Both the STM32 HAL and the FreeRTOS Cortex-M3 port use SysTick. The selected
configuration shares one 1 kHz SysTick:

- Before scheduler start, `SysTick_Handler()` only calls `HAL_IncTick()`.
- After scheduler start, it calls `HAL_IncTick()` and then
  `xPortSysTickHandler()`.
- The Cortex-M3 port directly owns the SVC and PendSV handlers.

This preserves `HAL_GetTick()`/`millis()` behavior without adding another HAL
timer. `HAL_InitTick()` initially configures the HAL 1 kHz tick, and the
FreeRTOS port configures SysTick to the same `configTICK_RATE_HZ` when the
scheduler starts. The FOTA-entry wait uses `vTaskDelay()` in task context rather
than busy-waiting in `HAL_Delay()`.

## Task and RAM configuration

| Item | Allocation | Rationale |
| --- | ---: | --- |
| AppTask stack | 256 words / 1,024 B | Conservative first-board-test value for the existing shallow polling loop and HAL calls |
| Idle stack | 128 words / 512 B | FreeRTOS minimum stack, with no idle hook |
| AppTask + Idle TCB | 120 B | Two 60-byte static TCBs in this build |
| FreeRTOS heap | 0 B | `configSUPPORT_DYNAMIC_ALLOCATION=0`; no heap implementation is linked |
| Linker C heap reserve | 512 B | Existing `_Min_Heap_Size`; not a FreeRTOS heap |
| Linker MSP reserve | 1,024 B | Existing `_Min_Stack_Size` for startup and interrupts |

`configCHECK_FOR_STACK_OVERFLOW=2` is enabled. The debugger-visible volatile
symbol `g_app_task_stack_high_water_mark_words` records
`uxTaskGetStackHighWaterMark(NULL)` at task entry and once per LED period. Its
unit is 32-bit stack words. Hardware testing measured a minimum remaining value
of 224 words (896 B), so the maximum observed AppTask stack use was 32 words
(128 B). Keep the initial 256-word AppTask stack until future task features have
also been measured.

## Release build verification

Commands:

```powershell
cmake --preset Release -S boot_can_fw_f103
cmake --build boot_can_fw_f103/build/Release
```

Tools:

- STM32CubeCLT 1.19.0
- GNU Tools for STM32 13.3.1 (`13.3.rel1`)
- CMake 3.28.1
- Ninja 1.11.1
- Build flags: Release, `-Os`, CLI/debug print disabled

Generated files: `boot_can_fw.elf`, `boot_can_fw.bin`, `boot_can_fw.hex`, and
`boot_can_fw.map`.

| Measurement | Result |
| --- | ---: |
| ELF file size | 33,872 B |
| BIN image / linker FLASH use | 10,092 B / 57,336 B (17.60%) |
| FLASH headroom | 47,244 B |
| Linker RAM use | 5,304 B / 20,480 B (25.90%) |
| RAM headroom | 15,176 B |
| `.isr_vector` | 268 B at `0x08004000` |
| `.text` | 9,740 B |
| `.rodata` | 56 B |
| `.data` | 16 B |
| `.bss` | 3,748 B |
| `._user_heap_stack` | 1,540 B |
| `Reset_Handler` | `0x080059F0` |

The four-byte alignment gap after `.isr_vector` explains why the 10,092-byte
linker/BIN FLASH use is four bytes larger than the sum reported by the standard
`size` text and data columns.

RAM increased by 1,888 B from the 3,416-byte baseline. This comprises the
1,536 B of explicit task stacks, 120 B of TCBs, the 4-byte high-water diagnostic,
and 228 B of scheduler/port state and alignment. No FreeRTOS heap array is
present.

The actual compile database uses `STM32F103xB`, STM32F1 HAL/CMSIS,
`startup_stm32f103xb.s`, and `system_stm32f1xx.c`. It contains no F4 startup,
system, HAL source, or include path.

## Hardware verification

All first-milestone checks passed on STM32F103RB:

- FreeRTOS scheduler started; AppTask high-water mark was 224 words.
- LED one-second period: PASS.
- CAN ID `0x200`, payload `DE AD` Custom bootloader entry: PASS.
- Normal Custom FOTA update: PASS.
- CAN disconnect during transfer followed by reconnect and existing Application
  boot: PASS.

The FreeRTOS Application first milestone is hardware-complete. The interrupted
transfer result covers the existing Custom staging validation behavior; it does
not add full A/B rollback protection for power loss during the final copy.

## ECU_READY GPIO milestone (V3.2)

`ECU_READY` is a level status signal, not a heartbeat. It uses STM32F103RB
`PA6` (NUCLEO-F103RB Morpho `CN10 pin 13`) connected to BBB `P9_12`
(`gpio1_28`). The Yocto BBB kernel patch configures `P9_12` as GPIO input with
an internal pull-down; the hardware must also fit an external 10 kOhm pull-down
from the net to the common ground.

| STM32 state | ECU_READY |
| --- | --- |
| Reset, bootloader, FOTA transfer, AppTask not yet running, or not ready | LOW |
| `hwInit()` and `apInit()` completed, scheduler started, and `AppTask` entered | HIGH |
| CAN ID `0x200`, payload `DE AD`, before FOTA magic/reset | LOW |

The CubeMX PA6 configuration is output push-pull, no pull, low speed, with
the generated initial output level LOW. `ecu_ready` sets LOW again during
hardware initialization, raises it at the start of `AppTask`, and lowers it
before the unchanged FOTA magic write and `NVIC_SystemReset()` call. No extra
FreeRTOS task is used.

The STM32 reset/bootloader state can leave the GPIO Hi-Z, so the external
pull-down—not MCU firmware—is the hardware guarantee that BBB reads LOW.
Both ends must use 3.3 V logic and share GND. Do not connect the signal to 5 V.
Reserve a separate GPIO/net for any future HEARTBEAT signal.

Hardware verification after wiring:

1. Confirm the external 10 kOhm pull-down and common GND, then observe the net
   with a scope or logic analyzer.
2. Reset STM32: verify LOW through reset and bootloader.
3. Boot the Application: verify HIGH only after AppTask begins running.
4. Send `cansend can0 200#DEAD`: verify LOW occurs before reset and remains LOW
   during Custom FOTA.
5. Complete a Custom FOTA update: verify the new Application returns HIGH only
   after its AppTask starts. Verify any future HEARTBEAT on a separate net.
