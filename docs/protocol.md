# CAN FOTA Protocol 명세

## 범위

이 문서의 규범적 기준은 현재 `main`의 다음 source입니다.

- Target: `boot_can_custom_f103/App/ap/boot_can/boot_can.[ch]`
- Target CAN driver: `boot_can_custom_f103/App/hw/src/can.c`
- Host: `can-fota-BBB/flasher/custom_fota.c`, `can_socket.c`, `protocol.h`

STM32F103RB Custom CAN을 먼저 정의하고, ISO-TP는 비교 구현으로 뒤에서 분리해 설명합니다. 모든 multi-byte integer와 bitmap은 **little-endian**입니다. Classic CAN data length는 최대 8 bytes입니다.

## 공통 FOTA entry

Application에서 bootloader로 전환하는 entry frame은 Custom과 ISO-TP가 공유합니다.

| 방향 | CAN ID | DLC | Data | 동작 |
| --- | ---: | ---: | --- | --- |
| BBB → STM32 application | `0x200` | 2 | `DE AD` | BKP DR1/DR2에 `0xDEADBEEF` 기록 후 `NVIC_SystemReset()` |

현재 BBB C flasher는 이 frame을 Standard 11-bit ID로 보내고 3초 기다린 뒤 stale RX frame을 비우고 protocol session을 시작합니다. F103 application은 ID와 앞의 2 bytes만 검사하며 `dlc >= 2`를 허용합니다.

## Custom CAN ID

| 방향 | Numeric CAN ID | 용도 |
| --- | ---: | --- |
| BBB → STM32 | `0x100` | `START`, `DATA`, `END`, `JUMP` command |
| STM32 → BBB | `0x101` | `ACK`, bitmap `NACK`, `ERR` response |
| BBB → STM32 application | `0x200` | FOTA entry request |

### Standard/Extended ID 주의

Host `send_can_frame()`은 `CAN_EFF_FLAG`를 넣지 않으므로 Standard frame을 전송합니다. 반면 F103 Custom target의 공용 `canMsgWrite()`는 response `0x101`을 Extended frame으로 설정합니다. BBB는 수신 시 `CAN_SFF_MASK`로 numeric 11 bits만 비교하므로 현재 pair에서는 response를 받아들입니다.

이것은 logical ID가 일치한다는 뜻이지 frame format이 일관된 것은 아닙니다. 현재 BBB parser가 numeric ID만 비교하기 때문에 동작하지만, strict CAN filter를 사용하는 다른 tool과의 interoperability에는 제약이 있습니다. ISO-TP F103 port는 `0x7E0/0x7E8`을 Standard ID로 명시합니다.

## Custom header

모든 Custom command/response의 byte 0은 다음과 같습니다.

```text
bit 7                  bit 6 bit 5                            bit 0
+---------------------------+-------------------------------------+
|        command (2 bits)   | sequence / result (6 bits)          |
+---------------------------+-------------------------------------+
```

```c
header = ((command & 0x03) << 6) | (sequence_or_result & 0x3F);
```

Command와 response는 같은 2-bit 위치를 사용하지만 namespace가 방향별로 다릅니다.

### Host → Target command

| Command | 값 | Header 범위 | 의미 |
| --- | ---: | --- | --- |
| `DATA` | `0` | `0x00`–`0x3F` | 하위 6 bits가 sequence |
| `START` | `1` | `0x40` | Session 시작 및 staging erase |
| `END` | `2` | `0x80` | CRC 검증 및 active copy |
| `JUMP` | `3` | `0xC0` | Application 유효성 확인 후 jump |

### Target → Host response

| Response | 값 | Header | 의미 |
| --- | ---: | --- | --- |
| `ACK` | `0` | `0x00` | START, block 또는 END 성공 |
| `NACK` | `1` | `0x40` | 현재 block의 receive bitmap 전달 |
| `ERR` | `2` | `0x80`과 `error_code`의 bitwise OR | Flash/CRC/jump 실패 |

## Host → Target packet layout

### START

| Byte | 값 |
| ---: | --- |
| 0 | `0x40` (`START`) |
| 1 | `firmware_size[7:0]` |
| 2 | `firmware_size[15:8]` |
| 3 | `firmware_size[23:16]` |
| 4 | `firmware_size[31:24]` |

- DLC: 5
- Target action: receive state와 256-byte buffer를 초기화하고 staging `0x08012000`부터 56 KiB 전체를 erase합니다.
- 성공: `ACK`; erase 실패: `ERR(0x03)`

현재 target은 size가 0이거나 57,336 B를 초과해도 `original_fw_size`에는 원래 값을 남기고 별도 local 값만 clamp합니다. Host도 target profile별 상한을 검사하지 않습니다. 따라서 현재 구현이 정상적으로 처리하는 입력은 valid vector table을 포함한 57,336 B 이하의 F103 application image입니다.

### DATA

| Byte | 값 |
| ---: | --- |
| 0 | `0b00ssssss`; `ssssss` = sequence `0..36` |
| 1–7 | Firmware data, frame당 1–7 bytes |

