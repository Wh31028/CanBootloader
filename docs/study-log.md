# CAN FOTA 학습 로그

## 기록 원칙

- 코드에서 확인한 사실에는 파일 경로와 함수·상수 등 근거를 남긴다.
- 실행 결과에는 환경, 명령, 결과, 실패 여부를 남긴다.
- 가설·외부 자료·미검증 hardware 동작은 별도 항목으로 분리한다.
- 토큰, 인증정보, 개인 경로, 사설 네트워크 정보는 기록하지 않는다.

## 현재 학습 단계

- 주차: Week 1 / 8
- 주제: 저장소 구조와 Custom CAN FOTA 기준 구현 파악
- 상태: 진행 중
- 기준 브랜치: 로컬 `main`
- 원격 최신 상태: 미확인
  - 사유: `git pull origin main`이 SSH public key 인증 실패로 완료되지 않음

## 현재 이해한 내용

| 항목 | 확인한 내용 | 근거 |
| --- | --- | --- |
| 기준 경로 | 현재 기준은 Custom CAN FOTA 경로다. | `README.md` |
| Bootloader | Custom bootloader는 `boot_can_custom_f103/`에 있다. | `README.md` |
| Application | F103 application은 `boot_can_fw_f103/`에 있다. | `README.md` |
| BBB gateway | flasher와 dashboard는 `can-fota-BBB/`에 있다. | `README.md` |
| Flash layout | Application 시작 주소는 `0x08004000`이다. | `docs/memory-map.md` |
| Staging | staging 시작 주소는 `0x08012000`이다. | `docs/memory-map.md` |
| Image limit | Custom FOTA 최대 firmware 크기는 57,336 B다. | `README.md`, `docs/protocol.md` |
| FOTA entry | CAN ID `0x200`, payload `DE AD`로 application이 bootloader 진입을 요청한다. | `docs/architecture.md`, `docs/protocol.md` |
| 비교 구현 | ISO-TP는 현재 baseline이 아닌 비교 구현이다. | `README.md` |

## 확인이 필요한 내용

| 질문 | 확인 방법 | 상태 |
| --- | --- | --- |
| 현재 원격 `origin/main`이 로컬 기준과 동일한가? | SSH 인증 복구 후 `git pull origin main` | 미확인 |
| BBB CAN Device Tree 설정은 어디서 관리되는가? | 저장소와 BBB 배포 환경을 분리하여 확인 | 미확인 |
| vcan에서 flasher 오류 흐름을 어느 범위까지 재현할 수 있는가? | vcan과 mock/simulator 실습 | 미확인 |
| 실제 보드에서 staging 복구가 재현되는가? | STM32F103/BBB hardware test | 미확인 |

## 다음 할 일

- [ ] `docs/architecture.md`와 application/bootloader source를 따라 Week 1 boot 흐름 정리
- [ ] `docs/memory-map.md`와 linker script로 Flash map 검증
- [ ] SSH 인증 복구 후 원격 `main` 최신 상태 확인
- [ ] BBB Device Tree 관련 파일 또는 배포 저장소의 위치 확인

---

## 주차별 기록 템플릿

### Week __ — 주제

- 상태: `시작 전 | 진행 중 | 완료 | 보류`
- 학습일:
- 목표:

#### 코드에서 확인한 사실

| 항목 | 내용 | 근거 파일/위치 |
| --- | --- | --- |
|  |  |  |

#### 실행으로 확인한 결과

| 환경 | 수행 내용 | 결과 | 증거 위치 |
| --- | --- | --- | --- |
|  |  |  |  |

#### 확인이 필요한 내용

| 질문 | 현재 가설 또는 배경 | 확인 방법 | 상태 |
| --- | --- | --- | --- |
|  |  |  | 미확인 |

#### 장애·한계·리스크

- 

#### 다음 할 일

- [ ] 

#### 포트폴리오 반영 메모

- README에 반영할 설명:
- 다이어그램 또는 CAN trace로 보강할 부분:
- 면접 질문 후보:
- 공개 전 비식별화·제거할 정보:
