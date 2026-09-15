# 1차 2주 실행 계획

## 범위와 시간 가정

이 계획은 10 working session을 기준으로 합니다. 하루 작업 시간이 다르면 날짜보다 Task 완료 조건을 우선합니다.

첫 2주의 목적은 새 기능을 추가하는 것이 아니라 현재 F103 Custom FOTA가 잘못된 입력과 통신 실패에서 안전하게 종료되도록 만드는 것입니다. Protocol v2 구현, 성능 결론 도출, 완전한 rollback은 이번 범위에 포함하지 않습니다.

필수 검증은 현재 보유한 BBB, STM32F103RB, CAN transceiver/배선과 개발 PC만 사용합니다. External analyzer, oscilloscope, relay power switch, 전문 fault injector는 필요하지 않습니다. CAN physical bit/CRC fault와 정밀 on-wire retransmission 측정은 이번 범위 밖입니다.

## 일정 요약

| 권장 시점 | Task | 예상량 | 핵심 산출물 |
| --- | --- | ---: | --- |
| Day 1 오전 | TW-00 | 0.5일 | baseline build/test 기록 |
| Day 1 오후~Day 3 | TW-01 | 2.5일 | target precondition과 명시적 state |
| Day 4~Day 5 | TW-02 | 2일 | flash/copy/boot 검증 강화 |
| Day 6~Day 7 | TW-03 | 2일 | bounded retry와 CAN error 처리 |
| Day 8 | TW-04 | 1일 | ISO-TP compile baseline과 안전성 수정 |
| Day 9~Day 10 | TW-05 | 2일 | 보유 장비 regression, 기록, 재계획 근거 |

Hardware 문제나 build 환경 문제로 지연되면 TW-04의 ISO-TP 개선 범위를 compile blocker와 memory safety까지만 줄입니다. TW-01~TW-03의 P0 신뢰성을 줄여 일정을 맞추지 않습니다.

### 1주차 목표

- Day 1: TW-00으로 변경 전 build와 known failure를 고정
- Day 1 오후~Day 3: TW-01로 malformed command와 잘못된 state transition 차단
- Day 4~Day 5: TW-02로 flash boundary, copy, application validation 강화
- 주간 종료 기준: target 단독 P0 defect가 정리되고 Custom bootloader/application build가 성공

1주차 종료 시 TW-01 또는 TW-02가 미완료라면 2주차 첫 작업으로 그대로 이어갑니다. 완료되지 않은 상태에서 host/ISO-TP 범위를 동시에 열지 않습니다.

### 2주차 목표

- Day 6~Day 7: TW-03으로 BBB sender의 무한 대기와 오류 전파 수정
- Day 8: TW-04로 ISO-TP compile blocker, buffer, FC baseline 수정
- Day 9~Day 10: TW-05 독립 regression과 보유 장비 evidence 정리
- 주간 종료 기준: 1차 2주 성공 기준을 항목별로 판정하고 다음 2주 우선순위를 다시 결정

2주차에는 새로운 protocol 기능을 시작하지 않습니다. 남은 시간을 Protocol v2 구현에 조금 쓰기보다 TW-05의 실패 재현, trace, test report를 완성하는 편이 다음 계획의 정확도를 높입니다.

### 모든 Task의 면접 산출물

TW-00부터 TW-05까지 각 Task 종료 시 다음을 함께 작성합니다.

- `docs/improvement-plan/interview/<TASK_ID>.md`
- 실제 source/function/test에 근거한 핵심 개념
- 30초 답변 최소 3개
- 대표 2분 답변 1개
- 예상 꼬리질문과 현재 설계 한계
- `interview/QUESTION_BANK.md`의 note link와 상태

[면접 지식 기록 가이드](interview/README.md)와 [노트 템플릿](interview/TEMPLATE.md)을 사용합니다. 면접 노트가 없으면 해당 Task를 `DONE`으로 변경하지 않습니다.

---

## TW-00 — Baseline과 검증 계약 고정

### 목적

변경 전 상태와 이후 검증 방법을 고정합니다. 이전 성능 CSV를 현재 staging 구조의 성능으로 재사용하지 않습니다.

