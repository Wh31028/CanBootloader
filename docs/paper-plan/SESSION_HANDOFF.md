# 논문 작업 인수인계

최종 갱신: 2026-10-10, P08 문서·근거 검토 종료. 이 상단이 현재 지시이며 접힌 P06 및 이전 기록은 실행 지시가 아니다.

## 현재 상태

- 폴더/branch: `C:/repos/CanBootloader-paper` / `paper/ksma-2026`.
- 시작 HEAD: `8757dcbf66793497f463ed5e48e2489f9d073699`, upstream보다 3 commits ahead, clean. P06 문서는 이미 HEAD에 포함돼 있었다.
- P08: **IN_PROGRESS**. 문서·근거 대조와 전문·요약문 정합화 완료. 공식 양식·저자·PDF 검증·교수/심사 의견 반영 조건은 미완료다. 외부 제출/채택 상태는 미확인이다.
- P07: **DEFERRED**, 이번 범위에서 제외·미실행. 다음 Task도 **P08만**이다.
- 원고 버전: `p08-doc-review-v1`. checksum·검증 명령·결과·발표 핵심 3개는 [P08 보고](reports/P08.md)에 있다.
- 변경 파일: `docs/paper/{abstract,manuscript,references}.md`, `docs/paper-plan/README.md`, 이 파일, `reports/P08.md`. 미커밋으로 인계한다.
- 두 ISO-TP submodule은 `5593428d95af10dde1e565cebcda16089fc74857`로 유지했다. P00~P06 보고/evidence, 예비 CSV/PPTX, P04 raw, P05 출력은 보존했다.
- build·host 기능 시험·hardware 재실행·PDF 검증은 NOT RUN. F103, main TW-03, 외부 제출·연락, commit/push/merge/reset을 하지 않았다. 이번 세션에서 시작한 지속 실행 프로세스는 없고 원격 장비 상태는 조회하지 않았다.

## 유효 입력과 검토 결과

원시 root: `docs/paper-plan/reports/artifacts/P04-20261009/bbb-p04-f407-500k-20261009/`.

| 구분 | run ID / 결과 | 사용 |
| --- | --- | --- |
| ISO-TP | `isotp-120-entry-v1`, 120 OK | 유효 입력 |
| Custom | `custom-120-terminal-probe-v1`, 120 OK | 유효 입력 |
| 보정 전 Custom | `custom-120-entry-v2`, 110 OK/10 FAIL_DATA_TIMEOUT | 별도 실패 기록; 유효 240건에 합치지 않음 |

분석 기준은 `experiments/ksma-2026/analysis/p05-terminal-probe-v1-20261009/`의 summary CSV·validation JSON·SVG 3개다. 읽기 전용 재계산에서 240 raw/JSONL/manifest/config, 8 summary 행, SVG 3개가 일치했다. 보정 전 10건은 모두 initial frame_index=36 누락을 포함했다. 새 Custom은 120회 전체 batch이며 실패 10건 대체가 아니다.

전문·요약문은 F407/500 kbit/s/65,536 B/direct-write `[0x08010000,0x08020000)`/sector 4를 함께 명시한다. 실제 elapsed는 protocol 호출 직전→JUMP 송신 호출 뒤이며 END ACK 뒤 처리도 포함한다. entry 뒤 3.0 s는 제외되고 이 경로에 0.5 s 대기는 없다. 원시 시간을 차감하거나 소급 분리하지 않는다. 240건의 boot_status는 모두 `JUMP_SENT_NOT_VERIFIED`다.

P04 보고 아래쪽의 보정 전/NOT RUN 기록, P05 보고의 옛 validation 링크·시간 설명, 분석 script 상단의 보정 전 run 이름은 과거 설명으로 보존했다. 현재 입력은 위 표와 P08 보고의 명시적 run 인자를 따른다.

## 미완료 조건과 다음 작업

