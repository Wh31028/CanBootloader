# STM32F103RB FreeRTOS Application 마일스톤

## 범위 및 설계 결정

첫 마일스톤은 기존 Custom FOTA Application 동작을 하나의 FreeRTOS task로
감싼다. Custom CAN protocol, bootloader, staging/copy 흐름, Flash layout은
변경하지 않는다.

시작 순서:

1. `HAL_Init()` 및 기존 clock/peripheral 초기화
2. `hwInit()` 및 `apInit()`
3. `AppTask`의 static 생성
4. `vTaskStartScheduler()`
5. `AppTask`가 기존 `apMain()` LED 및 CAN polling loop 실행

CAN RX interrupt callback은 계속 수신 frame을 기존 64-entry ring buffer에 쓴다.
`AppTask`는 이 buffer를 1 ms마다 polling한다. CAN ID `0x200`, payload
`DE AD`는 계속 BKP DR1/DR2에 `0xDEADBEEF`를 쓰고 Custom bootloader로
reset한다.

## FreeRTOS source

- FreeRTOS kernel: V10.3.1
- STM32 package: STM32Cube_FW_F1_V1.8.6
- Compiler port: `portable/GCC/ARM_CM3`
- 포함한 kernel source: `tasks.c`, `list.c`, `port.c`
- Allocation: static만 사용
- Software timer service: 비활성화

source는 로컬에 설치된 STM32Cube F1 firmware repository에서 가져왔으며,
외부 다운로드는 사용하지 않았다.

## SysTick 및 HAL tick

STM32 HAL과 FreeRTOS Cortex-M3 port는 모두 SysTick을 사용한다. 선택한
구성은 하나의 1 kHz SysTick을 공유한다.

- scheduler 시작 전 `SysTick_Handler()`는 `HAL_IncTick()`만 호출한다.
- scheduler 시작 후에는 `HAL_IncTick()`과
  `xPortSysTickHandler()`.
- Cortex-M3 port가 SVC 및 PendSV handler를 직접 소유한다.

이는 별도의 HAL timer를 추가하지 않고 `HAL_GetTick()`/`millis()` 동작을
유지한다. `HAL_InitTick()`은 처음에 HAL 1 kHz tick을 구성하고, FreeRTOS
port는 scheduler 시작 시 SysTick을 같은 `configTICK_RATE_HZ`로 구성한다.
FOTA 진입 대기는 `HAL_Delay()` busy-wait 대신 task context의
`vTaskDelay()`를 사용한다.

## Task 및 RAM 구성

| 항목 | 할당 | 근거 |
| --- | ---: | --- |
| AppTask stack | 256 words / 1,024 B | 기존의 얕은 polling loop 및 HAL 호출을 위한 보수적인 첫 보드 시험 값 |
| Idle stack | 128 words / 512 B | idle hook이 없는 FreeRTOS 최소 stack |
| AppTask + Idle TCB | 120 B | 이 빌드의 60-byte static TCB 2개 |
| FreeRTOS heap | 0 B | `configSUPPORT_DYNAMIC_ALLOCATION=0`; heap 구현을 link하지 않음 |
| Linker C heap reserve | 512 B | 기존 `_Min_Heap_Size`; FreeRTOS heap이 아님 |
| Linker MSP reserve | 1,024 B | startup 및 interrupt용 기존 `_Min_Stack_Size` |

`configCHECK_FOR_STACK_OVERFLOW=2`를 활성화했다. debugger에서 볼 수 있는
volatile symbol `g_app_task_stack_high_water_mark_words`는 task 진입 시와
LED period마다 `uxTaskGetStackHighWaterMark(NULL)`를 기록한다. 단위는
32-bit stack word다. 하드웨어 시험에서 최소 잔여값은 224 words(896 B)였으므로,
관측된 최대 AppTask stack 사용량은 32 words(128 B)였다. 이후 task 기능의 측정도
완료될 때까지 초기 256-word AppTask stack을 유지한다.

## Release 빌드 검증

명령:

```powershell
cmake --preset Release -S boot_can_fw_f103
cmake --build boot_can_fw_f103/build/Release
```

도구:

- STM32CubeCLT 1.19.0
- GNU Tools for STM32 13.3.1 (`13.3.rel1`)
- CMake 3.28.1
- Ninja 1.11.1
- 빌드 flags: Release, `-Os`, CLI/debug print 비활성화

생성 파일: `boot_can_fw.elf`, `boot_can_fw.bin`, `boot_can_fw.hex`,
`boot_can_fw.map`.

| 측정 항목 | 결과 |
| --- | ---: |
| ELF file size | 33,872 B |
| BIN image / linker FLASH use | 10,092 B / 57,336 B (17.60%) |
| FLASH headroom | 47,244 B |
| Linker RAM use | 5,304 B / 20,480 B (25.90%) |
| RAM headroom | 15,176 B |
| `.isr_vector` | 268 B at `0x08004000` |
| `.text` | 9,740 B |
| `.rodata` | 56 B |
| `.data` | 16 B |
| `.bss` | 3,748 B |
| `._user_heap_stack` | 1,540 B |
| `Reset_Handler` | `0x080059F0` |

