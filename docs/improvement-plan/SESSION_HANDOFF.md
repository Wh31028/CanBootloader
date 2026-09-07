# 현재 Codex 인수인계 상태

## 현재 상태

- 계획 작성일: 2026-09-07
- 마지막 완료 Task: 없음
- 다음 Task: `TW-00 — Baseline과 검증 계약 고정`
- CanBootloader 계획 기준: `main` / `c561ceb`
- yocto_capston 계획 기준: `main` / `6c393e8`
- source 수정: 없음
- hardware test: 아직 수행하지 않음
- 필수 장비 범위: BBB, STM32F103RB, 현재 CAN transceiver/배선, 개발 PC
- 범위 제외: external analyzer, oscilloscope, relay power switch, 전문 CAN fault injector
- 마지막 면접 노트: 없음
- 다음 면접 노트: `interview/TW-00.md`

## 다음 창에서 읽을 문서

1. `AGENTS.md`
2. `docs/improvement-plan/README.md`
3. `docs/improvement-plan/sprint-01-two-weeks.md`의 `TW-00`
4. `docs/improvement-plan/interview/README.md`
5. `docs/improvement-plan/interview/QUESTION_BANK.md`
6. `docs/f103-fota-baseline.md`

## 다음 창의 범위

TW-00에서는 source를 수정하지 않고 현재 build/test 기준선과 known failure를 기록합니다. 발견한 defect는 TW-01 이후 Task로 넘깁니다.

TW-00 report에는 현재 보유 장비와 software/toolchain을 기록하고, 별도 장비 없이 재현할 fault 범위를 baseline으로 고정합니다.

동시에 `interview/TW-00.md`를 작성해 현재 architecture, F103 memory map, boot flow, 과거 direct-write benchmark와 현재 staging 구조의 차이를 면접 답변 형태로 정리하고 질문 은행을 갱신합니다.

## 현재 주의 사항

- 이 문서를 작성한 시점에는 두 repository가 clean 상태였습니다.
- 다음 창은 작업 시작 시 두 repository의 `git status`와 HEAD를 다시 확인해야 합니다.
- Codex는 사용자 요청 없이 commit하거나 push하지 않습니다.
