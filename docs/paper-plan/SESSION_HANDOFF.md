# 논문 작업 인수인계

최종 갱신: 2026-10-05. 다음 대화는 이 파일을 먼저 읽는다.

## 현재 상태

- 폴더/branch: C:/repos/CanBootloader-paper / paper/ksma-2026
- HEAD: e5f20487f4e92332375e0590879e62ceb57cd035 (P01 시작과 동일)
- 마지막 완료: **P01 DONE** — F407 sender 시간·frame 집계/응답 검증 host 확인
- 진행 중 Task: 없음
- 다음 실행 Task: **P02만**
- 주 실험 후보: F407. 실제 board boot/smoke는 NOT RUN이며 P03에서 확정.
- F103: Custom/app PASS, ISO-TP는 Flash 17,224 bytes 초과로 FAIL. 보충 P07 선택 시 처리.
- 두 ISO-TP submodule: 5593428d95af10dde1e565cebcda16089fc74857로 초기화, 원형 유지.
- 원고: docs/paper/abstract.md, manuscript.md, references.md 생성. 모든 결과 [결과 미확정].
- 초기 설정: docs/paper/experiment-config.draft.json (실행 불가 초안).
- hardware/본 실험/제출: 모두 미실행. 공식 양식·저자·트랙 미확정.
- commit/push/merge/reset/외부 제출·연락: 미실행.
- 원본 main 및 TW-03: 이번 작업 범위 밖, 변경하지 않음.

## 변경과 evidence

[보고서 P00](reports/P00.md)와 [P01](reports/P01.md)에 명령·문제·완료 판정이 있다.

