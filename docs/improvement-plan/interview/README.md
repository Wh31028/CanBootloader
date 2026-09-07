# 면접 지식 기록 운영 가이드

## 목적

각 개선 Task에서 실제로 다룬 embedded, CAN, bootloader, Linux, Yocto 지식을 면접에서 설명할 수 있는 형태로 남깁니다.

이 문서는 일반적인 개념 요약집을 만드는 규칙이 아닙니다. 모든 설명은 다음 연결을 가져야 합니다.

```text
현재 code의 문제
  -> 필요한 기반 지식
  -> 선택한 해결 방법과 trade-off
  -> 실제 test evidence
  -> 남은 한계
```

Codex가 답변 초안을 작성할 수는 있지만, 사용자가 직접 설명해보지 않은 항목을 `REHEARSED`로 표시하지 않습니다.

## 파일 구성

- `README.md`: 면접 지식 기록 규칙과 Task별 학습 주제
- [노트 템플릿](TEMPLATE.md): 각 Task의 지식 노트 형식
- [질문 은행](QUESTION_BANK.md): 전체 예상 질문, 답변 노트와 학습 상태의 인덱스
- `<TASK_ID>.md`: 해당 Task를 실제 수행한 뒤 작성하는 근거 기반 면접 노트

예시는 다음과 같습니다.

```text
interview/TW-00.md
interview/TW-01.md
interview/F1.md
```

Task를 수행하기 전에는 없는 사실을 예상해서 답변 파일을 미리 완성하지 않습니다. 구현과 검증이 끝난 후 실제 diff와 test report를 근거로 작성합니다.

## 학습 상태

질문마다 다음 상태 중 하나를 사용합니다.

| 상태 | 의미 | 누가 변경하는가 |
| --- | --- | --- |
| `TODO` | 해당 Task를 아직 수행하지 않아 답변 노트가 없음 | 계획 문서 |
| `DRAFT` | Codex가 code와 test를 근거로 초안을 작성 | Codex |
| `VERIFIED` | 답변의 file/function/test 근거를 확인 | Codex 또는 사용자 |
| `REHEARSED` | 사용자가 문서를 보지 않고 직접 설명해봄 | 사용자만 |
| `WEAK` | 설명 중 막히거나 꼬리질문 답변이 부족함 | 사용자 |

새 Codex는 `DRAFT`와 `VERIFIED`까지만 갱신합니다. 사용자의 실제 연습 없이 `REHEARSED`로 변경하면 안 됩니다.

## Task 시작 시 수행할 일

1. [질문 은행](QUESTION_BANK.md)에서 현재 Task의 예정 질문을 확인합니다.
2. 기존 `<TASK_ID>.md`가 있으면 중복 작성하지 않고 현재 code와 일치하는지 확인합니다.
3. 이번 Task에서 설명할 기반 개념과 설계 결정을 작업 계획에 포함합니다.
4. 일반론이 아니라 어떤 file/function/test로 증명할지 정합니다.

## Task 종료 시 필수 산출물

각 Task를 `DONE`으로 변경하기 전에 다음을 수행합니다.

1. `interview/<TASK_ID>.md`를 [템플릿](TEMPLATE.md)에 맞게 작성 또는 갱신합니다.
2. 최소 3개의 핵심 질문에 30초 답변과 2분 답변을 작성합니다.
3. 각 답변에 관련 source function, protocol field, test report를 연결합니다.
4. 선택하지 않은 대안과 현재 설계의 한계를 적습니다.
5. 잘못 사용하기 쉬운 용어를 교정합니다.
6. [질문 은행](QUESTION_BANK.md)에 질문, note link, 상태를 반영합니다.
7. `SESSION_HANDOFF.md`에 마지막으로 갱신한 면접 노트를 기록합니다.

면접 노트가 없으면 source와 test가 완료됐더라도 Task 상태를 `DONE`으로 바꾸지 않습니다.