- Logical block 크기: 최대 256 bytes
- Full block frame 수: `ceil(256 / 7) = 37`
- Sequence 범위: full block은 0–36; 마지막 block은 `0..ceil(block_len/7)-1`
- Full block에서 seq 0–35는 각 7 bytes, seq 36은 4 bytes를 운반합니다.
- Target은 block buffer를 `0xFF`로 초기화하고 block 완료 시 항상 256 bytes를 staging에 씁니다. 마지막 block의 logical CRC 길이는 원본 size까지만이며 padding은 제외됩니다.

`seq > 36`은 target이 응답 없이 무시합니다. Explicit block number, absolute offset, session ID는 없습니다.

### END

| Byte | 값 |
| ---: | --- |
| 0 | `0x80` (`END`) |
| 1 | `crc32[7:0]` |
| 2 | `crc32[15:8]` |
| 3 | `crc32[23:16]` |
| 4 | `crc32[31:24]` |

- DLC: 5
- Target은 START에서 받은 original firmware size만큼 staging CRC를 계산합니다.
- CRC가 맞으면 size/CRC metadata를 기록하고 active application을 erase/copy합니다.
- 성공: `ACK`; CRC 불일치: `ERR(0x06)`; copy 실패: `ERR(0x04)`

### JUMP

| Byte | 값 |
| ---: | --- |
| 0 | `0xC0` (`JUMP`) |

- DLC: 1
- Target은 `0x08004004`의 Reset Handler가 application 범위에 있는지 검사합니다.
- 성공 시 ACK를 보내고 약 100 ms 뒤 VTOR/MSP를 전환하여 application으로 jump합니다.
- 실패 시 `ERR(0x05)`를 보냅니다.
- BBB flasher는 현재 JUMP response를 기다리지 않습니다.

## Target → Host packet layout

### ACK

| Byte | 값 |
| ---: | --- |
| 0 | `0x00` |
| 1 | `0x00` |

DLC는 2입니다. START erase, 각 256-byte block write, END copy 및 JUMP validation 성공에 사용합니다. ACK 자체에는 어느 block에 대한 응답인지 나타내는 identifier가 없습니다.

### Bitmap NACK

| Byte | 값 |
| ---: | --- |
| 0 | `0x40` |
| 1 | received bitmap bits 0–7 |
| 2 | received bitmap bits 8–15 |
| 3 | received bitmap bits 16–23 |
| 4 | received bitmap bits 24–31 |
| 5 | received bitmap bits 32–39 |
| 6 | received bitmap bits 40–47 |
| 7 | received bitmap bits 48–55 |

- Bit `1`: 해당 sequence를 target이 받음
- Bit `0`: 해당 sequence가 누락되어 host가 재전송해야 함
- 현재 block에서 의미 있는 bit만 해석하며 최대 bit 36까지 사용합니다.
- Target은 마지막 expected sequence가 들어왔지만 bitmap이 완성되지 않았을 때 NACK을 보냅니다.

예를 들어 full block에서 seq 2와 5만 누락됐다면 bitmap의 bit 2, 5가 0이고 나머지 expected bit가 1입니다. BBB는 0인 두 frame만 다시 전송합니다.

### ERR

| Byte | 값 |
| ---: | --- |
| 0 | `0x80`과 `error_code`의 bitwise OR |
| 1 | `0x00` |

| Error code | 이름 | 발생 조건 |
| ---: | --- | --- |
| `0x03` | `BOOT_ERR_FLASH_ERASE` | Staging/active erase 실패 |
| `0x04` | `BOOT_ERR_FLASH_WRITE` | Staging write 또는 active copy 실패 |
| `0x05` | `BOOT_ERR_FLASH_JUMP` | Reset Handler 범위 검사 실패 |
| `0x06` | `BOOT_ERR_CRC` | END의 expected CRC와 staging CRC 불일치 |

BBB parser는 header 하위 6 bits를 error code로 해석합니다.

## Sequence와 block 상태

1. BBB는 firmware를 앞에서부터 최대 256 bytes로 나눕니다.
2. 각 block에서 sequence를 다시 0부터 시작합니다.
3. Target은 수신 frame을 `boot_buf[seq * 7]`에 배치하고 해당 bitmap bit를 세웁니다.
4. Expected bitmap이 완성되면 buffer 전체 256 bytes를 staging에 쓰고 ACK합니다.
5. BBB는 ACK를 받은 뒤에만 다음 block으로 이동합니다.
6. Target은 ACK 후 bitmap과 buffer를 초기화하고 staging write address를 256만큼 증가시킵니다.

Protocol에 block index/offset/session state가 없으므로 오래 지연된 이전 block frame을 구별할 수 없습니다. CAN bus에 여러 updater가 있거나 stale frame이 섞이는 환경은 현재 설계 범위 밖입니다.

특히 target이 block을 staging에 기록하고 bitmap을 초기화한 뒤 보낸 ACK 자체가
유실되면, host는 이전 block의 마지막 frame을 재전송합니다. Target은 이를 다음
block의 sequence로 해석할 수 있어 block 경계가 desynchronize되고 최종 CRC 오류로
이어질 수 있습니다. 현재 protocol에는 duplicate block commit/ACK를 식별하는
idempotency mechanism이 없습니다.

