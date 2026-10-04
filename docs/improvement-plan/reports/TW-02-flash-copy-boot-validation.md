# TW-02 — Flash 복사와 boot 검증 안전성

## 한눈에 보기

- 상태: `DONE`
- 코드와 build: 완료
- BBB + STM32F103RB 정상 Custom FOTA 실장 시험: `PASS`
- 근거: NUCLEO-F103RB에 bootloader와 application을 SWD write/verify한 뒤, BBB web dashboard에서 Custom FOTA를 실행했다. `candump -L` trace에 END ACK와 JUMP ACK가 남았고, application LD2가 1초 주기로 다시 toggle되는 것을 관찰했다.

## 이 작업에서 막으려는 문제

Firmware를 staging 영역에서 active application 영역으로 옮길 때, 깨진 image를 실행하거나 copy 실패를 성공으로 처리하는 상황을 막는 것이 목표다.

| 기존 문제 | 왜 위험한가 | 이번 변경 |
| --- | --- | --- |
| `addr + length`로 Flash 범위를 검사 | 큰 값에서 덧셈이 overflow하면 범위 밖 접근을 놓칠 수 있음 | `length <= FLASH_ADDR_END - addr`로 검사 |
| 마지막 길이가 4 byte의 배수가 아님 | F103 Flash write가 실패할 수 있음 | 마지막 1–3 byte를 `0xFF`로 채워 4 byte로 write |
| metadata write 실패를 무시 | metadata가 불완전한데 active 영역을 erase할 수 있음 | size와 CRC write가 모두 성공해야 copy 시작 |
| CRC만 맞으면 copy 성공 처리 | 실행할 수 없는 데이터를 application으로 취급할 수 있음 | CRC와 vector table을 함께 검사 |
| boot, recovery, JUMP가 서로 다른 검사 사용 | 한 경로만 약하면 invalid image를 실행할 수 있음 | 모두 `bootVerifyFw()` 사용 |

## 변경 후 동작

```text
  1. BBB가 START(size)를 보낸다.
  2. Bootloader가 staging 영역을 erase한다.
  3. BBB가 DATA frame들을 보낸다.
  4. Bootloader는 DATA를 256-byte block으로 모아 staging Flash에 기록한다.
  5. BBB가 END(expected CRC)를 보낸다.
  6. Bootloader가 staging 영역의 original firmware size만 CRC32로 계산해 BBB가 보낸 CRC와 비교한다.
  7. CRC가 맞으면 staging image의 vector table도 검사한다.
  8. staging 마지막 8 byte에 metadata size와 CRC를 실제로 기록한다. 두 write가 모두 성공해야 다음 단계로 진행한다.
  9. active application 영역을 erase하고 staging firmware를 복사한다.
     - 마지막 1~3 byte는 0xFF를 채워 4 byte write한다.
     - SP와 Reset Handler인 첫 8 byte는 가장 마지막에 쓴다.
  10. active 영역의 original-size CRC와 vector table을 다시 검사한다.
  11. 모두 통과하면 ACK를 보내고, 이후 JUMP를 허용한다.
```

`0xFF` padding은 Flash에 쓰기 위한 처리일 뿐이다. CRC는 BBB가 보낸 원본 firmware 길이만 계산하므로, BBB sender와 CRC 값이 바뀌지 않는다.

## Vector table에서 확인하는 값

| 값 | 확인하는 이유 |
| --- | --- |
| Initial MSP | F103RB SRAM 범위 `0x20000000`~`0x20005000` 안의 aligned stack top(4byte 단위)인지 확인 |
| Reset Handler bit 0 | Cortex-M은 Thumb state만 실행하므로 bit 0이 1이어야 함 |
| Reset Handler 주소 | Thumb bit를 제거한 주소가 active application 범위 `0x08004000`~`0x08011FF7` 안인지 확인 |

CRC는 “전송한 byte가 같은가”를 확인한다. vector 검사는 “그 byte를 Cortex-M application으로 실행해도 되는가”를 확인한다. 둘은 서로 대체하지 못한다.

## 바뀐 파일

