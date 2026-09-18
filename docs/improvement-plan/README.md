# CAN-FOTA 개선 마스터 플랜

## 목적

이 디렉터리는 `CanBootloader`와 `yocto_capston`을 임베디드 SW, Automotive Embedded Linux, BSP 직무 포트폴리오 수준으로 개선하기 위한 단일 작업 기준입니다.

목표는 기능 수를 늘리는 것이 아니라 다음 세 가지를 증명하는 것입니다.

1. 잘못된 입력과 통신 장애가 발생해도 bootloader가 안전하게 실패한다.
2. Selective NACK와 ISO-TP 비교 결과를 같은 조건에서 재현할 수 있다.
3. 전원 차단과 update 중단을 현재 보유한 hardware 범위에서 검증하고 근거를 남긴다.

계획 수립 당시 기준 commit은 다음과 같습니다.

| Repository | Branch | Baseline commit |
| --- | --- | --- |
| `CanBootloader` | `main` | `c561ceb` |
| `yocto_capston` | `main` | `6c393e8` |

이 값은 비교 기준이며, 작업을 시작할 때마다 현재 HEAD와 `git status`를 다시 확인해야 합니다.

## 장비와 검증 범위

이 계획의 필수 완료 조건은 다음과 같이 현재 보유한 장비만 사용한다는 전제입니다.

- BeagleBone Black
- STM32F103RB target
- 현재 사용하는 CAN transceiver, cable, termination
- 개발 PC와 기존 debug/programming 수단

별도 USB-CAN adapter, external CAN analyzer, oscilloscope, relay형 power switch, 전문 CAN fault injector를 구매하지 않아도 모든 필수 Task를 `DONE` 처리할 수 있어야 합니다.

현재 장비로 수행할 fault 범위는 다음과 같습니다.

- software에서 결정적으로 발생시키는 DATA omission, duplicate, reorder
- ACK, NACK, Flow Control, application ACK 무시
- target disconnect, `can0` down, ACK error, error passive, bus-off
- SocketCAN TX queue 포화와 STM32 RX FIFO/software queue overflow
- BBB와 STM32를 이용한 background traffic과 arbitration 부하
- 잘못된 firmware CRC와 손상 image
- test build의 checkpoint reset과 수동 reset/power disconnect

다음 항목은 필수 검증 범위에서 제외하고 limitation으로 문서화합니다.

- 특정 bit 위치의 physical bit/stuff/form error 주입
- CAN controller가 생성하는 frame CRC를 의도적으로 손상
- hardware automatic retransmission의 정확한 on-wire 횟수 측정
- oscilloscope 기반 signal integrity 분석
- relay를 이용한 정밀·자동 power-cut

External analyzer나 power switch를 나중에 확보하더라도 optional evidence를 추가하는 용도로만 사용하며, 현재 로드맵의 dependency로 만들지 않습니다.

## 문서 구성

- [1차 2주 실행 계획](sprint-01-two-weeks.md): 지금 바로 수행할 범위와 완료 조건
- [2주 이후 후속 로드맵](follow-up-roadmap.md): 2주 결과에 따라 재평가할 전체 backlog
- [Codex 세션 운영 방법](codex-session-guide.md): 새 Codex 창을 여는 기준, 시작 prompt, 종료 보고 형식
- [현재 인수인계 상태](SESSION_HANDOFF.md): 직전 작업 결과와 다음 작업을 새 창에 전달하는 짧은 기록
- [면접 지식 기록 가이드](interview/README.md): Task별 학습 내용과 답변 작성 규칙
- [면접 질문 은행](interview/QUESTION_BANK.md): 질문, 근거 노트, 학습 상태 인덱스

관련 설계 기준은 다음 문서를 함께 사용합니다.

- [시스템 아키텍처](../architecture.md)
- [Custom CAN protocol](../protocol.md)
- [STM32F103RB memory map](../memory-map.md)
- [F103 FOTA baseline](../f103-fota-baseline.md)
- [FreeRTOS application](../f103-freertos-application.md)

## 실행 원칙

### 한 번에 한 Task만 수행

Codex 창 하나에는 하나의 Task ID만 맡깁니다. 같은 창에서 다음 Task까지 계속 구현하지 않습니다. Task가 너무 커지면 구현 범위를 줄이고 남은 항목을 인수인계합니다.