- 공식 양식 원본, 제출 트랙, 저자 순서·국문/영문 이름·소속·교신저자, 참고문헌 포함 페이지 계산·마감 시각이 필요하다. 아직 미확정이다.
- 양식이 확보되면 내용을 적용하고 PDF를 실제 export하여 페이지 수·글꼴·그림/표 가독성을 확인한다. 현재 요약문 1페이지/전문 2~3페이지는 목표이며 PASS가 아니다.
- 교수 검토와 채택 여부·심사 의견은 미제공이다. 미통보를 채택으로 기록하지 않는다. CAN FOTA 직접 선행연구 확충과 최종 서지 형식도 잔여 검토다.
- 이후 main TW-03 재개 및 졸업논문 확장은 P08 보고의 후보 목록만 인계한다. 현재 작업으로 실행하지 않는다.

## 다음 대화 시작 prompt

```text
C:\repos\CanBootloader-paper의 paper/ksma-2026에서 P08만 이어가줘.
AGENTS.md, docs/paper-plan/README.md, SESSION_HANDOFF.md, tasks.md의 P08,
codex-session-guide.md, reports/P08.md 및 docs/paper의 전문·요약문·출처 기록을 읽어줘.
먼저 git status --short --branch, git rev-parse HEAD, git submodule status를 확인하고
P08 미커밋 문서, P00~P06 evidence, 예비 CSV, P04 raw와 P05 출력을 보존해줘.
유효 데이터는 isotp-120-entry-v1 + custom-120-terminal-probe-v1의 240 OK뿐이며
custom-120-entry-v2의 110 OK/10 FAIL_DATA_TIMEOUT은 별도 실패 이력이다.
P05 p05-terminal-probe-v1-20261009 수치를 유지하고 JUMP 송신 호출을 포함한
실제 elapsed 한계를 유지해줘. 원시 시간을 보정하지 마.
제공된 공식 양식·저자/트랙 정보·교수/심사 의견이 있으면 반영하고,
PDF를 실제 생성한 경우에만 페이지·글꼴·그림 가독성을 검증해줘.
자료가 없으면 미확정/NOT RUN을 유지하고 P08을 DONE으로 바꾸지 마.
F103/P07, main TW-03, hardware 재실행, 외부 제출·연락,
commit/push/merge/reset은 하지 마. 종료 전에 P08 보고·README·handoff를 갱신해줘.
```

<details>
<summary>P06 종료 인계 원문 — 당시 이력, 현재 실행 지시가 아님</summary>

# 논문 작업 인수인계

최종 갱신: 2026-10-10, P06 종료. 이 파일 상단이 현재 지시이며 맨 아래 접힌 이전 기록은 이력 보존용이다.

## 현재 상태

- 폴더/branch: `C:/repos/CanBootloader-paper` / `paper/ksma-2026`.
- 시작 HEAD: `555fbb1b0e2bf37735ea483a144909001c4e1aa7`; upstream보다 2 commits ahead. staged·미커밋 변경 없이 시작했다.
- 마지막 완료: **P06 DONE — 2~3페이지 목표 전문 Markdown 내용 초안**. 공식 양식·PDF 페이지 검증·제출 완료를 뜻하지 않는다.
- 진행 중 Task/이번 세션에서 시작한 hardware 프로세스: 없음. 장비에 재접속하지 않았으므로 현재 원격 프로세스·장비 상태는 재확인하지 않았다.
- 다음 권장 Task: **P08 문서 검토만**. P07은 선택 과제로 미선택·미실행이며, 이번 종료에서 P07/P08을 시작하지 않았다.
- 변경 파일: `docs/paper/manuscript.md`, `docs/paper-plan/reports/P06.md`, `README.md`, 이 파일. 미커밋 상태로 인계한다.
- commit/push/merge/reset, F103, main TW-03, build/hardware 재실행, 외부 제출·연락은 하지 않았다.
- 두 ISO-TP submodule: `5593428d95af10dde1e565cebcda16089fc74857`, 변경 없음.

## 사용할 데이터와 원고

