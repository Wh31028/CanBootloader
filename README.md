# CAN FOTA for STM32 & BeagleBone Black

STM32F103RB의 firmware를 BeagleBone Black에서 Classic CAN으로 갱신하는 staging 기반 Custom FOTA 시스템입니다.

## 프로젝트 소개

차량 ECU의 firmware를 갱신하려면 제한된 CAN payload 안에서 대용량 image를 전송하고, packet loss와 전원 차단 상황에서도 실행 가능한 firmware를 보호해야 합니다.

이 프로젝트는 캡스톤 연구에서 ISO-TP와 Custom protocol의 성능을 비교한 뒤, 그 결과를 바탕으로 STM32F103RB 환경의 실제 FOTA 구조를 발전시킨 프로젝트입니다. 현재 `main`은 성능 실험용 구현이 아니라 다음 요소를 포함하는 **F103 Custom CAN FOTA 기준 구현**입니다.

- 16 KiB CAN bootloader
- Active application과 staging 영역 분리
- Selective NACK 기반 누락 frame 재전송
- CRC32 검증 후 application 반영
- Copy 중단을 고려한 vector-last write와 자동 복구
- FreeRTOS application과 `ECU_READY` 상태 신호
- BBB SocketCAN flasher와 web dashboard

## 연구에서 구현으로

이 repository에는 두 단계의 개발 흐름이 있습니다.

| 구분 | 목적 | 주요 내용 |
| --- | --- | --- |
| `capston-1` | Protocol 비교 연구 | ISO-TP와 Selective NACK 방식의 전송 시간·재전송 특성 비교, F407/F103 성능 실험 |
| `main` | F103 FOTA 시스템 구현 | Staging, CRC 검증, 복구 전략, FreeRTOS application, BBB gateway 통합 |

발표자료의 F103 64 KiB 결과는 staging 도입 전의 64 KiB direct-write 구성에서 측정한 값입니다. 이후 memory layout을 16 KiB bootloader와 두 개의 약 56 KiB 영역으로 재설계하면서 현재 Custom firmware 한도는 **57,336 B**가 됐습니다.

