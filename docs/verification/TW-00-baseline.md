# TW-00 Baseline과 검증 계약

## 판정

- Task 상태: `DONE`
- Source 변경: 없음. 이 Task는 baseline 문서화와 read-only build만 수행했다.
- 기준 시각: 2026-09-07, Asia/Seoul

## 시작 상태

| Repository | Branch | HEAD | 시작 dirty 상태 |
| --- | --- | --- | --- |
| CanBootloader | `docs/tw00-baseline` | `4f1ac7b6a175a476febcad2719df31ca3a6c6bd3` | clean |
| yocto_capston | `main` (`origin/main` 추적) | `6c393e8be4c0b1d4ad1038c3f5266245ad219296` | clean |

## 환경과 검증 계약

| 항목 | 실제 값/판정 |
| --- | --- |
| Host OS | macOS 26.6.2, Darwin 25.6.0, arm64 |
| CMake / Ninja | 4.1.2 / 1.11.1 |
| STM32 compiler | Arm GNU Toolchain 15.2.1 (`arm-none-eabi-gcc`) |
| Binary tool | GNU objcopy 2.45.1 |
| Target build 설정 | Cortex-M3, `STM32F103xB`, `startup_stm32f103xb.s`, `system_stm32f1xx.c`; 각 `cmake/stm32cubemx/CMakeLists.txt`에서 확인 |
| CAN bitrate | 설계 문서 `docs/architecture.md`의 500 kbps. 이번 세션에 실제 CAN interface를 올리거나 측정하지 않았으므로 hardware-verified 값은 아님. |
| BBB image / C flasher build | `NOT RUN`: 이 macOS 개발 PC 세션에는 접속 가능한 BBB/Linux target 정보·세션이 없었다. Linux/BBB에서만 Makefile build를 수행해야 한다. |
| STM32F103RB / CAN transceiver / 배선 hardware test | `NOT RUN`: 이 세션에서 보드 및 CAN interface가 연결되지 않아 flash/전송을 실행하지 않았다. |

필수 장비 범위는 BBB, STM32F103RB, 기존 CAN transceiver/배선, 개발 PC와 기존 debug/programming 수단으로 고정한다. external analyzer, oscilloscope, relay power switch, 전문 CAN fault injector는 새 dependency가 아니다.

software에서 결정적으로 재현 가능한 DATA omission/duplicate/reorder, ACK/NACK/FC/application ACK 무시, target disconnect 또는 `can0` down, SocketCAN queue pressure, target RX queue overflow, background traffic, CRC-corrupt image, checkpoint reset과 수동 reset/power disconnect는 이후 Task의 후보 fault이다. 특정 physical bit/stuff/form error, CAN controller frame CRC의 의도적 훼손, hardware automatic retransmission의 정확한 on-wire 횟수 측정, oscilloscope signal-integrity 분석, relay 기반 정밀 자동 power-cut은 범위 밖이다.

## Clean build 결과

기존 repository build directory를 사용하지 않고 `/private/tmp/can-fota-tw00-*`에서 별도 configure/build했다. binary artifact는 repository에 보관하지 않았다.

| Image | Command | 결과 | `.bin` size | SHA-256 | ELF memory summary |
| --- | --- | --- | ---: | --- | --- |
| `boot_can_custom_f103` | `cmake -S boot_can_custom_f103 -B /private/tmp/can-fota-tw00-custom -G Ninja -DCMAKE_TOOLCHAIN_FILE="$PWD/boot_can_custom_f103/cmake/gcc-arm-none-eabi.cmake" -DCMAKE_BUILD_TYPE=Release && cmake --build /private/tmp/can-fota-tw00-custom` | `PASS` | 9,832 B | `bc34ae3bc5ce1378f944702a47102ed68b71ef5f73d2e0f11d2a8cb27f7e7891` | Flash 9,832 B / 16 KiB (60.01%), RAM 3,184 B / 20 KiB (15.55%) |
| `boot_can_fw_f103` | `cmake -S boot_can_fw_f103 -B /private/tmp/can-fota-tw00-fw -G Ninja -DCMAKE_TOOLCHAIN_FILE="$PWD/boot_can_fw_f103/cmake/gcc-arm-none-eabi.cmake" -DCMAKE_BUILD_TYPE=Release && cmake --build /private/tmp/can-fota-tw00-fw` | `PASS` | 10,180 B | `fb236e5a05bba7ef7d8a7c5d8fb0758886ede99e86d6ca785ea75e2987efae4a` | Flash 10,180 B / 57,336 B (17.75%), RAM 5,304 B / 20 KiB (25.90%) |
| `boot_can_isotp_f103` | `cmake -S boot_can_isotp_f103 -B /private/tmp/can-fota-tw00-isotp -G Ninja -DCMAKE_TOOLCHAIN_FILE="$PWD/boot_can_isotp_f103/cmake/gcc-arm-none-eabi.cmake" -DCMAKE_BUILD_TYPE=Release && cmake --build /private/tmp/can-fota-tw00-isotp` | `FAIL` | — | — | `isotp_port.c` compile 단계에서 중단 |