## Timeout과 재전송

| 단계 | BBB timeout | 현재 동작 |
| --- | ---: | --- |
| Entry | 3.0 s 고정 대기 | 응답을 기다리지 않고 RX buffer를 비운 뒤 START |
| START | 10.0 s | ACK가 아니거나 timeout이면 session 종료 |
| DATA block | 150 ms | 마지막 expected frame을 다시 보내 NACK/ACK 판단을 유도 |
| NACK | 응답 수신 즉시 | Bitmap에서 0인 sequence만 재전송 |
| END | 10.0 s | ACK가 아니거나 timeout이면 session 종료 |
| JUMP | 0.5 s 지연 후 전송 | Response 대기 없음 |

Custom DATA retry loop에는 최대 횟수나 전체 session deadline이 없습니다. 따라서 지속적인 link fault에서는 retry가 계속될 수 있습니다.

Bootloader의 10초 무수신 fallback은 BKP magic으로 진입했을 때만 활성화됩니다. 그 시점에 active Reset Handler가 여전히 valid해야 기존 application으로 jump합니다.

## CRC32

Host와 target은 동일한 bitwise CRC32를 사용합니다.

| 항목 | 값 |
| --- | --- |
| Polynomial, reflected | `0xEDB88320` |
| Initial value | `0xFFFFFFFF` |
| Input processing | byte XOR 후 LSB-first 8회 shift |
| Final XOR/complement | `~crc` (`0xFFFFFFFF`) |
| 범위 | 원본 firmware의 정확한 byte length; 마지막 `0xFF` padding 제외 |

이는 일반적으로 IEEE 802.3/zlib CRC-32와 같은 parameter입니다. CRC는 accidental corruption 검출용이며 authenticity를 제공하지 않습니다.

## Flash 및 오류 처리 제약

- F103 Flash driver는 write length가 4의 배수가 아니면 실패합니다. DATA staging write는 항상 256 bytes라 맞지만, active copy의 마지막 `copy_len`은 original firmware size에 좌우됩니다. BBB는 현재 `.bin` size의 4-byte alignment를 검사하지 않습니다.
- Target은 START/DATA/END/JUMP의 엄격한 session state machine을 두지 않습니다. Unexpected command와 일부 잘못된 DLC는 명시적 ERR 없이 처리되거나 무시될 수 있습니다.
- Application validity 검사는 Reset Handler word의 Flash range만 봅니다. Initial SP의 SRAM 범위와 복사 후 active image CRC를 다시 확인하지 않습니다.
- Flash metadata와 CRC는 update recovery용일 뿐 version, signature 또는 anti-rollback counter가 아닙니다.

## ISO-TP 비교 구현

F103 ISO-TP 경로는 `boot_can_isotp_f103`과 BBB flasher의 `isotp_fota.c`에 있습니다. 현재 baseline은 아니며 **ISO-TP transport 위에 project-specific FOTA command를 얹은 비교 구현**입니다. UDS service 구현은 아닙니다.

| 항목 | 값 |
| --- | --- |
| Host → Target | Standard ID `0x7E0` |
| Target → Host | Standard ID `0x7E8` |
| Entry | `0x200#DEAD` |
| Command | `0x10` START, `0x20` DATA, `0x30` END, `0x40` JUMP |
| Chunk | START ACK에서 little-endian 256 bytes 협상 |
| Flow Control | default BS 8, STmin 0 ms |
| ISO-TP response timeout | target library 100 ms |
| Host DATA ACK timeout/retry | 150 ms, chunk 전체 최대 3회 |
| Flash | `0x08004000`부터 direct-write, staging 없음 |

START와 END는 ISO-TP Single Frame 형식으로 보내고, DATA는 command 1 byte + 최대 256 bytes를 First Frame/Consecutive Frame으로 분할합니다. DATA ACK 실패 시 Selective NACK이 아니라 chunk 전체를 다시 전송합니다.

ISO bootloader는 최대 112 KiB를 선언하지만 현재 `boot_can_fw_f103` linker는 57,336 B로 제한됩니다. 따라서 repository의 공용 F103 application과 ISO-TP bootloader가 표현하는 최대 범위는 서로 다릅니다.

## 설계상 한계

- Custom response는 Extended ID, request는 Standard ID를 사용합니다.
- Host와 target이 firmware size와 4-byte alignment를 완전하게 검증하지 않습니다.
- Explicit session ID와 block index가 없어 ACK 유실이나 stale frame을 식별하기 어렵습니다.
- DATA retry에 횟수 상한이 없습니다.
- Application validity는 Reset Handler 범위 중심으로 판단하며 active copy 후 전체 CRC를 다시 계산하지 않습니다.
- CRC32는 authenticity, confidentiality, anti-rollback을 제공하지 않습니다.

## 관련 문서

- [시스템 흐름](architecture.md)
- [Memory map](memory-map.md)
- [F103 Custom FOTA 기준선](f103-fota-baseline.md)
