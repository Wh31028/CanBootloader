# Sprint 01 리팩토링 경계와 후속 후보

## Sprint 01과의 관계

실행 순서와 완료 기준의 단일 기준은
[`improvement-plan/sprint-01-two-weeks.md`](improvement-plan/sprint-01-two-weeks.md)다.
이 문서는 별도 P0~P4 작업 계획이나 스프린트 범위 확장이 아니다. 각 TW 작업에서
구조 정리나 스타일 변경이 제안됐을 때, 현재 Task에 포함되는지 판단하는 참고 자료다.

- TW-01~TW-04의 source 변경은 해당 TW 문서의 변경 후보 파일과 완료 조건을 따른다.
- format-only 변경, 대량 rename, F4 legacy file 정리, toolchain 교체는 Sprint 01
  완료 조건에 필요하지 않으므로 현재 Task에 섞지 않는다.
- wire format과 F103 Flash layout은 Sprint 01 동안 유지한다.

## TW 매핑

| Sprint Task | 이 문서가 다루는 경계 | 이번 스프린트에서의 처리 |
| --- | --- | --- |
| TW-01 | protocol 상수, frame validation, bootloader state helper | 필요한 최소 함수 추출만 허용 |
| TW-02 | Flash/boot validation module 경계 | 안전성 수정에 직접 필요한 변경만 허용 |
| TW-03 | BBB timeout/error helper와 CAN ID type | 오류 처리 완료 조건에 필요한 변경만 허용 |
| TW-04 | ISO-TP include/type/build 경계 | compile·memory safety blocker만 허용 |
| TW-05 | 코드 구조 변경 없음 | regression evidence와 문서화만 수행 |

## Sprint 01 이후 후보

다음 항목은 TW-05 Review Gate 이후에만 우선순위를 다시 정한다.

### F103 toolchain 정합성

대상:

- `boot_can_custom_f103/cmake/starm-clang.cmake`
- `boot_can_isotp_f103/cmake/starm-clang.cmake`

두 파일에는 Cortex-M4/F407 linker script를 가리키는 설정이 남아 있다. 기본 GNU
build가 아닌 starm-clang 경로를 쓸 경우 F103 메모리 경계와 ABI가 틀어질 수 있다.
`cortex-m3`, soft-float, 각 프로젝트의 F103 linker script로 바꾸기 전에 실제
starm-clang 지원 여부를 확인한다.

완료 조건: 해당 toolchain으로 configure/build가 성공하고 map file의 vector table과
Flash region이 F103 linker script와 일치한다. 이 항목은 Sprint 01의 기본 GNU build
검증을 대체하지 않는다.

### F103 프로젝트의 F4 잔재 분리

대상:

- `boot_can_custom_f103/Core/Src/system_stm32f4xx.c`
- `boot_can_isotp_f103/Core/Src/system_stm32f4xx.c`
- 각 프로젝트의 `Drivers/STM32F4xx_HAL_Driver/`

현재 CMake source list는 F1 system/HAL과 F103 startup만 사용하므로 F4 파일은 build
입력이 아니다. 삭제 전 clean build와 `compile_commands.json`을 검사해 미참조임을
확인한다. F4 실험 자료로 보존해야 한다면 삭제 대신 `reference/legacy-f407/`로
이동하는 별도 변경으로 처리한다.

완료 조건: 두 F103 bootloader의 F1-only build input, 기존 binary size 비교, F4
include/source의 미참조 확인.

### Protocol 상수의 드리프트 방지

대상:

- `can-fota-BBB/flasher/protocol.h`
- `boot_can_custom_f103/App/ap/boot_can/boot_can.h`
- `boot_can_isotp_f103/App/ap/boot_can/iso15765/isotp_defines.h`
- `docs/protocol.md`

현재 BBB와 target에 CAN ID, command, error code, header packing 정의가 나뉘어 있다.
언어/빌드가 달라 하나의 C header를 공유하지 말고, `docs/protocol.md`를 규범 source로
유지한 뒤 compile-time assertion 또는 host-side protocol test로 상수값을 검증한다.

TW-01~TW-04에서 이미 필요한 test가 있다면 그 Task의 범위에서 추가할 수 있다. 별도
host-only protocol test 체계는 TW-05 결과를 바탕으로 정한다.

완료 조건: 문서 표와 양쪽 상수값을 확인하는 자동 test, protocol format 무변경.

### Custom bootloader module 경계 정리

대상:

- `boot_can_custom_f103/App/ap/boot_can/boot_can.c`
- `boot_can_custom_f103/App/ap/boot_can/boot_can.h`
- `boot_can_custom_f103/App/hw/src/flash.c`
- `boot_can_custom_f103/App/hw/src/can.c`

수신 state machine, frame 검증, response 생성, staging/active Flash 접근을 분리한다.
첫 변경에서는 함수 추출과 `static` 제한만 수행하며 call order, timeout, buffer layout,
CAN payload는 바꾸지 않는다. 특히 ACK 유실 뒤 stale frame을 구분하지 못하는 현행
wire-level 한계는 구조 정리만으로 해결됐다고 간주하지 않는다.

완료 조건: protocol regression test, target build, 기존 firmware image로 board FOTA
smoke test(가능한 경우), binary size 증가의 검토.

### BBB flasher 오류 처리 정리

대상:

- `can-fota-BBB/flasher/custom_fota.c`
- `can-fota-BBB/flasher/fota_common.c`
- `can-fota-BBB/flasher/can_socket.c`

send/receive 오류를 호출자까지 일관되게 전파하고, timeout/retry 값을 named constant로
옮긴다. 무제한 Custom DATA retry에는 상한 또는 session deadline을 도입할지 별도
설계 결정이 필요하다. 상한은 약한 CAN 환경에서 update 성공률을 낮출 수 있으므로
P3와 분리한다.

완료 조건: 정상 ACK, NACK selective retransmit, timeout, malformed response를
SocketCAN virtual interface 또는 mock으로 검증.

## 재계획 시점

TW-05에서 build, hardware regression, CAN trace의 근거를 정리한 뒤에만 이 후보의
우선순위를 정한다. 권장 기본 순서는 toolchain 정합성 → F4 잔재 분리 → protocol
drift test → module 경계 정리다. BBB 오류 처리는 이미 TW-03에서 해결하지 못한
항목만 후속으로 이관한다.
