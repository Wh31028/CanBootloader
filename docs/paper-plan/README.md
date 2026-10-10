# KSMA 2026 학회 논문 실행 계획

작성일: 2026-10-04. 이 문서는 논문용 작업의 기준이다. 졸업논문은 학회 실험 결과를 바탕으로 이후 확장한다.

## 먼저 할 일

1. Codex에서 `C:/repos/CanBootloader-paper`를 작업 폴더로 연다.
2. [인수인계](SESSION_HANDOFF.md)의 다음 대화 시작 prompt를 붙여 넣는다.
3. P08 문서·근거 검토를 마쳤고, 공식 양식·저자·PDF 검증이 남아 P08은 `IN_PROGRESS`다. 다음 대화도 P08만 이어간다. 선택 과제 P07은 이번 제출 범위에서 보류했다. 종료 보고와 [인수인계](SESSION_HANDOFF.md)가 저장되면 이전 대화/창을 닫는다.
4. 다음 대화도 같은 폴더에서 열고, handoff에 지정된 Task만 수행한다.

현재 단계는 **P08 IN_PROGRESS (2026-10-10, 문서·근거 검토 완료, 최종 양식 검증 대기)**다. P04 유효 dataset은 `isotp-120-entry-v1` 120/120 `OK`와 `custom-120-terminal-probe-v1` 120/120 `OK`다. 보정 전 `custom-120-entry-v2`의 110 `OK`/10 `FAIL_DATA_TIMEOUT`은 별도 실패 artifact로 보존하며 유효 240건에 합치지 않는다. 전문·요약문은 P05 `p05-terminal-probe-v1-20261009`의 summary CSV와 SVG를 사용하고 실제 elapsed의 JUMP 송신 호출 포함 한계를 함께 명시한다. 원시 시간은 보정하지 않았다. 공식 양식·저자·PDF 페이지·교수 검토는 미완료이며 제출 상태는 미확인이다. 실행한 검증·checksum·다음 prompt는 [P08 보고](reports/P08.md)와 [handoff](SESSION_HANDOFF.md)에 있다. 이전 보고서의 보정 전·미실행 snapshot은 당시 이력으로 보존한다.

## 문서 작성 원칙

- 쉬운 우리말을 먼저 쓴다.
- CAN, ISO-TP, ACK처럼 널리 쓰는 기술 용어는 처음 나올 때 짧은 뜻을 함께 쓴다.
- 약어만 나열하지 않고, 무엇을 뜻하고 왜 필요한지 한 문장으로 설명한다.
- 실제로 하지 않은 시험은 “실행하지 않음”이라고 분명히 쓴다.

## 브랜치와 원본 보존

| 위치/branch | 역할 |
| --- | --- |
| `origin/capston-1`의 `7527bca60a46c6e244214d56114109414388a3ae` | 분기 기준, 기존 실험 코드/CSV 보존 |
| `C:/repos/CanBootloader-paper`, `paper/ksma-2026` | 측정 수정, 재실험, 논문 문서 |
| `C:/repos/CanBootloader`, `main` | staging 기반 FOTA; TW-03은 학회 작업 이후 재개 |

분기 기준은 생성 당시 로컬 remote-tracking ref다. P08 시작 HEAD는 `8757dcbf66793497f463ed5e48e2489f9d073699`, upstream은 `origin/paper/ksma-2026`이며 로컬이 3 commits ahead였다. 시작 시 staged·미커밋·untracked 변경은 없었고 P06 문서는 이미 HEAD에 포함돼 있었다. P06 인계의 미커밋 표기는 당시 이력이다. P08에서는 commit/push/merge/reset하지 않으며 이번 문서 변경은 미커밋으로 남긴다. 다른 PC나 새 checkout에 자동 전달되지 않으므로 commit/원격 백업은 사용자가 별도로 요청한다.

## 연구 범위

가제: **CAN 기반 펌웨어 업데이트를 위한 비트맵 선택 재전송 기법의 구현 및 성능 평가**

연구 질문: 송신단에서 DATA 누락을 주입할 때, bitmap 선택 재전송과 ISO-TP 기반 FOTA의 application block 재시도는 전송 시간과 재전송량에서 어떤 차이를 보이는가?

