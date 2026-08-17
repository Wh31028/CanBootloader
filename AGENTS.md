# Project Instructions

## Project Overview

This repository workspace contains a CAN-based FOTA project.

Main components:

- `CanBootloader/`
  - STM32 CAN bootloader implementations.
  - Contains Custom CAN protocol and ISO-TP implementations.
  - Contains BBB-side CAN/FOTA applications.

- `yocto_capston/meta-can-fota/`
  - Custom Yocto layer for the BeagleBone Black FOTA system.

- `yocto_capston/kas-project.yml`
  - kas configuration for the Yocto project.

The STM32 bootloader, BBB application, and Yocto layer are related parts
of the same CAN FOTA system.

## Communication

- Always respond to the user in Korean.
- Technical terms, command names, APIs, and identifiers may remain in English.
- Code comments should preferably be written in English.

## General Rules

- Inspect existing code before making changes.
- Understand the relationship between BBB and STM32 code when relevant.
- Prefer minimal and targeted changes.
- Do not modify unrelated files.
- Do not remove existing functionality unless explicitly requested.
- Do not automatically commit changes.
- Do not push to remote repositories unless explicitly requested.

## Existing Changes

Before modifying files:

1. Check `git status` when working inside a Git repository.
2. Treat existing uncommitted changes as user-owned work.
3. Do not revert, overwrite, or discard existing user changes.
4. If a requested modification conflicts with existing changes, explain the
   conflict before proceeding.

## Yocto

When working with Yocto:

- Focus primarily on `yocto_capston/meta-can-fota/`.
- Inspect `kas-project.yml` when build configuration is relevant.
- Do not scan or analyze `build/tmp/` unless it is required to diagnose a
  specific build problem.
- Do not modify Poky or meta-openembedded upstream sources unless explicitly
  requested.
- Prefer solving problems in the custom layer.

## STM32 / CAN

When working with STM32 bootloader code:

- Check the corresponding BBB-side implementation when protocol behavior is
  relevant.
- Pay attention to CAN ID, command ID, sequence number, payload layout,
  timeout, retransmission, and error handling.
- Preserve compatibility between BBB and STM32 implementations.
- Do not change the CAN protocol format without explicitly explaining the
  compatibility impact.

## STM32F103RB FOTA Baseline

- `boot_can_custom_f103` and `boot_can_isotp_f103` are 16 KB bootloaders:
  `0x08000000` through `0x08003FFF`.
- The Custom FOTA baseline links `boot_can_fw_f103` at `0x08004000` with a
  57,336-byte region ending at `0x08011FF8`; staging begins at `0x08012000`.
- Keep the vector tables at `0x08000000` for both bootloaders and at
  `0x08004000` for the application.
- The F103 builds must use STM32F1 HAL/CMSIS, `startup_stm32f103xb.s`,
  `system_stm32f1xx.c`, and the `STM32F103xB` define. Do not include F4
  startup, system, or HAL sources in an F103 build.
- Do not add FreeRTOS code or refactor the FOTA/Flash layout unless explicitly
  requested.
- Custom FOTA uses staging at `0x08012000` and supports at most 57,336 bytes
  of firmware. It cannot update the full 112 KB application and overlaps a
  64 KB-or-larger application image.
- ISO-TP FOTA writes directly to `0x08004000` without staging. It is not the
  current baseline; using its full 112 KB range requires a separate
  application linker configuration and transfer-size/write-address validation.
- The FOTA entry path is CAN ID `0x200` with payload `DE AD`; the application
  writes `0xDEADBEEF` to BKP DR1/DR2 and invokes `NVIC_SystemReset()`.

## Verification

After modifying code:

1. Review the changed files.
2. Check `git diff`.
3. Run relevant build or tests when practical.
4. Report:
   - root cause
   - files changed
   - what was changed
   - verification performed
   - remaining concerns

Do not claim that a build or test succeeded unless it was actually executed
successfully.
