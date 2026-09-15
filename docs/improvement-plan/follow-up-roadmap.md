# 2주 이후 후속 로드맵

## 문서 성격

이 문서는 1차 2주 종료 후 사용할 전체 backlog입니다. 날짜가 확정된 약속이 아니라 dependency와 우선순위를 나타냅니다.

TW-05의 실제 test 결과를 반영해 순서와 범위를 다시 산정해야 합니다. 남아 있는 P0 defect가 있다면 아래 기능보다 먼저 해결합니다.

모든 필수 완료 조건은 현재 보유한 BBB, STM32F103RB, CAN transceiver/배선과 개발 PC만으로 수행합니다. External analyzer, oscilloscope, relay power switch, 전문 CAN fault injector는 optional이며 Task 완료 조건에 포함하지 않습니다.

F1~F6도 각 Task 종료 시 `interview/<TASK_ID>.md`와 질문 은행을 갱신합니다. 구현 전 예상 답변이 아니라 실제 diff, protocol spec, raw test evidence를 반영하며 [면접 지식 기록 가이드](interview/README.md)를 따릅니다.

## 권장 큰 흐름

| Phase | 예상 기간 | 핵심 결과 |
| --- | ---: | --- |
| F1 | 4~6일 | ACK loss에도 idempotent한 Protocol v2 |
| F2 | 5~7일 | 재현 가능한 Selective NACK 대 ISO-TP 실험 |
| F3 | 5~8일 | checkpoint reset과 수동 power-loss recovery evidence |
| F4 | 3~5일 | Yocto clean build와 production-like service 운영 |
| F5 | 2~4일 | pure logic unit test와 parser fuzzing |
| F6 | 3~6일 | signed manifest prototype, 조건부 |

시간이 2주 더 주어지면 F1과 F2를 우선합니다. F3는 test build의 결정적 reset injection과 수동 power disconnect로 수행하며 별도 power-cut 장비를 기다리지 않습니다.

---

## F1 — Transactional Protocol v2

### 해결할 현재 문제

v1에는 session과 block 식별자가 없습니다. Target이 block을 flash에 commit한 뒤 ACK가 유실되면 host는 이전 block의 frame을 다시 보내고, target은 이를 다음 block으로 해석할 수 있습니다. 이 문제는 timeout 값 조정만으로 해결되지 않습니다.

### 목표

- update session과 block transaction을 명시적으로 식별
- duplicate request를 재실행하지 않고 동일 response로 처리
- stale frame이 다음 block에 기록되지 않음
- target과 host가 recovery 가능한 오류와 session abort를 구분

### 설계 선행 작업

1. v1 failure trace를 확보합니다.
2. state transition table을 작성합니다.
3. 각 frame을 byte 단위로 정의하고 golden test vector를 만듭니다.
4. 다음 호환 방법 중 하나를 선택합니다.
   - v2 전용 CAN ID 사용으로 v1 보존
   - START negotiation/version field 사용
   - compile-time v1/v2 image 분리
5. Classic CAN 8-byte에서 NACK bitmap, block ID, session 식별자를 어떻게 나눌지 결정합니다.

### 최소 protocol 속성

- `START`: protocol version, image size, session 식별
- `BLOCK_BEGIN`: session 또는 active session 확인, block ID, actual block length
- `DATA`: sequence와 정의된 payload length
- `ACK/NACK`: 적어도 block ID를 echo; NACK은 누락 bitmap을 표현
- `END`: session 확인, firmware CRC
- duplicate `BLOCK_BEGIN`/DATA: 이미 commit된 block이면 cached ACK 반환
- timeout/ABORT: partial block을 폐기하되 active application은 보존

세부 byte layout은 구현 창에서 즉흥적으로 정하지 않고 별도 `docs/protocol-v2.md` review 후 확정합니다.

### 변경 예상 파일

- Custom target `boot_can_custom_f103/App/ap/boot_can/`
- BBB `can-fota-BBB/flasher/protocol.h`, `custom_fota.c`, 필요 시 새 protocol core module
- `docs/protocol-v2.md`
- unit/golden vector test
- Yocto source 사본은 F4에서 canonical source 반영 방법을 정한 후 갱신

### 완료 조건

- 정상 update regression 통과
- DATA omission은 selective retransmission으로 복구
- block ACK loss 후 이전 block을 다시 쓰지 않고 성공
- stale session frame 거부
- duplicate block이 flash address를 두 번 advance하지 않음
- v1 호환 정책과 migration 방법 문서화

### 포트폴리오 가치

높음. 단순 packet format 추가가 아니라 distributed state, idempotency, retransmission ambiguity를 해결한 사례로 설명할 수 있습니다.

---

