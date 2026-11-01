# TW-03(A) — BBB flasher timeout·retry·CAN error 처리

## 한눈에 보기

- 범위: BBB Custom flasher(`can-fota-BBB/flasher/`)의 host 측 처리. Target 측 변경(`canInit()` 반환값, 응답 Standard ID, RX drop counter, bus-off 정책)은 별도 작업(TW-03 B)이다.
- 코드와 build: 완료 (host gcc, ARM cross gcc 모두 warning 없음)
- BBB + STM32F103RB 실장 시험: 정상 update 3회와 실패 경로 5종 `PASS`
- Wire format(CAN ID, header, block/sequence, target timeout)은 바꾸지 않았다. 기존 STM32 bootloader와 그대로 호환된다.

## 이 작업에서 막으려는 문제

| 기존 문제 | 왜 위험한가 | 이번 변경 |
| --- | --- | --- |
| `send_can_frame()`이 `ENOBUFS`에서 무한 반복 | ACK하는 node가 없으면 process가 끝나지 않음 | monotonic deadline 100 ms 후 `TX_TIMEOUT` |
| DATA block 응답 loop에 상한 없음 | target이 응답하지 않으면 마지막 frame을 영원히 재전송 | block당 retry 20회, DATA 단계 전체 120 s |
| DATA, 재전송, END, JUMP, entry의 send 결과 무시 | 송신 실패를 성공으로 출력하고 TX count에 포함 | 모든 send 결과 확인, 성공한 send만 count |
| JUMP ACK를 기다리지 않음 | vector 검사 실패(`ERR 0x05`)도 성공으로 보임 | ACK 1 s 대기, 실패 시 non-zero exit |
| CAN error frame을 받지 않음 | dead bus와 단순 timeout을 구분할 수 없음 | `CAN_RAW_ERR_FILTER`로 수신. bus-off는 즉시 실패, warning/passive는 경고와 통계 |
| exit code가 0/1뿐 | dashboard나 script가 실패 원인을 알 수 없음 | `fota_err_t` code로 종료 (`docs/protocol.md`의 Host exit code 표) |

## 바뀐 파일

| 파일 | 핵심 변경 |
| --- | --- |
| `can-fota-BBB/flasher/fota_common.[ch]` | `fota_err_t`, `fota_err_str()`, `monotonic_now()`. `trigger_fota_entry()`가 send/flush 결과를 반환 |
| `can-fota-BBB/flasher/can_socket.[ch]` | bounded `send_can_frame()`, error filter 설정, error frame 처리와 통계, `flush_rx_buffer()`가 error frame을 기록, 응답 DLC 검사 |
| `can-fota-BBB/flasher/custom_fota.c` | DATA 단계를 `send_data_blocks()`로 분리, retry 상한과 deadline, `expect_ack()`로 START/END/JUMP 공통 처리, 실패 시에도 통계 출력 |
| `can-fota-BBB/flasher/main.c` | 실패 원인별 exit code |
| `docs/protocol.md` | BBB timeout 표, JUMP 응답 대기, host exit code |

ISO-TP 경로(`isotp_fota.c`)는 수정하지 않았다. 다만 공용 `send_can_frame()`을 쓰므로 bounded TX의 효과는 받는다. ISO-TP의 END/JUMP send 결과 무시는 TW-04 범위로 남긴다.

## 시험 환경

- BBB: Yocto `core-image-minimal`(yocto_capston `fac9c45`), kernel 6.6.21, `c_can` `can0` 500 kbit/s, `restart-ms 0`
- STM32: NUCLEO-F103RB, CanBootloader `62056c3` 기준 bootloader와 application(사전에 flash된 상태)
- Flasher: 이 branch를 `make CC=arm-linux-gnueabihf-gcc LDFLAGS=-static`(Ubuntu 22.04 `gcc-arm-linux-gnueabihf` 11.4.0)으로 빌드해 BBB의 임시 디렉터리에서 실행. Yocto recipe의 source 사본은 수정하지 않았다.
- Firmware: `boot_can_fw_f103` **Debug** build `boot_can_fw.bin` 15,180 B (`62056c3`, Windows STM32Cube for VS Code). 최대 크기 시험은 같은 image 뒤를 `0xFF`로 채운 57,336 B.
- Trace: 각 시험마다 `candump -L can0`. BBB에 RTC가 없어 trace timestamp의 절대 날짜는 의미가 없고, 시간 차이만 사용한다.
- BBB 커널에 `vcan` module이 없어 모든 시험은 실제 `can0`와 STM32로 수행했다.
- 장애 유도: NUCLEO RESET(B2) 버튼. 짧게 누르면 target 재부팅(CAN ACK는 하지만 protocol 응답 없음), 누른 채 유지하면 bus에 ACK하는 node가 없음.

## 실제로 실행한 검증

