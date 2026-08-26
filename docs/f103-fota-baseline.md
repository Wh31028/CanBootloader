# STM32F103RB Custom FOTA 기준선

## 개발 배경

캡스톤 단계에서는 ISO-TP와 Selective NACK protocol의 전송 성능을 비교하는 데 집중했습니다. 이후 `main`에서는 STM32F103RB를 기준 target으로 선택하고, 단순 direct-write 구조를 기존 application을 보호할 수 있는 staging 기반 FOTA로 발전시켰습니다.

이 문서는 FreeRTOS application을 추가하기 직전 확립한 F103 Custom FOTA 기준선을 설명합니다.

## 기준선의 핵심 결정

| 항목 | 결정 |
| --- | --- |
| Target | STM32F103RB, 128 KiB Flash, 20 KiB RAM |
| Bootloader | `0x08000000`부터 16 KiB |
| Application | `0x08004000`부터 최대 57,336 B |
| Staging | `0x08012000`부터 firmware payload와 8-byte metadata 저장 |
| Protocol | 256-byte block 기반 Custom CAN Selective NACK |
| Integrity | IEEE CRC-32 |
| Recovery | Staging CRC 검증과 vector-last copy |

F103 target은 STM32F1 HAL/CMSIS, `startup_stm32f103xb.s`, `system_stm32f1xx.c`, `STM32F103xB` define을 사용합니다. F407 실험 source와 build 구성을 현재 F103 기준선에서 분리했습니다.

## FOTA 동작

1. Application이 CAN ID `0x200`, payload `DE AD`를 수신합니다.
2. BKP DR1/DR2에 `0xDEADBEEF`를 저장하고 system reset합니다.
3. Bootloader가 magic을 확인한 뒤 FOTA mode에 진입합니다.
4. Firmware를 `0x08012000`의 staging 영역에 수신합니다.
5. 전체 image의 CRC32를 검증합니다.
6. CRC가 일치하면 active application 영역을 갱신합니다.
7. Initial SP와 Reset Vector를 마지막에 기록한 뒤 새 application을 실행합니다.

새 firmware의 download와 검증이 끝나기 전에는 active application을 수정하지 않습니다. Copy 중 reset으로 active vector가 유효하지 않으면 staging metadata와 CRC를 이용해 copy를 다시 시도합니다.

## 기준선 결과

GNU Arm 13.3.1 기반 Release build에서 기록한 결과입니다.

| Image | BIN 크기 | Flash 사용 | RAM 사용 | Vector table |
| --- | ---: | ---: | ---: | ---: |
| Custom Bootloader | 8,632 B | 52.69% / 16 KiB | 15.55% / 20 KiB | `0x08000000` |
| ISO-TP Bootloader | 12,364 B | 75.46% / 16 KiB | 19.18% / 20 KiB | `0x08000000` |
| Custom Application | 7,772 B | 13.56% / 57,336 B | 16.68% / 20 KiB | `0x08004000` |

이 결과는 FreeRTOS 추가 전의 기준선이며 현재 application image 크기와는 다릅니다.

## Hardware 검증 기록

- STM32F103RB에서 Custom FOTA 전송 성공
- 전송 중 CAN 연결을 끊은 뒤 기존 application boot 확인
- Bootloader와 application vector 위치 확인
- Application image가 staging 영역을 침범하지 않도록 linker 영역 제한

해당 hardware 실행의 CAN trace와 자동화된 test log는 repository에 보존되어 있지 않으므로, 위 내용은 당시 개발 검증 기록의 범위로 해석합니다.

## 이 기준선의 의미

이 단계에서 protocol format과 Flash layout을 먼저 고정함으로써, 이후 FreeRTOS를 application에 추가하면서도 bootloader 및 BBB flasher와의 호환성을 유지할 수 있었습니다.

다음 단계에서는 Custom FOTA 구조를 변경하지 않고 application loop를 static FreeRTOS task로 옮기고, BBB가 application 실행 상태를 관찰할 수 있도록 `ECU_READY`를 추가했습니다.

## 관련 문서

- [시스템 아키텍처](architecture.md)
- [Custom CAN Protocol](protocol.md)
- [Memory Map](memory-map.md)
- [FreeRTOS Application 확장](f103-freertos-application.md)
