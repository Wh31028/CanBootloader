# 현재 Codex 인수인계 상태

## 현재 상태

- 계획 작성일: 2026-09-07
- 마지막 완료 Task: `TW-01 — Target 입력·state·block 수신 안전성`
- 진행 중 Task: 없음
- 다음 Task: `TW-02 — Flash copy·metadata·boot validation 안전성`
- CanBootloader 검증 기준: `fix/tw-01-target-input-state` / `a4cf05fff92b072c1bf87054b76e8ec6cd41e3da`
- yocto_capston 계획 기준: `main` / `6c393e8`
- Task 시작 시 CanBootloader: `main` / `fb5e26663f45b2bbf4bc8d4dda83f5d4eaee96e1`, clean
- Task 시작 시 yocto_capston: `main` / `6c393e8be4c0b1d4ad1038c3f5266245ad219296`, clean
- source 수정: `boot_can_custom_f103/App/ap/boot_can/boot_can.[ch]`에 local state와 input validation 추가; wire format 변경 없음
- build: TW-01 Custom bootloader PASS (Flash 10,068 B / 16 KiB, RAM 3,184 B / 20 KiB); ISO-TP는 TW-04 범위의 기존 include-order FAIL 상태
- BBB/STM32F103RB CAN hardware test: PASS. BBB `can0` 500 kbit/s, all requested malformed-frame cases와 15,180-byte normal Custom FOTA를 `cansend`/`candump -L`로 실행; normal path ACK 63회와 application 정상 복귀 확인.
- 필수 장비 범위: BBB, STM32F103RB, 현재 CAN transceiver/배선, 개발 PC
- 범위 제외: external analyzer, oscilloscope, relay power switch, 전문 CAN fault injector
- 마지막 면접 노트: `interview/TW-01.md` (DRAFT, 사용자 rehearsal 없음)

## 다음 창에서 읽을 문서

1. `AGENTS.md`
2. `docs/improvement-plan/README.md`
3. `docs/improvement-plan/sprint-01-two-weeks.md`의 `TW-01`
4. `docs/improvement-plan/SESSION_HANDOFF.md`
5. `docs/improvement-plan/interview/README.md`
6. `docs/improvement-plan/interview/QUESTION_BANK.md`
7. `docs/improvement-plan/reports/TW-00-baseline.md`

## 다음 창의 범위

TW-01 source/build 단계는 완료했다. target은 `IDLE`/`RECEIVING`/`IMAGE_VERIFIED`/`FAILED` local state를 사용하며, START의 exact DLC/size, DATA의 block별 exact sequence/DLC, END의 complete-image, JUMP의 verified-state를 검증한다. 새 error code는 기존 `ERR` header의 하위 6 bits만 사용하므로 BBB sender의 wire format과 generic error print는 호환된다. Yocto 패키지 사본도 START/END DLC 5, JUMP DLC 1, DATA 마지막-frame short DLC 형식을 사용하지만 source drift 동기화는 F4 이전에 결정하지 않는다.

TW-01은 `DONE`이다. 다음 창은 TW-02만 수행하며 flash copy, metadata, application boot validation을 다룬다. ISO-TP type include-order 수정은 TW-04 범위입니다.

## 현재 주의 사항

- TW-00 시작 시 두 repository는 clean 상태였습니다. 이후 CanBootloader에는 TW-00 문서 변경만 있습니다.
- 다음 창은 작업 시작 시 두 repository의 `git status`와 HEAD를 다시 확인해야 합니다.
- Codex는 사용자 요청 없이 commit하거나 push하지 않습니다.