| 구분 | 경로/판정 |
| --- | --- |
| 유효 ISO-TP | `reports/artifacts/P04-20261009/bbb-p04-f407-500k-20261009/isotp-120-entry-v1`, 120/120 OK |
| 유효 Custom | 같은 root의 `custom-120-terminal-probe-v1`, 120/120 OK |
| 보정 전 Custom | 같은 root의 `custom-120-entry-v2`, 110 OK/10 FAIL_DATA_TIMEOUT; **유효 240건에 합치지 않음** |
| P05 분석 | `experiments/ksma-2026/analysis/p05-terminal-probe-v1-20261009/`의 summary CSV·validation JSON·SVG 3개 |
| 전문 | [manuscript.md](../paper/manuscript.md), P06 내용 초안 |
| 상세 검증·잔여 질문 | [reports/P06.md](reports/P06.md) |

P00~P05 보고/evidence, 예비 CSV, 실패 artifact, 기존 P05 분석 출력은 보존했다. 옛 `p05-20261009`는 보정 전 분석 이력이며 현재 원고 입력이 아니다. P04 보고의 일부 아래쪽 문구 및 접힌 handoff에는 보정 전·미실행 단계가 섞여 있으므로 현재 상태로 실행하지 않는다.

공통 조건은 F407/500 kbit/s/65,536 B/0xFF padding, direct-write `[0x08010000,0x08020000)`, sector 4 erase다. application SHA-256은 `1badd29c53120916c2f2b0f2e773c6af953960bedeb1c199b66021096b9870e1`이다. 두 run은 다른 seed·source revision으로 별도 batch 실행됐고 확률별 30회씩이다.

## P06에서 확인한 한계와 다음 검토

1. **시간 종료점:** 의도는 START 직전→END ACK 직후지만 실제 P04 sender는 JUMP 송신 호출 뒤 `elapsed_sec`를 기록했다. 원고는 이 차이를 명시하고 기존 P05 수치를 그대로 썼다. JUMP 처리 시간을 소급 분리하거나 0.5초를 차감하지 않는다. source 두 hash와 확인 위치는 P06 보고에 있다.
2. **요약문 잔여 문구:** `abstract.md`는 결과 숫자·dataset은 일치하지만 “loss 조건의 timeout 실패도 함께 발생했다”가 보정 전 실패임을 명시하지 않는다. 시간 경계 서술도 위 한계와 맞춰야 한다. 전문만 보완하라는 이번 요청에 따라 요약문·P05 보고는 수정하지 않았으며, 다음 P08에서 문구를 맞춘다.
3. **일반화 제한:** software omission, Custom DATA/ISO-TP CF 대상 비대칭, 별도 batch·seed, send error 및 host 영향. ISO-TP 전체·실제 차량·일반 신뢰성 우위를 주장하지 않는다. 성공 시간과 성공률/실패 이력을 함께 읽는다.
4. **외부 잔여:** 공식 양식·트랙·저자/소속/교신저자·참고문헌 포함 분량·교수 검토. PDF 미생성으로 2~3페이지 준수는 NOT RUN. 직접 CAN FOTA 선행연구 확충도 검토 대상이다.
5. F103 ISO-TP는 P00의 17,224-byte overflow 상태를 보존한다. main staging/TW-03과 이번 F407 결과를 섞지 않는다.

검증은 기존 분석 함수를 읽기 전용으로 호출해 raw/JSONL/manifest/config 240건, 입력 hash, 요약 8행, SVG 3개(메모리에서 재생성)를 대조했다. 보정 전 110/10 및 terminal 누락 대응도 확인했다. 명령·출력·최종 보존 점검은 P06 보고를 따른다. build, host/hardware 기능 시험, 공식 PDF 검증은 **NOT RUN**이다.

## 다음 대화 시작 prompt

