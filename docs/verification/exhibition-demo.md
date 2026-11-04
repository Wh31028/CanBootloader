# 전시회 시연: LED 구분과 결함 주입

## 시연 구성

`main`의 Custom 부트로더(복구 기능 포함)를 그대로 쓴다. STM32 쪽 프로토콜과 부트로더 코드는 변경하지 않았고, 결함은 BBB flasher에서만 주입한다.

| 상태 | LED(LD2) 토글 주기 | 이미지 |
| --- | --- | --- |
| 부트로더 | 100 ms | `boot_can_custom_f103.bin` |
| FW A | 1000 ms | `boot_can_fw_f103/build/Release/boot_can_fw.bin` |
| FW B | 400 ms | `boot_can_fw_f103/build/Release-led400/boot_can_fw.bin` |

FW B 빌드:

```sh
cd boot_can_fw_f103
cmake --preset Release -B build/Release-led400 -DAPP_LED_TOGGLE_MS=400
cmake --build build/Release-led400
```

## 결함 주입

```sh
./can_fota_flasher custom fw.bin can0 --loss 2        # DATA frame 2% 드롭
./can_fota_flasher custom fw.bin can0 --corrupt-image # 1 byte 손상, CRC 실패
```

대시보드에서는 `FAULT INJECTION (DEMO)` 메뉴로 같은 동작을 선택한다.

- `--loss`: 재전송을 포함한 DATA frame을 송신 전에 확률적으로 버린다. START/END/JUMP와 target 응답은 건드리지 않는다. 시드가 고정이라 같은 조건에서는 같은 frame이 드롭된다.
- `--corrupt-image`: 이미지 중앙의 1 byte를 전송 중에만 뒤집고, END에는 원본 CRC를 보낸다. Target은 `ERR 0x06`으로 거부해야 하고, flasher는 실패로 종료한다(exit code 6). 이 실패가 정상 결과다.

결함 주입은 Custom protocol 전용이다. 옵션을 주지 않으면 전송 동작은 기존과 같다.

## RAW CAN ANALYZER 표시

대시보드 분석 패널은 결함 이벤트를 일반 프레임과 구분해 표시한다. 첫 전송 DATA frame은 200 ms마다 최대 50개만 표본 표시하지만, 재전송과 START/END/JUMP, `0x101` 응답, `0x200`은 이 제한과 별도로 전달한다. 이벤트 행은 해석 문구와 실제 HEX를 함께 표시한다.

| 행 | 출처 | 의미 |
| --- | --- | --- |
| `seq N DROPPED (not on bus)` | flasher `[FAULT]` 로그 | 주입 기록이다. 드롭된 frame은 버스에 없으므로 수신 결과가 아니다 |
| `NACK missing: ...` | 버스의 `0x101` frame | Target이 보고한 누락 seq |
| `RETX seq N` | 버스의 `0x100` frame | 현재 block에서 이미 지난 seq가 다시 나온 frame |
| `ERR 0x06 (...)` | 버스의 `0x101` frame | Target 오류 응답 |

꼬리 frame이 드롭된 경우 그 재전송은 이미 지난 seq가 아니므로 `RETX`로 분류되지 않는다. 따라서 `RETX` 카운터는 flasher의 재전송 수보다 작을 수 있고, 정확한 값은 `[RESULT]` 로그를 기준으로 한다.

## 검증 결과

### Build (실행함)

| Target | Flash | RAM | 결과 |
| --- | --- | --- | --- |
| `boot_can_custom_f103` Release | 9,480 B / 16 KiB | 3,192 B | PASS |
| `boot_can_fw` Release (1000 ms) | 10,408 B / 57,336 B | 5,304 B | PASS |
| `boot_can_fw` Release (400 ms) | 10,408 B / 57,336 B | 5,304 B | PASS |
| BBB flasher, x86-64 Linux gcc `-Wall -Wextra` | - | - | PASS, 경고 없음 |

두 FW `.bin`은 1 byte만 다르다.

### Host simulation (실행함, hardware 시험 아님)

실제 `boot_can.c`(Cortex-M jump 코드 제외)와 실제 `custom_fota.c`, `fota_common.c`를 가짜 Flash/CAN과 연결해 ASan/UBSan으로 실행했다. 이미지는 FW A → FW B 이고, 하네스는 repo에 포함하지 않았다.