| 파일 | 핵심 변경 |
| --- | --- |
| `boot_can_custom_f103/App/hw/src/flash.c` | overflow-safe Flash range 검사, `flashRead()` guard |
| `boot_can_custom_f103/App/ap/boot_can/boot_can.c` | padding copy, metadata failure 처리, CRC readback, vector 검사 |
| `boot_can_custom_f103/App/ap/boot_can/boot_can.h` | `bootCopyFw()`에 expected CRC 전달 |
| `boot_can_custom_f103/App/ap/ap.c` | normal boot/recovery가 JUMP와 같은 validation/jump 경로 사용 |

Custom CAN protocol의 CAN ID, command, sequence, DLC, payload layout은 바꾸지 않았다. 따라서 BBB sender와 Yocto의 BBB source는 수정하지 않았다.

## 실제로 실행한 검증

| 항목 | 결과 | 확인 내용 |
| --- | --- | --- |
| Custom F103 bootloader build | **PASS** | 2026-10-04 `cmake --build boot_can_custom_f103/build/Debug`: Flash 13,792 B / 16 KiB, RAM 3,184 B / 20 KiB |
| F103 application build | **PASS** | 2026-10-04 `cmake --build boot_can_fw_f103/build/Release`: Flash 10,156 B / 57,336 B, RAM 5,304 B / 20 KiB |
| application vector 확인 | **PASS** | MSP `0x20005000`, Reset Handler `0x08005A35`; SRAM/Thumb/active-range 조건 충족 |
| `git diff --check` | **PASS** | whitespace error 없음 |
| CTest | **NOT RUN** | 두 build directory에서 실제 실행했지만 모두 `No tests were found!!!` (test target 없음) |
| BBB SSH preflight | **FAIL** | `ssh -o BatchMode=yes -o ConnectTimeout=10 debian@192.168.7.2 ...`가 connection timeout; BBB에 command를 실행하지 못함 |
| BBB `can0` preflight | **PASS** | 500 kbit/s, `UP`/`LOWER_UP`, `ERROR-ACTIVE`, TX/RX error counter 0으로 확인. dashboard가 시작 시 interface를 down/up 하므로 trace는 재시작 loop로 수집함 |
| STM32 programming | **PASS** | ST-LINK V2, NUCLEO-F103RB에서 bootloader `0x08000000` 13.47 KiB 및 application `0x08004000` 9.92 KiB를 각각 write/verify 성공 |
| BBB + STM32F103RB 정상 Custom FOTA | **PASS** | trace의 `0x100#80817459B2` END, `0x101#0000` END ACK, `0x100#C0` JUMP, `0x101#0000` JUMP ACK; 이후 application LD2가 1초 주기로 toggle |
| non-4-byte tail padding 실장 시험 | **NOT RUN** | valid vector를 유지한 1~3 byte tail image를 이번 session에서 전송하지 않음 |
| invalid SP/Thumb/staging Reset Handler 실장 시험 | **NOT RUN** | 기존 active application 보존 여부를 포함한 negative image 시험을 이번 session에서 전송하지 않음 |
| active corruption/checkpoint reset recovery | **NOT RUN** | current debug/programming 수단으로 안전한 재현 절차를 이번 session에서 실행하지 않음 |

기존 `FLASH_PAGE_SIZE` redefinition warning은 남아 있다. 이 Task에서 새로 발생한 warning은 아니며 build/link는 성공했다.

## 남은 hardware 시험

BBB, STM32F103RB, 현재 CAN transceiver/배선, 개발 PC만 사용한다.

1. valid vector를 유지한 1~3 byte tail image와 최대 크기 image를 전송해 padding/write 경계를 확인한다.
2. SRAM 밖 SP, Thumb bit가 0인 Reset Handler, staging을 가리키는 Reset Handler를 보낸다. active erase 전에 error가 나고 기존 application이 보존되는지 확인한다.
3. active copy 뒤 1 byte corruption과 checkpoint reset을 현재 debug/programming 수단으로 시험한다. CRC failure와 recovery 결과를 trace로 남긴다.

HAL program failure injection용 test hook은 아직 없으므로, 추가하지 않는 한 해당 시험은 `NOT RUN`이다.

## 범위 밖

physical bit/stuff/form fault, CAN controller frame CRC를 고의로 깨는 시험, hardware automatic retransmission의 정확한 on-wire 횟수, oscilloscope signal integrity, relay 기반 정밀 power-cut은 이번 Task 범위 밖이다. external analyzer, oscilloscope, relay power switch, 전문 CAN fault injector를 새 dependency로 제안하지 않는다.
