# Task별 범위와 완료 조건

상태의 단일 기준은 [README](README.md)의 표다. 다음 세션은 [SESSION_HANDOFF](SESSION_HANDOFF.md)의 지시를 따른다. 한 대화에서는 지정한 Task만 수행하며, 세션이 길어지면 미완료 Task를 그대로 다음 대화로 넘긴다.

## P00 — Baseline과 집필 준비

목표: 실제 실행 가능한 비교 환경과 제출 범위를 정하고 원고의 빈 골격을 만든다.

수행:

1. branch/HEAD/dirty 상태와 기존 CSV/script 관계를 기록한다. 기존 데이터는 수정하지 않는다.
2. F407/F103의 CMake preset, linker, Flash erase/write 경계, target protocol과 대응 Python sender를 읽는다. uninitialized submodule은 `.gitmodules`와 gitlink를 확인한 후 기록된 revision으로 초기화한다.
3. F407 Custom/ISO-TP/application의 재현 가능한 build를 시도하고 command, toolchain, map, size, binary hash를 기록한다. F103도 가능한 범위에서 build 문제를 확인하되, 주 실험을 막는 장기 F103 refactoring은 하지 않는다.
4. 후보 F407의 application 주소/erase 범위와 64 KiB image 적합성을 확인한다. F103의 16 KiB bootloader/64 KiB direct-write 조건을 main staging과 구별한다.
5. BBB 접속, CAN interface, 배선/종단, board 식별, ST-LINK 사용 가능 여부를 확인한다. 실제 flashing/FOTA는 P03으로 분리한다.
6. 공식 제출 양식, 제출 트랙, 저자·소속, deadline을 확인한다. 미제공 저자 정보와 미확보 양식은 TODO로 남기고 내용을 추정하지 않는다.
7. `docs/paper/abstract.md`, `manuscript.md`, `references.md`에 가제, 연구 질문, 구조, 실험 방법 골격을 작성한다. 재실험 결과는 `[결과 미확정]`으로 표시한다. 관련 연구는 실제 원문/공식 문서를 읽고 출처를 남긴다.

산출물: `reports/P00.md`, 원고 골격 3개, 초기 실험 설정안.

완료 조건:

- 주 실험 후보 한 보드의 두 bootloader와 application build가 실제 PASS이며 주소/크기 근거가 있다.
- 주입 모델, 측정 범위와 비교 대상을 원고 골격에 명시했다.
- hardware 접속/양식/저자 등 남은 외부 입력을 정리했다. 양식 미확보는 코드 수정 시작을 막지 않지만 제출 준비 완료는 아니다.
- build blocker가 해결되지 않으면 P00을 IN_PROGRESS/BLOCKED로 유지하고 가능한 최소 build 수정을 같은 Task의 후속 세션으로 수행한다.

## P01 — 시간 측정과 frame 집계

목표: 두 sender의 시간·count를 같은 정의로 기록한다.

수행:

- 주 MCU의 `loss_test_custom*.py`, `loss_test_isotp_raw*.py`를 최소 수정한다. 이번 코드 기준과 과거 CSV의 실제 생성 코드는 동일하다고 단정하지 않는다.
- monotonic clock으로 START 직전부터 검증된 END ACK까지 측정한다. download, entry 대기, JUMP 대기는 별도 phase로 분리한다.
- `send_attempts`, `software_drops`, `socket_send_success`, `send_errors`, `protocol_rx`, `retransmit_attempts`, `retransmit_send_success`를 명확히 정의한다. 부분/시스템 오류와 ENOBUFS 재시도를 중복 계수하지 않도록 규칙을 남긴다.
- 재전송 overhead의 분모를 명시한다. SocketCAN 송신 성공을 controller의 실제 on-wire 완료/자동 재전송 횟수로 부르지 않는다.
- ACK/NACK/ERR의 DLC, ID, EFF/RTR/ERR flag를 검증한다. ISO-TP SF/FC는 길이, 상태, BS/STmin을 검증하고 receiver 조건을 준수한다.
- 256-byte application chunk와 FC의 BS를 구분한다. 타이머 이름을 근거 없이 OEM 권장 N_Cr이라고 쓰지 않는다.
- 코드 변경과 metrics 정의를 `reports/P01.md`에 기록한다.

완료 조건:

- mock clock/socket 또는 작은 host 검증으로 양쪽 측정 종료 시점과 drop/실제 송신 count 차이를 확인했다.
- malformed ACK/NACK/FC를 성공으로 처리하지 않음을 확인했다.
- 실행한 검증 명령/결과가 있다. hardware trace 대조는 P03 예정이며 아직 PASS로 쓰지 않는다.

## P02 — Loss, retry, 실패 기록과 실행 runner

목표: 재현 가능한 시도 단위와 유한한 실행 시간을 확보한다.

수행:

