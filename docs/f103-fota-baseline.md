# STM32F103RB Custom FOTA 기준선

## 목적

이 문서는 FreeRTOS 작업을 시작하기 전 F103 FOTA 기준선을 기록한다.
선택된 기준선은 Custom CAN bootloader 흐름이며, 이 기준선에는 FreeRTOS 코드가
포함되지 않는다.

## 빌드 환경

- 호스트: Windows
- Toolchain: STM32CubeCLT 1.19.0, ARM GNU Toolchain 13.3.1
- 빌드 시스템: CMake 3.28.1 및 Ninja
- 빌드 프로파일: Release

빌드 명령:

```powershell
cmake --preset Release -S boot_can_custom_f103
cmake --build boot_can_custom_f103/build/Release
cmake --preset Release -S boot_can_isotp_f103
cmake --build boot_can_isotp_f103/build/Release
cmake --preset Release -S boot_can_fw_f103
cmake --build boot_can_fw_f103/build/Release
```

## Release 빌드 결과

| 이미지 | BIN 크기 | FLASH | RAM | Vector table | Reset_Handler |
| --- | ---: | ---: | ---: | --- | --- |
| Custom Bootloader | 8,632 B | 8,632 / 16,384 B (52.69%) | 3,184 / 20,480 B (15.55%) | `0x08000000` | `0x080018B0` |
| ISO-TP Bootloader | 12,364 B | 12,364 / 16,384 B (75.46%) | 3,928 / 20,480 B (19.18%) | `0x08000000` | `0x080019A4` |
| Custom Application | 7,772 B | 7,772 / 57,336 B (13.56%) | 3,416 / 20,480 B (16.68%) | `0x08004000` | `0x08005A00` |

Application linker 영역은 `0x08004000`부터 `0x08011FF7`까지
(`57,336 B`)다. 이는 Custom firmware 최대 크기와 일치하며, staging 영역은
`0x08012000`부터 `0x0801FFFF`까지 남긴다.

세 빌드는 모두 `.elf`, `.bin`, `.hex`, `.map` 파일을 생성했다.

## 주소 및 HAL 검증

- 두 bootloader는 `0x08000000`부터 `0x08003FFF`까지(16 KB)에 link된다.
- Custom Application은 `0x08004000`에서 시작하고 `57,336 B`로 엄격히
  제한되므로 Custom staging 영역과 겹칠 수 없다.
- 물리 Flash는 `0x08020000`에서 끝난다.
- 실제 빌드 명령은 `STM32F1xx_HAL_Driver`,
  `CMSIS/Device/ST/STM32F1xx`, `startup_stm32f103xb.s`,
  `system_stm32f1xx.c`, `STM32F103xB`를 사용한다.
- 실제 F103 빌드 명령에는 `STM32F4xx_HAL_Driver`,
  `startup_stm32f407xx.s`, or `system_stm32f4xx.c`.

## Custom FOTA 흐름

1. Application이 CAN ID `0x200`, payload `DE AD`를 수신한다.
2. BKP DR1/DR2에 `0xDEADBEEF`를 저장하고 `NVIC_SystemReset()`을 호출한다.
3. Custom Bootloader가 magic 값을 감지하고 FOTA mode에 진입한다.
4. firmware를 `0x08012000`의 staging 영역으로 내려받는다.
5. CRC 검증 뒤 Bootloader가 staging firmware를 `0x08004000`의
   Application 영역으로 복사한다.

이는 staging 검증이 끝나기 전 전송이 중단돼도 기존 Application을 보호한다.
다만 최종 복사 도중 전원이 손실되는 상황에 대한 완전한 A/B rollback 구현은 아니다.

## 기준선 제약

- FreeRTOS는 이 기준선에 포함되지 않는다.
- Custom 이미지에서는 Application CLI 및 debug print 경로를 비활성화한다.
- Application은 `-Os`로 빌드한다.
- Custom protocol은 57,336 B보다 큰 Application을 갱신할 수 없다.
- ISO-TP direct-write는 이 기준선 밖이다. staging이 없으므로 사용 전 별도의
  transfer-size 및 write-range 강화를 해야 한다.

## 하드웨어 검증 상태

- 개발자가 STM32F103RB 하드웨어에서 Custom FOTA 전송 성공을 확인했다.
- 개발자가 전송 중 CAN을 분리했다가 다시 연결한 뒤 기존 Application이 정상
  boot되는 것을 확인했다.
- 이 실행에 대한 CAN trace나 execution log는 repository에 없다.

## 알려진 빌드 경고

- F103 Flash source 파일에서 `FLASH_PAGE_SIZE`가 재정의된다.
- ISO-TP Bootloader에서는 사용되지 않는 `SendResponse` 함수 경고도 발생한다.
