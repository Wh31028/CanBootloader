# CAN FOTA C 코딩 규칙

## 목적과 적용 범위

이 규칙은 사람이 직접 관리하는 C/C header에 적용한다. 목적은 FOTA 동작을 바꾸지
않고 review diff와 protocol 변경 위험을 줄이는 것이다.

- 적용: `boot_can_custom_f103/App/`, `boot_can_isotp_f103/App/`,
  `boot_can_fw_f103/App/`, `can-fota-BBB/flasher/`
- 제외: `Drivers/`, `Middlewares/`, `Core/`의 CubeMX 생성 파일, startup assembly
- 생성 파일을 수정해야 하면 생성 도구의 입력과 재생성 방법을 같은 변경에 기록한다.

## 형식

- STM32 bootloader source는 각 프로젝트의 `.clang-format`을 사용한다. 현재 기준은
  LLVM 기반, 2-space indent, Allman brace이다.
- 새 C source와 header도 이 규칙을 따른다. 대규모 기존 코드 전체를 format-only로
  바꾸지 않는다.
- 하나의 변경은 기능 변경 또는 format-only 변경 중 하나여야 한다.
- public function, type, 상수는 영어 식별자를 쓴다. 새 코드 주석은 영어로 작성한다.
  기존 주석의 번역은 별도 format/documentation 변경으로 분리한다.

## 이름과 경계

- `UPPER_SNAKE_CASE`: compile-time constant, CAN ID, command, bit mask.
- `lower_snake_case`: BBB의 함수와 변수. STM32의 기존 CamelCase public API는
  호환성을 위해 유지하고, 새 module 내부 함수는 한 스타일로 일관되게 작성한다.
- protocol 상수에는 `CUSTOM_`, `ISOTP_`, `BOOT_`처럼 소유 protocol을 나타내는
  prefix를 붙인다. 숫자 literal을 frame 생성 코드에 직접 넣지 않는다.
- module public header에는 외부 사용 API만 선언한다. 파일 내부 helper는 `static`으로
  제한한다.

## 임베디드 안전 규칙

- Flash address, image size, CAN DLC, sequence, timeout은 named constant로 표현하고
  단위(`_MS`, `_BYTES`)를 이름에 포함한다.
- CAN frame을 해석하기 전에 ID format, DLC, command, sequence와 size를 검증한다.
- Flash erase/write, CAN send/receive, CRC, jump의 실패 결과를 무시하지 않는다.
- ISR와 일반 문맥이 공유하는 값은 volatile, atomicity, critical section의 근거를
  코드 가까이에 남긴다. 긴 처리와 blocking I/O는 ISR에서 수행하지 않는다.
- `uint8_t`, `uint16_t`, `uint32_t`, `bool` 같은 고정폭 타입을 사용한다. 포인터와
  integer 변환, signed/unsigned 혼합 비교는 명시적으로 검토한다.
- bootloader에서는 heap allocation, 재귀, 무제한 재시도를 새로 도입하지 않는다.

## Protocol 변경 규칙

Custom CAN wire format 변경은 `docs/protocol.md`, BBB flasher, STM32 bootloader를
동일 변경에서 함께 갱신하고 CAN trace 또는 통합 시험으로 검증한다. 다음은 호환성
계약이므로 의도 없이 바꾸지 않는다.

- entry: Standard CAN ID `0x200`, payload `DE AD`
- Custom command/response ID: `0x100` / `0x101`
- header bit layout, little-endian integer, 256-byte block과 sequence 범위
- F103 Custom bootloader/application/staging Flash layout

## Review 체크리스트

- protocol, Flash layout, timeout 중 하나가 바뀌었는가?
- BBB와 STM32 양쪽 구현 및 `docs/protocol.md`가 일치하는가?
- 오류 경로가 기존 application의 boot 가능성을 보존하는가?
- 변경된 target을 실제 toolchain으로 build했는가? hardware 검증 여부는 분리해
  명시했는가?