Custom bootloader와 application build에는 `FLASH_PAGE_SIZE` local redefinition warning이 각각 있었다. 이는 이번 Task의 수정 대상이 아니며 PASS 판정은 link와 `.bin` 생성 성공을 뜻한다.

ISO-TP build 실패의 직접 원인은 `boot_can_isotp_f103/App/ap/boot_can/isotp_port.h`가 `iso15765/isotp.h`를 `stm32f1xx_hal.h`보다 먼저 include하는 순서다. `isotp.h`와 그 하위 `isotp_defines.h`/`isotp_user.h`는 `uint8_t`, `uint16_t`, `uint32_t`를 사용하지만 C mode에서 `<stdint.h>`를 그 전에 포함하지 않는다. `isotp_port.c` compile에서 unknown type name error가 재현됐다. 수정은 TW-04 범위다.

## 변경 전 known failure와 코드 근거

| 항목 | 코드 근거 | 현재 판정 | 후속 Task |
| --- | --- | --- | --- |
| Oversize 또는 zero START가 reject되지 않음 | `boot_can_custom_f103/App/ap/boot_can/boot_can.c:bootProcessStart()`는 invalid `rx_size`를 local upper bound로만 바꾸고 `original_fw_size`에는 원본 invalid 값을 유지한 채 staging erase/ACK를 수행한다. | review evidence | TW-01 |
| START 없이 DATA/END/JUMP 가능 | 같은 file의 `bootProcess()`는 command dispatch 전에 explicit session state를 확인하지 않는다. DATA는 `original_fw_size - total_received_bytes`를 사용하고, END/JUMP도 START 완료를 요구하지 않는다. | review evidence | TW-01 |
| Custom ACK loss 후 block desynchronization | `can-fota-BBB/flasher/custom_fota.c:start_custom_fota()`는 ACK timeout마다 마지막 frame만 무한 재송한다. target은 block commit 뒤 bitmap을 clear하므로 lost ACK 뒤 frame을 다음 block frame으로 해석할 수 있다. block/session identity는 없다. | review evidence | F1; TW-03은 host loop bounded retry만 다룸 |
| Host retry/send가 유한하지 않음 | `can_socket.c:send_can_frame()`은 `ENOBUFS`에서 무한 loop, `custom_fota.c` DATA feedback loop도 retry cap/deadline이 없다. | review evidence | TW-03 |
| ISO-TP type include-order compile failure | 위 clean build의 `isotp_port.c` error와 `isotp_port.h` include 순서. | `FAIL` 재현 | TW-04 |

## Architecture와 baseline 경계

`docs/architecture.md` 기준 FOTA 경로는 BBB CLI/dashboard → C flasher → Linux SocketCAN → F103 application entry (`0x200`, `DE AD`) → BKP magic/reset → Custom bootloader → staging → CRC32 → active copy → application이다. Custom bootloader/application memory map은 bootloader `0x08000000`–`0x08003FFF`, active application `0x08004000`–`0x08011FF7`, staging payload `0x08012000`–`0x0801FFF7`, metadata 마지막 8 B다. 최대 logical firmware는 57,336 B다.

과거 64 KiB direct-write benchmark는 current staging/copy design의 성능으로 사용하지 않는다. 현재 구조는 download/CRC 완료 전 active application 보호와 copy recovery를 위한 staging을 사용하고, image limit도 57,336 B다. true dual-bank/A/B, atomic slot swap, automatic rollback이 아니다.

`yocto_capston/meta-can-fota/recipes-apps/can-fota/can-fota_1.0.bb`는 Yocto 내부 `files/can-fota-BBB`를 build source로 지정한다. working tree `can-fota-BBB`와 비교하면 `can_fota_flasher.c`, `web_dashboard/main.py` 등이 이미 달라 source drift가 존재한다. TW-00에서는 어느 copy를 source-of-truth로 정하거나 동기화하지 않았다.

## 다음 Task 진입 기준

TW-01은 Custom protocol wire format을 바꾸지 않고 target의 START size/DLC validation, explicit state precondition, sequence/last-block/누적-byte boundary를 고친다. STM32 protocol 동작 변경 시 BBB sender의 `custom_fota.c`와 Yocto에 패키징된 사본의 compatibility/drift를 함께 검토해야 한다.