`.isr_vector` 뒤의 4-byte alignment gap 때문에 linker/BIN FLASH 사용량
10,092 B는 표준 `size`의 text와 data 열 합계보다 4 B 크다.

RAM은 3,416-byte 기준선에서 1,888 B 증가했다. 이는 명시적 task stack
1,536 B, TCB 120 B, 4-byte high-water 진단값, scheduler/port state 및
alignment 228 B로 구성된다. FreeRTOS heap array는 없다.

실제 compile database는 `STM32F103xB`, STM32F1 HAL/CMSIS,
`startup_stm32f103xb.s`, `system_stm32f1xx.c`를 사용한다. F4 startup,
system, HAL source 또는 include path는 포함하지 않는다.

## 하드웨어 검증

STM32F103RB에서 첫 마일스톤의 모든 검증을 통과했다.

- FreeRTOS scheduler 시작, AppTask high-water mark 224 words
- LED 1초 period: PASS
- CAN ID `0x200`, payload `DE AD` Custom bootloader 진입: PASS
- 일반 Custom FOTA update: PASS
- 전송 중 CAN 분리 후 재연결 및 기존 Application boot: PASS

FreeRTOS Application 첫 마일스톤의 하드웨어 검증은 완료됐다. 중단된 전송
결과는 기존 Custom staging validation 동작을 검증한 것이며, 최종 복사 중 전원
손실에 대한 완전한 A/B rollback 보호를 추가하지는 않는다.

## ECU_READY GPIO 마일스톤 (V3.2)

`ECU_READY`는 heartbeat가 아닌 level 상태 신호다. STM32F103RB `PA6`
(NUCLEO-F103RB Morpho `CN10 pin 13`)를 BBB `P9_12`(`gpio1_28`)에
연결한다. Yocto BBB kernel patch는 `P9_12`를 internal pull-down GPIO input으로
구성하며, 하드웨어에도 신호선과 공통 GND 사이의 external 10 kOhm pull-down을
구성해야 한다.

| STM32 상태 | ECU_READY |
| --- | --- |
| Reset, bootloader, FOTA 전송, AppTask 시작 전 또는 not ready | LOW |
| `hwInit()`, `apInit()` 완료 후 scheduler 시작 및 `AppTask` 진입 | HIGH |
| CAN ID `0x200`, payload `DE AD`의 FOTA magic/reset 직전 | LOW |

CubeMX PA6 구성은 output push-pull, no pull, low speed이며 생성된 초기 output
level은 LOW다. `ecu_ready`는 hardware 초기화 중 다시 LOW로 설정하고,
`AppTask` 시작 시 HIGH로 올리며, 변경하지 않은 FOTA magic write와
`NVIC_SystemReset()` 호출 전에 LOW로 내린다. 별도의 FreeRTOS task는
사용하지 않는다.

<!--
The STM32 reset/bootloader state can leave the GPIO Hi-Z, so the external
pull-down—not MCU firmware—is the hardware guarantee that BBB reads LOW.
양 끝은 3.3 V logic을 사용하고 GND를 공통으로 연결해야 한다. 신호선을 5 V에
연결하면 안 된다. 향후 HEARTBEAT에는 별도의 GPIO/net을 예약한다.
-->

STM32 reset/bootloader 상태에서는 GPIO가 Hi-Z가 될 수 있으므로, BBB가 LOW를
읽도록 보장하는 주체는 MCU firmware가 아니라 external pull-down이다. 양 끝은
3.3 V logic을 사용하고 GND를 공통으로 연결해야 한다. 신호선을 5 V에 연결하면
안 된다. 향후 HEARTBEAT에는 별도의 GPIO/net을 예약한다.

배선 후 하드웨어 검증:

1. external 10 kOhm pull-down 및 common GND를 확인하고, scope 또는 logic
   analyzer로 신호선을 관찰한다.
2. STM32를 reset하고 reset 및 bootloader 동안 LOW인지 검증한다.
3. Application을 boot하고 AppTask가 시작된 뒤에만 HIGH인지 검증한다.
4. `cansend can0 200#DEAD`를 전송하고 reset 전 LOW가 되며 Custom FOTA
   동안 LOW를 유지하는지 검증한다.
5. Custom FOTA update를 완료하고 새 Application의 AppTask 시작 뒤에만 HIGH로
   복귀하는지 검증한다. 향후 HEARTBEAT는 별도 net에서 검증한다.

소프트웨어 검증에서는 runtime에 Linux GPIO character device를 식별한다.
AM335x 하드웨어 신호는 `gpio1_28`이지만 `/dev/gpiochipN` 번호는 kernel
probe 순서로 결정되므로 고정된 하드웨어 contract가 아니다. 검증한 image에서는
`gpiochip0` line `28`이다.

```sh
gpiodetect
gpioget -c gpiochip0 28
gpiomon --edges=both -c gpiochip0 28
```

`gpioget`은 STM32 reset, bootloader, FOTA 중 `inactive`를 보고하고,
`AppTask` 시작 뒤 `active`를 보고해야 한다.