```text
C:\repos\CanBootloader-paper의 paper/ksma-2026에서 진행해줘.
AGENTS.md, docs/paper-plan/README.md, SESSION_HANDOFF.md,
tasks.md의 P08, codex-session-guide.md, reports/P05.md와 P06.md,
docs/paper/manuscript.md, abstract.md, references.md를 읽어줘.

이번 대화에서는 P08의 문서·근거 검토만 수행해줘.
먼저 git status --short --branch, git rev-parse HEAD, git submodule status를 확인하고
P06 미커밋 문서, P00~P05 evidence, 예비 CSV, P04 raw artifact를 보존해줘.
유효 입력은 isotp-120-entry-v1과 custom-120-terminal-probe-v1의 240 OK이며,
custom-120-entry-v2의 110 OK/10 FAIL_DATA_TIMEOUT은 별도 실패 기록이다.
P05 p05-terminal-probe-v1-20261009의 summary CSV와 SVG를 사용해
전문·요약문의 dataset/수치/시간 경계/실패 이력 표현을 맞춰줘.
실제 elapsed에 JUMP 송신 호출까지 포함된 한계를 유지하고 원시 시간은 보정하지 마.
공식 양식·저자 정보가 없으면 미확정으로 남기고 PDF 페이지 검증을 PASS로 쓰지 마.
F103/P07, main TW-03, hardware 재실행, 외부 제출·연락,
commit/push/merge/reset은 하지 마.
종료 전에 reports/P08.md, README 상태, SESSION_HANDOFF.md에
실행한 검증·미완료 조건·다음 프롬프트를 기록해줘.
```

## 이전 handoff 원문 (이력 보존)

<details>
<summary>2026-10-09 및 이전 snapshot — 현재 실행 지시가 아님</summary>

아래의 P04 재실행 prompt, 연결 실패, 미커밋 여부와 NOT RUN은 각각 기록 당시 상태다. 현재 작업에는 위 P06 종료 상태를 적용한다.

# 논문 작업 인수인계

최종 갱신: 2026-10-09. 다음 대화는 이 파일을 먼저 읽는다.

## 현재 상태

- 폴더/branch: C:/repos/CanBootloader-paper / paper/ksma-2026
- HEAD: c1d1e21c31c59eb1c436a7b6f587bcbba6e59a5e (P05 종료 문서·분석 산출물은 미커밋)
- 마지막 완료: **P05 DONE (내용 초안)** — ISO-TP 120/120 + terminal-frame probe 보정 Custom 120/120 재분석
- 진행 중 Task: 없음
- 다음 실행 Task: **P06만**
- 주 실험 후보: F407. P03 hardware smoke와 readback은 완료했으며, P04의 live 상태 재확인도 PASS다.
- F103: Custom/app PASS, ISO-TP는 Flash 17,224 bytes 초과로 FAIL. 보충 P07 선택 시 처리.
- 두 ISO-TP submodule: 5593428d95af10dde1e565cebcda16089fc74857로 초기화, 원형 유지.
- 원고: docs/paper/abstract.md는 P05 검증 수치를 반영한 내용 초안이며, manuscript.md/references.md는 다음 P06에서 연결한다. 공식 양식·저자·제출 트랙은 미확정이다.
- 초기 설정: docs/paper/experiment-config.draft.json (실행 불가 초안).
- hardware/본 실험/제출: P03 hardware smoke는 완료. P04 유효 dataset은 ISO-TP `isotp-120-entry-v1` 120/120 OK와 terminal-frame probe 보정 Custom `custom-120-terminal-probe-v1` 120/120 OK다. entry `0x200#DEAD`와 3.0 s 대기(측정 제외)는 유지했다. post-run application readback SHA-256도 approved image와 일치한다. 보정 전 Custom 110 OK/10 FAIL_DATA_TIMEOUT 및 초기 runner/dependency/CAN-unresponsive artifact는 삭제하지 않고 별도 실패 기록으로 보존한다.
- commit/push/merge/reset/외부 제출·연락: P03 Custom checkpoint commit은 존재하지만 push/merge/외부 제출·연락은 미실행.
- 원본 main 및 TW-03: 이번 작업 범위 밖, 변경하지 않음.

## P05 완료 기록

