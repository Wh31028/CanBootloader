# CLAUDE.md

CAN-based FOTA: a BeagleBone Black (BBB, Linux/SocketCAN) gateway updates an
STM32F103RB (NUCLEO-F103RB) over Classic CAN. `main` = F103 Custom CAN FOTA
baseline; ISO-TP is a comparison path only.

## Working rules

- Respond to the user in Korean. Identifiers, commands, and technical terms may stay in English. New code comments in English.
- State only what repo files or executed commands show. Separate verified facts, assumptions, and unverified hardware behavior. Never claim a build, CAN trace, or board test passed unless it was run.
- Before modifying files: inspect code/docs and `git status`, present a short plan and expected diff, and wait for approval. Treat existing uncommitted changes as the user's work.
- No commit or push without explicit approval. Keep changes minimal; don't touch unrelated files or remove functionality.
- Never write secrets, personal info, absolute local paths, or private IP addresses into code, docs, or commits. `web_dashboard/startup.sh` and the `*_lte_gateway*.py` scripts already contain environment-specific values; do not copy them elsewhere.

## Layout

| Path | Side | Role |
| --- | --- | --- |
| `boot_can_custom_f103/` | STM32 | Custom CAN bootloader (baseline). Protocol: `App/ap/boot_can/boot_can.[ch]`, layout: `App/hw/hw_def.h` |
| `boot_can_fw_f103/` | STM32 | FreeRTOS application (`App/freertos/`), FOTA entry, `ECU_READY` |
| `boot_can_isotp_f103/` | STM32 | ISO-TP comparison bootloader (`iso15765` = isotp-c submodule) |
| `can-fota-BBB/flasher/` | BBB | C SocketCAN flasher (current). Protocol constants: `protocol.h` |
| `can-fota-BBB/web_dashboard/` | BBB | FastAPI dashboard; runs the flasher binary |
| `can-fota-BBB/can_fota_flasher.c`, `*_lte_gateway*.py` | BBB | Legacy, not built by the Makefile; not the reference implementation |
| `docs/` | Shared | `protocol.md` (normative spec), `memory-map.md`, `architecture.md`, `coding-style.md`, `verification/` (build and board test reports) |

Work plans, task status, and study/interview notes live in a separate private
repository, not here. Keep this repo's docs focused on design and verification evidence.

Yocto layer lives in a separate repository (known source drift vs. `can-fota-BBB/`).
Known leftovers, do not "fix" unasked: stale `boot_can_isotp` entry in `.gitmodules`,
`boot_can_custom_f103/boot_can_isotp_f103.ioc` filename, unused `Core/Src/system_stm32f4xx.c`.

## Build

STM32 (Arm GNU `arm-none-eabi-`, CMake + Ninja; presets `Debug`/`Release` → `build/<preset>/`):

```sh
cd boot_can_custom_f103 && cmake --preset Release && cmake --build --preset Release   # boot_can_custom_f103.{elf,bin,hex}
cd boot_can_fw_f103     && cmake --preset Release && cmake --build --preset Release   # boot_can_fw.{elf,bin,hex}
```

- Without a build type, `CMakeLists.txt` defaults to `MinSizeRel`.
- ISO-TP: run `git submodule update --init` first. Builds since TW-04 (`isotp_port.h` now includes `<stdint.h>` before `isotp.h`; see `docs/verification/TW-04-isotp-build.md`). Its `CMakeLists.txt` forces `MinSizeRel` and `-Os`, so the `Debug`/`Release` presets produce the same binary.
- F103 builds must use STM32F1 HAL/CMSIS, `startup_stm32f103xb.s`, `system_stm32f1xx.c`, define `STM32F103xB`. Never add F4 sources.

BBB flasher: build natively on the BBB (needs Linux `linux/can.h`; does not build on macOS):

```sh
cd can-fota-BBB && make        # produces can-fota-BBB/can_fota_flasher
```

Cross-compiling (`make CC=arm-linux-gnueabihf-gcc`) is possible via `CC ?= gcc` but is not set up or verified.

## Flash and run

- STM32: ST-LINK V2 over SWD. Bootloader `.bin` → `0x08000000`, application `.bin` → `0x08004000`. (Programming tool/command not yet documented.)
- Flasher: `./can_fota_flasher <custom|isotp> <firmware.bin> [iface]` (iface default `can0`).
- Dashboard: in `web_dashboard/`, `python3 -m uvicorn main:app --host 0.0.0.0 --port 8000`. It re-runs `ip link set can0 down/up` at each FOTA start (interrupts running `candump`).

## CAN configuration

