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
unit is 32-bit stack words. Hardware measurements should be used before reducing
the initial 256-word AppTask stack.

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

## Hardware verification required

The Release build and static ELF checks pass, but hardware behavior has not yet
been tested for this FreeRTOS image. The development host had no enumerated
ST-LINK or CAN adapter during this work, so flashing and CAN traffic tests could
not be executed. Complete these checks on STM32F103RB:

- Confirm scheduler start and a changing AppTask high-water mark.
- Confirm the one-second LED period.
- Send CAN ID `0x200`, payload `DE AD`, and confirm Custom bootloader entry.
- Complete a normal Custom FOTA update with this image.
- Disconnect CAN during transfer, reconnect it, and confirm the previous
  Application still boots.

Do not treat the milestone as hardware-complete until all five checks pass.
