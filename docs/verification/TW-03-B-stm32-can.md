# TW-03(B) — STM32 응답 Standard ID·`canInit()` 결과·CAN RX drop counter

## 한눈에 보기

- 범위: Issue #6 중 **B1** (target software). 응답 Standard ID, `canInit()` 실제 결과 반환과 caller 처리, RX drop/overrun/bus-off counter.
- bus-off recovery 정책(AutoBusOff, BBB `restart-ms`)은 hardware 실험 후 결정한다 (**B2**, 이 문서 범위 밖).
- Build: bootloader·application의 Debug/Release 모두 `PASS`, 새 warning 없음.
- 실장 시험(BBB + NUCLEO-F103RB): Standard 응답, 수동 ERR, erase 중 FIFO overrun 감지, `canInit()` 실패 처리(app 유효/무효) 모두 `PASS`. software queue drop은 이번 부하에서 발생하지 않아 증가를 확인하지 못함.
- Wire format 변화: 응답 frame format만 Extended에서 Standard로 바뀐다. numeric ID `0x101`, payload, timing은 같다. 현재 BBB flasher는 `CAN_SFF_MASK`로 비교하므로 이전·이후 target 모두와 호환된다.

## 이 작업에서 막으려는 문제

| 기존 문제 | 왜 위험한가 | 이번 변경 |
| --- | --- | --- |
| `canMsgWrite()`가 응답을 Extended ID로 송신 | host는 Standard로 송신. strict filter를 쓰는 tool과 호환되지 않음 (TW-03 trace: Standard `100#` 2,197, Extended `00000101#` 63) | `IDE = CAN_ID_STD`, ID `> 0x7FF`와 DLC `> 8` 거부 |
| `canInit()`이 항상 `true` 반환, filter 결과 무시 | CAN이 동작하지 않아도 bootloader가 FOTA mode로 들어가 응답 없이 대기 | 콜백 등록·notification·filter·start 결과를 모두 반영. 앞 단계가 실패하면 `HAL_CAN_Start()`를 부르지 않음 |
| caller가 CAN init 결과를 모름 | 실패가 밖으로 보이지 않음 | bootloader: FOTA mode 진입 전에 `canIsInit()` 확인. 실패하면 app이 유효할 때 jump하고, 아니면 LED 켜진 채 정지. app: CLI가 켜진 build에서 오류 출력 |
| software RX queue 가득 참(`qbufferWrite()` 실패)을 무시 | frame 유실이 보이지 않음 | `g_can_rx_queue_drop_count` |
| bxCAN RX FIFO1 overrun 미감지 | flash erase/program 중에는 CPU가 멈춰 ISR도 돌지 않으므로 hardware FIFO(3개)에서 먼저 유실될 수 있음 (가설) | `CAN_IT_RX_FIFO1_OVERRUN` 활성화, `g_can_rx_fifo_overrun_count` |
| bus-off interrupt를 켜고도 처리하지 않음 (bootloader) | bus-off 발생 여부를 알 수 없음 | `g_can_busoff_count`. 복구 정책은 B2 |

## 바뀐 파일

| 파일 | 핵심 변경 |
| --- | --- |
| `boot_can_custom_f103/App/hw/src/can.c`, `include/can.h` | Standard ID 송신과 인자 검사, `canInit()` 결과 반환, `canIsInit()`, error callback 등록(`HAL_CAN_ERROR_CB_ID`), 진단 counter 3개 |
| `boot_can_fw_f103/App/hw/src/can.c`, `include/can.h` | 위와 같음. app은 notification에 `RX_FIFO1_OVERRUN`, `BUSOFF`, `ERROR`를 추가 (기존: `RX_FIFO1_MSG_PENDING`만) |
| `boot_can_custom_f103/App/ap/ap.c` | FOTA mode 진입 전 `canIsInit()` 검사, `bootHandleCanInitFail()` |
| `boot_can_fw_f103/App/ap/ap.c` | CLI build에서 CAN init 실패 출력 |
| `docs/protocol.md`, `CLAUDE.md` | Standard ID 설명과 이전 firmware 호환성, 진단 counter |

CubeMX 생성 파일(`Core/`, `.ioc`)은 바꾸지 않았다. `AutoBusOff = DISABLE`은 그대로다.

### 설계 메모