- 유일한 tracked source 수정: boot_can_isotp/App/ap/boot_can/isotp_port.h에 stdint.h 선행 include 2줄 추가. wire format·Flash 경계 변경 없음.
- 기존 untracked AGENTS.md, docs/paper-plan/ 보존. README와 이 handoff는 상태 갱신.
- 새 원고 3개·초기 설정·P00 report/evidence·build archive는 미커밋 파일이다.
- 핵심 log / patch / manifest: docs/paper-plan/reports/artifacts/P00-20261005/ (`build.log`, `manifest.json`, `source-dirty.patch`)
- P01 host 검증 log/manifest: docs/paper-plan/reports/artifacts/P01-20261005/ (`build.log`, `manifest.json`); 실제 FOTA 결과/CSV 없음.
- 실제 binary/map: experiments/ksma-2026/p00-build-20261005/
- 실패한 F407 최초 compile과 F103 ISO link overflow의 원문은 build.log에 합쳐 보존했다.
- *.bin/*.map는 Git ignore 대상이다. archive의 실제 binary를 보존해야 하며 hash만으로 복원된다고 생각하지 않는다.

## 실제 검증 결과

CMake 3.28.1 / Ninja 1.11.1 / ARM GCC 13.3.1, 각 프로젝트에서 cmake --preset Release 및 cmake --build --preset Release --parallel 4 실행.

| 항목 | 결과 |
| --- | --- |
| F407 Custom / ISO-TP / app | PASS; bin 33,472 / 42,140 / 36,832 bytes |
| F103 Custom / app | PASS; bin 8,240 / 35,240 bytes |
| F103 ISO-TP | FAIL; Flash used 33,608 > 16,384, 실행 binary 없음 |
| 고정 submodule SHA / 생성 binary vector·크기·MCU family | PASS |
| 기존 CSV 5개와 PPTX hash 전후 비교 | PASS |
| ST-LINK 열거 | 도구 실행됨, No ST-Link detected |
| BBB 접속·실제 CAN·Flash programming·boot·FOTA | NOT RUN |
| 공식 양식 적용/PDF 페이지 검증 | NOT RUN |

P00는 build 기준 확보 완료이며 정상 CAN FOTA를 증명한 것이 아니다. 현재 archive는 수정 전 측정 sender와 최적화 차이를 포함한 baseline이다. 시험 binary로 확정하기 전 P03에서 정책/설정을 재검토하고 새 hash를 남긴다.

F407 64 KiB image: [0x08010000, 0x08020000), erase sector 4. F103: bootloader 16 KiB, app [0x08004000, 0x08014000). main staging 0x08012000/57,336-byte 한도와 혼용 금지.

## P01 완료와 다음 P02 범위

[P01 보고](reports/P01.md)의 host 검증으로 두 F407 sender의 time boundary는 monotonic START 직전부터 유효 END ACK 직후까지로 통일됐다. FOTA-entry reset/JUMP phase는 측정에서 제외한다. Metrics는 send attempt/software drop/socket acceptance/error/protocol RX/retransmission을 구분하며 overhead 분모는 모든 send attempt다. SocketCAN acceptance는 on-wire 완료나 CAN automatic retransmission 수가 아니다.

Custom은 standard `0x101`, ACK/ERR DLC 2, NACK DLC 8을 검증한다. ISO-TP는 padded standard `0x7e8` SF 및 FC DLC 8, CTS/BS=8/STmin=0을 검증하고 initial FC와 8 CF마다의 FC를 준수한다. malformed response는 성공이 아니다. fixed submodule의 response timeout은 100 ms이나 P01 sender의 host wait/retry 정책은 바꾸지 않았다.

P02에서는 loss 대상과 seed/model, bounded deadline, runner manifest/exit status, START/DATA/END/JUMP failure 기록을 정한다. P01에서 기존 `MAX_RETRIES=50`과 Custom timeout tail probe의 무한 반복 가능성은 정책 변경 없이 남겼으므로 P02에서 유한 종료 기준으로 처리한다. hardware trace/actual FOTA는 P03까지 NOT RUN이다.

후속 gate:

- P02: omission 대상/재전송 정책·bounded retry·실패/중단 기록·image 입력 검증.
- P03: F407 Custom -Os / ISO-TP -O0 불일치 해소 정책, 주소 상한 불일치 검토, 새 binary/hash 고정 후 hardware smoke.
- F407 hw_def의 end=0x08080000과 max=960 KiB/app linker=960 KiB가 불일치한다. 정상 64 KiB 적합성만 점검했으며 비정상·큰 image 안전성은 검증하지 않았다.
- F103은 현재 Custom 5 ms pacing과 ISO-TP STmin 기반 pacing도 다르다. 과거 CSV와 현재 sender를 동일시하지 않는다.

## 사용자가 준비할 것

- 공식 행사 공지 URL/양식 파일, 일반/학부경진대회 트랙, 저자 순서·소속·교신저자, 정확한 마감/분량/발표 형식.
- F407 모델/board ID, 현재 기록 image와 보존 필요 여부, ST-LINK 및 복구 방법.
- BBB 접속 주소·계정(비밀번호를 문서에 넣지 않음), OS/kernel, can0, CAN transceiver/배선/종단 정보.
- 위 장비는 P03 전에 필요하다. P01의 host 검증은 장비 없이 진행 가능하다.
- 실제 program/erase 허가는 대상·binary/hash/address를 확인한 뒤 P03에서 별도로 받는다.

실행 중인 프로세스: **없음**. P01은 CSV/run을 만들지 않았다. 다음 run은 새 ID를 사용하고 기존 archive를 덮어쓰지 않는다. P01 evidence는 `reports/artifacts/P01-20261005/build.log`, `manifest.json`이며 source SHA-256로 dirty sender를 특정한다.

## 다음 대화 시작 prompt

```text
C:\repos\CanBootloader-paper의 paper/ksma-2026에서 진행해줘.
AGENTS.md와 docs/paper-plan/README.md, SESSION_HANDOFF.md,
tasks.md의 P02, codex-session-guide.md, reports/P00.md, reports/P01.md를 읽어라.
이번 대화에서는 P02만 수행해줘. 먼저 git status, HEAD, submodule 상태를 확인하고
기존 미커밋 수정과 P00/P01 evidence 및 예비 CSV를 보존해줘.
F407 sender의 loss 대상·seed/model·bounded deadline·모든 종료 상태 기록과 runner manifest를 정리하고 host 검증해줘.
P03 hardware flashing/FOTA, F103, main TW-03은 자동 시작하지 마.
종료 전에 reports/P02.md, README 상태, SESSION_HANDOFF를 갱신하고
다음 prompt와 준비할 것을 알려줘. commit/push, 외부 제출·연락은 하지 마.
```