### 현재 근거

- Custom baseline 설명: `docs/f103-fota-baseline.md`
- 현재 memory layout: `docs/memory-map.md`
- Custom target: `boot_can_custom_f103/App/ap/boot_can/boot_can.c`
- BBB sender: `can-fota-BBB/flasher/`
- Yocto build 설정: `../yocto_capston/kas-project.yml`

### 수행 내용

1. 두 repository의 HEAD, branch, dirty 상태를 기록합니다.
2. 사용한 compiler, CMake, host OS, BBB image, CAN bitrate와 보유 장비 구성을 기록합니다.
3. 다음 image의 clean build 결과와 `.bin` 크기를 기록합니다.
   - `boot_can_custom_f103`
   - `boot_can_fw_f103`
   - `boot_can_isotp_f103`
4. BBB C flasher build는 Linux/BBB에서 실행합니다. 실행하지 못하면 `NOT RUN`으로 기록합니다.
5. 현재 known failure를 변경 전 상태로 기록합니다.
   - ISO-TP include/type compile failure
   - oversize START 처리
   - START 없는 DATA/END
   - Custom block ACK loss 후 desynchronization
6. binary artifact 자체는 필요하지 않으면 commit하지 않고, hash와 size만 기록합니다.

### 산출물

- `docs/improvement-plan/reports/TW-00-baseline.md`
- `docs/improvement-plan/interview/TW-00.md`
- `SESSION_HANDOFF.md` 갱신

### 완료 조건

- build별 command, result, toolchain, commit hash가 문서에 있다.
- 실행하지 않은 검증이 명시적으로 `NOT RUN`이다.
- 이후 Task가 비교할 수 있는 baseline이 있다.

### 권장 새 Codex 창 범위

문서와 read-only build만 수행합니다. source defect를 발견해도 TW-01 범위의 코드를 함께 수정하지 않습니다.

---

## TW-01 — Target 입력·state·block 수신 안전성

### 현재 문제

`boot_can_custom_f103/App/ap/boot_can/boot_can.c`에는 다음 문제가 연결되어 있습니다.

- `bootProcessStart()`가 invalid size를 local `rx_size`에만 clamp하고 `original_fw_size`에는 invalid 값을 남깁니다.
- command 순서를 강제하는 state machine이 없어 START 없이 DATA/END/JUMP가 처리됩니다.
- `bootProcessData()`는 현재 block에서 기대하는 DLC와 sequence를 엄격히 검사하지 않습니다.
- buffer copy가 거부되어도 receive bitmap을 mark할 수 있습니다.
- `original_fw_size - total_received_bytes`가 잘못된 순서에서 underflow할 수 있습니다.
- 완전한 block인지와 전체 firmware byte가 모두 수신됐는지를 END에서 확인하지 않습니다.

### 변경 후보 파일

- `boot_can_custom_f103/App/ap/boot_can/boot_can.c`
- `boot_can_custom_f103/App/ap/boot_can/boot_can.h`
- protocol error code가 바뀌면 `can-fota-BBB/flasher/protocol.h`
- host가 새 error를 표시해야 하면 `can-fota-BBB/flasher/custom_fota.c`
- protocol 문서: `docs/protocol.md`

### 구현 방향

1. 기존 wire format을 유지한 채 명시적 state를 추가합니다.
   - 예: `IDLE`, `RECEIVING`, `IMAGE_VERIFIED`, `FAILED`
2. 각 command의 허용 state와 실패 후 state를 표로 먼저 정의합니다.
3. START는 정확한 DLC와 `1 <= size <= 57,336`을 만족할 때만 erase를 시작합니다.
4. invalid START는 기존 active/staging을 변경하지 않고 error를 반환합니다.
5. 현재 block의 expected byte/frame/DLC를 overflow와 underflow 없이 계산합니다.
6. `seq`가 현재 block 범위를 벗어나거나 payload length가 틀리면 bitmap을 mark하지 않습니다.
7. 같은 sequence의 duplicate 수신 정책을 명시합니다. 같은 block 안의 duplicate는 overwrite 없이 수신 완료 상태를 유지하는 방향을 권장합니다.
8. END는 모든 firmware byte가 commit되고 미완료 block이 없을 때만 CRC 단계로 이동합니다.
9. JUMP는 verified state 또는 기존 valid application 정책에 맞는 경우에만 허용합니다.