- HAL은 `hcan->ErrorCode`에 error bit를 누적(OR)한다. callback마다 `HAL_CAN_ResetError()`로 지워야 같은 사건이 두 번 세어지지 않는다.
- counter는 ISR에서만 증가하고 debugger가 읽는다. 32-bit aligned `volatile uint32_t` 읽기는 Cortex-M3에서 단일 접근이다.
- bootloader에는 UART/CLI 출력이 없으므로(`logPrintf`가 빈 macro) counter는 non-static 전역 변수로 두고 SWD로 읽는다. app의 `g_app_task_stack_high_water_mark_words`와 같은 방식이다.
- CAN init 실패 시 bootloader가 FOTA mode에 머물러도 update는 불가능하다. 유효한 app이 있으면 즉시 돌려보내고, 없으면 LED를 켠 상태(정상 FOTA mode는 100 ms 깜빡임)로 원인을 구분할 수 있게 했다.

## 실제로 실행한 검증

환경: Windows, STM32CubeCLT 1.19.0 (`arm-none-eabi-gcc` 13.3.1), CMake preset `Debug`/`Release`, branch `feature/TW-03-B-stm32-can` (base `bce11de`).

| Target | Preset | 변경 전 FLASH / RAM | 변경 후 FLASH / RAM | 결과 |
| --- | --- | --- | --- | --- |
| bootloader (`boot_can_custom_f103`, 16 KiB) | Debug | 13,800 B (84.23%) / 3,184 B | 14,060 B (85.82%) / 3,200 B | PASS |
| bootloader | Release | 9,004 B (54.96%) / 3,184 B | 9,208 B (56.20%) / 3,200 B | PASS |
| application (`boot_can_fw_f103`, 57,336 B) | Debug | 15,196 B (26.50%) / 5,304 B | 15,388 B (26.84%) / 5,312 B | PASS |
| application | Release | 10,156 B (17.71%) / 5,304 B | 10,284 B (17.94%) / 5,312 B | PASS |

- warning: 기존 `flash.c:6 FLASH_PAGE_SIZE redefined` 외에 없음.
- `arm-none-eabi-nm`로 counter symbol 확인 (bootloader Debug/Release 모두: `g_can_busoff_count 0x2000066C`, `g_can_rx_fifo_overrun_count 0x20000670`, `g_can_rx_queue_drop_count 0x20000674`). 주소는 build마다 달라질 수 있으니 시험 시 다시 확인한다.
- 두 firmware 모두 `_USE_HW_CLI`가 꺼져 있어 `cliCmd()`와 CLI 출력 변경은 **컴파일되지 않았다** (검증 안 됨).
- bootloader Debug가 16 KiB의 85.8%다. 이후 기능 추가 시 여유를 확인해야 한다.

## 실장 시험

### 환경

