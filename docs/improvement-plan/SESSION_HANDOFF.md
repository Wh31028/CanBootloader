# 현재 Codex 인수인계 상태

## 현재 상태

- 계획 작성일: 2026-09-07
- 마지막 완료 Task: `TW-00 — Baseline과 검증 계약 고정`
- 다음 Task: `TW-01 — Target 입력·state·block 수신 안전성`
- CanBootloader 계획 기준: `main` / `c561ceb`
- yocto_capston 계획 기준: `main` / `6c393e8`
- Task 시작 시 CanBootloader: `docs/tw00-baseline` / `4f1ac7b6a175a476febcad2719df31ca3a6c6bd3`, clean
- Task 시작 시 yocto_capston: `main` / `6c393e8be4c0b1d4ad1038c3f5266245ad219296`, clean
- source 수정: 없음 (TW-00 산출 문서만 추가/갱신)
- build: Custom bootloader PASS, F103 application PASS, ISO-TP bootloader FAIL (fixed-width integer include-order failure)
- BBB/Linux flasher build 및 hardware test: NOT RUN (이 macOS 개발 PC 세션에 BBB/Linux target과 CAN hardware가 연결되어 있지 않음)
- 필수 장비 범위: BBB, STM32F103RB, 현재 CAN transceiver/배선, 개발 PC
- 범위 제외: external analyzer, oscilloscope, relay power switch, 전문 CAN fault injector
- 마지막 면접 노트: `interview/TW-00.md` (DRAFT, 사용자 rehearsal 없음)
- 다음 면접 노트: `interview/TW-01.md`

## 다음 창에서 읽을 문서

1. `AGENTS.md`
2. `docs/improvement-plan/README.md`
3. `docs/improvement-plan/sprint-01-two-weeks.md`의 `TW-01`
4. `docs/improvement-plan/SESSION_HANDOFF.md`
5. `docs/improvement-plan/interview/README.md`
6. `docs/improvement-plan/interview/QUESTION_BANK.md`
7. `docs/improvement-plan/reports/TW-00-baseline.md`

## 다음 창의 범위

TW-01은 `boot_can_custom_f103/App/ap/boot_can/boot_can.c`의 START precondition, size/DLC/sequence/누적 byte 경계를 다룹니다. TW-00에서 source는 수정하지 않았으므로 protocol 호환성은 변하지 않았습니다. BBB sender와 Yocto source 사본의 drift는 발견 사실만 기록했으며, 동기화 결정은 F4 이전에 하지 않았습니다.

TW-00 report의 실제 command, binary hash/size, ISO-TP compile error를 기준으로 변화량을 비교합니다. ISO-TP type include-order 수정은 TW-04 범위입니다.

## 현재 주의 사항

- TW-00 시작 시 두 repository는 clean 상태였습니다. 이후 CanBootloader에는 TW-00 문서 변경만 있습니다.
- 다음 창은 작업 시작 시 두 repository의 `git status`와 HEAD를 다시 확인해야 합니다.
- Codex는 사용자 요청 없이 commit하거나 push하지 않습니다.