이번 Task에서는 `session_id`와 `block_id`를 wire에 추가하지 않습니다. ACK loss로 발생하는 block 간 desynchronization은 Protocol v2에서 해결합니다.

### 필수 test case

| Case | 기대 결과 |
| --- | --- |
| START size `0` | erase 없이 ERR |
| START size `57,337` | erase 없이 ERR |
| START DLC `< 5` | erase 없이 ERR |
| IDLE에서 DATA | write 없이 ERR 또는 명시적 ignore |
| IDLE에서 END | CRC/copy 없이 ERR |
| IDLE에서 JUMP | 정책에 따른 안전한 ERR/기존 app jump |
| `seq > last_expected_seq` | buffer/map 변경 없음 |
| 중간 frame의 짧은 DLC | 해당 bit mark 없음 |
| 마지막 frame의 정확한 짧은 DLC | 정상 수신 |
| 모든 byte 전 END | CRC/copy 실행 안 됨 |

### 완료 조건

- command/state transition 표가 code와 `docs/protocol.md`에 일치한다.
- invalid size가 erase 전에 거부됨을 test log로 확인했다.
- DATA 처리의 모든 offset, length, subtraction이 경계 조건에서 안전하다.
- Custom bootloader build가 성공한다.
- BBB 호환 영향이 문서에 적혀 있다.

### 예상 면접 질문

- Bootloader에서 protocol state machine이 필요한 이유는 무엇인가?
- malformed CAN frame이 flash erase로 이어지지 않게 어떻게 막았는가?
- duplicate DATA와 out-of-order DATA를 어떻게 정의했는가?

---

## TW-02 — Flash copy·metadata·boot validation 안전성

### 현재 문제

- `boot_can_custom_f103/App/hw/src/flash.c`의 `addr + length` 검사는 integer overflow에 안전하지 않습니다.
- `bootCopyFw()`는 마지막 write 길이가 4-byte 배수가 아닐 때 실패할 수 있습니다.
- staging metadata 두 번의 `flashWrite()` 반환값이 무시됩니다.
- copy 후 active image 전체 CRC readback이 없습니다.
- `bootVerifyFw()`는 Reset Handler만 넓은 flash 범위에서 검사하고 Initial SP, Thumb bit, active slot 범위를 확인하지 않습니다.
- metadata가 staging 마지막 flash page의 마지막 8 byte를 사용하므로 향후 transactional metadata 설계 시 page erase 단위를 고려해야 합니다.

### 변경 후보 파일

- `boot_can_custom_f103/App/hw/src/flash.c`
- `boot_can_custom_f103/App/hw/include/flash.h`
- `boot_can_custom_f103/App/ap/boot_can/boot_can.c`
- `boot_can_custom_f103/App/ap/ap.c`
- `docs/memory-map.md`
- `docs/architecture.md`

### 구현 방향

1. address 검사는 `length <= END - addr` 형태로 바꾸고 `addr` 자체를 먼저 검사합니다.
2. erase와 write 허용 영역을 generic physical flash 범위가 아니라 용도별 active/staging 범위로 제한하는 방법을 검토합니다.
3. arbitrary firmware size를 지원하려면 마지막 word를 `0xFF` padding하여 write하되 CRC는 original size만 계산합니다.
4. metadata size/CRC write를 모두 확인하고 실패하면 active erase/copy를 시작하지 않습니다.
5. copy 완료 후 active 영역의 CRC를 다시 계산해 staging metadata CRC와 비교합니다.
6. application validation은 최소한 다음을 확인합니다.
   - Initial SP가 STM32F103RB SRAM 범위에 있음
   - Reset Handler의 Thumb bit가 set
   - Thumb bit를 제외한 주소가 active application image 범위에 있음
   - 가능하면 metadata size/CRC와 active CRC가 일치함
7. validation helper를 boot decision과 JUMP에서 같은 방식으로 사용합니다.