## 답변 작성 원칙

### 사실과 판단을 구분

다음처럼 작성합니다.

- 사실: `bootProcessStart()`는 size 초과 시 현재 `original_fw_size`에 invalid 값을 남긴다.
- 판단: invalid input이 erase/read 범위 밖 동작으로 이어질 수 있어 P0로 분류했다.
- 변경: size를 erase 전에 reject하고 state를 유지하도록 수정했다.
- 증거: boundary test와 build log 경로를 제시한다.

### 구현한 것만 말함

다음 표현을 피합니다.

- staging 구조를 `dual-bank/A-B`라고 부름
- application-level frame omission을 실제 CAN bit error라고 부름
- ISO-TP 위의 자체 command를 UDS라고 부름
- SocketCAN send count를 실제 on-wire automatic retransmission 수라고 부름
- checkpoint reset을 cycle-accurate brownout test라고 부름

### 숫자를 설명할 수 있어야 함

Memory address, maximum firmware size, block 크기, frame 수, timeout, retry 수를 답변에 쓰면 다음도 함께 설명합니다.

- code 또는 linker에서 값이 나온 위치
- 단위와 end-inclusive/end-exclusive 여부
- 해당 값이 바뀌면 영향을 받는 component

### 대안과 trade-off를 포함

“best practice라서 적용했다”로 끝내지 않습니다. 다음 중 실제로 검토한 내용을 답합니다.

- 기존 방식이 실패하는 구체적 sequence
- 선택한 해결 방법의 RAM/Flash/protocol overhead
- 호환성 영향
- 더 강한 대안을 선택하지 않은 hardware/time 제약

## Task별 핵심 학습 주제

| Task | 반드시 이해할 주제 |
| --- | --- |
| TW-00 | 전체 architecture, F103 memory map, boot/application 경계, current baseline과 legacy benchmark 구분 |
| TW-01 | finite state machine, precondition, DLC/sequence validation, integer underflow, duplicate/out-of-order 처리 |
| TW-02 | flash erase/program 단위, alignment/padding, vector table, MSP, Reset Handler, Thumb bit, CRC readback |
| TW-03 | SocketCAN, blocking/non-blocking I/O, `ENOBUFS`, monotonic deadline, Standard/Extended ID, CAN error state와 bus-off |
| TW-04 | ISO-TP SF/FF/CF/FC, BS, STmin, transport timeout, application-level retry, 비교 baseline 공정성 |
| TW-05 | regression, fault injection, trace provenance, PASS/FAIL/NOT RUN, known limitation 설명 |
| F1 | distributed transaction, session/block identity, idempotency, duplicate ACK, backward compatibility |
| F2 | random seed, paired experiment, loss model, success rate, p50/p95, goodput, measurement bias |
| F3 | transactional metadata, power-loss state, vector-last copy, checkpoint reset, rollback과 recovery 차이 |
| F4 | Yocto layer/recipe, BitBake task, reproducible build, systemd dependency, least privilege, source-of-truth |
| F5 | pure logic 분리, unit test, mock, sanitizer, fuzzing, regression corpus |
| F6 | CRC와 hash/signature 차이, authenticity, anti-rollback, key provisioning, secure boot 경계 |

## 면접 연습 방법

Task 완료 직후에는 다음 순서로 연습합니다.

1. 30초 답변을 문서 없이 말합니다.
2. “왜?”, “실패하면?”, “다른 방법은?” 세 가지 꼬리질문에 답합니다.
3. whiteboard에 state/sequence/memory map을 그립니다.
4. 실제 file/function과 test evidence를 한 개씩 말합니다.
5. 막힌 질문은 `WEAK`로 표시하고 다음 학습 항목을 적습니다.

TW-05에서는 TW-00~TW-04 질문 중 최소 5개를 무작위로 골라 다시 설명하고, 사용자가 직접 연습한 질문만 `REHEARSED`로 변경합니다.
