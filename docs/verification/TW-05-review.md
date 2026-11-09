# TW-05 — 정상 update 확인과 성능 수치 조건·한계

## 한눈에 보기

- 범위(2차 축소): ① `main` clean build 후 BBB → F103 Custom 정상 update 1회 ② 이력서 성능 수치의 측정 조건·한계 확정 ③ README 조건·한계 표.
- 진행 상태: **② 완료(문서 분석, hardware 불필요)**. ①·③은 아직 하지 않았다(`NOT RUN`).
- ② 결론: 이력서 수치(0.1% 손실, 16.011 s → 9.362 s, 재전송 1,424.5 → 35.3)는 결과 CSV에서 그대로 재현된다. 다만 CSV를 만든 code는 실행 당시 commit되어 있지 않았고, 두 방식의 시간 경계와 재전송 counter 정의가 다르다. 수치는 아래 조건을 붙여서만 인용한다.

## ② 성능 수치의 조건과 한계

### 근거 자료

| 자료 | 위치 |
| --- | --- |
| 결과 CSV | `origin/capston-1`(`7527bca`)의 `can-fota-BBB/result/fota_results_new.csv` (현재 `main`에는 없음) |
| CSV 첫 commit | `b45708c` (2026-05-21) |
| CSV 실행일에 commit되어 있던 source | `42d2e25` (2026-05-09, CSV timestamp와 같은 날) |
| CSV 조건과 일치하는 source | `b1f32a3` (2026-05-16) `can-fota-BBB/loss_test_custom.py`, `loss_test_isotp_raw.py`, `test_runner.sh` |
| F407 target source | `42d2e25`의 `boot_can_custom/`(Custom), `boot_can/`(ISO-TP) |

### 재현: PASS

CSV를 조건별로 다시 계산했다(재현 명령은 맨 아래).

- 960행, 모두 `OK`. 4 sizes(64/128/256/512 KiB) × 4 loss(0/0.01/0.05/0.1%) × 2 방식 × 30회.
- 256 KiB, 0.1% loss 평균:

| 방식 | 전송 시간 평균 (sd, min–max) | 재전송 frame 평균 (min–max) |
| --- | --- | --- |
| RAW ISO-TP | 16.011 s (0.889, 13.965–17.801) | 1,424.50 (962–1,850) |
| Custom | 9.362 s (0.184, 9.140–9.867) | 35.30 (26–48) |

### source로 확인한 측정 조건

| 항목 | Custom (Selective NACK) | RAW ISO-TP (block 재시도) | 근거 |
| --- | --- | --- | --- |
| Target | STM32F407, `0x08010000`에 **direct-write**(staging 없음), START에서 erase | 같음 | `42d2e25` `hw_def.h`, `boot_can.c` |
| CAN bitrate | 1 Mbit/s | 1 Mbit/s | 두 sender의 `ip link set can0 up type can bitrate 1000000` |
| Payload | 256 B block, DATA 7 B/frame, 최대 37 frame | `CMD` 1 B + 256 B를 ISO-TP FF 1 + CF 36으로 전송 | 두 sender |
| Firmware | `received_fw.bin`을 `i % 256` pattern으로 목표 크기까지 padding | 같음 | 두 sender |
| Loss 모델 | 송신 측 application에서 `random.random() < p`이면 frame을 보내지 않음 (Bernoulli omission). DATA와 재전송 DATA에만 적용 | 같은 방식. **CF에만 적용**, FF·SF 제외 | 두 sender |
| 응답 frame loss | 없음 (ACK/NACK, START/END, tail probe는 드롭하지 않음) | 없음 (FC, ACK, SF는 드롭하지 않음) | 두 sender |
| Random seed | 설정하지 않음 | 설정하지 않음 | `random.seed` 사용 0건 |
| **시간 경계** | START 송신 → END ACK 수신 | START 송신 → END ACK → **`sleep(0.5)` → JUMP 송신** | 두 sender |
| **tx counter** | 드롭한 frame도 셈 (송신 시도 수) | 실제 송신한 frame만 셈 | 두 sender |
| **재전송 counter** | 실제 재송신 시도 수(NACK 선택 재전송 + tail probe) | **block 재시도 횟수 × 37** (실제 송신 수가 아닌 추정값) | 두 sender |
| 손실 복구 | target이 bitmap NACK → 누락 frame만 즉시 재전송. 마지막 frame 유실 시 150 ms 후 tail probe | ACK 150 ms timeout 후 256 B block 전체 재전송 (최대 50회) | 두 sender |
| 실행 순서 | Custom 480회 전부 → ISO-TP 480회 전부. 교차·무작위화 없음 | | CSV timestamp |
| 반복 | 조건당 30회 | 조건당 30회 | CSV |

### 확인할 수 없는 것