| 조건 | 결과 | 드롭 | 재전송 | NACK | 타임아웃 | Active 영역 |
| --- | --- | --- | --- | --- | --- | --- |
| 손실 0% | 성공 | 0 | 0 | 0 | 0 | FW B |
| 손실 1% | 성공 | 11 | 11 | 9 | 0 | FW B |
| 손실 2% | 성공 | 29 | 29 | 20 | 1 | FW B |
| 손실 5% | 성공 | 81 | 80 | 40 | 8 | FW B |
| 손실 20% | 성공 | 399 | 351 | 82 | 64 | FW B |
| 1 byte 손상 | `ERR 0x06`, exit 6 | 0 | 0 | 0 | 0 | FW A 유지 |
| 1 byte 손상 + 손실 2% | `ERR 0x06`, exit 6 | 29 | 29 | 20 | 1 | FW A 유지 |

CRC 실패 뒤 정상 재시도는 두 경우 모두 성공했다. 시뮬레이션은 전송 시간, 실제 CAN timing, 10초 timeout 복귀를 재현하지 않는다.

### Analyzer 해석 (실행함, hardware 시험 아님)

시뮬레이션 frame trace를 `decode_custom_event()`에 넣어 flasher 로그와 비교했다.

| 조건 | 드롭 행 | NACK 누락 목록 | RETX / flasher 재전송 | ERR |
| --- | --- | --- | --- | --- |
| 손실 1% | 11 | 9건 모두 일치 | 11 / 11 | 없음 |
| 손실 2% | 29 | 20건 모두 일치 | 28 / 29 | 없음 |
| 손실 5% | 81 | 40건 모두 일치 | 78 / 80 | 없음 |
| 1 byte 손상 | 0 | 없음 | 0 / 0 | `ERR 0x06` |

화면 로직은 DOM stub과 QuickJS로 실행해 카운터, 이벤트 행 유지, 토글, 초기화를 확인했다. 실제 브라우저 렌더링은 확인하지 않았다.

### BBB 배포 (실행함)

BBB는 Yocto 이미지이고 target에 compiler가 없어 flasher를 `arm-linux-gnueabihf-gcc`로 static cross build했다.

```sh
cd can-fota-BBB/flasher
make CC=arm-linux-gnueabihf-gcc LDFLAGS=-static
```

- `/usr/share/can-fota`의 `can_fota_flasher`, `web_dashboard/main.py`, `web_dashboard/templates/index.html`을 교체하고 `can-fota.service`만 재시작했다.
- Target의 `main.py`는 Yocto용으로 수정된 사본이라(`/sbin/ip` 직접 호출, `sudo` 미사용) repo 파일로 덮어쓰지 않고 fault 관련 변경만 적용했다.
- 확인 결과: 새 flasher 실행, 대시보드 페이지의 fault 메뉴 제공, 잘못된 `fault` 값과 ISO-TP + fault 조합 거부, `can0` `ERROR-ACTIVE` / 500 kbps.
- Analyzer 배포 후 `cansend`로 `0x101` frame을 보내 ERR/NACK 이벤트 행이 WebSocket으로 전달되는 것을 확인했다. 이 시험의 NACK은 block 정보가 없어 누락 목록이 비어 있다.
- 이 변경은 Yocto layer에 반영되지 않았으므로 이미지를 다시 굽으면 사라진다.

### Hardware

아래 "사용자 관찰"은 대시보드에서 사용자가 직접 실행하고 본 결과이며, 자동 측정이나 저장된 trace가 아니다.

| 항목 | 상태 | 근거 |
| --- | --- | --- |
| 대시보드 경유 실행 | 사용자 관찰 | 패킷 손실과 CRC Failure를 대시보드에서 실행 |
| CRC 실패 시 `ERR 0x06` 표시 | 사용자 관찰 | Analyzer에 `ERR 0x06 (CRC mismatch, image rejected)` 표시 |
| 손실 주입 시 재전송 | 사용자 관찰 | Analyzer의 `RETX seq 10` 뒤 ACK, JUMP 행 확인. 전체 trace와 `[RESULT]`는 보관하지 않음 |
| Analyzer 이벤트 표시 | 사용자 관찰 | 수정 후 동작 확인. DROP 카운터와 `[RESULT]` 값 비교는 기록 없음 |
| LED 3단계 구분 | **NOT RUN** | 결과 기록 없음 |
| CRC 실패 후 약 10초 뒤 기존 FW 복귀 | **NOT RUN** | 부트로더 대기는 관찰했으나 복귀 후 LED 속도 기록 없음 |
