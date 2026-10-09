# CAN 기반 펌웨어 업데이트를 위한 비트맵 선택 재전송 기법의 구현 및 성능 평가

상태: P05 내용 초안, 2026-10-09. terminal-frame probe 보정 Custom 120회 반영. 공식 1페이지 양식 미적용, 저자 정보 미확정, 제출본 아님.

저자: [저자 순서·국문/영문 성명 미확정]
소속: [소속·학과 미확정]
교신저자: [성명·이메일 미확정]
제출 트랙: [일반 학술대회 / 학부논문경진대회 미확정]

## 요약문 초안

CAN 기반 펌웨어 업데이트에서 송신 데이터가 누락되었을 때 재전송 단위는 전송 시간과 재전송량에 영향을 줄 수 있다. 본 연구는 BeagleBone Black 송신단과 STM32 수신단으로 구성된 direct-write 업데이트에서, 수신 비트맵으로 누락 프레임을 식별하는 Custom 방식과 ISO-TP transport 위에 구현한 application block 재시도 방식의 차이를 평가하고자 한다. 비교 대상은 본 프로젝트의 두 구현이며 ISO-TP 표준 전체의 우열을 평가하지 않는다.

주 실험은 STM32F407의 같은 보드와 500 kbit/s CAN에서 수행했다. 두 방식은 같은 65,536-byte application image(SHA-256 `1badd29c…9870e1`)와 Flash 범위 `[0x08010000,0x08020000)`를 사용했다. 송신단에서 DATA 운반 프레임의 소프트웨어 누락을 주입하며 물리 계층 bit error rate를 재현한다고 해석하지 않는다. 누락 확률 0, 0.0001, 0.0005, 0.001마다 각 방식 30회, 총 240회 시도했다.

측정 구간은 monotonic clock 기준 START 송신 직전부터 유효한 END ACK 수신 직후까지이며 erase/write/CRC를 포함한다. 모든 시도의 성공·실패·중단을 기록하고, 성공률과 성공 조건부 전송 시간, 재전송량을 함께 분석한다. application 기동 확인은 transaction 성공과 별도로 기록한다.

결과: RAW_ISO-TP와 terminal-frame probe 보정 Custom은 각각 120/120 성공했다. RAW_ISO-TP의 성공 조건부 시간은 loss 0%에서 18.193 s(95% CI 18.148–18.238), 0.1%에서 26.448 s(25.276–27.620)였고, Custom은 9.484–9.617 s였다. 0.1% 조건의 재전송 overhead(모든 send attempt 분모)는 Custom 0.091%, RAW_ISO-TP 3.351%였다. 보정 전 Custom 10 `FAIL_DATA_TIMEOUT`은 별도 실패 artifact로 보존하며 유효 240 trial에는 합치지 않는다.

결론: 이 direct-write 구현과 software omission 조건에서는 Custom의 성공한 transaction 시간이 더 짧고 재전송 overhead가 작게 관측됐지만, loss 조건의 timeout 실패도 함께 발생했다. 따라서 성공 시간만으로 신뢰성 또는 ISO-TP 전체에 대한 우위를 주장하지 않는다.

핵심어: CAN, 펌웨어 업데이트, 선택 재전송, 비트맵, ISO-TP

## 작성 메모

- 질문: software DATA omission 조건에서 선택 재전송과 256-byte application block 재시도의 시간·재전송량이 어떻게 다른가?
- 비교의 의미: 특정 direct-write 구현의 조건부 평가. staging, rollback, 서명, 전원 차단 복구, 다중 ECU 보장은 주장하지 않는다.
- 기존 CSV는 예비자료이며 위 결과에 전용하지 않는다. 0.5초 일괄 차감 금지.
- 선행 배경과 인용 후보: [references.md](references.md). 상세 방법과 미확정 항목: [manuscript.md](manuscript.md).
- 공식 양식·저자·제출 트랙·페이지 계산·마감 시각을 사용자와 확인한 뒤 양식을 적용한다. Markdown만으로 1페이지 준수를 판정하지 않는다.
