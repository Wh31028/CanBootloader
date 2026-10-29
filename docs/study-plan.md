# CAN FOTA 포트폴리오 8주 학습 계획

## 목적

이 문서는 BBB Linux gateway와 STM32F103 CAN-FOTA 시스템을 실제 코드와 실행 근거로
이해하고, GitHub 포트폴리오 및 면접 자료로 정리하기 위한 8주 학습 계획이다.

현재 학습 기준은 Custom CAN FOTA 경로다.

- Bootloader: `boot_can_custom_f103/`
- Application: `boot_can_fw_f103/`
- BBB flasher: `can-fota-BBB/flasher/`
- 설계 근거: `docs/architecture.md`, `docs/protocol.md`,
  `docs/memory-map.md`, `docs/f103-fota-baseline.md`

`boot_can_isotp_f103/`은 비교 구현으로 학습하되, Custom protocol과 동일한 동작 또는
동일한 Flash 전략이라고 가정하지 않는다.

## 기록 원칙

- 코드에서 확인한 사실, 직접 실행한 결과, 외부 자료 또는 가정을 구분한다.
- 실제 BBB/STM32 보드 검증 전에는 hardware 동작을 검증 완료로 기록하지 않는다.
- 민감정보, 토큰, 개인 경로, 사설 네트워크 정보는 기록하지 않는다.

## Week 1 — 전체 구조와 Boot 흐름

- 목표: BBB, STM32 application, bootloader, Flash 영역의 역할과 reset 흐름 이해
- 근거 파일: `README.md`, `docs/architecture.md`,
  `boot_can_fw_f103/App/ap/ap.c`,
  `boot_can_custom_f103/App/ap/boot_can/boot_can.c`
- 산출물: 일반 boot, FOTA entry, invalid application의 분기 흐름도

## Week 2 — Flash map과 복구 설계

- 목표: bootloader, active application, staging 영역의 주소·크기·제약 이해
- 근거 파일: `docs/memory-map.md`, `docs/f103-fota-baseline.md`,
  F103 linker script, Flash 관련 source
- 산출물: Flash map 다이어그램, 57,336 B 한도 설명, vector-last copy와 복구 흐름

## Week 3 — Custom CAN Protocol

- 목표: START/DATA/END/JUMP와 ACK/NACK/ERR, bitmap 기반 선택 재전송 이해
- 근거 파일: `docs/protocol.md`, `can-fota-BBB/flasher/protocol.h`,
  `can-fota-BBB/flasher/custom_fota.c`,
  `boot_can_custom_f103/App/ap/boot_can/boot_can.c`
- 산출물: CAN ID·packet layout 표, 정상/누락 frame sequence diagram, protocol 한계 목록

## Week 4 — BBB SocketCAN Flasher

- 목표: Linux SocketCAN socket, CAN frame 송수신, timeout과 오류 처리 이해
- 근거 파일: `can-fota-BBB/flasher/can_socket.c`,
  `can-fota-BBB/flasher/fota_common.c`,
  `can-fota-BBB/flasher/main.c`
- 산출물: CLI flasher 호출 흐름과 protocol state 연결 설명

## Week 5 — vcan 기반 Host-side 실습

- 목표: 실제 보드 없이 CAN frame 관찰과 정상·오류 흐름의 기초 재현
- 실습: `vcan` interface, `candump`, `cansend`, mock/simulator 가능성 확인
- 산출물: 재현 명령, CAN trace, 실제 STM32 Flash write를 대체하지 못하는 한계
- 주의: vcan 결과는 Linux SocketCAN 검증이며, 실제 CAN transceiver·STM32 Flash
  동작 검증과 분리한다.

## Week 6 — BBB CAN Device Tree

- 목표: Device Tree, pinmux, CAN controller, transceiver, SocketCAN interface의 관계 이해
- 확인 방식:
  - 저장소 내 BBB 설정 파일 존재 여부 확인
  - 외부 BBB kernel/Device Tree 자료는 출처를 분리해 기록
  - 실제 보드 적용 여부는 실행 결과로만 확정
- 산출물: Device Tree → kernel CAN interface → SocketCAN application 흐름도

## Week 7 — 장애 테스트와 신뢰성 검토

- 목표: 실패 상황에서 기존 application의 boot 가능성을 분석
- 시나리오: 누락 frame, bitmap NACK, CRC 불일치, Flash 실패, copy 중 reset,
  ACK 유실, malformed packet, bootloader timeout
- 산출물: 시나리오별 코드 근거, 실행 결과, 미검증 가정 및 개선 후보

## Week 8 — README와 면접 준비

- 목표: 설계 결정·검증 범위·한계를 과장 없이 전달하는 포트폴리오 구성
- 산출물:
  - README 개선안
  - Flash staging, Selective NACK, vector-last copy, SocketCAN, Device Tree,
    vcan의 차이를 다루는 면접 질문·답변
  - 공개 전 민감정보·개인 경로 점검표

## 완료 기준

- 설명마다 코드 파일 또는 실행 증거가 연결되어 있다.
- 직접 검증한 내용과 계획·가정을 구분했다.
- Custom FOTA 기준 구현과 ISO-TP 비교 구현을 혼동하지 않는다.
- Flash 한도, protocol 한계, firmware authenticity 부재를 명시한다.
