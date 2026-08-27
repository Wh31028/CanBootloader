# STM32F407 CAN FOTA Benchmark

## 실험 목적

STM32F407VGT6 환경에서 ISO-TP와 Custom Selective NACK의 전송 시간, bus traffic 및 재전송 overhead를 firmware size와 software-injected packet loss에 따라 비교했습니다. F407 결과의 기준 데이터는 [`fota_results_new.csv`](../can-fota-BBB/result/fota_results_new.csv)입니다.

## 실험 조건

| 항목 | 조건 |
|---|---|
| Target MCU | STM32F407VGT6, Cortex-M4, 168 MHz, 1 MB Flash, 192 KB RAM |
| Sender | BeagleBone Black, Linux SocketCAN |
| CAN bitrate | 1 Mbit/s |
| Firmware size | 64, 128, 256, 512 KB |
| CSV loss-rate | 0, 0.01, 0.05, 0.1% |
| 반복 | 각 size × loss × protocol 조합 30회 |
| 전체 record | 4 sizes × 4 loss-rates × 2 protocols × 30 = 960, 모두 `OK` |
| ISO-TP 설정 | 발표자료 기준 `BS=256`, `STmin=0`, `N_Cr=150 ms` |
| Custom 설정 | 256 B block, Selective NACK, `N_Cr=150 ms` |

`test_runner.sh`가 네 firmware size와 네 loss input을 순회하고, `loss_test_custom.py`와 `loss_test_isotp_raw.py`가 timestamp, frame count, retransmission 및 status를 CSV schema로 기록합니다.

## 전송 시간 결과

다음 값은 `fota_results_new.csv`에서 조건별 30회 전송 시간을 산술 평균한 결과입니다.

| Firmware | Loss | Custom | RAW ISO-TP | 관측된 차이 |
|---:|---:|---:|---:|---:|
| 64 KB | 0% | 2.221 s | 2.805 s | ISO-TP +26.3% |
| 64 KB | 0.1% | 2.271 s | 4.288 s | ISO-TP +88.8% |
| 128 KB | 0% | 4.876 s | 5.554 s | ISO-TP +13.9% |
| 128 KB | 0.1% | 4.947 s | 8.456 s | ISO-TP +70.9% |
| 256 KB | 0% | 9.140 s | 10.016 s | ISO-TP +9.6% |
| 256 KB | 0.1% | 9.362 s | 16.011 s | ISO-TP +71.0% |
| 512 KB | 0% | 17.834 s | 19.110 s | ISO-TP +7.2% |
| 512 KB | 0.1% | 18.246 s | 30.716 s | ISO-TP +68.3% |

0% loss에서도 ISO-TP에는 Flow Control 및 block-level coordination 비용이 존재하지만 image가 커질수록 비율 차이는 26.3%에서 7.2%로 줄었습니다. 반면 0.1% loss에서는 block retry가 누적되어 ISO-TP 시간이 더 크게 증가했습니다. Custom도 재전송이 발생했지만 해당 CSV에서 시간 증가 폭은 상대적으로 작았습니다.

## Traffic과 재전송

0.1% loss, 256 KB에서 평균 재전송 frame은 Custom 35.30, RAW ISO-TP 1,424.50이었습니다. 발표자료는 이를 재전송 overhead 약 0.09%와 3.62%로 요약합니다. 이 차이는 누락 frame만 다시 보내는 Selective NACK과 256 B block을 다시 보내는 ISO-TP 실험 recovery 단위의 차이를 반영합니다.

## 발표자료 그래프와의 대응

발표자료 [`capstone-presentation.pptx`](../reference/capstone-presentation.pptx)의 다음 그래프는 `fota_results_new.csv`의 F407 실험과 대응합니다.

- 전체 전송 시간: size·loss-rate별 평균과 64/512 KB 상대 차이
- Total bus traffic: ISO-TP block retry와 Custom selective retry의 frame 증가
- Retransmission overhead: 256 KB, 0.1% loss 대표 비교

발표자료의 수치와 CSV 평균이 일치하므로 문서의 대표 값에 활용했습니다. [`plot_all_graphs.py`](../can-fota-BBB/result/plot_all_graphs.py)는 같은 CSV schema를 시각화하는 코드입니다. [`fota_result_STmin5.csv`](../can-fota-BBB/result/fota_result_STmin5.csv)는 STmin 5 ms stress test이므로 이 F407 기본 결과 표에는 포함하지 않았습니다.

## F103 실험과의 구분

F103RBT6 실험은 500 kbit/s와 64 KB만 사용했습니다. 발표자료는 저사양 MCU로 변경하면서 64 KB 기본 전송 시간이 약 2.2 s에서 약 6.1 s로 늘었다고 설명합니다. 이는 MCU와 bitrate가 함께 달라진 결과이므로 protocol 자체의 효과로 분리하지 않습니다. F103 수치는 [`benchmark-study.md`](benchmark-study.md)의 별도 표에서 다룹니다.

## 해석 한계

packet loss는 실제 차량 BER 재현이 아니라 software fault injection 기반 sensitivity analysis입니다. 실험은 gateway와 단일 ECU 간 1:1 통신이며 혼합 CAN traffic, arbitration delay, 다중 ECU 동시 update는 평가하지 않았습니다. 또한 authentication, firmware signature, anti-rollback, 전원 차단 recovery 또는 production-grade reliability를 검증하지 않았습니다.