- software 누락의 eligible frame 집합, payload offset mapping, retransmission 적용 여부를 명세한다. 가능하면 두 방식의 DATA 운반 frame(FF 포함 여부를 명시)을 대칭적으로 취급한다. 기존 CF-only 모델을 유지하면 비대칭과 그 영향을 명시한다.
- seed, 모델 version, 실제 drop 수/위치를 기록한다. 원본 DATA와 retransmission의 frame 수가 다르므로 seed 동일을 fault schedule 동일이라고 쓰지 않는다.
- ENOBUFS, response timeout, 반복 NACK, FC WAIT 등에 유한한 deadline을 둔다. block/전체 transaction 한도와 동일한 비교 정책을 기록한다. 무손실 pilot 결과를 보고 전체 한도를 고정하고 본 실험 중 유리한 방식에만 바꾸지 않는다.
- START/DATA/END/JUMP send failure, timeout, CRC error, target error, interrupt/runner kill 등 가능한 모든 종료를 기록한다. runner는 시작한 trial manifest와 exit status를 남겨 결과 행이 없는 crash도 시도로 집계한다.
- `transaction_status`와 `boot_status`를 구분한다. END ACK 성공은 application 정상 기동 성공과 같지 않다.
- 각 trial ID에 command/config/seed/firmware hash/bootloader hash/host source fingerprint를 연결한다. 미커밋 코드도 재구성 가능한 diff와 파일 hash를 보존한다.
- planned trial 순서와 실패 처리 기준을 config로 저장하고, unique run-set 경로에 새 결과를 쓴다. 재실행은 새로운 attempt ID와 사유를 남긴다.
- crash 후 resume은 이미 기록한 trial을 덮어쓰지 않는다. runner가 protocol 간 bootloader 교체가 필요한 시점을 명시하도록 한다.

완료 조건:

- 정상 종료, ENOBUFS 지속, 무응답, CRC 실패, 중단을 mock/host 검증으로 기록하고 유한 종료를 확인했다.
- 같은 seed/config 재실행에서 정의한 범위의 주입 결정이 재현된다.
- 모든 계획된 시도와 누락된 결과를 대조할 manifest가 있다.
- raw CSV/JSONL schema, status, overhead 분모, runner 명령이 report에 있다.

## P03 — Hardware smoke와 측정 대조

목표: 본 실험 전에 build한 binary와 실제 보드 동작, 측정 정의를 연결한다.

수행:

1. 사용할 board/Flash 주소/binary hash/복구 수단을 사용자와 확인하고 허가된 대상에만 program/verify한다. OS/BBB 설정과 CAN bitrate도 기록한다.
2. 양쪽 동일 64 KiB image로 loss 0%, 각 5회 수행한다. 알려진 정상 app image에 padding할 경우 원본/padded hash와 padding 방법을 모두 기록한다.
3. `candump`와 sender phase/counter를 대조한다. `can0` 재설정으로 capture가 끊기면 시험 순서를 고치고 trace gap을 성공 trace로 취급하지 않는다.
4. 통제된 한 frame 누락과 timeout/failure를 확인하고, 잘못된 성공 처리나 block desynchronization이 있으면 P01/P02 또는 최소 target 수정을 위해 현재 Task에 근거를 남긴다.
5. ISO-TP BS/STmin, 실제 CAN ID type, 실제 binary가 manifest와 일치하는지 확인한다.

완료 조건:

- 정상 smoke 각 5회 결과와 frame trace 표본이 있으며 시간 측정/계수 정의가 검증됐다.
- DATA loss 복구 및 timeout 종료의 실제 결과가 있다.
- application 기동 확인 방법/관측 결과를 transaction 성공과 구분했다.
- unresolved 측정 결함이 없고 P04 config를 고정했다.

hardware가 없으면 NOT RUN으로 남긴다. 이 경우 P04를 시작하지 않는다. 독립적인 원고 배경 정리는 계속 가능하다.

## P04 — 주 실험 240회

목표: 주 MCU에서 고정된 조건의 모든 시도를 수집한다.

- README의 2 × 4 × 30 matrix를 실행한다. smoke 결과와 본 실험을 별도 dataset으로 둔다.
- protocol 교차 또는 작은 균형 batch로 실행하고 순서/교체/재시작을 기록한다.
- 임의 실패 삭제/성공 대체를 하지 않는다. 불가피한 실행 오류의 제외 여부는 사전 기준과 원본 기록을 함께 남긴다.
- 최소한 각 protocol/loss 조건의 trace 표본과 모든 trial의 raw 결과, manifest, stdout/stderr를 보존한다.
- 코드/config가 중간에 바뀌면 별도 run-set으로 분리한다. 서로 다른 조건을 같은 모집단처럼 합치지 않는다.

산출물: `experiments/ksma-2026/<run-set-id>/`, `reports/P04.md`.

완료 조건: 240개 계획 시도 각각의 결과/실패/중단이 manifest와 대응하고 누락이 설명되어 있다. 240개 OK를 요구하는 것이 아니다. 시험이 일부만 실행됐으면 IN_PROGRESS다.

