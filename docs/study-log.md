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
- 원격 최신 상태: 확인 완료
  - `origin/main` 최신 변경을 local `main`에 반영했다.
  - local `main`은 학습 문서 commit 1개만 `origin/main`보다 앞선 상태다.

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

### Week 1 메모 — Vector Table, SP, Reset Handler

STM32F103RB의 일반 Flash boot에서 bootloader는 Flash `0x08000000`에,
application은 `0x08004000`에 link된다. 두 image 모두 시작 위치에 vector table을 둔다.

```text
Bootloader vector table              Application vector table

0x08000000: Initial SP               0x08004000: Initial SP
0x08000004: Reset_Handler address    0x08004004: Reset_Handler address
0x08000008: NMI_Handler address      0x08004008: NMI_Handler address
...
```

- `Initial SP`는 application 시작 시 MSP(Main Stack Pointer)에 설정할 RAM 주소값이다.
  이 값은 stack pointer 변수의 주소가 아니라, stack의 초기 위치 자체다.
- `Reset_Handler address`는 reset 후 처음 실행할 startup 함수의 실행 주소다.
  vector table의 두 번째 32-bit 항목이므로 image 시작 주소 `+4`에 저장된다.
- Cortex-M에서는 Reset Handler 주소의 bit 0이 Thumb state를 나타낸다.
  예를 들어 `0x080045A1`에서 `1`은 Thumb bit이고, 범위 검사용 실제 정렬 주소는
  `0x080045A0`이다.

```c
uint32_t initial_sp = *(uint32_t *)image_addr;
uint32_t reset_handler = *(uint32_t *)(image_addr + 4);
uint32_t reset_addr = reset_handler & ~1UL;
```

`bootVerifyImageAt()`은 Initial SP가 F103RB SRAM 범위인지, Reset Handler의
Thumb bit가 설정됐는지, 그리고 handler가 active application Flash 범위에
있는지를 확인한다.

일반 reset에서는 bootloader vector table이 먼저 사용된다. application으로 넘길 때
bootloader는 `SCB->VTOR = 0x08004000`으로 interrupt vector table의 기준을
application으로 바꾸고, application vector table에서 읽은 SP와 Reset Handler로 jump한다.

Bootloader와 application은 모두 SRAM `0x20000000`부터 20 KiB를 사용하며,
현재 두 linker script의 `_estack`은 RAM 끝인 `0x20005000`이다. 즉 RAM을 둘로
고정 분할하는 구조가 아니라, 실행 시점에 bootloader와 application이 같은 RAM을
번갈아 사용하는 구조다.

근거:

- `boot_can_custom_f103/STM32F103XX_FLASH.ld`
- `boot_can_fw_f103/STM32F103XX_FLASH.ld`
- `boot_can_custom_f103/startup_stm32f103xb.s`
- `boot_can_fw_f103/startup_stm32f103xb.s`
- `boot_can_custom_f103/App/ap/boot_can/boot_can.c`

## 확인이 필요한 내용

| 질문 | 확인 방법 | 상태 |
| --- | --- | --- |
| BBB CAN Device Tree 설정은 어디서 관리되는가? | 저장소와 BBB 배포 환경을 분리하여 확인 | 미확인 |
| vcan에서 flasher 오류 흐름을 어느 범위까지 재현할 수 있는가? | vcan과 mock/simulator 실습 | 미확인 |
| 실제 보드에서 staging 복구가 재현되는가? | STM32F103/BBB hardware test | 미확인 |

## 다음 할 일

- [ ] `docs/architecture.md`와 application/bootloader source를 따라 Week 1 boot 흐름 정리
- [ ] `docs/memory-map.md`와 linker script로 Flash map 검증
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
