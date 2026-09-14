# TW-01 Target 입력·state·block 수신 안전성

## 판정

- Task 상태: `IN_PROGRESS`
- source/build 단계: 완료
- `DONE` 보류 사유: BBB, STM32F103RB, 현재 CAN transceiver/배선이 이 macOS 세션에 연결되지 않아 필수 hardware test를 실행하지 못했다.
- 기준 시각: 2026-09-14, Asia/Seoul

## 시작 상태와 코드 근거

| Repository | Branch | HEAD | 시작 dirty 상태 |
| --- | --- | --- | --- |
| CanBootloader | `main` | `fb5e26663f45b2bbf4bc8d4dda83f5d4eaee96e1` | clean |
| yocto_capston | `main` | `6c393e8be4c0b1d4ad1038c3f5266245ad219296` | clean |

기존 `bootProcessStart()`는 invalid size를 local `rx_size`만 clamp하고 `original_fw_size`에는 원 값을 남긴 채 erase/ACK했다. `bootProcess()`에는 session state guard가 없어서 START 없이 DATA/END/JUMP dispatch가 가능했고, DATA는 `original_fw_size - total_received_bytes`를 guard 없이 계산했다. 또한 DATA는 copy length가 invalid여도 bitmap을 mark할 수 있었고 END는 incomplete image를 먼저 거부하지 않았다.

## 변경 파일과 내용

| File | 변경 |
| --- | --- |
| `boot_can_custom_f103/App/ap/boot_can/boot_can.c` | local state, exact command DLC/sequence 검사, size 선검사, block-local length 계산, duplicate 정책, END/JUMP precondition을 구현 |
| `boot_can_custom_f103/App/ap/boot_can/boot_can.h` | 기존 ERR frame namespace 안의 input/state error code `0x07`–`0x0B` 추가 |
| `docs/protocol.md` | state transition, packet validation, error code, v1 stale-frame 한계를 code와 일치시킴 |
| `docs/improvement-plan/*` | Task 상태, 검증 증거, 면접 노트와 handoff 갱신 |

wire format, CAN ID, command ID, sequence field, payload layout은 변경하지 않았다. BBB working-tree sender와 Yocto recipe 안의 sender 사본은 모두 정상 경로에서 START/END DLC 5, JUMP DLC 1, DATA의 마지막 frame만 short DLC를 보낸다. 새 ERR code는 양쪽 sender가 이미 header 하위 6 bits를 generic error code로 표시하므로 호환된다. Yocto source drift 자체의 동기화는 F4 범위다.

## state transition

| 현재 state | 허용 command | 성공 결과 | 거부 결과 |
| --- | --- | --- | --- |
| `IDLE` | valid START | erase 후 `RECEIVING` | DATA/END/JUMP: `ERR(0x07)` |
| `RECEIVING` | valid DATA, complete END, valid START(restart) | block ACK 유지, END 성공 시 `IMAGE_VERIFIED` | malformed input은 state 유지, CRC/flash failure는 `FAILED` |
| `IMAGE_VERIFIED` | valid JUMP, valid START(restart) | jump 또는 새 receive | DATA/END: `ERR(0x07)` |
| `FAILED` | valid START(restart) | erase 후 `RECEIVING` | DATA/END/JUMP: `ERR(0x07)` |

invalid START는 state, RAM receive context, staging flash erase를 수행하지 않는다. DATA는 `total_received_bytes < original_fw_size`를 먼저 확인한 뒤 남은 logical block 길이, expected sequence, exact payload length를 계산한다. bitmap bit는 successful in-range `memcpy()` 뒤에만 set된다. 같은 block의 duplicate는 overwrite하지 않으며 마지막 sequence duplicate는 current bitmap NACK을 다시 보낸다.

## 실제 검증

| 검증 | Command/방법 | 결과 | Evidence |
| --- | --- | --- | --- |
| Custom F103 clean configure/build | `cmake -S boot_can_custom_f103 -B /private/tmp/can-fota-tw01-custom -G Ninja -DCMAKE_TOOLCHAIN_FILE="$PWD/boot_can_custom_f103/cmake/gcc-arm-none-eabi.cmake" -DCMAKE_BUILD_TYPE=Release && cmake --build /private/tmp/can-fota-tw01-custom` | PASS | Arm GNU 15.2.1, ELF/BIN link 성공; Flash 10,068 B/16 KiB, RAM 3,184 B/20 KiB |
| CTest discovery | `ctest --test-dir /private/tmp/can-fota-tw01-custom --output-on-failure` | NOT RUN | `No tests were found!!!`; repository에 target protocol unit-test target 없음 |
| Static diff whitespace | `git diff --check` | PASS | output 없음 |
| BBB/STM32 malformed-frame cases | 현재 BBB + STM32F103RB + CAN transceiver/배선 | NOT RUN | 이 세션의 host interface에는 `can0`/Linux BBB가 없음 |

`FLASH_PAGE_SIZE` redefinition warning은 existing `flash.c` warning이며 TW-01 범위 밖이다. build/link는 성공했다.

## 남은 hardware checklist

BBB에서 기존 Custom flasher가 정상 update 하는 것을 먼저 확인한 뒤, CAN sender 또는 flasher test mode로 아래 frame을 target에 보내고 response/staging erase 여부를 UART 또는 기존 debug/programming 수단으로 기록한다.

| Case | 기대 결과 |
| --- | --- |
| START size 0 / 57,337 / DLC 4 | `ERR(0x08)` / `ERR(0x08)` / `ERR(0x09)`, staging erase 없음 |
| IDLE DATA / END / JUMP | 각각 `ERR(0x07)`, write/CRC/copy/jump 없음 |
| DATA `seq >= expected` 또는 middle short DLC | `ERR(0x0A)` 또는 `ERR(0x09)`, bitmap/buffer unchanged |
| final DATA exact short DLC | block ACK, logical byte count 증가 |
| all bytes before END | `ERR(0x0B)`, CRC/copy 없음 |
| normal BBB update | START ACK, per-block ACK/NACK, END ACK, JUMP 후 application 실행 |

이 checklist에는 external analyzer, oscilloscope, relay power switch, 전문 CAN fault injector가 필요하지 않다. 특정 physical bit/stuff/form error 주입, CAN controller frame CRC의 의도적 훼손, hardware automatic retransmission의 정확한 on-wire 횟수 계측은 범위 밖이다.

## 남은 설계 한계

같은 block 내 duplicate overwrite는 막지만 Custom v1 wire format에는 session/block ID가 없다. 따라서 block commit ACK 유실 후 stale 마지막 frame을 다음 block frame으로 해석하는 문제는 해결하지 못하며 F1 Protocol v2 범위다. metadata write 결과와 active copy/vector validation의 강화는 TW-02 범위다. BBB retry boundedness는 TW-03 범위다.