- 유효 입력은 오직 `reports/artifacts/P04-20261009/bbb-p04-f407-500k-20261009/isotp-120-entry-v1` 및 `custom-120-entry-v2`다. 초기 runner/dependency/CAN 무응답 artifact와 `custom-120-entry-v1`은 삭제하지 않았고, 유효 240 trial에 합치지 않았다.
- `python experiments/ksma-2026/analysis/p05_analyze.py --input-root docs/paper-plan/reports/artifacts/P04-20261009/bbb-p04-f407-500k-20261009 --output experiments/ksma-2026/analysis/p05-20261009`은 PASS다. CSV/JSONL/manifest 240 trial, schema/ID/planned config/hash/exit-status 대응을 검증했다. derived summary CSV, validation JSON, SVG 세 그림을 생성하며 raw evidence는 수정하지 않는다.
- ISO-TP는 120/120 OK, Custom은 110 OK/10 FAIL_DATA_TIMEOUT이다. 성공 조건부 시간과 실패율을 분리했다. Custom timeout elapsed는 성공 시간으로 대체하거나 시간 평균에 포함하지 않았다. entry `0x200#DEAD` 뒤 3.0 s 대기는 transaction 시간에서 제외된 상태를 유지했다.
- P05 report와 abstract 내용 초안을 갱신했다. 공식 1페이지 양식·저자·소속·트랙은 아직 없으므로 제출본이나 양식 검증 PASS가 아니다. P05에서 build/hardware 재실행은 NOT RUN이다.

## P04 terminal-frame probe 보정 기록

- 원본 Custom 10 `FAIL_DATA_TIMEOUT`은 전부 initial `frame_index=36` 누락이고, 성공 110건에는 이 누락이 없었다. target은 마지막 frame 수신 뒤에만 bitmap NACK를 보내며, P04 `fota_sender_p02.py`는 무응답 때 즉시 실패했던 것이 원인이다.
- `can-fota-BBB/fota_sender_p02.py`는 마지막 frame을 최대 4회 probe하고 기존 loss 모델·deadline을 유지하도록 수정했다. 새 sender SHA-256은 `620ffba37e818282beeac26a1722c79c02794310575ad9c3067df17d6d0b46b1`이다. `test_p02_host.py`에 terminal probe recovery와 bounded timeout test를 추가했고 `python can-fota-BBB/test_p02_host.py`, `python -m py_compile ...`, `git diff --check`는 PASS다.
- 새 config/run script는 `experiments/ksma-2026/make_p04_custom_terminal_probe_config.py`, `start_p04_custom_terminal_probe.sh`다. 새 run ID는 `custom-120-terminal-probe-v1`이며 원본 run directory를 덮어쓰지 않는다. firmware/bootloader hash/address와 500 kbit/s 조건은 기존 P04와 같다.
- SSH read-only 상태 확인을 두 번 시도했으나 `192.168.7.2:22` timeout이다. 연결 회복 전에는 source/config copy, CAN reset, FOTA를 실행하지 않는다. 연결 후 현재 `can0`, firmware/bootloader hash, 새 run directory 부재를 다시 확인하고, 새 source/config를 BBB에 복사한 뒤 120회 실행한다.

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

## P02 완료와 다음 P03 범위

[P01 보고](reports/P01.md)의 host 검증으로 두 F407 sender의 time boundary는 monotonic START 직전부터 유효 END ACK 직후까지로 통일됐다. FOTA-entry reset/JUMP phase는 측정에서 제외한다. Metrics는 send attempt/software drop/socket acceptance/error/protocol RX/retransmission을 구분하며 overhead 분모는 모든 send attempt다. SocketCAN acceptance는 on-wire 완료나 CAN automatic retransmission 수가 아니다.

Custom은 standard `0x101`, ACK/ERR DLC 2, NACK DLC 8을 검증한다. ISO-TP는 padded standard `0x7e8` SF 및 FC DLC 8, CTS/BS=8/STmin=0을 검증하고 initial FC와 8 CF마다의 FC를 준수한다. malformed response는 성공이 아니다. fixed submodule의 response timeout은 100 ms이나 P01 sender의 host wait/retry 정책은 바꾸지 않았다.

