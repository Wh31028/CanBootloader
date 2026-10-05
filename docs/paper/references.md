# 관련 배경·출처 확인 기록

열람일: 2026-10-05. P00 배경 골격용이다. 아래 요약은 실제 열람한 부분에 한정하며 관련 연구 조사를 완료했다는 뜻이 아니다.

| ID | 서지/직접 출처 | 열람 범위와 활용 | 한계 |
| --- | --- | --- | --- |
| R1 | Linux Kernel documentation, [ISO 15765-2 (ISO-TP)](https://docs.kernel.org/networking/iso15765-2.html) | Overview, frame types, socket API, Flow Control options: SF/FF/CF/FC, BS/STmin 개념 | 공식 Linux 구현 문서이며 ISO 표준 원문 자체가 아님. 프로젝트 Python은 CAN_RAW이므로 kernel CAN_ISOTP의 시험 결과로 쓰지 않음 |
| R2 | M. Mathis, J. Mahdavi, S. Floyd, A. Romanow, [TCP Selective Acknowledgment Options, RFC 2018](https://www.rfc-editor.org/rfc/rfc2018.html), Oct. 1996 | Abstract, §1, §3, §5: 수신 구간 보고와 선택 재전송 배경 | TCP 연구를 CAN의 성능 근거로 대체하지 않음. 이 구현의 bitmap wire format과 같다고 하지 않음 |
| R3 | lishen2/isotp-c, [고정 revision 5593428d95af10dde1e565cebcda16089fc74857](https://github.com/lishen2/isotp-c/tree/5593428d95af10dde1e565cebcda16089fc74857) | 로컬 checkout의 isotp_config.h 및 isotp.c 열람. BS=8, STmin=0, response timeout=100 ms | peer-reviewed 선행연구가 아닌 실제 비교 구현의 의존성. submodule 원형 보존 |
| R4 | 본 저장소 capston-1 기준 7527bca60a46c6e244214d56114109414388a3ae 및 [P00 보고](../paper-plan/reports/P00.md) | target, sender, linker, compile_commands, binary와 map | 기존 CSV 생성 당시 정확한 dirty source/binary를 복원했다고 단정하지 않음 |

R1에 언급된 ISO 15765-2:2024 전문은 확보·열람하지 않았다. 따라서 표준의 특정 조항이나 적합성 인증을 주장하지 않는다. 학회용 논문에서 필요할 CAN FOTA/선택 재전송 관련 직접 선행연구 추가 조사는 후속 집필의 TODO이다.

## 제출 조건 확인

[KSMA 공식 홈페이지](https://www.ksma.or.kr/) 검색 결과에서 한국제조데이터인공지능학회와 2026 추계 종합학술대회·학부논문 경진대회 안내의 존재를 확인했다. 직접 페이지 열기는 웹 도구에서 Internal Error로 실패했다. 공식 상세 공지·첨부 양식은 확보하지 못했다. 동명의 다른 KSMA 학회 양식을 사용하지 않는다.

[공식 논문집 목록](https://www.ksma.or.kr/publications/proceedings)의 검색 색인에는 2026.10월 예정이라는 표시가 있으나, 제공된 행사 공지의 11/5~7과 다르다. 이 목록의 예정 표기로 기존 일정을 바꾸지 않았다. 최신 상세 공지와 사용자의 원문 확인이 필요하다.

현재 계획의 요약문 10/16(1페이지), 심사 10/30, 최종본 11/2(2~3페이지), 행사 11/5~7은 사용자 제공 공지 기준이며 독립 공식 검증 완료가 아니다. 제출 트랙, 저자·소속·교신저자, 최종 양식, 참고문헌 포함 페이지 계산, 발표 형식, 정확한 마감 시각은 TODO이다.
