# CAN 기반 펌웨어 업데이트를 위한 비트맵 선택 재전송 기법의 구현 및 성능 평가

상태: P08 문서·근거 검토본, 2026-10-10 (`p08-doc-review-v1`). P05 유효 240회 수치 유지. 공식 1페이지 양식 미적용, 저자 정보 미확정, PDF 페이지 검증 NOT RUN, 제출본 아님.

저자: [저자 순서·국문/영문 성명 미확정]
소속: [소속·학과 미확정]
교신저자: [성명·이메일 미확정]
제출 트랙: [일반 학술대회 / 학부논문경진대회 미확정]

## 요약문 초안

CAN 기반 펌웨어 업데이트에서 송신 데이터가 누락되었을 때 재전송 단위는 전송 시간과 재전송량에 영향을 줄 수 있다. 본 연구는 BeagleBone Black 송신단과 STM32 수신단으로 구성된 direct-write 업데이트에서, 수신 비트맵으로 누락 프레임을 식별하는 Custom 방식과 ISO-TP transport 위에 구현한 application block 재시도 방식의 차이를 평가하고자 한다. 비교 대상은 본 프로젝트의 두 구현이며 ISO-TP 표준 전체의 우열을 평가하지 않는다.

주 실험은 STM32F407의 같은 보드와 500 kbit/s CAN에서 수행했다. 두 방식은 같은 65,536-byte application image(SHA-256 `1badd29c…9870e1`)와 Flash 범위 `[0x08010000,0x08020000)`, sector 4 erase를 사용했다. 송신단에서 Custom DATA와 ISO-TP CF의 소프트웨어 누락을 주입했고 ISO-TP FF와 제어·응답 프레임은 제외했다. 이는 물리 계층 bit error rate를 재현하지 않는다. 누락 확률 0, 0.0001, 0.0005, 0.001(0, 0.01, 0.05, 0.1%)마다 각 방식 30회로 구성된 유효 240회를 분석했다. 두 방식은 서로 다른 seed·송신단 revision과 별도 batch로 실행되어 같은 누락 위치의 짝비교가 아니다.

의도한 측정 구간은 START 송신 직전부터 유효 END ACK 수신 직후까지이나, 실제 monotonic `elapsed_sec`는 protocol 호출 직전부터 JUMP 송신 호출 뒤까지다. erase/write/CRC와 호스트 처리·대기, END ACK 뒤 처리도 포함한 원시 시간을 그대로 사용했다. 다운로드, entry 뒤 3.0 s 대기와 실제 부팅 확인은 제외되며 이 경로에는 JUMP 전 0.5 s 대기가 없다. 추가 시간을 소급 분리하거나 차감하지 않았다. 모든 시도의 성공·실패·중단을 기록하고 성공률, 성공 조건부 시간과 재전송량을 함께 분석한다. 유효 240건의 `OK`는 END ACK/CRC 확인과 JUMP 송신 호출 성공을 포함하나, 부팅 필드는 모두 `JUMP_SENT_NOT_VERIFIED`이므로 개별 application 기동 성공을 뜻하지 않는다.

결과: RAW_ISO-TP와 terminal-frame probe 보정 Custom은 각각 120/120 성공했다. RAW_ISO-TP의 성공 조건부 평균 raw elapsed는 loss 0%에서 18.193 s(95% Student-t CI 18.148–18.238), 0.1%에서 26.448 s(25.276–27.620)였고, Custom은 네 조건에서 9.484–9.617 s였다(각 n=30). 0.1% 조건의 재전송 overhead(모든 논리적 send attempt 분모)는 Custom 0.091%, RAW_ISO-TP 3.351%였다. 분모는 software drop을 포함한 START/DATA/END 시도이며 entry·JUMP·수신 응답은 제외한다. 보정 전 `custom-120-entry-v2`의 110 `OK`/10 `FAIL_DATA_TIMEOUT`은 별도 실패 기록으로 보존하며 유효 240회에는 합치지 않는다. 보정 Custom은 새 120회 전체 batch이며 실패 10건만 대체한 자료가 아니다.

결론: 이 direct-write 구현과 software omission 조건에서 보정 Custom의 성공 조건부 시간이 더 짧고 재전송 overhead가 작게 관측됐다. 유효 데이터는 양 방식 모두 120/120 성공했으며 timeout 10건은 보정 전 별도 batch의 이력이다. 누락 대상·실행 순서·seed의 차이와 JUMP 송신을 포함한 시간 경계 때문에 일반 신뢰성 향상이나 ISO-TP 전체에 대한 우위로 확대하지 않는다.

핵심어: CAN, 펌웨어 업데이트, 선택 재전송, 비트맵, ISO-TP

## 작성 메모

- 질문: software DATA omission 조건에서 선택 재전송과 256-byte application block 재시도의 시간·재전송량이 어떻게 다른가?
- 비교의 의미: 특정 direct-write 구현의 조건부 평가. staging, rollback, 서명, 전원 차단 복구, 다중 ECU 보장은 주장하지 않는다.
- 기존 CSV는 예비자료이며 위 결과에 전용하지 않는다. 0.5초 일괄 차감 금지.
- 유효 입력은 `isotp-120-entry-v1`과 `custom-120-terminal-probe-v1`뿐이다. 수치·그림 기준은 P05 `p05-terminal-probe-v1-20261009`의 [summary CSV](../../experiments/ksma-2026/analysis/p05-terminal-probe-v1-20261009/p05-summary-by-protocol-loss.csv), [시간 SVG](../../experiments/ksma-2026/analysis/p05-terminal-probe-v1-20261009/p05-success-time.svg), [overhead SVG](../../experiments/ksma-2026/analysis/p05-terminal-probe-v1-20261009/p05-retransmit-overhead.svg)다. 검토·checksum·잔여 조건은 [P08 보고](../paper-plan/reports/P08.md)에 기록한다.
- 선행 배경과 인용 후보: [references.md](references.md). 상세 방법과 미확정 항목: [manuscript.md](manuscript.md).
- 공식 양식·저자·제출 트랙·페이지 계산·마감 시각을 사용자와 확인한 뒤 양식을 적용한다. Markdown만으로 1페이지 준수를 판정하지 않는다.