새 창을 여는 것 자체보다 중요한 것은 다음 정보가 repository에 남아 있는 것입니다.

- 어떤 문제를 고쳤는가
- 어떤 파일과 protocol 동작이 바뀌었는가
- 실제로 실행한 build/test는 무엇인가
- 이번 Task에서 면접용으로 이해하고 설명해야 할 지식은 무엇인가
- 통과하지 못했거나 현재 보유 장비에서 확인할 수 없는 것은 무엇인가
- 다음 Task가 시작해도 되는가

### 순서를 건너뛰지 않음

기본 실행 순서는 다음과 같습니다.

```text
TW-00 -> TW-01 -> TW-02 -> TW-03 -> TW-04 -> TW-05 -> 2주 Review Gate
                                                        |
                                                        v
F1 Protocol v2 -> F2 Benchmark -> F3 Reset/Power-loss Recovery -> F4 Yocto
```

앞 Task의 완료 조건이 충족되지 않았다면 다음 Task를 시작하지 않습니다. 현재 보유 장비로 원래부터 관찰할 수 없는 physical-layer 항목은 `BLOCKED`가 아니라 명시적 범위 제외로 기록합니다. BBB나 STM32를 일시적으로 사용할 수 없어 필수 시험을 못 한 경우에만 `NOT RUN`으로 남기고 Review Gate에서 판단합니다.

### 현재 protocol을 먼저 안전하게 만듦

1차 2주 동안에는 기존 Custom protocol의 wire format을 바꾸지 않습니다. size, DLC, sequence, state, flash boundary, timeout 같은 안전성 문제를 먼저 해결합니다.

`session_id`, `block_id`, duplicate ACK를 포함하는 Protocol v2는 wire format 호환성에 영향을 주므로 별도 설계 문서와 test vector가 승인된 뒤 구현합니다.

### Task마다 면접 지식을 기록

모든 Task는 source/test report와 함께 `docs/improvement-plan/interview/<TASK_ID>.md`를 남깁니다. 면접 노트는 일반 이론을 복사하지 않고 실제 문제, code 위치, 설계 선택, test evidence, 한계를 연결해야 합니다.

각 노트에는 최소한 다음 내용이 있어야 합니다.

- 반드시 이해해야 할 기반 개념
- 선택한 방법과 선택하지 않은 대안
- 실패 시나리오와 수정 후 동작
- 30초 답변 3개와 대표 2분 답변
- 예상 꼬리질문과 용어 교정
- 관련 source/function과 test report

Codex는 답변을 `DRAFT` 또는 `VERIFIED`까지 작성할 수 있습니다. 사용자가 문서를 보지 않고 직접 설명한 뒤에만 [질문 은행](interview/QUESTION_BANK.md)의 상태를 `REHEARSED`로 바꿉니다. 자세한 규칙은 [면접 지식 기록 가이드](interview/README.md)를 따릅니다.

### 근거 없는 완료 처리를 금지

다음 표현은 구분해서 기록합니다.

- `PASS`: 실제 command를 실행하거나 hardware에서 관찰하여 통과
- `FAIL`: 실제 검증에서 실패
- `NOT RUN`: 환경이나 hardware가 없어 실행하지 못함
- `BLOCKED`: 외부 조건 때문에 다음 단계로 진행할 수 없음

Build하지 않은 코드를 “build 가능”, hardware에서 실행하지 않은 기능을 “검증 완료”라고 기록하지 않습니다.

### 변경과 commit 경계

- 작업 시작 전 두 repository에서 `git status --short --branch`를 확인합니다.
- 기존 변경은 사용자 작업으로 간주하며 임의로 되돌리지 않습니다.
- Task 범위 밖의 refactoring과 formatting을 섞지 않습니다.
- STM32 protocol을 바꾸면 BBB sender의 호환 영향을 반드시 함께 확인합니다.
- 두 repository를 함께 수정했다면 repository별 변경 이유와 검증을 따로 기록합니다.
- Codex는 사용자가 명시적으로 요청하지 않으면 commit하거나 push하지 않습니다.
- 권장 commit 단위는 Task 하나 또는 독립 검증 가능한 subtask 하나입니다.

## 전체 Task 현황

