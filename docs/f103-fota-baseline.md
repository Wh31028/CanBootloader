# STM32F103RB Custom FOTA Baseline

## Purpose

This document records the F103 FOTA baseline before FreeRTOS work begins.
The Custom CAN bootloader flow is the selected baseline. FreeRTOS code is not
included in this baseline.

## Build Environment

- Host: Windows
- Toolchain: STM32CubeCLT 1.19.0, ARM GNU Toolchain 13.3.1
- Build system: CMake 3.28.1 and Ninja
- Build profile: Release

Build commands:

```powershell
cmake --preset Release -S boot_can_custom_f103
cmake --build boot_can_custom_f103/build/Release
cmake --preset Release -S boot_can_isotp_f103
cmake --build boot_can_isotp_f103/build/Release
cmake --preset Release -S boot_can_fw_f103
cmake --build boot_can_fw_f103/build/Release
```

## Release Build Results

| Image | BIN size | FLASH | RAM | Vector table | Reset_Handler |
| --- | ---: | ---: | ---: | --- | --- |
| Custom Bootloader | 8,632 B | 8,632 / 16,384 B (52.69%) | 3,184 / 20,480 B (15.55%) | `0x08000000` | `0x080018B0` |
| ISO-TP Bootloader | 12,364 B | 12,364 / 16,384 B (75.46%) | 3,928 / 20,480 B (19.18%) | `0x08000000` | `0x080019A4` |
| Custom Application | 7,772 B | 7,772 / 57,336 B (13.56%) | 3,416 / 20,480 B (16.68%) | `0x08004000` | `0x08005A00` |

The Application linker region is `0x08004000` through `0x08011FF7`
(`57,336 B`). This matches the maximum Custom firmware size and leaves the
staging region at `0x08012000` through `0x0801FFFF`.

All three builds produced `.elf`, `.bin`, `.hex`, and `.map` files.

## Address and HAL Validation

- Both bootloaders link in `0x08000000` through `0x08003FFF` (16 KB).
- The Custom Application starts at `0x08004000` and is hard-limited to
  `57,336 B`; it cannot overlap Custom staging.
- Physical Flash ends at `0x08020000`.
- Actual build commands use `STM32F1xx_HAL_Driver`,
  `CMSIS/Device/ST/STM32F1xx`, `startup_stm32f103xb.s`,
  `system_stm32f1xx.c`, and `STM32F103xB`.
- No actual F103 build command includes `STM32F4xx_HAL_Driver`,
  `startup_stm32f407xx.s`, or `system_stm32f4xx.c`.

## Custom FOTA Flow

1. The Application receives CAN ID `0x200` with payload `DE AD`.
2. It stores `0xDEADBEEF` in BKP DR1/DR2 and calls `NVIC_SystemReset()`.
3. The Custom Bootloader detects the magic value and enters FOTA mode.
4. Firmware is downloaded to staging at `0x08012000`.
5. After CRC validation, the Bootloader copies the staged firmware to the
   Application region at `0x08004000`.

This protects the existing Application when download transmission is
interrupted before staging validation completes. It is not a full A/B rollback
implementation for power loss during the final copy operation.

## Baseline Constraints

- FreeRTOS is not part of this baseline.
- Application CLI and debug print paths are disabled for the Custom image.
- The Application is built with `-Os`.
- The Custom protocol cannot update an Application larger than 57,336 B.
- ISO-TP direct-write remains outside this baseline. It has no staging and
  needs independent transfer-size and write-range hardening before use.

## Hardware Verification Status

- Custom FOTA successfully transferred on the STM32F103RB hardware, as
  confirmed by the developer.
- During an interrupted download, disconnecting and reconnecting CAN allowed
  the existing Application to boot normally, as confirmed by the developer.
- The repository has no CAN trace or execution log for this run.

## Known Build Warnings

- `FLASH_PAGE_SIZE` is redefined in the F103 Flash source files.
- The ISO-TP Bootloader also reports an unused `SendResponse` function.
