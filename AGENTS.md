# Project Instructions

## Project Purpose

This repository contains a CAN-FOTA system composed of:

- A BeagleBone Black (BBB) Linux gateway using SocketCAN
- STM32F103 firmware, including a CAN bootloader and application
- A Custom CAN FOTA baseline and an ISO-TP comparison implementation

Main directories:

- `boot_can_custom_f103/`: current STM32F103 Custom CAN FOTA bootloader baseline
- `boot_can_fw_f103/`: STM32F103 application
- `boot_can_isotp_f103/`: ISO-TP-based comparison implementation
- `can-fota-BBB/`: BBB flasher, gateway scripts, and web dashboard
- `docs/`: design, protocol, memory-map, verification, and study documents

## Communication and Evidence

- Always respond to the user in Korean.
- Technical terms, command names, APIs, and identifiers may remain in English.
- Prefer English for new code comments.
- Describe implementation behavior only from actual repository files or executed
  verification results.
- Clearly distinguish verified facts, assumptions, plans, and unverified hardware
  behavior.
- Do not claim that a build, test, CAN trace, or board test passed unless it was
  actually executed successfully.

## Security and Privacy

- Never output, add, stage, commit, or push secrets, access tokens, passwords,
  private keys, certificates, personal information, or personal local paths.
- Do not place absolute local paths, private network addresses, or environment
  configuration in source code, documentation, examples, commits, or portfolio
  materials.
- Inspect potentially sensitive files only when necessary and redact sensitive
  values from explanations.

## Change Control

Before modifying files:

1. Inspect relevant code, documents, and `git status`.
2. Present a concise plan and expected diff.
3. Wait for the user's explicit approval.
4. Preserve existing uncommitted changes as user-owned work.

- Do not commit without explicit user approval.
- Do not push to a remote repository without explicit user approval.
- Do not modify unrelated files or remove functionality without explicit request.
- Prefer minimal and targeted changes.

## Yocto

When Yocto sources are present in the workspace:

- Focus primarily on `yocto_capston/meta-can-fota/`.
- Inspect `kas-project.yml` when build configuration is relevant.
- Do not scan or analyze `build/tmp/` unless it is required to diagnose a
  specific build problem.
- Do not modify Poky or meta-openembedded upstream sources unless explicitly
  requested.
- Prefer solving problems in the custom layer.

## STM32 / CAN Compatibility

- Check BBB-side code when protocol behavior is relevant.
- Preserve compatibility for CAN IDs, commands, sequence numbers, payload layout,
  timeouts, retransmission, CRC, Flash layout, and error handling.
- Explain compatibility impact before changing the CAN protocol or Flash layout.
- Update both endpoints and protocol documentation when an approved protocol
  change requires it.

## STM32F103RB Custom FOTA Baseline

- `boot_can_custom_f103` and `boot_can_isotp_f103` reserve `0x08000000`
  through `0x08003FFF` for their 16 KiB bootloaders.
- The application begins at `0x08004000`.
- The Custom FOTA staging area begins at `0x08012000`.
- The Custom FOTA firmware limit is 57,336 B.
- Keep vector tables at `0x08000000` for bootloaders and at `0x08004000` for
  the application.
- The FOTA entry request is CAN ID `0x200` with payload `DE AD`.
- The application writes `0xDEADBEEF` to BKP DR1/DR2 and invokes
  `NVIC_SystemReset()` for FOTA entry.
- The F103 build must use STM32F1 HAL/CMSIS, `startup_stm32f103xb.s`,
  `system_stm32f1xx.c`, and the `STM32F103xB` define.
- Do not include F4 startup, system, or HAL sources in an F103 build.
- Do not add FreeRTOS code or refactor the FOTA/Flash layout unless explicitly
  requested.
- Custom FOTA cannot update the full 112 KiB application range and overlaps a
  64 KiB-or-larger application image.
- ISO-TP is a comparison implementation, not the current Custom FOTA baseline.
- ISO-TP writes directly to `0x08004000`; using its full 112 KiB range requires
  a separate application linker configuration and transfer-size/write-address
  validation.

## Verification and Reporting

After an approved change:

1. Review changed files and `git diff`.
2. Run relevant checks when practical.
3. Report the root cause, files changed, behavior changed, verification
   performed, and remaining concerns.