| ID | 항목 | 결과 | 확인 내용 |
| --- | --- | --- | --- |
| B1 | host build (`gcc -Wall -Wextra`) | **PASS** | warning 없음 |
| B2 | ARM cross build (static) | **PASS** | warning 없음, `ELF 32-bit LSB executable, ARM, EABI5, statically linked` |
| T1 | 정상 update, 15,180 B | **PASS** | exit 0, 3.73 s. TX 2,197 / RX 63 = 60 block 계산과 일치. END ACK, JUMP ACK(JUMP 후 약 0.2 ms) 확인. LD2 1 s toggle |
| T1b | 정상 update, 최대 57,336 B | **PASS** | exit 0, 9.13 s. TX 8,290 / RX 227 = 224 block 계산과 일치 |
| T2 | `can0` down | **PASS** | entry send에서 `ENETDOWN`, **exit 4 `SOCKET`**, 약 20 ms 만에 종료. 시험 후 `can0`을 500 kbit/s로 복구 |
| T3 | DATA 22.8%에서 RESET 짧게 | **PASS** | 재부팅한 target이 DATA에 응답하지 않음. 재전송 20회 후 **exit 8 `RETRY_EXHAUSTED`**. 마지막 ACK부터 마지막 TX까지 3.165 s(21 × 150 ms). 보고된 TX 1,945 = trace `100#` 1,945 |
| T4 | DATA 28.1%에서 RESET 유지 | **PASS** | warning → error-passive 경고 후, `ENOBUFS`가 100 ms 이상 지속되어 **exit 3 `TX_TIMEOUT`**. 보고된 TX 2,375, trace `100#` 2,303 |
| T5 | RESET을 누른 채 시작 (수정 전 binary) | **FAIL → 수정** | exit 5로 종료는 됐지만 결과가 `last controller state 0x00`으로 잘못 보고됨. 진입 대기 중 받은 error frame 2개를 `flush_rx_buffer()`가 stale data로 버림 |
| T5b | T5 재시험 (수정 후 binary) | **PASS** | 진입 대기 중 `0x08 (warning)` → `0x20 (error-passive)` 경고 출력, 10.01 s 후 **exit 5 `RESP_TIMEOUT`**, `last controller state 0x20` |
| T6 | 장애 시험 후 정상 update (수정 후 binary) | **PASS** | exit 0, TX 2,197 / RX 63. `can0`이 ERROR-PASSIVE(TEC 131)에서 ERROR-ACTIVE(TEC 0)로 복구되고 `0x40 (error-active)` 기록 |
| T7 | T3~T5 후 기존 application 보존 | **PASS** | 매 시험 후 버튼을 떼면 LD2가 1 s 주기로 toggle (END 전 중단이라 active 영역 변경 없음) |
| ID | Standard/Extended ID trace 확인 | **관측** | T1에서 요청 Standard `100#` 2,197개, 응답 Extended `00000101#` 63개, Standard `101#` 0개. 불일치는 TW-03 B에서 수정 |

T1, T1b, T2, T3, T4는 수정 전 binary로 실행했다. 수정(error frame 기록, `0x40` 표시)은 진입 대기 중 flush 경로와 출력 문구에만 영향을 주며, 수정 후 binary로 정상 경로(T6)와 진입 실패 경로(T5b)를 다시 확인했다.

## 관측에서 얻은 사실

- **`write()` 성공은 전달 성공이 아니다.** T4에서 72 frame(2,375 − 2,303)은 kernel queue에 들어갔지만 ACK가 없어 bus로 나가지 못했다. T5에서는 candump가 0 byte였다. SocketCAN loopback은 송신 완료된 frame만 echo하기 때문이다. 따라서 결과의 `송신 프레임 (TX)`는 "kernel이 받아들인 frame 수"를 뜻하며, 전달 확인은 ACK/NACK 응답으로만 판단한다.
- **`c_can`은 ACK error를 개별 frame으로 보고하지 않았다.** 모든 시험에서 ACK error count는 0이었다. `berr-reporting`이 꺼진 상태에서는 controller state 변화(warning, passive, active 복귀)만 error frame으로 왔다. ACK 노드 부재는 이 state 변화와 `ip -statistics`의 `error-warn`/`error-pass` 증가로 확인했다.
- **ACK error만으로는 bus-off가 되지 않았다.** T4와 T5에서 TEC는 128~133에서 멈추고 error-passive를 유지했다. Error-passive 상태에서 ACK error는 TEC를 더 올리지 않는다는 CAN 규칙과 일치한다. 따라서 bus-off 즉시 실패 경로(`FOTA_ERR_BUS`)는 이번에 실제로 실행되지 않았다.

## NOT RUN과 남은 일

| 항목 | 상태 | 이유 / 다음 단계 |
| --- | --- | --- |
| END send 실패 | **NOT RUN** | END 한 frame만 골라 실패시킬 방법이 현재 장비에 없다. 코드상 모든 send 실패는 같은 경로(`send_cmd_frame()` → 실패 반환)로 처리되며, 그 경로는 T2와 T4에서 실행됐다 |
| JUMP ACK 실패 / `ERR 0x05` | **NOT RUN** | invalid vector image가 필요하다. TW-02의 negative image 시험과 함께 수행 |
| bus-off (`FOTA_ERR_BUS`) | **NOT RUN** | 위 관측대로 ACK error로는 유도되지 않았다. 보유 장비로 안전하게 유도할 방법은 TW-03 B의 bus-off 정책 결정과 함께 검토 |
| `CUSTOM_DATA_PHASE_TIMEOUT_MS` 초과 | **NOT RUN** | block retry 상한(최대 약 3 s/block)이 먼저 걸리므로, 120 s에 도달하려면 여러 block에 걸친 간헐 장애가 필요 |
| NACK 선별 재전송 회귀 | **NOT RUN** | 이번 시험에서 NACK이 발생하지 않음(재전송 0). 경로의 결정적 시험은 F2 fault injection 범위 |
| dashboard 경유 실행 | **NOT RUN** | dashboard는 `returncode == 0`만 검사하므로 원인별 exit code와 호환된다(코드 확인만) |
| `ECU_READY` GPIO 확인 | 범위 밖 | JUMP ACK까지만 확인. application 기동 확인은 별도 작업 |
| Yocto source 사본 동기화 | 범위 밖 | 이 변경이 merge된 뒤 yocto_capston에서 별도 작업 (F4의 source-of-truth 결정) |

## 범위 밖

Physical bit/stuff/form fault, controller frame CRC 손상, hardware 자동 재전송의 on-wire 횟수 측정, oscilloscope 분석, relay power-cut은 범위 밖이다. External analyzer, fault injector 같은 새 장비를 dependency로 제안하지 않는다.