P02는 `p02-frame-omission-v1`로 Custom DATA와 ISO-TP CF만 software omission 대상으로 정했다. START/END/JUMP/FF/ACK/NACK/FC는 제외하며, 원본과 재전송 모두 seed 기반 독립 추첨이다. sender는 transaction deadline 120 s, START 15 s, DATA 0.15 s, END 3 s, FC 1 s, ISO block 최대 4회로 끝난다. ENOBUFS도 deadline에서 멈춘다. 새 run-dir의 raw.csv/events.jsonl와 manifest에는 status·seed·실제 drop·hash·exit status를 append하고 기존 CSV는 건드리지 않는다. 상세는 [P02 보고](reports/P02.md)를 따른다. hardware trace/actual FOTA는 P03까지 NOT RUN이다.

## P03 진행 기록

**2026-10-07 최종 종료 갱신:** P03은 **DONE**이다. F407 Custom/ISO-TP의 500 kbit/s loss 0% baseline 각 5회, 양 방식의 software omission recovery, ISO-TP bounded timeout과 FOTA recovery/readback을 완료했다. F103, `main` TW-03 및 P04 240회는 시작하지 않았다.

ISO-TP bootloader `7f9412a4…647ae5eb`는 사용자 허가 뒤 `0x08000000`에 sector 0--2만 erase/program/verify했고 mass erase는 하지 않았다. timeout `isotp-timeout-01`은 application sector 4 erase 뒤 의도대로 `FAIL_DATA_RETRY` (4.553979 s)로 끝났다. post-flash target 무응답인 recovery-01/02는 `FAIL_START`로 보존했다. CAN entry trigger `0x200#DEAD` 뒤 올바른 raw sender를 쓴 `isotp-recovery-after-timeout-06`은 **OK**, 12.111229 s였다. ST-LINK read-only dump `reports/artifacts/P03-20261007/f407-app-after-isotp-timeout-recovery.bin`은 65,536 B와 SHA-256 `1badd29c53120916c2f2b0f2e773c6af953960bedeb1c199b66021096b9870e1`가 approved application과 정확히 일치했다. 종료 시 BBB source/run 전체를 `reports/artifacts/P03-20261007/bbb-p03-f407-500k-prep-20261007-sync2/`에 별도 동기화했다.

### 다음 창의 BBB 자동 접속·CAN reset

처음 보는 사람을 위한 전체 접속ㆍCAN resetㆍ기록 보존 절차는 [F407ㆍBBB 장비 운영 안내](hardware-operations.md)를 먼저 따른다.

P03 전용 key `C:\\Users\\wh310\\.ssh\\canboot_p03_agent_ed25519`를 사용하면 `debian@192.168.7.2`에 passwordless SSH가 된다. BBB의 `/etc/sudoers.d/canboot-can0`은 `visudo -cf`에서 parsed OK이고 다음 두 `ip` 명령만 `NOPASSWD`로 제한했다. 다음 창에서도 먼저 `sudo -n`을 붙여 이 정확한 500 kbit/s reset을 실행할 수 있다. P04 실행 자체는 이 기록만으로 허가되지 않으며, P04의 별도 scope/허가를 먼저 확인한다.

```bash
sudo -n /bin/ip link set can0 down
sudo -n /bin/ip link set can0 up type can bitrate 500000 sample-point 0.875
ip -details link show can0
```

2026-10-07에 위 명령을 SSH로 실제 실행했고, 결과는 `UP, LOWER_UP, ERROR-ACTIVE`, 500,000 bit/s, sample point 0.875, tx/rx error 0/0이었다.

대상은 STM32F4DISCOVERY/ST-LINK SN `066BFF3332584B3043252734` (V2J46M31, Device ID `0x413`)이며, BBB는 `debian@192.168.7.2` (beaglebone, Linux 4.19.94-ti-r42)다. 최종 can0은 500,000 bit/s, sample point 0.833, ERROR-ACTIVE, tx/rx error 0/0이었다. BBB clock은 unsynchronized 2026-08-10이므로 raw CSV timestamp는 신뢰하지 말고 monotonic elapsed만 사용한다.

