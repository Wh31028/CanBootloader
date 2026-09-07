# Codex 세션 운영 방법

## 새 창을 여는 기준

새 Codex 창은 context window를 다 썼을 때가 아니라 다음 조건 중 하나일 때 엽니다.

- 하나의 Task ID가 완료됨
- 다음 작업의 subsystem이 달라짐
- 변경 파일이 많아져 검토 관점이 바뀜
- hardware 검증과 source 구현을 분리하고 싶음
- 현재 창의 요약만으로 안전한 변경이 어렵다고 판단됨

같은 Task를 단순히 이어가는 중이고 context가 충분하다면 새 창을 열 필요는 없습니다. 반대로 Task가 끝났다면 context가 남아 있어도 새 창에서 독립 검토하는 편이 좋습니다.

권장 단위는 다음과 같습니다.

- TW-00 한 창
- TW-01 한 창
- TW-02 한 창
- TW-03 한 창
- TW-04 한 창
- TW-05는 검증 전용 새 창

모든 Task는 BBB, STM32F103RB, 현재 CAN transceiver/배선과 개발 PC만으로 완료해야 합니다. 새 장비 구매를 해결책이나 완료 조건으로 제안하지 않습니다. Physical bit/CRC fault, external analyzer 계측, 자동 relay power-cut은 명시적 범위 밖입니다.

## 새 창이 자동으로 알지 못하는 것

새 Codex 창은 이전 창의 판단, 실행 command, hardware 상태를 자동으로 신뢰할 수 있게 전달받지 못합니다. 다음 네 가지가 repository에 있어야 합니다.

1. 계획 문서의 Task 상태
2. `SESSION_HANDOFF.md`
3. 실제 diff/commit과 test report
4. Task별 면접 지식 노트와 질문 은행 상태

대화 내용만 인수인계 자료로 사용하지 않습니다.

## 공통 시작 prompt

아래 prompt에서 `<TASK_ID>`만 바꿔 새 창에 사용합니다.

```text
CanBootloader와 yocto_capston의 CAN-FOTA 개선 작업을 이어서 수행해줘.

이번 창에서는 <TASK_ID> 하나만 수행해.

작업 전에 반드시 다음을 순서대로 읽어줘.
1. /Users/wh31028/repos/CanBootloader/AGENTS.md
2. /Users/wh31028/repos/CanBootloader/docs/improvement-plan/README.md
3. /Users/wh31028/repos/CanBootloader/docs/improvement-plan/sprint-01-two-weeks.md
4. /Users/wh31028/repos/CanBootloader/docs/improvement-plan/SESSION_HANDOFF.md
5. /Users/wh31028/repos/CanBootloader/docs/improvement-plan/interview/README.md
6. /Users/wh31028/repos/CanBootloader/docs/improvement-plan/interview/QUESTION_BANK.md
7. <TASK_ID>와 관련된 기존 source와 설계 문서

두 repository의 git status와 현재 HEAD를 먼저 확인하고, 기존 변경을 임의로 되돌리지 마.
이번 Task 범위 밖의 refactoring이나 다음 Task 구현을 섞지 마.
STM32 protocol 동작을 바꾸면 BBB sender 호환성을 반드시 같이 확인해.
필수 검증은 현재 보유한 BBB, STM32F103RB, CAN transceiver/배선과 개발 PC만 사용해.
External analyzer, oscilloscope, relay power switch, 전문 CAN fault injector를 새 dependency로 제안하지 마.
Physical bit/CRC fault와 정밀 on-wire retransmission 계측은 범위 밖이라고 명시해.

먼저 현재 문제를 코드 근거로 재확인하고, 수행할 변경과 test를 짧게 설명한 뒤 구현해.
관련 build/test를 실제로 실행하고 PASS/FAIL/NOT RUN을 구분해 보고해.
이번 Task에서 내가 면접을 위해 이해해야 할 기반 지식, 설계 trade-off, 예상 질문을 실제 변경과 test 근거에 연결해 정리해.
마지막에 다음을 수행해.
- git diff 검토
- 해당 Task의 상태 갱신
- docs/improvement-plan/reports/<TASK_ID>-*.md 작성 또는 갱신
- docs/improvement-plan/interview/<TASK_ID>.md 작성 또는 갱신
- docs/improvement-plan/interview/QUESTION_BANK.md 갱신
- SESSION_HANDOFF.md 갱신

면접 답변은 DRAFT 또는 VERIFIED까지만 표시하고, 내가 실제로 연습하지 않은 답변을 REHEARSED로 표시하지 마.
자동 commit이나 push는 하지 마.
```

사용자가 해당 Task의 source 수정까지 원한다는 문장을 prompt에 명시합니다. 단순 분석 prompt는 구현 권한으로 간주하지 않기 때문입니다.

예:

```text
이번에는 TW-01 범위의 source와 문서를 실제로 수정해도 된다.
```

## 첫 응답에서 확인할 내용

Codex가 구현을 시작하기 전에 다음을 확인하게 합니다.