- BBB와 STM32, Classical CAN, 동일 보드 내 두 방식의 direct-write 비교.
- 기존 Python 실험 sender를 기준으로 최소한의 측정/실패 처리 수정.
- F407이 주 실험 대상이며 P03 smoke와 P04 본 실험, P05 분석을 완료했다. F103은 선택 과제 P07의 보충 검증 후보이며 P08 문서 검토 범위에서는 보류·미실행이다.
- F103에만 정상 baseline이 확보되면 주 대상을 F103으로 변경하고 근거를 기록할 수 있다.
- 두 보드를 반드시 끝내야 요약문을 제출할 수 있는 것은 아니다.
- power-loss recovery, staging, rollback, signature, 실제 차량 BER, 다중 ECU 신뢰성은 이번 필수 주장에 포함하지 않는다.
- 기존 CSV와 현재 main의 성능을 혼합하지 않는다. ISO-TP 표준 전체에 대한 절대 우위를 주장하지 않는다.

TW-03 전체는 보류하지만 실험 sender의 bounded retry/deadline, malformed response 검증, 실패 누락 방지는 P01/P02에서 수행한다. main의 C sender나 CAN HAL 개선으로 자동 확대하지 않는다.

## 제출 일정

아래 일정/분량은 사용자가 전달한 행사 공지에 근거한다. P00에서 공식 홈페이지 검색 색인의 행사 안내는 확인했으나 상세 페이지 열기 실패로 공식 양식을 확보하지 못했다. 이 표의 일정·분량은 아직 독립 공식 검증 완료가 아니다. [출처 확인 기록](../paper/references.md)에 남겼으며 원문 확인 후 갱신한다.

| 항목 | 공지상 일정/분량 | 내부 목표 |
| --- | --- | --- |
| 제목·요약문 | 2026-10-16, 1페이지 | 10/12 초안, 10/13~15 교수 검토·제출 |
| 심사 통보 | 2026-10-30 | 통보 전에 전문 준비 |
| 최종본 | 채택 시 2026-11-02, 2~3페이지 | 10/25까지 전문 수정본 |
| 사전등록 | 2026-11-02 | 사용자 직접 진행 |
| 행사 | 2026-11-05~07, 제주 호텔브릿지 서귀포 | 발표 준비 별도 |

학부논문경진대회/일반 학술대회 중 제출 트랙, 저자·소속·교신저자, 템플릿, 참고문헌 포함 페이지 계산, 발표 형식은 확인 대상이다. Codex가 저자 정보를 추정하거나 대신 제출하지 않는다.

## 한 대화당 한 Task

상태는 `TODO`, `IN_PROGRESS`, `BLOCKED`, `DONE`, `DEFERRED`를 사용한다. Task 완료와 개별 시험 PASS는 구별한다. 필수 완료 조건에 NOT RUN이 남으면 해당 실험 Task는 DONE이 아니다.

| ID | 작업 | 목표 시점 | 선행 | 현재 상태 |
| --- | --- | --- | --- | --- |
| P00 | 실험 baseline·build·제출 조건 확인, 글 골격 | 10/4~5 | 없음 | DONE |
| P01 | 시간·frame 집계 기준 통일 | 10/5~6 | P00 | DONE |
| P02 | loss/retry/실패 기록·runner 정리 | 10/6~7 | P01 | DONE |
| P03 | hardware smoke와 측정 검증 | 10/7~8 | P02 | DONE — 양 방식 5회 baseline, recovery/timeout, boot/readback 기록 |
| P04 | 주 MCU의 240회 핵심 실험 | 10/8~10 | P03 | DONE — ISO-TP 120/120 OK + terminal-frame probe 보정 Custom 120/120 OK; 원본 실패 artifact 보존 |
| P05 | 통계·그림·1페이지 요약문 | 10/11~12 | P04 | DONE — 보정 240 trial 재분석 내용 초안; 공식 양식·저자 정보는 외부 blocker |
| P06 | 2~3페이지 전문 초안 | 10/12~15 | P05 | DONE — Markdown 내용 초안; 공식 양식·PDF 페이지 검증 NOT RUN |
| P07 | F103 등 보충 실험, 필요 시만 | 10/17~22 | P06 | DEFERRED — 사용자 지정 P08 문서 검토 범위에서 제외; 미실행 |
| P08 | 최종 원고·근거 검토 | 10/23~25, 심사 후 재개 | P06; P07은 선택 | IN_PROGRESS — 문서·수치·근거 대조 완료; 공식 양식·저자·PDF 검증·교수/심사 의견 대기 |

상세 범위와 완료 조건은 [tasks.md](tasks.md)에 있다. 큰 Task는 P02-a/P02-b처럼 handoff의 세부 작업만 나누고 동일 Task를 다음 대화에서 이어간다. 여러 대화를 동시에 실행하지 않는다.

P00에서 abstract/manuscript 골격을 작성했다. hardware가 일시적으로 없으면 골격과 관련 연구 정리는 진행할 수 있지만, P03/P04의 미실행을 완료로 바꾸거나 P05에 수치를 만들어 넣지 않는다. 초록 결과 입력은 검증된 데이터가 생긴 뒤 한다.