## F2 — 결정적 fault injection과 공정한 benchmark

### 해결할 현재 문제

- 과거 loss injection은 application에서 frame send를 임의로 생략한 Bernoulli 모델입니다.
- Custom과 ISO-TP에 loss를 적용한 frame 종류가 다릅니다.
- random seed가 기록되지 않았고 source와 저장 CSV의 timing 조건이 일치하지 않는 정황이 있습니다.
- 현재 C ISO-TP counter는 data FF/CF를 세지 않습니다.
- Custom은 staging+copy, ISO는 direct-write이므로 end-to-end 시간만으로 transport를 비교할 수 없습니다.

### 실험을 두 층으로 분리

1. `Transport-only benchmark`
   - 같은 payload와 block size
   - flash 대신 같은 RAM sink 또는 같은 처리 지연
   - Selective NACK와 ISO-TP transport 비용 비교
2. `End-to-end FOTA benchmark`
   - 실제 erase/write/CRC/copy 포함
   - phase별 시간을 분리해 system downtime 관점에서 평가

### fault model

- loss 0% control
- 독립 Bernoulli sparse loss
- Gilbert-Elliott 형태의 burst loss
- 연속 2/4/8 frame omission
- ACK/NACK/FC loss
- background bus load 0/30/60%
- bus-off와 physical disconnect는 packet loss 실험과 별도 분류

동일 seed와 동일 logical fault schedule을 두 protocol에 사용합니다. 단, protocol frame 역할이 다르므로 “모든 frame”과 “DATA frame only” 실험을 분리합니다.

### 측정 지표

- update success rate
- total time과 phase별 time
- p50, p95; p99는 충분한 반복 수가 있을 때만 보고
- goodput
- send attempt/software fault drop/SocketCAN success/error frame count
- control/data/retransmission frame과 byte
- SocketCAN에서 관찰한 frame과 payload byte
- DLC 기반 nominal bus occupancy 추정치와 그 한계
- timeout/retry per block
- RX queue drop, error passive, bus-off count
- JUMP 이후 `ECU_READY`까지의 ECU downtime

### 반복 수

- 개발 smoke: 조건별 5회
- 평균/p95 보고: 조건별 최소 30~50회, 가능하면 100회
- p99 주장: 조건별 500회 이상을 권장하며 sample 수와 confidence limitation을 함께 표기

### 공정성 통제

- Standard CAN ID와 bitrate 동일
- firmware hash, image size, block/chunk size 동일
- host/target build hash 기록
- timeout, retry cap, pacing 명시
- 실험 순서를 randomize하거나 protocol을 번갈아 실행
- background traffic seed와 rate 기록
- 같은 BBB에서 수집한 SocketCAN timestamp와 `candump -L` trace 대조
- controller error state는 `ip -details -statistics link show can0`과 STM32 error counter로 기록
- hardware automatic retransmission은 application frame count에 포함되지 않는다고 명시

### 산출물

- command-line benchmark runner
- versioned experiment config와 seed
- raw JSONL/CSV
- summary 생성 script
- 실험 환경 README
- 자동 생성된 표와 plot

### 완료 조건

- 한 command로 같은 조건을 재실행할 수 있다.
- raw data에서 summary를 다시 생성할 수 있다.
- application/SocketCAN frame count 표본이 같은 BBB의 `candump`와 일치한다.
- 실제 on-wire automatic retransmission을 측정한 것처럼 표현하지 않는다.
- “Selective NACK가 유리한 조건과 유리하지 않은 조건”이 success rate와 tail latency를 포함한 수치로 설명된다.

### 기대 가설

Selective NACK는 feedback이 안정적이고 block 안의 sparse independent DATA loss가 있을 때 재전송 byte를 줄일 가능성이 큽니다. Loss가 없거나 block이 작거나, ACK/NACK 자체가 유실되거나, 긴 burst/bus-off가 발생하거나, CAN hardware retransmission이 오류를 이미 숨기는 환경에서는 이점이 작거나 없을 수 있습니다.

### 현재 장비에서의 fault 범위

다음은 필수 실험에 포함합니다.

- seed와 logical payload offset이 기록되는 DATA omission
- duplicate, reorder, last-frame omission
- Custom ACK/NACK와 ISO-TP FC/application ACK 무시
- target disconnect와 `can0` down
- ACK error, error passive, bus-off와 recovery
- SocketCAN `ENOBUFS`와 target RX queue overload
- STM32가 생성하는 높은 우선순위 background traffic

다음은 별도 장비 없이는 정밀하게 재현하거나 계측할 수 없으므로 실험 범위에서 제외합니다.

