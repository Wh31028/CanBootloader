# CAN-FOTA 면접 질문 은행

## 사용 방법

이 파일은 질문과 실제 답변 노트의 인덱스입니다. 상세 답변을 이 파일에 중복 작성하지 않습니다.

- Task 구현 전: 예정 질문을 확인
- Task 구현 후: `<TASK_ID>.md`를 작성하고 note link 연결
- Codex 검증 후: `DRAFT` 또는 `VERIFIED`
- 사용자 직접 연습 후: `REHEARSED` 또는 `WEAK`

## 1차 2주 질문

| ID | Task | 질문 | Note | 상태 |
| --- | --- | --- | --- | --- |
| Q-TW00-01 | TW-00 | 전체 FOTA 경로와 각 component의 책임을 설명할 수 있는가? | 생성 예정 | TODO |
| Q-TW00-02 | TW-00 | 현재 target이 F407이 아니라 F103이라고 판단한 근거는 무엇인가? | 생성 예정 | TODO |
| Q-TW00-03 | TW-00 | 과거 direct-write benchmark와 현재 staging 구조를 왜 분리해야 하는가? | 생성 예정 | TODO |
| Q-TW01-01 | TW-01 | Bootloader protocol에 명시적 state machine이 필요한 이유는 무엇인가? | 생성 예정 | TODO |
| Q-TW01-02 | TW-01 | Invalid size와 잘못된 DLC가 어떤 flash 위험으로 이어질 수 있는가? | 생성 예정 | TODO |
| Q-TW01-03 | TW-01 | Duplicate와 out-of-order DATA를 어떤 정책으로 처리했는가? | 생성 예정 | TODO |
| Q-TW02-01 | TW-02 | Flash erase 단위와 program alignment가 copy 설계에 미치는 영향은 무엇인가? | 생성 예정 | TODO |
| Q-TW02-02 | TW-02 | Initial MSP, Reset Handler, Thumb bit를 왜 검증해야 하는가? | 생성 예정 | TODO |
| Q-TW02-03 | TW-02 | Vector-last copy는 true A/B나 atomic update와 어떻게 다른가? | 생성 예정 | TODO |
| Q-TW03-01 | TW-03 | SocketCAN `write()` 성공이 ECU 수신 성공을 보장하지 않는 이유는 무엇인가? | 생성 예정 | TODO |
| Q-TW03-02 | TW-03 | `ENOBUFS`, response timeout, target error를 왜 구분해야 하는가? | 생성 예정 | TODO |
| Q-TW03-03 | TW-03 | CAN error active/passive/bus-off와 recovery 정책을 설명할 수 있는가? | 생성 예정 | TODO |
| Q-TW04-01 | TW-04 | ISO-TP FF, CF, FC, BS, STmin의 역할은 무엇인가? | 생성 예정 | TODO |
| Q-TW04-02 | TW-04 | 현재 ISO-TP retry를 “표준 Go-Back-N”이라고 부르기 어려운 이유는 무엇인가? | 생성 예정 | TODO |
| Q-TW04-03 | TW-04 | Custom과 ISO-TP의 flash backend가 다르면 성능 비교에 어떤 bias가 생기는가? | 생성 예정 | TODO |
| Q-TW05-01 | TW-05 | 어떤 fault를 실제로 검증했고 어떤 physical-layer fault는 제외했는가? | 생성 예정 | TODO |
| Q-TW05-02 | TW-05 | PASS, FAIL, NOT RUN을 어떻게 구분했고 결과 provenance를 어떻게 보존했는가? | 생성 예정 | TODO |
| Q-TW05-03 | TW-05 | 2주 개선 전후 가장 크게 달라진 신뢰성 속성은 무엇인가? | 생성 예정 | TODO |

## 후속 Task 질문

| ID | Task | 질문 | Note | 상태 |
| --- | --- | --- | --- | --- |
| Q-F1-01 | F1 | ACK loss가 host와 target의 block state를 어떻게 desynchronize하는가? | 생성 예정 | TODO |
| Q-F1-02 | F1 | Session ID, block ID, idempotent ACK가 각각 해결하는 문제는 무엇인가? | 생성 예정 | TODO |
| Q-F1-03 | F1 | Protocol v1과 v2의 호환성을 어떻게 관리했는가? | 생성 예정 | TODO |
| Q-F2-01 | F2 | Application frame omission과 실제 CAN bit error는 어떻게 다른가? | 생성 예정 | TODO |
| Q-F2-02 | F2 | Random seed와 paired experiment가 공정성에 필요한 이유는 무엇인가? | 생성 예정 | TODO |
| Q-F2-03 | F2 | 평균 외에 success rate와 p95가 필요한 이유는 무엇인가? | 생성 예정 | TODO |
| Q-F3-01 | F3 | Transactional metadata가 power-loss recovery를 어떻게 결정적으로 만드는가? | 생성 예정 | TODO |
| Q-F3-02 | F3 | Checkpoint reset과 실제 brownout test의 차이는 무엇인가? | 생성 예정 | TODO |
| Q-F3-03 | F3 | Recovery와 rollback은 어떻게 다른가? | 생성 예정 | TODO |
| Q-F4-01 | F4 | Yocto recipe와 image configuration에서 이 application이 어떻게 통합되는가? | 생성 예정 | TODO |
| Q-F4-02 | F4 | systemd dependency와 `network-online.target`이 왜 필요한가? | 생성 예정 | TODO |
| Q-F4-03 | F4 | 두 repository의 BBB source drift를 어떻게 방지했는가? | 생성 예정 | TODO |
| Q-F5-01 | F5 | HAL 의존 code에서 pure protocol logic을 분리하면 무엇을 test할 수 있는가? | 생성 예정 | TODO |
| Q-F5-02 | F5 | Unit test, fault injection, fuzzing의 목적은 어떻게 다른가? | 생성 예정 | TODO |
| Q-F6-01 | F6 | CRC32, SHA-256, digital signature가 각각 보장하는 것은 무엇인가? | 생성 예정 | TODO |
| Q-F6-02 | F6 | Signature verification만으로 secure boot가 완성되지 않는 이유는 무엇인가? | 생성 예정 | TODO |

## 공통 프로젝트 질문

| ID | 질문 | 연결할 최종 노트 | 상태 |
| --- | --- | --- | --- |
| Q-PROJ-01 | 이 프로젝트에서 직접 발견하고 해결한 가장 위험한 defect는 무엇인가? | TW-01/TW-02 | TODO |
| Q-PROJ-02 | Selective NACK가 ISO-TP 대비 유리한 조건과 불리한 조건은 무엇인가? | F2 | TODO |
| Q-PROJ-03 | 장비 제약 안에서 fault injection의 신뢰성을 어떻게 확보했는가? | TW-05/F2 | TODO |
| Q-PROJ-04 | 현재 구현과 실제 automotive production bootloader의 가장 큰 차이는 무엇인가? | TW-05/F3/F6 | TODO |
| Q-PROJ-05 | 다시 설계한다면 hardware와 protocol에서 무엇을 바꾸겠는가? | F3/F6 | TODO |