## P05 — 분석과 요약문

목표: 원시 데이터로 재생성 가능한 표·그림과 검증된 1페이지 요약문을 만든다.

- schema, 중복 trial ID, 누락 status, hash/config 혼합을 검사한다.
- protocol/loss별 시도 수, 성공 수, 실패 유형과 성공률을 보고한다. timeout 시간을 임의 성공 시간으로 바꾸지 않는다.
- 성공한 transaction 시간의 평균·표준편차·95% CI와 표본 수를 제시한다. CI 계산 방법과 가정을 적고, 다른 seed/host 환경까지 보장하는 구간으로 해석하지 않는다. 성공 조건부 시간과 실패율을 함께 표시한다.
- 재전송량과 overhead는 같은 분모로 계산한다. 통계 script로 모든 표/그림을 재생성한다.
- 개선율은 `(기준 방식 - 제안 방식) / 기준 방식` 등 분모를 명시한다. “ISO-TP가 X% 길다”와 “Custom이 X% 짧다”를 혼용하지 않는다.
- 결과가 가설을 지지하지 않아도 관측값을 그대로 서술한다. physical loss/차량 환경/ISO-TP 전체로 일반화하지 않는다.
- 공식 양식에 맞춰 요약문을 작성하고 미확정 저자/수치 placeholder를 표시한다. 사용자와 교수님의 검토가 남았으면 제출용 확정본이라고 부르지 않는다.

완료 조건: 수치마다 raw data/분석 명령으로 추적 가능하고, 요약문 초안에 근거 없는 성능 주장이 없다. 양식 미확보 시 내용 초안만 완료이며 양식 적용은 handoff의 제출 blocker다.

## P06 — 전문 초안

목표: 심사 통보 전에 2~3페이지 전문을 준비한다.

- 서론/관련 연구, 시스템·복구 방식, 실험 방법/결과, 결론·한계로 구성한다.
- 시스템 또는 sequence 그림 1개, 실험 조건표, 시간/재전송량 그래프를 우선한다.
- 표준 transport와 프로젝트의 application retry를 구분하고 검토한 원문을 인용한다.
- 서술/그림/요약문이 같은 dataset/config를 참조하는지 확인한다.
- 공식 양식과 페이지 수는 실제 export한 PDF 등으로 확인한다. Markdown 분량만 보고 페이지 검증 PASS로 쓰지 않는다.
- 원고와 질문 목록을 사용자에게 전달한다. 지도교수/학회에 자동 발송하지 않는다.

완료 조건: 핵심 본문과 수치/인용이 연결된 전문 초안이 있고, 양식/저자/교수 검토 등 외부 잔여 항목이 명시되어 있다.

## P07 — 보충 실험 (선택)

목표: 제출 핵심 결과를 확보한 뒤 필요할 때만 두 번째 MCU 또는 크기 확장을 평가한다.

- F407이 주 대상이면 F103의 build/link 문제를 먼저 해결한다. main staging과 혼용하지 않는다.
- F103에서는 같은 64 KiB, 보드 내 두 protocol을 비교하고 기존 주 dataset과 분리한다.
- 둘 다 정상 baseline이 확보된 경우 동일 240회 matrix를 후보로 삼는다. 시간 부족이면 0%/0.1% 등 사전에 정한 축소 조건과 표본 수를 명시한다.
- F407의 128/256/512 KiB 확장은 두 번째 MCU와 동시에 필수로 만들지 않는다.
- 서로 다른 bitrate/clock의 절대 시간 차이를 MCU 효과라고 단정하지 않는다.

선택하지 않으면 DEFERRED와 사유를 기록하고 P08로 진행한다. 필수 실험의 미완료를 선택 과제로 바꾸지 않는다.

## P08 — 최종 검토와 제출 인수인계

- P00~P06의 주장/데이터/인용/파일 경로를 점검한다. 사용한 경우에만 P07을 포함한다.
- 제목·요약문과 전문의 범위가 같은지, 과거 CSV와 재실험 결과가 구분됐는지 확인한다.
- 저자·소속·교신저자·제출 트랙·페이지 수·PDF 글꼴/그림 가독성을 확인한다.
- 채택 후 심사 의견을 반영하고 변경 내역을 남긴다. 미채택/미통보를 채택으로 기록하지 않는다.
- 원고 버전과 checksum, dataset/분석 재현 명령, 발표 핵심 3개를 정리한다.
- 사용자가 직접 제출/등록한다. 제출 확인을 받기 전 상태는 “최종 원고 준비”이며 “제출 완료”가 아니다.
- 종료 후 main TW-03 재개 항목과 졸업논문 확장 후보를 기록한다.

완료 조건: 최종 원고 검토와 재현 자료 인수인계가 끝났다. 외부 제출 상태는 별도 필드로 관리한다.