- physical bit/stuff/form error의 특정 bit 주입
- 의도적으로 잘못된 CAN frame CRC 송신
- transceiver waveform과 signal integrity 측정
- controller automatic retransmission의 정확한 on-wire 횟수

Firmware image의 CRC mismatch는 CAN frame CRC와 다른 항목이므로 기존 장비에서 별도로 검증합니다.

---

## F3 — Transactional metadata와 reset/manual power-loss recovery

### 해결할 현재 문제

현재 staging CRC와 vector-last copy는 download 중 기존 active image를 보호하고, 일부 copy 중단에서 재복사를 가능하게 합니다. 그러나 다음 한계가 있습니다.

- old application을 보관하는 true rollback slot이 없음
- metadata write가 atomic transaction으로 정의되지 않음
- valid vector를 가진 손상 image가 boot될 가능성
- 새 application의 boot 성공 확인과 rollback 정책이 없음
- metadata 8 byte가 staging 마지막 erase page에 함께 있음

### 현실적인 목표

F103RB의 128 KiB single flash 제약 안에서 true A/B를 억지로 구현하지 않습니다. 다음을 목표로 합니다.

- metadata state를 이용해 `EMPTY`, `DOWNLOADING`, `VERIFIED`, `COPYING`, `ACTIVE_PENDING`, `CONFIRMED`를 구분
- metadata record의 magic, version, size, CRC, generation/state integrity 검증
- copy 전후 active CRC 확인
- boot 성공 확인 또는 `ECU_READY` 관측
- 각 erase/write/copy 단계에서 reset해도 bootloader가 안전한 결정을 내림

Metadata 전용 1 KiB page를 예약하면 maximum image가 줄어듭니다. linker/memory map 변경과 portfolio 효과를 비교해 Review Gate에서 결정합니다.

### 추가 장비 없는 fault injection 방법

두 종류의 시험을 구분합니다.

1. `Deterministic checkpoint reset`
   - test build에서 지정된 flash operation의 직전 또는 직후 `NVIC_SystemReset()` 실행
   - 같은 checkpoint를 반복할 수 있고 state transition을 검증하기 좋음
   - 실제 word programming 도중의 brownout을 재현하는 시험은 아님
2. `Manual reset/power disconnect`
   - update 진행 중 board reset 또는 기존 전원을 수동 차단
   - 실제 restart 경로를 확인할 수 있지만 정확한 차단 시점은 보장하지 못함

### 검증 checkpoint

- staging erase 직전/직후
- block write 직전/직후
- metadata field 기록 전/후
- active erase 직전/직후
- middle block copy 직전/직후
- vector table 기록 직전/직후
- JUMP 직후 application boot 전

각 지점에서 checkpoint reset을 반복하고, 대표 phase에서는 수동 reset/power disconnect도 수행합니다. 결과는 다음 중 하나로 수렴해야 합니다.

- 기존 valid application boot
- verified staging에서 deterministic recopy
- bootloader에 머물러 update 대기

임의 주소 jump나 silent corrupted application boot는 허용하지 않습니다.

다음 항목은 별도 장비가 필요한 범위로 남깁니다.

- flash word programming 도중의 cycle-accurate power cut
- brownout voltage와 pulse width sweep
- relay를 이용한 수백 회 자동 power cycle

### 완료 조건

- checkpoint별 기대 동작과 실제 결과 표가 있다.
- deterministic reset은 각 핵심 checkpoint에서 반복하고 raw log를 남긴다.
- 수동 power disconnect는 대표 phase에서 수행 횟수와 timing limitation을 기록한다.
- active CRC가 맞지 않으면 application으로 jump하지 않는다.
- recovery가 불가능한 상태에서도 bootloader 접근성이 유지된다.
- true rollback을 지원하지 않는 한계를 README에서 정확히 표현한다.
- 정밀 brownout 또는 mid-word power-cut을 검증했다고 주장하지 않는다.

---

## F4 — Yocto/systemd와 gateway 재현성

### 해결할 현재 문제

- `can-fota_1.0.bb`는 `file://ngrok.yml`을 요구하지만 repository에는 sample만 추적되어 clean build가 막힐 수 있습니다.
- `kas-project.yml`의 layer branch는 exact commit으로 고정되지 않았습니다.
- CanBootloader source가 Yocto recipe 안에 복사되어 두 구현이 drift합니다.
- recipe install 범위가 source/object까지 포함할 가능성이 있습니다.
- service가 root, `0.0.0.0`, unauthenticated upload, auto ngrok을 사용합니다.
- `debug-tweaks`가 켜져 있고 실제 LTE provisioning과 ECU_READY 소비가 없습니다.
- firmware path와 update 실행이 global하여 동시 요청 race가 가능합니다.