이번 Task에서는 metadata page layout을 크게 바꾸거나 true A/B를 구현하지 않습니다. 이는 F3에서 power-loss fault 결과와 함께 설계합니다.

### 필수 test case

- size `1`, `3`, `4`, `255`, `256`, `257`, 최대 크기의 padding/write 경계
- `addr`가 valid지만 `length` 덧셈이 overflow하는 synthetic test 또는 review evidence
- invalid SP
- Reset Handler가 staging 영역을 가리키는 image
- Reset Handler Thumb bit가 clear인 image
- metadata 첫 write/둘째 write 실패
- active copy 후 한 byte corruption에 대한 CRC failure

### 완료 조건

- non-4-byte firmware 처리 정책이 코드와 문서에 일치한다.
- 모든 metadata/write/copy 결과가 상위 state에 전달된다.
- boot decision과 JUMP가 같은 image validation 규칙을 사용한다.
- Custom bootloader와 application build가 성공한다.
- HAL failure 반환이나 checkpoint reset으로 재현할 수 없는 flash 내부 동작은 범위 밖으로 명시하고, 실행하지 않은 보유 장비 시험은 `NOT RUN`으로 남긴다.

### 예상 면접 질문

- vector-last copy가 atomic update와 어떻게 다른가?
- SP와 Reset Handler만 검사하는 것과 CRC까지 검사하는 것의 차이는 무엇인가?
- flash page erase 단위가 metadata 설계에 어떤 영향을 주는가?

---

## TW-03 — BBB timeout·retry·CAN error 처리

### 현재 문제

- `can-fota-BBB/flasher/can_socket.c`의 `send_can_frame()`은 `ENOBUFS`에서 무한 반복합니다.
- `custom_fota.c`의 block response loop는 전체 retry/deadline이 없습니다.
- 일부 DATA, END, JUMP send 반환값이 무시됩니다.
- JUMP ACK나 application의 `ECU_READY`를 확인하지 않습니다.
- target `canInit()`은 내부 실패를 기록해도 항상 `true`를 반환합니다.
- target response가 Extended ID로 전송되지만 BBB request는 Standard ID이며, host의 mask가 이 차이를 숨깁니다.
- CAN RX queue overflow, bus-off, error passive가 update 결과에 연결되지 않습니다.

### 변경 후보 파일

- `can-fota-BBB/flasher/can_socket.c`
- `can-fota-BBB/flasher/can_socket.h`
- `can-fota-BBB/flasher/custom_fota.c`
- `can-fota-BBB/flasher/fota_common.*`
- `can-fota-BBB/flasher/main.c`
- `boot_can_custom_f103/App/hw/src/can.c`
- `boot_can_custom_f103/App/hw/include/can.h`
- 필요 시 dashboard 실행 결과 처리
- Yocto 내 source 사본은 F4의 source-of-truth 결정 전까지 무작정 수동 동기화하지 않고 drift를 보고합니다.

### 구현 방향

1. `send_can_frame()`에 monotonic absolute deadline 또는 제한 횟수를 전달합니다.
2. error return을 최소한 `invalid argument`, `queue deadline`, `socket error`, `response timeout`, `target error`로 구분합니다.
3. START, 모든 DATA/retransmit, END, JUMP에서 send 결과를 확인합니다.
4. block retry에는 per-attempt timeout과 전체 retry cap을 모두 둡니다.
5. timeout마다 마지막 frame을 무한 재전송하는 동작은 제한하고, v1 protocol의 ACK loss 한계를 오류로 명확히 보고합니다.
6. SocketCAN receive filter를 사용하는 경우 expected response와 CAN error frame을 함께 수신하도록 설계합니다.
7. target response ID는 request와 같은 Standard 11-bit 정책으로 통일하고 문서화합니다.
8. target `canInit()`은 실제 초기화 결과를 반환합니다.
9. RX software queue drop counter와 CAN error/bus-off 상태를 관찰할 최소 hook을 추가합니다.
10. AutoBusOff 정책은 hardware 설정과 recovery 방법을 함께 결정하고, 단순 enable만 한 뒤 검증 없이 완료 처리하지 않습니다.

### 필수 test case

