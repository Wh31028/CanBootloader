# TW-02 — Flash 복사와 boot 검증 안전성

## 한눈에 보기

- 상태: `IN_PROGRESS`
- 코드와 build: 완료
- BBB + STM32F103RB 실장 시험: `NOT RUN`
- 이유: 이번 세션에서는 board에 직접 연결해 시험할 수 없었다. 실행하지 않은 시험을 통과했다고 기록하지 않는다.

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
| Custom F103 bootloader build | **PASS** | Flash 10,212 B / 16 KiB, RAM 3,184 B / 20 KiB |
| F103 application build | **PASS** | Flash 10,180 B / 57,336 B, RAM 5,304 B / 20 KiB |
| application vector 확인 | **PASS** | MSP `0x20005000`, Reset Handler `0x08005A35`; SRAM/Thumb/active-range 조건 충족 |
| `git diff --check` | **PASS** | whitespace error 없음 |
| CTest | **NOT RUN** | command는 실행했지만 repository에 test가 없음 (`No tests were found!!!`) |
| BBB + STM32F103RB FOTA 시험 | **NOT RUN** | 이번 세션에 board 연결 경로가 없음 |

기존 `FLASH_PAGE_SIZE` redefinition warning은 남아 있다. 이 Task에서 새로 발생한 warning은 아니며 build/link는 성공했다.

## 다음 hardware 시험

BBB, STM32F103RB, 현재 CAN transceiver/배선, 개발 PC만 사용한다.

1. sizes `1`, `3`, `4`, `255`, `256`, `257`, `57,336`을 전송한다. 8 byte보다 작은 image는 valid vector를 가질 수 없으므로 END에서 vector error가 나는 것이 정상이다.
2. SRAM 밖 SP, Thumb bit가 0인 Reset Handler, staging을 가리키는 Reset Handler를 보낸다. active erase 전에 error가 나고 기존 application이 보존되는지 확인한다.
3. active copy 뒤 1 byte corruption과 checkpoint reset을 현재 debug/programming 수단으로 시험한다. CRC failure와 recovery 결과를 trace로 남긴다.

HAL program failure injection용 test hook은 아직 없으므로, 추가하지 않는 한 해당 시험은 `NOT RUN`이다.

## 범위 밖

physical bit/stuff/form fault, CAN controller frame CRC를 고의로 깨는 시험, hardware automatic retransmission의 정확한 on-wire 횟수, oscilloscope signal integrity, relay 기반 정밀 power-cut은 이번 Task 범위 밖이다. external analyzer, oscilloscope, relay power switch, 전문 CAN fault injector를 새 dependency로 제안하지 않는다.
