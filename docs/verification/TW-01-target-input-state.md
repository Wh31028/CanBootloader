# TW-01 Target 입력·state·block 수신 안전성

## 판정

- Task 상태: `DONE`
- source/build 및 BBB–STM32F103RB CAN hardware 단계: 완료
- 기준 시각: 2026-09-15, Asia/Seoul

## 시작 상태와 코드 근거

| Repository | Branch | HEAD | 시작 dirty 상태 |
| --- | --- | --- | --- |
| CanBootloader | `fix/tw-01-target-input-state` | `a4cf05fff92b072c1bf87054b76e8ec6cd41e3da` | `?? boot_can_isotp/` (기존 사용자 untracked 변경, 미수정) |
| yocto_capston | 확인하지 않음 | 확인하지 않음 | 이번 창의 범위는 CanBootloader TW-01 hardware verification |

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
| BBB `can0` preflight | `ip -details link show can0` | PASS | `UP, LOWER_UP, ERROR-ACTIVE`, bitrate 500000, tx/rx error counter 0 |
| TW-01 CAN hardware cases | BBB `cansend` + `candump -L can0`, STM32F103RB | PASS | 아래 case별 timestamped trace와 application 복귀 관찰 |

`FLASH_PAGE_SIZE` redefinition warning은 existing `flash.c` warning이며 TW-01 범위 밖이다. build/link는 성공했다.

## Hardware verification

BBB의 `can0`은 500 kbit/s, `ERROR-ACTIVE` 및 error counter 0으로 확인했다. 모든 trace는 BBB에서 `candump -L can0`으로 수집했고, request는 `cansend can0`으로 보냈다. target response `00000101`은 현재 F103 target의 Extended response ID 표기이며 logical CAN ID는 `0x101`이다. 각 negative case는 `0x200#DEAD`로 application에 bootloader reset을 요청한 뒤 3초 안에 보냈다.

| Case | 실제 command/frame | candump trace (request → response) | STM32 관찰 및 판정 |
| --- | --- | --- | --- |
| 1. 정상 Custom FOTA regression | dashboard에서 verified 15,180-byte F103 `.bin` upload 후 Custom/500 kbps Update | `200#DEAD`; `100#404C3B0000`; 63× `00000101#0000`; `100#8017E8E104`; `100#C0`; ERR 없음 | `ceil(15180/256)=60` block ACK와 START/END/JUMP ACK이 총 63회로 일치, JUMP 뒤 application 정상 복귀. **PASS** |
| 2. START size 0 | `100#4000000000` | `100#4000000000 → 00000101#8800` | target이 `ERR(0x08)`을 반환; handler가 erase 전 return하는 경로. **PASS** |
| 3. START size 57,337 | `100#40F9DF0000` | `100#40F9DF0000 → 00000101#8800` | target이 `ERR(0x08)`을 반환; erase 전 return. **PASS** |
| 4. START DLC 4 | `100#40010000` | `100#40010000 → 00000101#8900` | target이 `ERR(0x09)`을 반환; erase 전 return. **PASS** |
| 5. IDLE DATA | `100#0001020304050607` | `100#0001020304050607 → 00000101#8700` | target이 `ERR(0x07)`을 반환; DATA write path 미진입. **PASS** |
| 6. IDLE END | `100#8000000000` | `100#8000000000 → 00000101#8700` | target이 `ERR(0x07)`을 반환; CRC/copy path 미진입. **PASS** |
| 7. IDLE JUMP | `100#C0` | `100#C0 → 00000101#8700` | target이 `ERR(0x07)`을 반환; application jump 미실행. **PASS** |
| 8. RECEIVING invalid sequence | valid START `100#4008000000`, then `100#0200000000000000` | `100#4008000000 → 00000101#0000`; invalid DATA `→ 00000101#8A00` | target이 `ERR(0x0A)`을 반환; memcpy/bitmap mark 전 return. **PASS** |
| 9. RECEIVING middle short DLC | valid START `100#4010000000`, seq0 full `100#0001020304050607`, then short seq1 `100#01010203040506` | START `→ 00000101#0000`; short DATA `→ 00000101#8900` | target이 `ERR(0x09)`을 반환; memcpy/bitmap mark 전 return. **PASS** |
| 10. final DATA exact short DLC | valid START `100#4008000000`; `100#0001020304050607`; `100#0108` | START `→ 00000101#0000`; final short DATA `→ 00000101#0000` | 8-byte logical block commit ACK 확인. **PASS** |
| 11. incomplete image END | valid START `100#4008000000`; only seq0 `100#0001020304050607`; END `100#8000000000` | START `→ 00000101#0000`; END `→ 00000101#8B00` | target이 `ERR(0x0B)`을 반환; CRC/copy path 미진입. **PASS** |

invalid START, IDLE command, invalid sequence/DLC, incomplete END의 erase/write/CRC/copy/RAM side effect는 target이 실제 CAN response를 반환한 input guard 경로와 대응 source의 early return으로 검증했다. 이번 session에서는 ST-LINK로 flash/RAM address를 별도 dump하지 않았으므로 이를 direct memory observation이라고 주장하지 않는다.

이 checklist에는 external analyzer, oscilloscope, relay power switch, 전문 CAN fault injector가 필요하지 않다. 특정 physical bit/stuff/form error 주입, CAN controller frame CRC의 의도적 훼손, hardware automatic retransmission의 정확한 on-wire 횟수 계측은 범위 밖이다.

## 남은 설계 한계

같은 block 내 duplicate overwrite는 막지만 Custom v1 wire format에는 session/block ID가 없다. 따라서 block commit ACK 유실 후 stale 마지막 frame을 다음 block frame으로 해석하는 문제는 해결하지 못하며 F1 Protocol v2 범위다. metadata write 결과와 active copy/vector validation의 강화는 TW-02 범위다. BBB retry boundedness는 TW-03 범위다.