- BBB: Yocto `core-image-minimal`(yocto_capston `8546d49`), kernel 6.6.21, `c_can` `can0` 500 kbit/s, `restart-ms 0`. 접속은 USB NCM gadget SSH.
- Flasher: TW-03 A 시험 때 BBB에 올린 binary(PR #5로 merge된 코드와 같은 source)를 그대로 사용.
- STM32: NUCLEO-F103RB. 이 branch의 **Debug** build를 ST-LINK(SWD, `STM32_Programmer_CLI`, verify 포함)로 flash. bootloader 14,060 B → `0x08000000`, application 15,388 B → `0x08004000`.
- Update image: 같은 application `.bin` 15,388 B, 최대 크기 시험은 그 뒤를 `0xFF`로 채운 57,336 B.
- 관측: 각 시험마다 BBB `candump -L can0`, SWD hotplug 읽기(core를 멈추지 않음). Counter 주소는 `arm-none-eabi-nm`으로 확인한 값(bootloader Debug: `0x2000066C` bus-off, `0x20000670` FIFO overrun, `0x20000674` queue drop).
- BBB에 RTC가 없어 trace timestamp의 절대 날짜는 의미가 없고, 시간 차이만 사용한다.

### 결과

| # | 시험 | 결과 | 근거 |
| --- | --- | --- | --- |
| 1 | 정상 update 15,388 B | PASS, exit 0, 3.77 s | 응답 Standard `101#` 64개, Extended `00000101#` 0개 (flasher RX 64와 일치). TX 2,227, 재전송 0 |
| 1b | 정상 update 57,336 B | PASS, exit 0, 9.15 s | `101#` 227개, `00000101#` 0개. TX 8,290 (TW-03 A와 같음) |
| 2 | 수동 ERR (`200#DEAD` 후 START 없이 JUMP, END) | PASS | `100#C0` → `101#8700`, `100#80` → `101#8700` |
| 3 | RX flood 중 counter | PASS(FIFO overrun) / 미확인(queue drop) | 아래 표 |
| 4a | `canInit()` 강제 실패 + 유효한 app + FOTA 요청 | PASS | 요청 후 1.6/3.3/5.1 s에 VTOR `0x08004000`(app 실행 중). flasher는 START 응답 없음(`RESP_TIMEOUT`, 10 s) |
| 4b | `canInit()` 강제 실패 + 무효 app(첫 page 지움) | PASS | `0x08004000` = `FFFFFFFF`, VTOR `0x00000000`(bootloader에 머묾), GPIOA ODR 6회 모두 `0x0000A020`(LED PA5 켜진 채) |
| 4c | 대조: 정상 bootloader + FOTA 요청 | PASS | VTOR `0x00000000`이 유지되고 ODR이 `A020`/`A000`으로 바뀜(100 ms 깜빡임), 10 s timeout 후 VTOR `0x08004000` |
| 5 | 복구 후 정상 update | PASS, exit 0 | `101#` 64개, `00000101#` 0개 |

모든 시험에서 BBB `can0`는 `ERROR-ACTIVE`, berr-counter tx 0 rx 0, bus-error 0이었다.

### 시험 3 상세 (RX flood)

FOTA mode에서 다른 ID(`0x123`, DLC 8)로 `cangen -g 0 -i`를 실행했다. 대조는 bootloader가 대기 중일 때, 본 시험은 최대 크기 START 직후(staging erase 중)다. START ACK는 START 후 1.23 s에 왔으므로, 0.10 s 동안의 두 번째 flood는 erase 구간 안에 있다.

| 시점 | bus-off | FIFO overrun | queue drop |
| --- | --- | --- | --- |
| FOTA mode 진입 후 | 0 | 0 | 0 |
| 대조 flood 후 (flash 작업 없음) | 0 | 0 | 0 |
| erase 중 flood 후 | 0 | 4 | 0 |

- `cangen -n 2000`을 두 번 요청했지만 `-i`(ENOBUFS 무시) 때문에 BBB TX queue(qlen 10)에서 대부분 버려졌다. 실제로 bus에 나간 `0x123` frame은 trace 기준 두 번 합쳐 548개다.
- FIFO overrun counter는 **잃은 frame 수가 아니라 overrun 사건 수**다. erase 중에는 CPU가 flash fetch에서 멈춰 ISR이 돌지 못하므로, 그동안 들어온 frame은 FIFO 3개를 넘는 만큼 사라지고 overrun은 ISR이 다시 돌 때 1회로 세어진다. 4회인 것은 erase가 page 단위로 진행되어 page 사이에 ISR이 실행되기 때문으로 추정한다 (미검증).
- 결론: flash erase 중에는 software queue가 아니라 bxCAN hardware FIFO에서 frame을 잃는다는 가설을 확인했다. 대기 중에는 같은 flood에서 유실이 없었다.
- software queue(64개) drop은 발생하지 않았다. main loop가 ISR보다 늦어지는 구간(예: END의 CRC 계산)에 flood를 맞춰야 하지만, END 직후 JUMP로 app이 실행되면 bootloader RAM의 counter가 덮어써져 읽을 수 없다. 이 counter의 증가는 아직 hardware로 확인하지 못했다.

### 시험 4 방법

commit하지 않는 임시 build에서 `canInit()`의 `is_init = ret;` 직전에 `ret = false;`를 넣어 bootloader만 flash했다. 4b는 `STM32_Programmer_CLI -e 16`으로 app 첫 page를 지운 뒤 reset했다(staging은 시험 3의 START로 이미 지워져 auto-recovery도 실패한다). 시험 후 정상 bootloader와 application을 다시 flash했고, 임시 줄은 source에서 제거했다.

## NOT RUN과 남은 일

| 항목 | 상태 | 비고 |
| --- | --- | --- |
| software queue drop counter 증가 | NOT RUN | 위 시험 3 상세 참고 |
| 시험 4a flasher의 exit code | 기록 안 됨 | 시험 script의 quoting 오류로 exit code가 잘못 기록됨. log의 `RESP_TIMEOUT` 메시지만 근거로 사용 |
| Release build 실장 시험 | NOT RUN | 실장 시험은 Debug build로만 수행 |
| CLI 경로 컴파일 | NOT RUN | `_USE_HW_CLI` 꺼짐 |
| bus-off 유도와 recovery 정책 (AutoBusOff, BBB `restart-ms`) | TODO (B2) | 유도 방법 미정. physical bus short·전압 인가는 하지 않음(상대 node down/disconnect만 사용) |
| BBB의 Standard-only 응답 filter | TODO | 모든 target 갱신 후. 지금은 이전 firmware 호환을 위해 유지 |
| target 수신 시 `id_type` 검사 | 범위 밖 | `bootProcess()`는 numeric ID `0x100`만 비교 (Extended `0x100`도 수락) |
| `SendResponse()`/`SendNackMap()`의 `canMsgWrite()` 반환값 무시 | 범위 밖 | TX mailbox가 가득 차면 응답이 조용히 사라짐. host는 timeout/retry로 처리 |
