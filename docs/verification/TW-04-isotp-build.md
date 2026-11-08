# TW-04 — ISO-TP target build 확인

## 한눈에 보기

- 범위: Issue #8. ISO-TP 비교 bootloader(`boot_can_isotp_f103`)의 compile blocker 제거와 build 확인만 한다.
- 원인: `isotp_port.h`가 `iso15765/isotp.h`를 `<stdint.h>`보다 먼저 include한다. `isotp.h`는 C++일 때만 `<stdint.h>`를 include한다.
- 변경: `isotp_port.h`에 `#include <stdint.h>` 한 줄 추가. submodule(isotp-c `5593428`)은 바꾸지 않았다.
- Build: 변경 전 Release/Debug 모두 `FAIL`(compile), 변경 후 모두 `PASS`. Flash 12,364 B / 16 KiB (75.46%), RAM 3,928 B / 20 KiB (19.18%).
- Hardware 시험(flash, ISO-TP update)은 하지 않았다.

## 시험 방법

로컬 checkout의 submodule에 commit되지 않은 수정이 있을 수 있으므로(아래 "미해결" 참고), commit된 내용만으로 사본을 만들어 build했다.

```sh
git archive 7062bdc boot_can_isotp_f103 | tar -x -C <scratch>
git -C boot_can_isotp_f103/App/ap/boot_can/iso15765 archive 5593428 \
  | tar -x -C <scratch>/boot_can_isotp_f103/App/ap/boot_can/iso15765
cd <scratch>/boot_can_isotp_f103
cmake --preset Release && cmake --build --preset Release
cmake --preset Debug   && cmake --build --preset Debug
```

변경 후 시험은 같은 사본에 수정한 `isotp_port.h`만 덮어써서 실행했다.

Toolchain: GNU Tools for STM32 13.3.rel1 (`arm-none-eabi-gcc` 13.3.1), CMake 3.28.1, Ninja 1.11.1 (STM32CubeCLT 1.19.0, Windows).

## 결과

| Preset | 변경 전 (`7062bdc`) | 변경 후 |
| --- | --- | --- |
| Release | `FAIL`: `isotp_port.c.obj` compile, `error:` 61개 (`unknown type name 'uint8_t'` 등) | `PASS` (link, `.bin` 생성) |
| Debug | `FAIL`: 위와 같음 | `PASS` |

- `ninja -k 0`으로 끝까지 build해도 실패한 object는 `isotp_port.c.obj` 하나였다. `isotp.c`는 첫 줄에서 `<stdint.h>`를, `boot_can.c`는 `boot_can.h` → `ap_def.h`를 먼저 include하므로 통과한다.
- 변경 후 warning 2개는 기존 warning이다: `boot_can.c` `SendResponse` 미사용, `flash.c` `FLASH_PAGE_SIZE` 재정의.

### Memory 사용량 (변경 후)

| Preset | `text` | `data` | `bss` | Flash (16 KiB) | RAM (20 KiB) | `.bin` SHA-256 |
| --- | --- | --- | --- | --- | --- | --- |
| Release | 12,268 | 96 | 3,832 | 12,364 B (75.46%) | 3,928 B (19.18%) | `65cf019813a08e07455835c5b9166f289152a403588ba16fee08e12c1c571f93` |
| Debug | 12,268 | 96 | 3,832 | 12,364 B (75.46%) | 3,928 B (19.18%) | `65cf019813a08e07455835c5b9166f289152a403588ba16fee08e12c1c571f93` |

변경 전에는 link까지 가지 못해 memory 사용량을 측정할 수 없다. 추가한 줄은 type 선언만 가져오므로 code와 data를 만들지 않는다.

## 미해결 / 한계

- **Debug/Release preset이 적용되지 않는다.** `boot_can_isotp_f103/CMakeLists.txt`가 `CMAKE_BUILD_TYPE`을 `MinSizeRel`로 `FORCE`하고 target option에 `-Os`를 항상 넣는다. configure log도 두 preset 모두 `Build type: MinSizeRel`이고, 두 `.bin`의 hash가 같다. 이번 범위에서는 고치지 않았다.
- **로컬 submodule 수정:** 작업한 Windows checkout의 submodule에는 `isotp_defines.h`에 `#include "ap_def.h"`가 추가돼 있었고, 로컬 config의 `submodule.<path>.ignore = dirty` 때문에 `git status`에 보이지 않았다. commit되지 않은 수정이라 clone에서는 재현되지 않는다. 이번 수정 후에는 그 수정 없이도 build된다.
- TW-04의 선택 항목(START size 검증, receive/padding buffer 경계, host FC BS/STmin 준수, frame counter)은 하지 않았다. ISO target은 active 영역에 직접 쓰므로 Custom staging/copy 결과와 같은 조건으로 비교하지 않는다.
