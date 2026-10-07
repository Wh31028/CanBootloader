# F407ㆍBBB 실험 장비 운영 안내

이 문서는 처음 장비를 넘겨받은 사람이 F407 보드와 BeagleBone Black(BBB)에 **안전하게 접속하고 상태를 확인하는 방법**을 설명한다. P03에서 실제로 확인한 구성 기준이며, 이 문서는 Flash 기록이나 P04 본 실험을 자동으로 허가하지 않는다.

## 1. 알고 있어야 할 장비 구성

| 항목 | 확인된 값 |
| --- | --- |
| MCU 보드 | STM32F4DISCOVERY, Device ID `0x413` |
| ST-LINK | SN `066BFF3332584B3043252734`, V2J46M31 |
| BBB | `debian@192.168.7.2`, hostname `beaglebone` |
| CAN | BBB `can0`, 500,000 bit/s, external CAN transceiver와 양 끝 종단 저항 사용 |
| F407 CAN1 pin | PD0=RX, PD1=TX, AF9 |
| application FOTA 영역 | `[0x08010000, 0x08020000)` (64 KiB, sector 4) |
| bootloader 영역 | `0x08000000`; 기록 시 sector 0--2만 대상 |

CAN H/CAN L/GND와 transceiver 전원을 연결하고, 보드와 BBB가 모두 켜진 뒤 시작한다. `can0`이 `ERROR-PASSIVE`이면 sender를 실행하지 말고 아래 CAN reset을 먼저 한다.

## 2. SSH 접속

P03용 private key는 이 PC의 다음 위치에 있다. **키 파일 내용이나 BBB 비밀번호를 문서ㆍGit에 넣지 않는다.**

```text
C:\Users\wh310\.ssh\canboot_p03_agent_ed25519
```

PowerShell에서 접속을 확인하는 명령은 다음과 같다.

```powershell
ssh -i C:\Users\wh310\.ssh\canboot_p03_agent_ed25519 `
  -o IdentitiesOnly=yes -o BatchMode=yes -o ConnectTimeout=5 `
  debian@192.168.7.2 "hostname; id"
```

`beaglebone`과 `uid=1000(debian)`이 보이면 접속 성공이다. `Permission denied`가 나오면 private key 경로, BBB USB 연결, 그리고 BBB의 `~/.ssh/authorized_keys`에 해당 public key가 남아 있는지를 확인한다.

사람이 자주 쓴다면 Windows의 `C:\Users\wh310\.ssh\config`에 아래 별칭을 추가할 수 있다. 이미 같은 `Host` 이름이 있으면 새로 만들지 말고 기존 설정을 사용한다.

```sshconfig
Host canboot-bbb
    HostName 192.168.7.2
    User debian
    IdentityFile C:/Users/wh310/.ssh/canboot_p03_agent_ed25519
    IdentitiesOnly yes
    BatchMode yes
```

그 뒤에는 `ssh canboot-bbb`로 접속한다.

## 3. CAN 상태 확인과 재설정

먼저 상태를 읽는다.

```bash
ip -details -statistics link show can0
```

정상 기준은 `UP`, `LOWER_UP`, `ERROR-ACTIVE`, `bitrate 500000`이며 tx/rx error counter가 0이다. BBB의 `/etc/sudoers.d/canboot-can0`에는 아래 두 명령만 비밀번호 없이 실행하도록 제한돼 있다. 다른 `sudo` 명령은 비밀번호가 필요하다.

```bash
sudo -n /bin/ip link set can0 down
sudo -n /bin/ip link set can0 up type can bitrate 500000 sample-point 0.875
ip -details link show can0
```

Codex나 PowerShell에서 원격 실행할 때는 위 세 줄을 SSH로 전달한다. P03에서 이 명령은 실제로 성공했고, reset 뒤 `ERROR-ACTIVE`, 500 kbit/s, tx/rx error 0/0을 확인했다.

## 4. FOTA를 실행하기 전의 안전 gate

다음 항목이 모두 확인되기 전에는 CAN sender나 ST-LINK write 명령을 실행하지 않는다.

1. 대상 보드 모델ㆍST-LINK serialㆍ현재 image와 복구 수단을 확인한다.
2. `can0`이 위 정상 기준인지 확인한다.
3. 사용할 bootloader와 application의 **정확한 SHA-256, 주소, erase 범위**를 기록한다.
4. 사용자가 해당 exact hash에 대해 program/verify 및 FOTA를 명시 허가했는지 확인한다.
5. 새 run ID와 저장 위치를 정한다. 기존 CSV/run은 덮어쓰지 않는다.

P03에서 application이 정상 실행 중일 때는 standard CAN `0x200#DEAD`가 FOTA-entry reset trigger였다. application이 없거나 깨진 상태에서는 이 frame이 bootloader 진입을 보장하지 않는다. 이 경우 먼저 실제 board 상태와 recovery 계획을 확인한다.

## 5. 기록과 보존

각 시도에는 run ID, command, bootloader/application hash, bitrate, seed, 종료 상태, `raw.csv`, `events.jsonl`, `candump`를 남긴다. BBB의 wall clock은 P03에서 동기화되지 않아 raw CSV의 UTC timestamp를 절대 시간 근거로 쓰지 않았다. 시간 비교에는 sender의 monotonic `elapsed_sec`를 사용한다.

원시 hardware evidence는 로컬 `docs/paper-plan/reports/artifacts/<Task-ID>/bbb-.../`에 보관한다. 이 경로와 Flash readback `.bin`은 `.gitignore` 대상이다. GitHub에는 원시 로그 대신 보고서에 다음을 남긴다.

- 목적과 안전 gate 통과 여부
- run ID와 exact hash/address/erase 범위
- 성공ㆍ실패를 포함한 결과 요약과 monotonic 시간
- raw evidence의 로컬 경로와 SHA-256
- 재현에 필요한 sender 명령

P03의 실제 예와 실패 원인은 [P03 보고서](reports/P03.md), 다음 대화의 현재 상태와 SSH reset 준비는 [SESSION_HANDOFF](SESSION_HANDOFF.md)를 기준으로 한다.

## 6. 새 대화에서의 최소 시작 순서

1. `AGENTS.md`, `README.md`, `SESSION_HANDOFF.md`, 해당 Task 절과 직전 보고서를 읽는다.
2. `git status --short --branch`, `git rev-parse HEAD`, `git submodule status`로 기존 변경을 보존한다.
3. SSH 연결과 `can0` 상태를 확인하고, 필요할 때만 허용된 500 kbit/s reset을 실행한다.
4. 현재 Task의 허가와 범위 안에서만 새 run을 만든다.
5. 종료 시 보고서ㆍREADME 상태ㆍhandoff를 갱신하고, 사용자의 별도 요청 없이는 commit/push하지 않는다.