1. **CSV를 만든 code가 실행 당시 commit되지 않았다.** CSV 실행일(05-09)의 `42d2e25` `test_runner.sh`는 크기별로 loss 배열이 달랐다(64 KiB: 0.01/0.1/0.5%, 그 외: 0.001/0.005/0.01%). CSV는 모든 크기에서 0.01/0.05/0.1%이며, 이 배열은 7일 뒤 `b1f32a3`에서 처음 나타난다. ISO-TP 재시도 상한도 `42d2e25`는 3회, `b1f32a3`는 50회다. 따라서 CSV는 BBB에 있던 commit되지 않은 code로 실행된 것으로 보이며, `b1f32a3`는 조건이 일치하는 가장 가까운 commit일 뿐이다.
2. **당시 target ISO-TP library와 BS/STmin 설정.** isotp-c는 2026-08-11(`12b5972`)에야 submodule로 들어왔다. CSV의 수신 frame 수(block당 2 = FC 1 + ACK 1)는 BS=0과 맞지만 증명은 아니다. sender는 첫 FC의 type만 확인하고 BS=0/STmin=0을 가정한다.
3. Bootloader·application binary hash, BBB 시계의 timezone, candump trace는 남아 있지 않다.

### 해석

- **무손실 차이는 대부분 측정 경계에서 나온다.** ISO-TP 시간에만 0.5 s sleep이 들어 있다. 이 0.5 s를 빼면(추정) 0% loss 차이는 64 KiB에서 +26.3% → 약 +3.8%(2.305 s vs 2.221 s), 256 KiB에서 +9.6% → 약 +4.1%(9.516 s vs 9.140 s)로 줄어든다.
- **0.1% loss의 시간 차이는 유지된다.** 0.5 s를 빼도 256 KiB에서 15.51 s vs 9.36 s다(Custom이 약 40% 짧음, 원값 기준 41.5%).
- **ISO-TP 시간 증가는 sender의 timeout 값에 크게 의존한다.** 256 KiB의 0% → 0.1% 증가는 5.995 s다. 평균 block 재시도 38.5회(1,424.5 / 37) × 150 ms ≈ 5.78 s로 거의 설명된다. 즉 이 비교는 "누락 frame만 즉시 재전송" 대 "150 ms timeout 후 block 전체 재시도"의 비교다. ISO-TP 표준 자체와 비교한 것이 아니다(ISO-TP에는 재전송이 없고, 재시도는 이 실험 sender의 application 정책이다).
- **1,424.5 → 35.3은 같은 방식으로 센 숫자가 아니다.** ISO-TP는 재시도 1회당 37을 더한 추정값이고, Custom은 실제 재송신 시도 수다. 두 값 모두 software omission 기준이며 bus 위 frame 수(candump)가 아니다.
- **현재 F103 구조의 성능이 아니다.** 현재 `main`의 F103 Custom은 500 kbit/s, 57,336 B 한도의 staging + CRC + active copy 구조다. 이 수치는 F407 direct-write, 1 Mbit/s 결과다.

### 인용 범위

| 해도 되는 표현 | 하지 않는 표현 |
| --- | --- |
| F407 direct-write, 256 KiB, 1 Mbit/s, 송신 측 software 손실 0.1%(seed 미기록), 각 30회에서 block 재시도 방식 대비 평균 전송 시간 16.0 s → 9.4 s | "ISO-TP보다 41.5% 빠르다" (표준 ISO-TP 일반화) |
| 재전송 frame 약 1,424 → 35 (재시도 방식은 block 단위 추정치, 150 ms timeout 의존) | "재전송 97.5% 감소"를 조건 없이 사용 |
| 무손실에서는 차이가 작다 | 무손실 +26.3% 차이를 protocol 비용으로 해석 |
| | 실제 bus error, BER, 차량 환경 신뢰성, 현재 F103 staging 구조의 성능 |

### 문서 반영

- job_prepare 이력서 `resume-master-v1.md`, 경험 카드 `exp-20261101-02`를 위 "해도 되는 표현"에 맞게 수정했다(같은 날, job_prepare `main`).
- README 조건·한계 표(③)에 이 절을 요약한다(`NOT RUN`).
- 선택(하지 않음): 고정 seed와 같은 fault schedule로 재측정.

### 재현 명령

```sh
git show 7527bca:can-fota-BBB/result/fota_results_new.csv > fota_results_new.csv
python3 - fota_results_new.csv <<'EOF'
import csv, sys, statistics as st, collections
g = collections.defaultdict(list)
for r in csv.DictReader(open(sys.argv[1])):
    g[(r['protocol'], int(r['fw_size_bytes']), r['loss_rate_pct'])].append(r)
for k in sorted(g):
    t = [float(r['total_time_sec']) for r in g[k]]
    rt = [int(r['retransmit_frames']) for r in g[k]]
    print(k, len(t), f"{st.mean(t):.3f} sd={st.stdev(t):.3f}", f"retx={st.mean(rt):.2f}")
EOF
git diff 42d2e25 b1f32a3 -- can-fota-BBB/test_runner.sh   # loss 배열 차이
git grep -n "random.seed" b1f32a3 -- can-fota-BBB/        # 0건
```

## ① 정상 update 1회

`NOT RUN` (다음 세션, Windows + WSL).

## ③ README 조건·한계 표

`NOT RUN`.