상태 값은 `TODO`, `IN_PROGRESS`, `BLOCKED`, `DONE` 중 하나를 사용합니다.

| ID | 범위 | 현재 상태 | 선행 Task | 계획 위치 |
| --- | --- | --- | --- | --- |
| TW-00 | Baseline과 검증 계약 고정 | DONE | 없음 | 1차 2주 |
| TW-01 | Target 입력·state·block 수신 안전성 | DONE | TW-00 | 1차 2주 |
| TW-02 | Flash copy·boot validation 안전성 | IN_PROGRESS | TW-01 | 1차 2주 |
| TW-03 | BBB timeout·retry·CAN error 처리 | TODO | TW-02 | 1차 2주 |
| TW-04 | ISO-TP build와 최소 baseline 수정 | TODO | TW-03 | 1차 2주 |
| TW-05 | 통합 regression과 2주 결과 정리 | TODO | TW-04 | 1차 2주 |
| F1 | Transactional Protocol v2 | TODO | 2주 Review Gate | 후속 |
| F2 | 결정적 fault injection과 공정한 benchmark | TODO | F1 또는 별도 baseline 결정 | 후속 |
| F3 | Transactional metadata와 reset/manual power-loss recovery | TODO | F1 | 후속 |
| F4 | Yocto/systemd 재현성과 gateway hardening | TODO | TW-03 | 후속 |
| F5 | Unit test·parser fuzzing | TODO | core module 분리 | 후속 |
| F6 | Signed firmware manifest | DEFERRED | update 신뢰성 완료 | 후속 |

Task가 끝날 때 이 표와 [현재 인수인계 상태](SESSION_HANDOFF.md)를 갱신합니다.

## 1차 2주 성공 기준

다음 조건을 모두 만족하면 첫 2주가 성공한 것입니다.

- 잘못된 firmware size가 flash erase 전에 거부된다.
- START 없이 DATA/END/JUMP를 보내도 flash나 application으로 잘못 전이하지 않는다.
- DLC, sequence, 마지막 block 길이, 누적 수신 byte에 대한 경계가 명시적이다.
- flash 주소 검사가 integer overflow에 안전하고 write 결과가 검증된다.
- application SP와 Reset Handler가 올바른 RAM/active image 범위인지 검사한다.
- BBB sender의 모든 retry가 횟수 또는 deadline으로 제한된다.
- CAN send 실패와 response timeout이 사용자에게 구분되어 반환된다.
- Custom bootloader/application이 build된다.
- ISO-TP bootloader가 최소한 compile되며 buffer와 size 오류가 수정된다.
- 성공 경로와 주요 실패 경로의 test log가 repository 문서로 남는다.
- 기존 v1에서 해결할 수 없는 ACK loss 문제가 Protocol v2 요구사항으로 명확히 정리된다.
- 모든 필수 결과가 현재 보유 장비와 software 관측치만으로 재현된다.
- TW-00~TW-05마다 실제 변경과 검증에 연결된 면접 지식 노트가 있다.
- 질문 은행에서 각 답변의 `DRAFT`, `VERIFIED`, `REHEARSED`, `WEAK` 상태를 확인할 수 있다.

2주 안에 모든 조건을 만족하지 못하면 미완료 Task를 다음 기간의 최우선으로 이동합니다. 일정에 맞추기 위해 미검증 코드를 `DONE`으로 처리하지 않습니다.

## 2주 Review Gate

TW-05 종료 후 새 계획을 세울 때 다음 질문에 답합니다.

1. 남은 P0 defect가 있는가?
2. hardware test에서 재현된 가장 심각한 실패는 무엇인가?
3. Protocol v2가 실제로 필요한 실패가 로그로 증명됐는가?
4. ISO-TP와 Custom의 공정한 비교를 막는 차이가 무엇인가?
5. 다음 2주 동안 현재 BBB, STM32, CAN 배선을 반복 시험에 사용할 수 있는가?
6. 남은 시간에는 Protocol v2, benchmark, power-loss 중 어떤 두 개를 깊게 끝낼 수 있는가?

권장 기본 선택은 `F1 Protocol v2`와 `F2 benchmark`입니다. 다만 active copy 중 reset 또는 수동 전원 차단 실패가 실제로 더 심각하게 나타나면 `F3 recovery`를 F2보다 먼저 수행합니다.