- Bitrate 500 kbit/s on both sides: `ip link set can0 up type can bitrate 500000`. STM32 bxCAN: APB1 36 MHz, Prescaler 4, BS1 14 tq, BS2 3 tq.
- Interface `can0`. STM32 CAN pins PA11 (RX) / PA12 (TX), no remap.
- IDs: `0x200` FOTA entry (shared); Custom `0x100` BBB→STM32 cmd, `0x101` STM32→BBB response; ISO-TP `0x7E0` / `0x7E8` (Standard).
- All Custom frames use Standard 11-bit IDs. Since TW-03 B the F103 `canMsgWrite()` sends Standard frames (response `101#...` in `candump`); older target firmware sent Extended (`00000101#...`). BBB masks with `CAN_SFF_MASK`, so it accepts both.
- F103 CAN diagnostics (bootloader and app): `g_can_rx_queue_drop_count`, `g_can_rx_fifo_overrun_count`, `g_can_busoff_count`. The bootloader has no UART/CLI output, so read them over SWD (address from `arm-none-eabi-nm`). `canInit()` returns the real init result; the bootloader jumps to a valid app (or halts with LED on) instead of entering FOTA mode when CAN init fails.

## Custom FOTA protocol (details: `docs/protocol.md`)

- Entry: `0x200#DEAD` → app writes `0xDEADBEEF` to BKP DR1/DR2 → `NVIC_SystemReset()`. BBB waits 3 s, flushes RX, then sends START.
- Byte 0 = `(cmd << 6) | seq6`. Commands: DATA `0`, START `0x40` (+u32 size LE, DLC 5), END `0x80` (+u32 CRC32 LE, DLC 5), JUMP `0xC0` (DLC 1).
- DATA: 256 B blocks, 7 B per frame, seq 0–36 per block (resets each block). All integers little-endian.
- Responses: ACK `0x00 0x00`; NACK `0x40` + 56-bit received bitmap (BBB resends only 0-bits); ERR `0x80 | code` (`0x03`–`0x0B`, see spec).
- BBB timeouts: START/END 10 s, DATA block 150 ms per attempt (resends the last frame to provoke NACK/ACK), 20 retries per block, 120 s DATA phase, JUMP ACK 1 s. TX `ENOBUFS` retried up to 100 ms. Exit code = `fota_err_t` (see `docs/protocol.md`).
- Integrity: CRC32 (reflected `0xEDB88320`, init/xorout `0xFFFFFFFF`) over the original size. Staging → CRC check → copy to active with the first 8 B (SP + Reset vector) written last → vector/range check. Boot retries the copy from staging if active is invalid.
- Known limit: no session/block ID, so a lost ACK can desync block boundaries.

## Do not change without explicit approval

Explain compatibility impact first. A protocol change must update the STM32 bootloader,
BBB flasher, and `docs/protocol.md` together.

- Flash layout (F103RB, 128 KiB): bootloader `0x08000000`–`0x08003FFF` (16 KiB, vector at `0x08000000`); active app `0x08004000`–`0x08011FF7` (vector at `0x08004000`, linker `56K - 8`); staging `0x08012000`; metadata size `0x0801FFF8`, CRC `0x0801FFFC`. Firmware limit 57,336 B (START rejects larger sizes with `ERR 0x08`).
- CAN IDs, header bit layout, block/sequence sizes, timeouts, CRC parameters, error codes.
- Pins/clocks: HSE + PLL x9 (72 MHz), CAN PA11/PA12, USART1 PA9/PA10, LED PA5, `ECU_READY` PA6 (app), `SWJ_NOJTAG` remap. CubeMX-generated files (`Core/`, `Drivers/`, `Middlewares/`, startup) are regenerated from `.ioc`.
- No FreeRTOS in bootloaders; no layout refactor. ISO-TP writes directly to `0x08004000`; its declared 112 KiB range is not supported by the current app linker.

## Coding rules (full: `docs/coding-style.md`)

- Format with each project's `.clang-format` (LLVM, 2-space, Allman). Never mix format-only and functional changes.
- Named constants with units (`_MS`, `_BYTES`) for addresses, sizes, DLC, timeouts; protocol prefixes `CUSTOM_`, `ISOTP_`, `BOOT_`.
- Validate ID, DLC, command, sequence, and size before using a frame. Never ignore Flash/CAN/CRC/jump errors.
- Bootloader: no heap, recursion, or unbounded retries. Keep existing STM32 CamelCase APIs; BBB uses `lower_snake_case`.

## Testing

1. Build every changed target (commands above) and check the memory usage summary.
2. On the BBB: `ip -details link show can0` should show `UP`, `ERROR-ACTIVE`, and bitrate 500000.
3. Trace: `candump -L can0` (run in another terminal; restart it if the dashboard resets `can0`).
4. Manual entry: `cansend can0 200#DEAD`, then send commands within 3 s, e.g. `cansend can0 100#C0` with no START should return `ERR 0x07` (`101#8700` in `candump`; `00000101#8700` with pre-TW-03 B firmware).
5. Full update: `./can_fota_flasher custom boot_can_fw.bin can0`. Expect ACK per block, END `0x101#0000`, JUMP ACK, then LD2 (PA5) blinking at 1 s.
6. Record results in `docs/verification/` and label hardware runs separately from builds.

After a change, report root cause, files changed, behavior change, verification run, and open concerns.