- `can0` down 또는 unplug 상황에서 정해진 시간 안에 process 종료
- 지속적인 `ENOBUFS`가 무한 hang으로 이어지지 않음
- target 무응답 시 block retry cap 이후 non-zero exit
- END send 실패가 성공으로 출력되지 않음
- JUMP send/ACK 실패가 결과에 반영됨
- Standard/Extended ID를 `candump`에서 확인
- CAN RX queue overflow counter의 증가를 synthetic 또는 load test로 확인

이 시험은 BBB와 STM32만 사용합니다. ACK error와 bus-off는 상대 node를 down/disconnect하여 유도하고, physical bus를 short하거나 임의 전압을 인가하지 않습니다.

### 완료 조건

- 사용자 중단 없이 모든 host loop가 유한 시간 내 종료한다.
- 성공과 실패가 CLI exit code에 반영된다.
- frame send 실패를 성공 frame count로 세지 않는다.
- host와 target CAN ID type이 문서와 trace에서 일치한다.
- Custom end-to-end 정상 update가 regression을 통과한다.

### 예상 면접 질문

- SocketCAN의 `ENOBUFS`는 무엇을 의미하며 어떻게 처리했는가?
- retry count와 absolute deadline을 둘 다 둔 이유는 무엇인가?
- CAN controller bus-off 복구 정책은 어떻게 정했는가?

---

## TW-04 — ISO-TP build와 최소 baseline 수정

### 현재 문제

- `boot_can_isotp_f103/App/ap/boot_can/isotp_port.h`가 fixed-width integer type이 보장되기 전에 `iso15765/isotp.h`를 include하여 현재 build가 실패합니다.
- target START의 invalid size 처리도 Custom과 같은 local clamp 문제를 가집니다.
- DATA padding loop가 receive buffer 경계를 넘을 가능성이 있습니다.
- BBB `isotp_send_chunk()`가 최초 Flow Control의 STmin은 사용하지만 BS마다 다음 FC를 기다리지 않습니다.
- ISO-TP data FF/CF와 FC가 frame counter에 포함되지 않아 현재 metrics가 비교 자료로 사용할 수 없습니다.
- ISO target은 active 영역에 direct write하여 Custom staging/copy와 end-to-end 시간이 구조적으로 다릅니다.

### 변경 후보 파일

- `boot_can_isotp_f103/App/ap/boot_can/isotp_port.h`
- `boot_can_isotp_f103/App/ap/boot_can/iso15765/isotp.h`
- `boot_can_isotp_f103/App/ap/boot_can/boot_can.c`
- `boot_can_isotp_f103/App/ap/boot_can/iso15765/isotp_config.h`
- `can-fota-BBB/flasher/isotp_fota.c`
- 공통 counter 구조를 도입할 경우 `can_socket.*`, `fota_common.*`
- `docs/protocol.md` 또는 별도 baseline report

### 구현 방향

1. ISO-TP target compile blocker를 최소 수정으로 해결합니다.
2. size `0`과 maximum 초과는 erase 전에 거부합니다.
3. receive/padding/write 길이를 buffer capacity 안으로 제한합니다.
4. host가 FC의 FS, BS, STmin을 해석하고 BS가 0이 아닐 때 다음 FC를 기다리게 합니다.
5. frame counter는 send attempt, software fault drop, SocketCAN send success, receive success, protocol retransmission을 분리합니다.
6. 이번 Task에서 Selective NACK 우월성 결론을 다시 내리지 않습니다.
7. Custom staging과 ISO direct-write 차이를 결과에 명시하고, transport-only benchmark 필요성을 F2 입력으로 남깁니다.

### 필수 test case

- ISO target clean compile
- size 0/초과 START 거부
- 최대 receive buffer 경계와 padding 경계
- BS `0`, `1`, `8`에 대한 host 송신 동작
- STmin millisecond 및 `0xF1`~`0xF9` 처리
- 실제 FF, CF, FC, ACK의 application/SocketCAN count가 같은 BBB의 `candump -L` trace와 일치하는지 표본 확인

### 완료 조건