## 실험 계약

| 항목 | 기본 계획 |
| --- | --- |
| 주 실험 | MCU 1종, Custom/ISO-TP 기반 FOTA |
| firmware | 같은 65,536-byte image와 hash, 같은 padding 패턴; 두 방식의 유효 주소 범위 확인 |
| 누락 확률 | `0`, `0.0001`, `0.0005`, `0.001` → CSV의 `0`, `0.01`, `0.05`, `0.1%` |
| 반복 | 2방식 × 4확률 × 30회 = 240개의 계획된 시도 |
| Flash | 같은 board 내 동일 direct-write 시작 주소·erase 범위·검증 정책 |
| bitrate | 같은 board 내 동일; F407 1 Mbit/s, F103 500 kbit/s는 후보 값이며 실제 설정 확인 |
| 시간 | monotonic clock, START 송신 직전 → 유효한 END ACK 수신 직후 |
| 시간 제외 | download, bootloader 진입 대기, JUMP 전 0.5초 대기, boot 확인 |
| 측정 이름 | erase/write/CRC를 포함한 CAN FOTA transaction 시간; transport-only 또는 전체 ECU downtime이라고 부르지 않음 |
| 성공 기준 | END ACK/CRC 성공을 transaction 성공으로 정의; application boot 확인은 별도 필드 |
| 기록 | 모든 시도, 실패·timeout·중단 포함. 실패를 성공할 때까지 대체하여 30개 OK만 만들지 않음 |
| 통계 | 시도/성공/실패 수, 성공률, 성공 조건부 시간의 평균·표준편차·95% CI, 재전송량 |

위 시간 항목은 의도한 실험 계약이다. P06에서 P04의 실행 source hash를 대조한 결과, 실제 `elapsed_sec`는 protocol 호출 직전부터 JUMP 송신 호출 뒤까지이며 END ACK 뒤 처리도 포함했다. entry 뒤 3.0 s는 제외되고 이 경로에는 0.5 s 대기가 없다. P05 원시 수치와 SVG는 보존하며, 그 차이를 전문에 명시했다. 정확한 END ACK 종료 시간으로의 소급 보정은 하지 않는다.

주입 모델은 software omission이다. P02에서 eligible frame 집합과 재전송 주입 정책을 확정한다. 같은 seed만으로 두 protocol에 동일한 누락 위치가 생긴다고 가정하지 않는다. protocol별 frame 역할, payload offset, 실제 drop count를 남기고 동일 fault schedule인지 같은 분포의 독립 시행인지 명시한다. ACK/NACK/FC loss는 기본 240회 matrix에 섞지 않는다.

실행 순서는 가능한 범위에서 protocol 교차/조건 무작위화한다. bootloader 재기록 비용 때문에 batch로 수행하면 작은 균형 batch와 실행 순서를 기록한다. 둘 사이 board/bitrate가 다르면 MCU 성능 효과로 해석하지 않는다.

## 현재 알려진 검토 항목

다음은 분기 기준 source/기존 자료를 읽어 발견한 사항이며 재실험 결과가 아니다.

- P01에서 두 sender 모두 END ACK 직후까지의 monotonic transaction 시간으로 통일했다. JUMP 전 0.5초 대기는 제외한다.
- P01에서 Custom과 ISO-TP 모두 software drop을 포함한 send attempt와 socket acceptance를 분리했다.
- ISO-TP START/END 실패는 P01에서 결과 상태로 기록하도록 보완했으며, socket 초기화·입력 파일 실패 등 모든 종료 상태와 runner 기록은 P02에서 정리한다.
- loss 대상은 Custom DATA와 ISO-TP CF로 다르며, 재전송/마지막 frame 정책도 확인해야 한다.
- 256-byte application chunk와 FC의 BS=8 CF-count는 P01에서 구분했다.
- F407 ISO-TP sender는 P01에서 FC BS=8/STmin=0을 검증하고 준수한다. hardware trace 대조는 P03에서 수행한다.
- P00에서 F103 ISO-TP의 16 KiB FLASH overflow 17,224 bytes를 재현했다. Custom/app만 PASS이며 보충 비교는 미확보다.
- P00에서 두 ISO-TP submodule을 gitlink 5593428d95af10dde1e565cebcda16089fc74857로 초기화했다. 최신 upstream으로 임의 갱신하지 않는다.
- 기존 CSV F407 960행/F103 240행은 모두 OK지만 모든 실패를 포함한 전체 시도였다는 근거는 부족하다.

## 산출물 위치

