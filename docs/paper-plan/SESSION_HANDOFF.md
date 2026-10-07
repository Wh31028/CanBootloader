# 논문 작업 인수인계

최종 갱신: 2026-10-07. 다음 대화는 이 파일을 먼저 읽는다.

## 현재 상태

- 폴더/branch: C:/repos/CanBootloader-paper / paper/ksma-2026
- HEAD: f0c6257568f0624557b38f8a1aade66322b0e80b (P03 Custom checkpoint; 이번 종료 문서/evidence 갱신은 미커밋)
- 마지막 완료: **P03 DONE** — F407 Custom/ISO-TP hardware smoke와 측정 대조
- 진행 중 Task: 없음
- 다음 실행 Task: **P04만**
- 주 실험 후보: F407. 실제 board boot/smoke는 NOT RUN이며 P03에서 확정.
- F103: Custom/app PASS, ISO-TP는 Flash 17,224 bytes 초과로 FAIL. 보충 P07 선택 시 처리.
- 두 ISO-TP submodule: 5593428d95af10dde1e565cebcda16089fc74857로 초기화, 원형 유지.
- 원고: docs/paper/abstract.md, manuscript.md, references.md 생성. 모든 결과 [결과 미확정].
- 초기 설정: docs/paper/experiment-config.draft.json (실행 불가 초안).
- hardware/본 실험/제출: P03 hardware smoke는 완료, P04 본 실험·제출은 미실행. 공식 양식·저자·트랙 미확정.
- commit/push/merge/reset/외부 제출·연락: P03 Custom checkpoint commit은 존재하지만 push/merge/외부 제출·연락은 미실행.
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

다음 대화는 P03만: 먼저 status/HEAD/submodule 및 미커밋 변경을 보존하고, ISO-TP 실행 전 최종 ISO artifact hash와 `0x08000000` sector 0--2 erase/program/verify의 새 명시 허가를 받는다. ISO-TP smoke/trace와 이후 남은 P03 조건을 실행하되 P04를 시작하지 않는다.

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
tasks.md의 P03, codex-session-guide.md, reports/P00.md~P03.md를 읽어라.
이번 대화에서는 IN_PROGRESS인 P03만 재개해줘. 먼저 git status, HEAD, submodule 상태를 확인하고
기존 미커밋 수정과 P00~P03 evidence 및 예비 CSV를 보존해줘.
사용자가 제공한 F407 board 모델/ID·현재 image·복구 수단, BBB 접속/OS/kernel/can0 상태,
CAN 배선·종단, ST-LINK, exact binary/hash/address/erase 범위별 flashing 허가를 대조해줘.
누락되거나 허가되지 않은 항목이 있으면 hardware를 실행하지 말고 P03 BLOCKED를 유지해줘.
모두 충족될 때만 새 run ID에 artifact를 고정하고 제한된 hardware smoke와 측정 대조를 수행해줘.
F103, main TW-03, P04의 240회 실험은 시작하지 마. 종료 전에 P03 report, README 상태,
SESSION_HANDOFF를 갱신하고 commit/push, 외부 제출·연락은 하지 마.
```