- 현재 branch/HEAD
- dirty file과 이전 Task 결과
- 이번 Task의 in-scope/out-of-scope
- 변경할 가능성이 있는 파일
- software-only test와 현재 BBB/STM32가 필요한 test
- 현재 장비로 관찰할 수 없는 physical-layer limitation
- protocol compatibility 영향
- 이번 Task에서 기록할 면접 기반 지식과 예상 질문

계획 문서와 현재 code가 충돌하면 code를 사실 기준으로 삼고, 차이를 먼저 보고하도록 합니다.

## Task 중간 규칙

- 60초 이상 걸리는 build/test에서는 중간 상태를 공유합니다.
- 발견한 다른 defect는 바로 고치지 않고 report의 `새로 발견한 문제`에 기록합니다.
- 범위 밖 defect가 현재 Task의 안전한 완료를 막으면 `BLOCKED`로 보고하고 사용자와 범위를 다시 정합니다.
- BBB나 STM32를 일시적으로 사용할 수 없으면 software-only test를 수행하고 필수 board test는 `NOT RUN`으로 둡니다.
- External analyzer나 fault injector가 없다는 이유로 Task를 `BLOCKED` 처리하지 않습니다.
- 실제 on-wire automatic retransmission을 SocketCAN frame count로 측정했다고 주장하지 않습니다.
- 발견한 기반 지식과 trade-off를 현재 Task의 면접 노트에 계속 반영합니다.
- 일반적인 교과서 설명만 기록하지 않고 이번 Task의 file/function/test를 근거로 연결합니다.
- 사용자의 직접 연습 없이 질문 상태를 `REHEARSED`로 변경하지 않습니다.
- 자동 생성 build artifact를 source tree에 불필요하게 commit하지 않습니다.

## 종료 보고 형식

각 Task report는 다음 형식을 사용합니다.

```markdown
# <TASK_ID> 실행 결과

## 기준

- CanBootloader HEAD:
- yocto_capston HEAD:
- 작업 branch:
- 작업 환경/toolchain:
- 사용한 보유 장비:

## 해결한 문제

- 문제:
- root cause:
- 변경:

## 변경 파일

- `path`: 변경 이유

## Protocol/호환 영향

- wire format:
- STM32/BBB compatibility:
- memory map/linker 영향:

## 검증

| Test | Command/환경 | Result | Evidence |
| --- | --- | --- | --- |
| ... | ... | PASS/FAIL/NOT RUN | log/trace 경로 |

## 면접 지식 기록

- 면접 노트: `../interview/<TASK_ID>.md`
- 핵심 기반 지식:
- 대표 질문:
- 답변 근거가 된 source/test:
- 질문 은행 상태: DRAFT/VERIFIED

## 남은 문제

- 이번 Task 안에서 남은 것:
- 다음 Task로 넘길 것:
- 새로 발견한 문제:

## 다음 작업 시작 조건

- [ ] 현재 Task 완료 조건 충족
- [ ] git diff 검토
- [ ] hardware 미검증 항목 표시
- [ ] 현재 장비에서 제외한 physical-layer 항목 표시
- [ ] `<TASK_ID>` 면접 노트와 질문 은행 갱신
- [ ] 다음 Task 시작 가능 여부 결정
```

## `SESSION_HANDOFF.md` 갱신 방법

인수인계 문서는 짧아야 합니다. 상세 내용은 report로 보내고 다음 정보만 남깁니다.

- 마지막 완료/진행 Task
- dirty worktree 여부
- 실제 실행한 핵심 test 결과
- 아직 실행하지 못한 BBB/STM32 test
- 현재 장비에서 의도적으로 제외한 physical-layer test
- 마지막으로 작성한 면접 노트와 질문 은행 상태
- 사용자가 다음에 연습할 질문
- 다음 Task와 시작 전에 읽을 report
- 절대 덮어쓰면 안 되는 사용자 변경

## Review 전용 새 창

TW-01~TW-04 구현 창과 별도로 TW-05는 새 창에서 수행하는 것을 권장합니다. 구현한 Codex의 가정을 그대로 이어받지 않고 다음을 독립적으로 확인하기 위함입니다.

- state transition 누락
- target/host protocol 불일치
- size/DLC/address off-by-one
- test가 실제 defect를 재현하는지
- build 성공 주장과 실제 command 일치 여부
- documentation과 code 불일치
- 면접 답변과 실제 source/test 불일치

## Commit 권장 방식

사용자가 diff를 검토한 뒤 직접 commit하거나 Codex에 명시적으로 요청합니다.

권장 예시는 다음과 같습니다.

```text
fix(bootloader): reject invalid FOTA states and lengths
fix(flash): validate application bounds and copy CRC
fix(gateway): bound CAN retries and propagate failures
fix(isotp): honor flow control and guard receive bounds
docs(test): record two-week FOTA reliability results
```

두 repository가 함께 바뀌면 한 repository의 commit 메시지에 다른 repository 변경이 포함된 것처럼 쓰지 않습니다. 각 repository에서 독립적으로 재현 가능한 commit을 만듭니다.