원고: [P05 요약문](../paper/abstract.md), [P06 전문](../paper/manuscript.md), [참고 출처](../paper/references.md), [초기 설정안](../paper/experiment-config.draft.json). 초기 설정안은 실행 config가 아니다. P04 유효 결과와 P05 분석은 위 현재 상태를 따른다. [P00 report](reports/P00.md)와 [원시 근거](reports/artifacts/P00-20261005/) 및 experiments/ksma-2026/p00-build-20261005/의 실제 build 산출물을 보존한다.

기존 계획 문서: 이 README, [Task 상세](tasks.md), [새 대화 안내](codex-session-guide.md), [F407ㆍBBB 장비 운영 안내](hardware-operations.md), [handoff](SESSION_HANDOFF.md), [보고 템플릿](reports/TEMPLATE.md).

P00~P06 보고·build/host/hardware evidence와 분석 자료를 보존했다. P08에서는 전문·요약문·출처 기록 및 종료 문서만 갱신했다.

- `docs/paper-plan/reports/P00.md` ~ `P08.md`: 작업 근거·검증.
- `docs/paper/abstract.md`, `docs/paper/manuscript.md`: 저자 검토용 원고.
- `docs/paper/references.md`: 확인한 선행연구와 출처.
- `experiments/ksma-2026/<run-set-id>/`: config, manifest, raw CSV/JSONL, trace, stdout/stderr, hashes.
- `experiments/ksma-2026/analysis/`: 원시 자료로부터 표/그림을 재생성하는 script와 사용법.

실험 파일이 `.gitignore`로 제외되는지 확인한다. binary를 무조건 commit하지는 않되, 재실행할 정확한 binary는 별도 artifact로 보존하고 hash만으로 복원이 가능하다고 가정하지 않는다. Git commit 권한이 없으면 dirty diff/파일 hash와 binary 보관 경로로 실행 버전을 특정한다.

## 학회 이후

main의 TW-03을 원래 C sender/target 코드 기준으로 재개한다. Python 실험 코드의 수정은 검토 후 필요한 개념만 반영하며 branch 전체를 무조건 merge하지 않는다. 졸업논문에서는 image-size 확장, 두 MCU, burst loss, ACK loss, staging/recovery 등을 별도 연구 질문으로 확장한다.

## P00에서 추가 확인한 후속 gate (당시 snapshot)

아래는 P00 당시의 기록이며 현재 장비 상태나 재실행 지시가 아니다. 이후 해결·실행 내역은 P03~P05 보고서를 따른다.

- F407 ISO-TP의 stdint.h 누락만 수정했다. build binary 33,472/42,140/36,832 bytes(Custom/ISO/app)이며 hardware 동작 PASS는 아니다.
- 고정 dependency는 FC BS=8/STmin=0/response timeout=100 ms다. P01 sender는 BS=8/STmin=0 FC를 검증하고 8 CF마다 대기한다.
- F407 Custom -Os와 ISO 사용자 코드 -O0 차이는 P03 비교 설정 고정 전에 처리한다.
- F407 source end=0x08080000과 max/app linker=960 KiB 불일치가 있다. P00는 정상 64 KiB [0x08010000,0x08020000) 및 sector 4 적합성만 확인했다.
- 현재 네 sender의 CSV 출력 경로는 모두 can-fota-BBB/fota_results.csv다. 보관 CSV와 생성 코드의 동일성을 단정하지 않는다.
- 기존 CSV/PPTX hash를 보존했다. F103 Custom의 현재 5 ms pacing도 과거 CSV와 구별한다.
- P00 DONE은 hardware·공식 양식·저자 확정·제출 준비 완료가 아니다. ST-LINK는 현재 PC에서 미검출, BBB·보드 접속 정보는 TODO이다.

## 증거 파일 정리 원칙

각 Task는 보고서에서 핵심 근거를 읽을 수 있게 한다. `reports/artifacts/<Task-ID>/`에는 원칙적으로 `build.log` 또는 `run.log`, `manifest.json`, 필요한 dirty patch만 둔다. 프로젝트별 configure/build 로그, 수집 script, 중간 검토본은 통합 로그에 필요한 원문을 넣은 뒤 보관하지 않는다. 실패 원문과 종료 상태는 통합 로그와 manifest에서 보존한다.

실행 binary가 필요한 Task는 `experiments/.../<run-id>/`에 binary와 map만 둔다. ELF·HEX·CMake cache·build.ninja 등은 재현에 별도로 필요하다고 판단한 경우에만 보관한다. 새 run은 기존 run ID를 덮어쓰지 않고 새 디렉터리를 사용한다.