CAN trace로 Custom response numeric `0x101`이 extended frame으로 나가 P01 sender에 거부되는 것을 확인했다. Custom/ISO-TP `canMsgWrite`를 11-bit ID는 standard, 그 외는 extended로 수정했다. Custom의 마지막 256-byte block fragment가 padded DLC=8이면 offset 252의 네 bytes를 skip한 채 ACK하는 버그도 수정했다. final Custom은 `experiments/ksma-2026/p03-f407-500k-custom-tailfix-20261007/boot_can_custom-500k-stdid-tailfix.bin`, SHA-256 `280410bf713630b66f16f233989486de60387a648cfa9b1ae6b1a201826e9391`, 33,488 B다. 사용자의 exact-hash 허가 후 sector 0--2만 erase/program/verify했다 (mass erase 없음). application은 SHA-256 `1badd29c53120916c2f2b0f2e773c6af953960bedeb1c199b66021096b9870e1`, 65,536 B, `[0x08010000,0x08020000)`이며 FOTA START로 sector 4만 erase됐다.

BBB `custom-smoke-05`는 `OK`, elapsed 8.873758 s, attempts/socket success 9474/9474, errors/drops/retransmit 0, protocol RX 258, invalid RX 0이다. END CRC ACK 및 JUMP ACK trace는 `101#0000`; boot 상태는 `JUMP_SENT_NOT_VERIFIED`다. ST-LINK read-only dump `reports/artifacts/P03-20261007/f407-app-after-custom-smoke-05.bin`은 application과 SHA-256 일치하고 byte-for-byte first difference가 -1이다. 앞선 smoke-01~04 실패와 smoke-04 mismatching dump도 P03 보고에 보존했다.

다음 대화는 P04만: 먼저 status/HEAD/submodule 및 미커밋 변경을 보존한다. BBB SSH가 회복했는지 읽기 전용으로 확인하고, `can0`/현재 firmware·bootloader hash/new run directory를 대조한다. `fota_sender_p02.py` SHA-256 `620ffba3…d0b46b1`와 새 config를 BBB에 복사한 뒤 `custom-120-terminal-probe-v1`만 실행한다. 원본 P04 run은 절대 덮어쓰지 않는다. 완료 후 raw CSV/JSONL/manifest를 동기화하고 P05 분석을 재생성한다. F103, main TW-03, 외부 제출·연락은 시작하지 않는다.

### P03 초기 snapshot (보존용)

이 아래는 P03 실행 전 기록이며, 위 2026-10-07 종료 갱신과 [P03 보고](reports/P03.md)의 `처음 읽는 사람을 위한 실행 기록`이 현재 기준이다. 시작 상태는 branch `paper/ksma-2026`, HEAD `26cd5c7699257baae51cbb6b94d9d9299528b1c4`, 두 ISO-TP submodule `5593428d95af10dde1e565cebcda16089fc74857`였고, `git status --short --branch`의 미커밋 파일·`git diff --check`·untracked-file 조회 출력은 없었다. P00~P02 evidence와 예비 CSV는 읽기만 했고 수정하지 않았다.

F407 target은 `STM32F4DISCOVERY`, ST-LINK SN `066BFF3332584B3043252734`/firmware `V2J46M31`로 확인했고 사용자가 ST-LINK 복구 가능을 확인했다. BBB USB SSH는 `debian@192.168.7.2`, hostname `beaglebone`, Linux `4.19.94-ti-r42`이며, `can0`은 500,000 bit/s/sample point 0.875에서 UP/LOWER_UP/ERROR-ACTIVE와 tx/rx error 0/0이다. `candump`가 설치됐고 idle 10초 capture는 오류 없이 종료했다. F407 CAN1 PD0=RX/PD1=TX(AF9)와 transceiver/종단 배선도 사용자가 확인했다. erase/program/verify, FOTA, smoke run 및 CSV/run 생성은 여전히 **NOT RUN**이다.