### 우선 구현

1. secret이 없는 clean build 정책 확립
   - sample config를 설치하고 token은 first-boot/runtime에 주입하거나
   - ngrok을 optional package/service로 분리
2. canonical BBB source 한 곳을 결정하고 recipe가 해당 revision을 가져오게 함
3. install 대상은 binary, template, service, config로 명시
4. systemd dependency를 `network-online.target`, `can0` 준비, application 순으로 검토
5. update lock과 session별 temporary upload path 도입
6. service hardening과 최소 권한 검토
7. `journalctl`에서 session ID 기반으로 update 결과를 추적

### 후순위

- 실제 modem APN/PPP 또는 NetworkManager profile
- ngrok 이외 production tunnel
- dashboard visual polish

### 완료 조건

- clean checkout에서 secret 없이 kas/BitBake build가 시작되고 recipe fetch/package가 재현된다.
- source drift 방지 방법이 문서화된다.
- 두 동시 update 요청 중 하나만 실행된다.
- service start order와 CAN interface failure가 journal에 명확히 남는다.
- 개발 image의 `debug-tweaks`와 배포 image 정책이 분리된다.

---

## F5 — Unit test와 parser fuzzing

### 시작 조건

HAL, flash, SocketCAN에 직접 묶인 code에서 protocol parsing/state logic을 pure C module로 분리한 뒤 수행합니다. Test를 위해 대규모 architecture rewrite를 먼저 하지 않습니다.

### 우선 test 대상

- CRC32 known vector
- firmware size/address arithmetic
- expected frame/DLC 계산
- bitmap complete/missing 계산
- state transition
- duplicate block/idempotent ACK
- ISO-TP PCI length와 FC parsing
- metadata validity/state transition

### fuzzing

Host에서 build 가능한 parser 함수에 libFuzzer/AFL 계열을 적용합니다. 목표는 malformed CAN frame에서 crash, overflow, invalid state transition이 없음을 보이는 것입니다.

### 완료 조건

- hardware 없이 핵심 state/length logic을 반복 검증할 수 있다.
- sanitizer build가 있다.
- regression corpus에 발견된 실제 failure frame이 포함된다.
- GitHub Actions에서 host-side test가 자동 실행된다.

---

## F6 — Signed firmware manifest

### 우선순위

조건부 후순위입니다. CRC는 transmission integrity만 제공하며 firmware authenticity는 제공하지 않습니다. 하지만 signature를 추가하기 전에 update state와 power-loss 동작이 검증되어야 합니다.

### 권장 범위

- firmware size, version, board ID, image CRC/hash를 포함하는 manifest
- SHA-256
- 공개키 기반 signature verification prototype
- downgrade policy와 key provisioning 한계 문서화

AES encryption은 현재 threat model에서 우선하지 않습니다. Firmware 기밀성보다 authenticity와 anti-rollback 정책이 먼저입니다. MCU secure boot 전체를 구현한 것처럼 표현하지 않습니다.

## 명시적 보류 항목

| 항목 | 현재 판단 | 다시 검토할 조건 |
| --- | --- | --- |
| True A/B / dual-bank | 보류 | 외부 flash 또는 더 큰 MCU로 hardware 변경 |
| Full rollback | 보류 | old image slot과 boot confirmation 설계 확보 |
| Resume update | v2 이후 | session/block transaction과 metadata 완료 |
| Watchdog | 조건부 | recovery state가 정의된 뒤 reset 정책 연결 |
| Full UDS | 낮음 | 진단 job 요구 또는 최소 service subset 필요 |
| CAN-FD | 제외 | F103 hardware 변경 |
| FreeRTOS 기능 확대 | 제외 | 현재 bootloader 신뢰성에 직접 필요할 때만 |
| Multi-ECU | 보류 | single ECU update가 정량 검증된 이후 |
| Python→C migration | 불필요 | 현재 active sender가 이미 C임 |
| AES encryption | 낮음 | 명확한 firmware confidentiality threat가 생김 |

## 포트폴리오 최종 산출물

기능 개발이 끝났을 때 GitHub 첫 화면에서 다음 evidence로 연결되어야 합니다.

- 실제 target과 memory map
- update sequence/state diagram
- 실패 mode와 복구 표
- reproducible build command
- fault injection 방법과 seed
- raw data와 자동 생성 그래프
- p50/p95/success rate 및 retransmitted bytes
- checkpoint reset/manual power-loss test matrix와 CAN trace
- 보유 장비로 관찰하지 못한 physical-layer limitation
- known limitation과 product 수준으로 가기 위한 다음 단계

이 산출물이 없다면 기능이 많아도 면접관이 신뢰성을 검증하기 어렵습니다.
