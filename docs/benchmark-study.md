# Benchmark Study

## 목적과 가설

이 benchmark는 direct-write Flash 조건에서 ISO-TP와 Custom Selective NACK의 전송·재전송 특성을 비교합니다. 가설은 누락 frame만 식별해 재전송하는 Custom 방식이 손실이 있는 특정 조건에서 전체 block 재시도보다 적은 재전송을 보일 수 있다는 것입니다. 이는 실험 가설이지 일반적 성능 보장은 아닙니다.

## 공통 구현 조건

F103의 두 bootloader는 `0x08004000`부터 `0x08013FFF`까지, 최대 64 KB(65,536 bytes) application image를 직접 erase/write합니다. END 단계의 CRC 검사는 전송 protocol의 종료 확인으로 남아 있지만, staging, persistent recovery metadata, active image copy는 이 비교 구성에 없습니다.

## 실험 환경과 데이터

| 구분 | F103 direct-write 실험 | F407 실험 |
|---|---|---|
| bootloader/script | `boot_can_*_f103/`, `*_f103.py` | `boot_can_custom/`, `boot_can_isotp/`, `boot_can_fw/`, 비-F103 sender |
| CAN bitrate | 500 kbit/s | script 기준 1 Mbit/s |
| firmware size | runner 기준 64 KB | runner 기준 64/128/256/512 KB |
| loss setting | 0, 0.01, 0.05, 0.1% | 0, 0.01, 0.05, 0.1% |
| 반복 | 각 조건·protocol 30회 | 각 조건·protocol 30회 |
| CSV | `result/fota_results_f103.csv` | `result/fota_results_new.csv` |

runner는 loss probability `0`, `0.0001`, `0.0005`, `0.001`을 sender에 전달하고 sender는 여기에 100을 곱해 CSV `loss_rate_pct`에 0, 0.01, 0.05, 0.1%로 기록합니다.

## F103 CSV에서 확인되는 결과

`fota_results_f103.csv`는 65,536 byte, `OK` record를 담습니다. protocol·CSV loss-rate별 record 수는 각각 30건입니다.

| CSV loss-rate 표기 | Custom 평균 시간 / 평균 재전송 | RAW ISO-TP 평균 시간 / 평균 재전송 |
|---:|---:|---:|
| 0.00000 | 6.142 s / 0.00 | 6.661 s / 0.00 |
| 0.01000 | 6.145 s / 0.93 | 6.779 s / 27.13 |
| 0.05000 | 6.187 s / 4.50 | 7.427 s / 180.07 |
| 0.10000 | 6.186 s / 9.43 | 8.078 s / 334.23 |

이 표는 해당 CSV의 산술 평균입니다. sender 처리, test-run 순서, CAN controller 상태, packet-loss 주입 방식이 결과에 영향을 줄 수 있으므로 신뢰구간이나 다른 환경의 성능을 뜻하지 않습니다.

## F407 CSV에서 확인되는 결과

`fota_results_new.csv`는 1 Mbit/s에서 64/128/256/512 KB, 네 loss-rate, 두 protocol, 조건별 30회로 총 960개의 `OK` record를 담습니다. 대표적으로 0%와 0.1% 구간의 평균 전송 시간은 다음과 같습니다.

| Firmware | Loss | Custom | RAW ISO-TP |
|---:|---:|---:|---:|
| 64 KB | 0% | 2.221 s | 2.805 s |
| 64 KB | 0.1% | 2.271 s | 4.288 s |
| 128 KB | 0% | 4.876 s | 5.554 s |
| 128 KB | 0.1% | 4.947 s | 8.456 s |
| 256 KB | 0% | 9.140 s | 10.016 s |
| 256 KB | 0.1% | 9.362 s | 16.011 s |
| 512 KB | 0% | 17.834 s | 19.110 s |
| 512 KB | 0.1% | 18.246 s | 30.716 s |

발표자료의 “64 KB +26.3%, 512 KB +7.2%”는 0% 구간에서 ISO-TP 시간이 Custom보다 긴 비율이고, “64 KB +88.8%, 512 KB +68.3%”는 0.1% 구간의 같은 비교입니다. 원시 CSV 평균과 반올림 수준에서 일치합니다.

## Script, CSV, 발표자료의 관계

- `test_runner_f103.sh`가 `_f103` sender를 64 KB 대상으로 호출합니다.
- `loss_test_custom_f103.py`와 `loss_test_isotp_raw_f103.py`가 `fota_results_f103.csv`에 같은 column schema로 기록합니다.
- Git history에서 F103 loss test는 `4ebcb04`, F103 CSV/그래프 추가는 `4abd123`에 나타납니다. 따라서 script와 CSV는 하나의 단일 commit으로 묶어 단정하지 않습니다.
- `reference/capstone-presentation.pptx`의 1 Mbit/s, 64–512 KB 그래프는 `fota_results_new.csv` 기반 F407 결과와 대응합니다. F103 및 STmin 5 ms 슬라이드는 별도 실험 단계이므로 F407 평균과 섞지 않습니다.

## 범위와 재현성

script는 firmware padding, loss rate, trial을 입력받고 timestamp, frame 수, retransmission, status를 CSV에 기록합니다. 이 repository는 실행 script와 원시 CSV를 제공하지만, hardware setup·배선·Yocto 설정은 이 포트폴리오 문서 범위에서 제외합니다. 재실행 결과는 board, CAN bus 및 host load에 따라 달라질 수 있습니다.