P03는 CubeMX의 500 kbit/s 설정(prescaler 6)을 Custom/ISO-TP/application에 반영하고, ISO-TP의 강제 `-O0`을 Custom과 같은 `-Os` 및 `--gc-sections` 정책으로 맞췄다. 새 archive의 Custom `66cb0d40d77fe975237d87d3c95e298a9b3bd63bb987bae34c9aa5609887932a`, ISO-TP `d63862926aa56761ae0f8d8087b06f73cc2b7ffe381ad260b5f8b29c5de9cf80`, 0xFF padded 65,536 B application `1badd29c53120916c2f2b0f2e773c6af953960bedeb1c199b66021096b9870e1`는 `experiments/ksma-2026/p03-f407-500k-prep-20261007/`에 있다. exact hash별 program/verify 허가는 아직 받지 않았다.

후속 gate:

- P03 재개: 사용자 장비/허가를 확인한 뒤 F407 Custom `-Os` / ISO-TP `-O0` 불일치 해소 정책, 주소 상한 불일치 검토, 새 binary/hash 및 64 KiB padded application 고정 후 hardware smoke.
- F407 hw_def의 end=0x08080000과 max=960 KiB/app linker=960 KiB가 불일치한다. 정상 64 KiB 적합성만 점검했으며 비정상·큰 image 안전성은 검증하지 않았다.
- F103은 현재 Custom 5 ms pacing과 ISO-TP STmin 기반 pacing도 다르다. 과거 CSV와 현재 sender를 동일시하지 않는다.

## 사용자가 준비할 것

- 공식 행사 공지 URL/양식 파일, 일반/학부경진대회 트랙, 저자 순서·소속·교신저자, 정확한 마감/분량/발표 형식.
- F407 모델/board ID, 현재 기록 image와 보존 필요 여부, ST-LINK 및 복구 방법.
- BBB 접속 주소·계정(비밀번호를 문서에 넣지 않음), OS/kernel, can0, CAN transceiver/배선/종단 정보.
- 위 장비와 대상별 flashing 허가는 P03 재개 전에 필요하다. P01의 host 검증은 장비 없이 진행 가능하다.
- 실제 program/erase 허가는 대상·binary/hash/address를 확인한 뒤 P03에서 별도로 받는다.

실행 중인 프로세스: **없음**. P03은 CSV/run을 만들지 않았다. 다음 run은 새 ID를 사용하고 기존 archive를 덮어쓰지 않는다. P01 evidence는 `reports/artifacts/P01-20261005/build.log`, `manifest.json`이며 source SHA-256로 dirty sender를 특정한다.

## 다음 대화 시작 prompt

```text
C:\repos\CanBootloader-paper의 paper/ksma-2026에서 진행해줘.
AGENTS.md와 docs/paper-plan/README.md, SESSION_HANDOFF.md,
tasks.md의 P04, codex-session-guide.md, reports/P00.md~P05.md를 읽어라.
이번 대화에서는 P04 terminal-frame probe 보정 Custom 재실험만 수행해줘. 먼저 git status, HEAD,
submodule 상태를 확인하고 기존 미커밋 수정, 예비 CSV, 원본 P04 raw artifact를 보존해줘.
BBB SSH/can0/current firmware·bootloader hash와 새 run directory 부재를 읽기 전용으로 확인한 뒤,
새 sender/config를 복사하고 `custom-120-terminal-probe-v1` 120회를 실행해 raw CSV/JSONL/manifest를 보존해줘.
원본 Custom/ISO-TP run을 덮어쓰거나 결과를 혼합하지 마. 연결 불가면 hardware 실행을 NOT RUN으로 기록하고
P04 report·README·SESSION_HANDOFF를 갱신해줘. F103, main TW-03, 외부 제출·연락은 하지 마.
```

</details>

</details>