- ISO target build가 성공한다.
- known buffer overflow 경로가 제거된다.
- host가 receiver의 BS를 준수한다.
- metric counter 정의가 문서화되고 trace 표본과 일치한다.
- ISO direct-write 결과를 Custom staging 결과와 동일 조건인 것처럼 표시하지 않는다.

### 예상 면접 질문

- ISO-TP의 BS와 STmin은 receiver resource를 어떻게 보호하는가?
- application-level retry와 ISO-TP 자체 retransmission은 어떻게 다른가?
- 두 protocol의 flash backend가 다르면 측정 결과에 어떤 bias가 생기는가?

---

## TW-05 — 통합 regression과 2주 결과 정리

### 목적

앞선 변경이 실제 정상 update를 깨뜨리지 않았는지 확인하고, 다음 2주 계획을 결정할 수 있는 증거를 남깁니다.

### 수행 내용

1. 두 repository의 최종 diff와 protocol 호환 영향을 검토합니다.
2. 가능한 모든 image와 BBB flasher를 clean build합니다.
3. Custom 정상 update와 실패 case를 현재 BBB와 STM32에서 수행합니다.
4. ISO-TP는 build, protocol trace, 가능한 범위의 update를 확인합니다.
5. 다음 v1 한계를 재현하고 결과를 기록합니다.
   - target이 block을 commit한 직후 ACK 유실
   - host가 이전 block의 마지막 frame을 재전송
   - target과 host의 block position desynchronization
6. 주요 시험에서 같은 BBB의 `candump -L` trace, `ip -details -statistics link show can0`, firmware hash, command, exit code, 실행 시간을 보존합니다.
7. TW-00 baseline 대비 code size/RAM 변화와 동작 차이를 표로 만듭니다.
8. [마스터 현황](README.md)과 [인수인계 문서](SESSION_HANDOFF.md)를 갱신합니다.
9. TW-00~TW-04 면접 노트를 검토하고 질문 은행에서 최소 5개를 골라 사용자 rehearsal 대상으로 표시합니다. 실제 `REHEARSED` 상태는 사용자가 직접 연습한 뒤에만 변경합니다.

### 최소 test matrix

| Category | Case | Required result |
| --- | --- | --- |
| Build | Custom bootloader | PASS |
| Build | FreeRTOS application | PASS |
| Build | ISO-TP bootloader | PASS |
| Build | BBB C flasher on Linux/BBB | PASS 또는 환경 근거가 있는 NOT RUN |
| Normal | Custom valid image | PASS |
| Boundary | size 0/max/max+1 | 예상 결과 일치 |
| Order | DATA/END before START | flash 변경 없음 |
| Loss | DATA 1-frame omission | NACK 후 성공 |
| Failure | target disconnect | deadline 내 실패 |
| Boot | invalid SP/PC image | jump 거부 |
| Recovery | checkpoint reset 또는 수동 power disconnect | 현재 결과와 재현 한계 기록, F3 입력 |
| Protocol limit | block ACK loss | 실패 재현 및 F1 요구사항 연결 |

### 산출물

- `docs/improvement-plan/reports/TW-05-review.md`
- `docs/improvement-plan/interview/TW-05.md`
- test log와 trace의 상대 경로
- 미해결 defect 목록
- 다음 2주에 선택할 F1~F4 우선순위 제안

### 완료 조건

- 1차 2주 성공 기준 각각에 PASS/FAIL/NOT RUN 상태가 있다.
- 실패 결과도 삭제하거나 숨기지 않고 원인과 다음 Task를 연결했다.
- 후속 계획을 시작할지, P0를 연장할지 판단할 수 있다.

## 2주 안에 하지 않을 것

- true dual-bank/A-B
- full rollback
- AES encryption
- secure boot 전체 구현
- full UDS stack
- CAN-FD 전환
- multi-ECU update
- Python sender 재작성
- dashboard UI polish
- 현재 문제와 무관한 FreeRTOS task 추가
- physical bit/CRC/stuff/form error 정밀 주입
- external analyzer 기반 on-wire retransmission 계측
- relay 기반 자동 power-cut

이 기능들은 현재 P0 결함과 실험 재현성을 해결하지 못합니다.