캡스톤 연구 자료는 [`capston-1` branch](https://github.com/Wh31028/CanBootloader/tree/capston-1)에서 확인할 수 있습니다.

## 시스템 아키텍처

```mermaid
flowchart LR
    User[사용자] --> Dashboard[BBB Web Dashboard]
    Dashboard --> Flasher[C FOTA Flasher]
    CLI[CLI] --> Flasher
    Flasher --> SocketCAN[Linux SocketCAN]
    SocketCAN <-->|Classic CAN| Boot[STM32F103RB Bootloader]
    SocketCAN --> App[FreeRTOS Application]
    App -->|FOTA request + reset| Boot
    Boot --> Staging[Staging Image]
    Staging -->|CRC 검증 후 copy| Active[Active Application]
    Active --> App
```

BBB는 firmware 전달과 protocol 진행을 담당하고, STM32 bootloader는 Flash erase/write, CRC 검증, application 교체와 복구를 담당합니다. 상세 구조는 [시스템 아키텍처](docs/architecture.md)에 정리했습니다.

## 핵심 설계

### Selective NACK

Firmware를 256-byte block으로 나누고, 각 block을 최대 37개의 CAN frame으로 전송합니다. Target은 56-bit receive bitmap을 관리하며 누락된 sequence만 NACK으로 알려줍니다. BBB는 block 전체가 아니라 누락 frame만 다시 보냅니다.

### Staging 기반 update

새 firmware는 active application에 바로 기록되지 않습니다. 먼저 staging 영역에 수신하고 전체 CRC32가 일치한 경우에만 active 영역으로 복사합니다. 전송이나 CRC 검증이 실패하면 기존 application은 변경되지 않습니다.

### 복구 가능한 copy 순서

Application의 Initial SP와 Reset Vector가 있는 첫 8 bytes를 마지막에 기록합니다. Copy 도중 reset되어 active image가 유효하지 않으면, bootloader가 staging metadata와 CRC를 확인해 복사를 다시 시도합니다.

### Application 상태 연동

현재 application은 하나의 static FreeRTOS `AppTask`에서 CAN request와 application logic을 처리합니다. `ECU_READY` 신호는 application task가 실제로 실행 중인지를 BBB가 별도로 관찰할 수 있게 합니다.

## FOTA 동작 흐름

```mermaid
sequenceDiagram
    participant BBB as BeagleBone Black
    participant App as F103 Application
    participant Boot as Custom Bootloader
    participant Stage as Staging Flash
    participant Active as Active Flash

    BBB->>App: FOTA request (0x200, DE AD)
    App->>Boot: BKP magic 기록 후 reset
    BBB->>Boot: START + firmware size
    Boot->>Stage: Staging erase
    Boot-->>BBB: ACK
    loop 256-byte block
        BBB->>Boot: DATA frames
        alt frame 누락
            Boot-->>BBB: NACK + receive bitmap
            BBB->>Boot: 누락 frame만 재전송
        else block 완료
            Boot->>Stage: Block write
            Boot-->>BBB: ACK
        end
    end
    BBB->>Boot: END + CRC32
    Boot->>Stage: Image CRC 검증
    Boot->>Active: 검증된 image copy
    Boot-->>BBB: ACK
    BBB->>Boot: JUMP
    Boot->>App: Application 실행
```

## 기술 스택

| 영역 | 기술 |
| --- | --- |
| Target | STM32F103RB, bxCAN, STM32F1 HAL/CMSIS |
| Application | C, FreeRTOS, static task allocation |
| Bootloader | C, Custom CAN protocol, Flash staging, IEEE CRC-32 |
| Gateway | BeagleBone Black, Linux, SocketCAN, POSIX C |
| Dashboard | Python, FastAPI, WebSocket |
| Build | CMake, Ninja, GNU Arm Embedded Toolchain, Make |

## Repository 구성

```text
.
├── boot_can_custom_f103/   # 현재 기준 Custom CAN bootloader
├── boot_can_fw_f103/       # FreeRTOS application
├── boot_can_isotp_f103/    # ISO-TP 비교 구현
├── can-fota-BBB/           # BBB flasher와 web dashboard
└── docs/                   # 설계 및 개발 과정 문서
```

F407 실험 구현과 benchmark script/CSV는 연구 목적의 `capston-1` branch에 보존하고, 현재 `main`에서는 F103 구현에 집중합니다. Yocto layer와 image 구성은 별도 repository에서 관리합니다.

## Custom CAN과 ISO-TP

| 항목 | Custom CAN | ISO-TP 비교 구현 |
| --- | --- | --- |
| 목적 | 현재 F103 FOTA 기준 | 캡스톤 비교 및 reference 구현 |
| 전송 복구 | Bitmap 기반 누락 frame 선택 재전송 | Timeout 시 256-byte chunk 전체 재전송 |
| Flash 전략 | Staging 검증 후 active copy | Active 영역 direct-write |
| Application protocol | Project-specific command | ISO-TP transport 위의 project-specific command |
| 현재 위치 | `boot_can_custom_f103` | `boot_can_isotp_f103` |

ISO-TP 구현은 UDS가 아니라 ISO-TP transport 위에 자체 START/DATA/END/JUMP command를 정의한 비교 구현입니다.

## 검증 결과

| 범위 | 결과 | 근거 |
| --- | --- | --- |
| 캡스톤 protocol 비교 | F407/F103에서 loss rate와 firmware size 조건별 Custom/ISO-TP 비교 수행 | `capston-1`의 test script, CSV, graph와 발표자료 |
| F103 Custom 기준선 | 실제 board에서 FOTA와 전송 중단 후 기존 application boot 확인 | [F103 Custom FOTA 기준선](docs/f103-fota-baseline.md) |
| FreeRTOS application | Scheduler, LED, CAN FOTA entry, `ECU_READY` 동작 확인 | [FreeRTOS application 확장](docs/f103-freertos-application.md) |
| 현재 `main` 정상 update | `6972058` Release build를 BBB에서 Custom으로 1회 update, exit 0, 재전송 0 | [TW-05 검토](docs/verification/TW-05-review.md) ① |

발표 성능 수치는 당시 direct-write 시험 구성의 결과이며 현재 staging layout의 성능 수치로 사용하지 않습니다. 인용 조건은 아래 표에 정리했습니다.

## 검증 조건과 한계

| 항목 | 상태 | 조건 / 한계 | 근거 |
| --- | --- | --- | --- |
| 캡스톤 성능 수치 (16.0 s → 9.4 s, 재전송 약 1,424 → 35) | 조건부 인용 | F407 direct-write, 1 Mbit/s, 256 KiB, 송신 측 software omission 0.1%(seed 미기록), 조건당 30회. 비교 대상은 150 ms timeout 후 block 전체를 재시도하는 실험 sender이며 표준 ISO-TP 일반이 아님. 재전송 수는 두 방식의 counter 정의가 다름(block 재시도 × 37 추정 vs 실제 재송신). CSV를 만든 code는 실행 당시 commit되지 않음 | [TW-05](docs/verification/TW-05-review.md) ② |
| F103 정상 update | PASS | 500 kbit/s, 무손실. 10,284 B(TW-05), 15,180 B·최대 57,336 B(TW-03). 시간은 참고값이며 반복 측정 아님 | TW-03, TW-05 ① |
| 입력 검증 | PASS | START size 0 / 57,337 B, DLC 오류, 순서 오류(IDLE DATA/END/JUMP), 잘못된 sequence → ERR, Flash 변경 없음 | [TW-01](docs/verification/TW-01-target-input-state.md) |
| 전송 실패 경로 | PASS | `can0` down, 전송 중 target reset, 무응답 → 원인별 exit code로 종료, 기존 application 유지 | [TW-03](docs/verification/TW-03-bbb-timeout-retry.md) |
| Selective NACK 재전송 | 실장 미검증 | F103 실장 시험에서는 손실이 없어 NACK이 한 번도 발생하지 않음. 근거는 code와 F407 실험뿐 | TW-03 |
| 복사 중 reset / 전원 차단 복구 | NOT RUN | vector-last write와 staging 재복사는 구현만 되어 있음 | [TW-02](docs/verification/TW-02-flash-copy-boot-validation.md) |
| invalid SP/PC image jump 거부, 1~3 B tail | NOT RUN | negative image를 전송하지 않음 | TW-02 |
| block ACK 유실 | 알려진 한계, 재현 안 함 | session/block ID가 없어 ACK 유실 시 host와 target의 block 위치가 어긋날 수 있음 | [protocol](docs/protocol.md) |
| bus-off | NOT RUN | 보유 장비로 안전하게 유도하지 못함. counter만 추가 | TW-03 |
| Firmware 인증 | 범위 밖 | CRC32는 오류 검출만 하고 발행자를 인증하지 않음 | — |

## 현재 구현 범위

- Custom firmware 최대 크기는 57,336 B입니다.
- 하나의 physical Flash를 active/staging으로 나눈 구조이며 true dual-bank/A/B update는 아닙니다.
- CRC32는 전송 오류를 검출하지만 firmware의 발행자를 인증하지는 않습니다.
- BBB dashboard는 FOTA 시연과 진행 상태 관찰을 위한 prototype입니다.
- ISO-TP와 Custom protocol은 동일한 application command 표준을 구현한 것이 아니라 서로 다른 비교 경로입니다.

## 다음 단계

- Host-side protocol/CRC 단위 테스트와 CI firmware build
- Session/block ID를 포함한 protocol v2 (ACK 유실 시 block desync 해결)

## 문서

- [시스템 아키텍처와 FOTA 설계](docs/architecture.md)
- [Custom CAN Protocol](docs/protocol.md)
- [STM32F103RB Memory Map](docs/memory-map.md)
- [F103 Custom FOTA 기준선](docs/f103-fota-baseline.md)
- [FreeRTOS Application 확장](docs/f103-freertos-application.md)
- [C 코딩 규칙](docs/coding-style.md)
- [하드웨어 검증 기록](docs/verification/)

## 데모 자료

- [BBB Web Dashboard](can-fota-BBB/web_dashboard/)
