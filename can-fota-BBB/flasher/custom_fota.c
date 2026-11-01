#include <stdio.h>
#include <string.h>

#include "can_socket.h"
#include "custom_fota.h"
#include "fota_common.h"
#include "protocol.h"

/* Host-side timeout and retry policy (not part of the wire format). */
#define CUSTOM_START_ACK_TIMEOUT_MS  10000
#define CUSTOM_BLOCK_RESP_TIMEOUT_MS 150
#define CUSTOM_BLOCK_MAX_RETRIES     20
#define CUSTOM_DATA_PHASE_TIMEOUT_MS 120000
#define CUSTOM_END_ACK_TIMEOUT_MS    10000
#define CUSTOM_JUMP_DELAY_MS         500
#define CUSTOM_JUMP_ACK_TIMEOUT_MS   1000

typedef struct {
    int tx_frames;
    int rx_frames;
    int retransmitted_frames;
} custom_stats_t;

static uint8_t pack_custom_header(uint8_t cmd, uint8_t seq) {
    return ((cmd & 0x03) << 6) | (seq & 0x3F);
}

/* Counts the frame only when it was actually queued. */
static int send_cmd_frame(int sock, const uint8_t *data, uint8_t len, custom_stats_t *stats) {
    int ret = send_can_frame(sock, CUSTOM_CAN_ID_CMD, data, len);
    if (ret == 0) stats->tx_frames++;
    return ret;
}

/* Waits for an ACK; ERR, NACK or timeout is reported as a failure. */
static int expect_ack(int sock, int timeout_ms, const char *stage, custom_stats_t *stats) {
    uint8_t rx_cmd;
    uint64_t rx_args;
    int ret = wait_custom_response(sock, timeout_ms / 1000.0, &rx_cmd, &rx_args);
    if (ret < 0) {
        printf("[CAN] Error: %s 응답 없음 (%s, %d ms)\n", stage, fota_err_str(ret), timeout_ms);
        return ret;
    }
    stats->rx_frames++;
    if (rx_cmd == CUSTOM_CMD_TX_ACK) return 0;
    if (rx_cmd == CUSTOM_CMD_TX_ERR) {
        printf("[CAN] Error: %s 실패, target ERR 코드 0x%02llX\n", stage, (unsigned long long)rx_args);
    } else {
        printf("[CAN] Error: %s 단계에서 예상하지 않은 응답 (cmd=%u)\n", stage, rx_cmd);
    }
    return -FOTA_ERR_TARGET;
}

static void print_stats(double start_time, const custom_stats_t *stats) {
    double total_time = monotonic_now() - start_time;
    double overhead_pct = (stats->tx_frames > 0)
                              ? ((double)stats->retransmitted_frames / stats->tx_frames * 100.0)
                              : 0.0;
    printf("=============================================\n");
    printf("[RESULT] 총 소요 시간: %.2f 초\n", total_time);
    printf("[RESULT] 송신 프레임 (TX): %d 프레임\n", stats->tx_frames);
    printf("[RESULT] 수신 프레임 (RX): %d 프레임\n", stats->rx_frames);
    printf("[RESULT] 재전송 프레임: %d 프레임 (%.2f%% overhead)\n", stats->retransmitted_frames, overhead_pct);
    print_can_error_stats();
    printf("=============================================\n");
}

static int send_data_blocks(int sock, const uint8_t *fw_data, size_t fw_size, custom_stats_t *stats) {
    const double data_deadline = monotonic_now() + CUSTOM_DATA_PHASE_TIMEOUT_MS / 1000.0;
    uint8_t rx_cmd;
    uint64_t rx_args;
    int ret;

    size_t idx = 0;
    while (idx < fw_size) {
        size_t block_len = (fw_size - idx < 256) ? (fw_size - idx) : 256;

        /* Prepare frames for this block */
        int expected_frames = (block_len + 6) / 7;
        uint8_t block_frames[37][8]; /* 256 / 7 = 36.57 frames max -> 37 */
        uint8_t frame_lens[37];

        for (int seq = 0; seq < expected_frames; seq++) {
            size_t chunk_offset = seq * 7;
            size_t chunk_len = (block_len - chunk_offset < 7) ? (block_len - chunk_offset) : 7;

            block_frames[seq][0] = pack_custom_header(CUSTOM_CMD_RX_DATA, seq);
            memcpy(&block_frames[seq][1], &fw_data[idx + chunk_offset], chunk_len);
            frame_lens[seq] = chunk_len + 1;
        }

        /* Send block frames */
        for (int seq = 0; seq < expected_frames; seq++) {
            ret = send_cmd_frame(sock, block_frames[seq], frame_lens[seq], stats);
            if (ret < 0) {
                printf("\n[CAN] Error: DATA 송신 실패 (offset %zu, seq %d, %s)\n", idx, seq, fota_err_str(ret));
                return ret;
            }
        }

        /* Receive feedback: each timeout or NACK round consumes one retry. */
        int retries = 0;
        for (;;) {
            if (monotonic_now() >= data_deadline) {
                printf("\n[CAN] Error: DATA 전송 전체 제한 시간 %d ms 초과 (offset %zu)\n",
                       CUSTOM_DATA_PHASE_TIMEOUT_MS, idx);
                return -FOTA_ERR_RETRY_EXHAUSTED;
            }

            ret = wait_custom_response(sock, CUSTOM_BLOCK_RESP_TIMEOUT_MS / 1000.0, &rx_cmd, &rx_args);
            if (ret == -FOTA_ERR_RESP_TIMEOUT) {
                if (++retries > CUSTOM_BLOCK_MAX_RETRIES) break;
                printf("\n[CAN Warning] 응답 타임아웃! 꼬리 프레임 단독 송출하여 NACK 검사 트리거! (%d/%d)\n",
                       retries, CUSTOM_BLOCK_MAX_RETRIES);
                int last_seq = expected_frames - 1;
                ret = send_cmd_frame(sock, block_frames[last_seq], frame_lens[last_seq], stats);
                if (ret < 0) {
                    printf("[CAN] Error: 꼬리 프레임 재전송 실패 (%s)\n", fota_err_str(ret));
                    return ret;
                }
                stats->retransmitted_frames++;
                continue;
            }
            if (ret < 0) {
                printf("\n[CAN] Error: DATA 응답 수신 실패 (%s)\n", fota_err_str(ret));
                return ret;
            }
            stats->rx_frames++;

            if (rx_cmd == CUSTOM_CMD_TX_ACK) {
                idx += block_len;
                printf("\r[CAN] 진행률: %zu/%zu bytes (%.1f%%)", idx, fw_size, ((double)idx / fw_size) * 100.0);
                fflush(stdout);
                break;
            } else if (rx_cmd == CUSTOM_CMD_TX_NACK) {
                if (++retries > CUSTOM_BLOCK_MAX_RETRIES) break;
                uint64_t nack_map = rx_args;
                printf("\n[CAN Recovery] NACK 비트맵 수신! 선별 재전송 실행! (%d/%d)\n",
                       retries, CUSTOM_BLOCK_MAX_RETRIES);
                for (int seq = 0; seq < expected_frames; seq++) {
                    if ((nack_map & ((uint64_t)1 << seq)) == 0) {
                        ret = send_cmd_frame(sock, block_frames[seq], frame_lens[seq], stats);
                        if (ret < 0) {
                            printf("[CAN] Error: 선별 재전송 실패 (seq %d, %s)\n", seq, fota_err_str(ret));
                            return ret;
                        }
                        stats->retransmitted_frames++;
                    }
                }
            } else {
                printf("\n[CAN Error] 타겟 보드 치명적 에러! 코드: 0x%02llX\n", (unsigned long long)rx_args);
                return -FOTA_ERR_TARGET;
            }
        }

        if (retries > CUSTOM_BLOCK_MAX_RETRIES) {
            /* Protocol v1 has no block ID, so a lost block ACK cannot be told
             * apart from a silent target here. */
            printf("\n[CAN] Error: block retry 상한 %d회 초과 (offset %zu). "
                   "target 무응답 또는 v1 protocol의 ACK 유실 한계일 수 있음\n",
                   CUSTOM_BLOCK_MAX_RETRIES, idx);
            return -FOTA_ERR_RETRY_EXHAUSTED;
        }
    }
    printf("\n[CAN] 펌웨어 전체 데이터 전송 완료!\n");
    return 0;
}

/* Main FOTA Processors */
int start_custom_fota(int sock, const uint8_t *fw_data, size_t fw_size) {
    printf("=============================================\n");
    printf("[CAN] 비트맵 NACK 적용 FOTA Gateway 시작!\n");
    printf("=============================================\n");

    int ret = trigger_fota_entry(sock, CUSTOM_CAN_ID_FOTA_REQUEST);
    if (ret < 0) return ret;

    const double fota_start_time = monotonic_now();
    custom_stats_t stats = {0};

    /* 1. START */
    uint8_t start_payload[5];
    start_payload[0] = pack_custom_header(CUSTOM_CMD_RX_START, 0);
    start_payload[1] = fw_size & 0xFF;
    start_payload[2] = (fw_size >> 8) & 0xFF;
    start_payload[3] = (fw_size >> 16) & 0xFF;
    start_payload[4] = (fw_size >> 24) & 0xFF;

    ret = send_cmd_frame(sock, start_payload, 5, &stats);
    if (ret < 0) {
        printf("[CAN] Error: START CMD 송신 실패 (%s)\n", fota_err_str(ret));
        goto out;
    }
    printf("[CAN] CMD_RX_START 전송 (Flash 지우기 대기 중... ⏳)\n");

    ret = expect_ack(sock, CUSTOM_START_ACK_TIMEOUT_MS, "START(Erase)", &stats);
    if (ret < 0) goto out;
    printf("[CAN] Erase 완료! 본격 데이터 전송 시작 🚀\n");

    /* 2. DATA */
    ret = send_data_blocks(sock, fw_data, fw_size, &stats);
    if (ret < 0) goto out;

    /* 3. END */
    printf("[CAN] 전체 펌웨어 CRC32 로컬 계산 및 비교 전송 중...\n");
    uint32_t fw_crc32 = calculate_crc32(fw_data, fw_size);
    uint8_t end_payload[5];
    end_payload[0] = pack_custom_header(CUSTOM_CMD_RX_END, 0);
    end_payload[1] = fw_crc32 & 0xFF;
    end_payload[2] = (fw_crc32 >> 8) & 0xFF;
    end_payload[3] = (fw_crc32 >> 16) & 0xFF;
    end_payload[4] = (fw_crc32 >> 24) & 0xFF;

    ret = send_cmd_frame(sock, end_payload, 5, &stats);
    if (ret < 0) {
        printf("[CAN] Error: END CMD 송신 실패 (%s)\n", fota_err_str(ret));
        goto out;
    }

    printf("[CAN] 대상 기기에서 무결성 검증 및 Dual-Bank 플래시 복사를 진행 중입니다... (최대 10초 대기 ⏳)\n");
    ret = expect_ack(sock, CUSTOM_END_ACK_TIMEOUT_MS, "END(CRC/Copy)", &stats);
    if (ret < 0) {
        printf("[CAN] Error: CRC 불일치 또는 복사/End 응답 실패! (벽돌 방지 활성화)\n");
        goto out;
    }
    printf("[CAN] 펌웨어 무결성 최종 통과 및 복사 완료! (CRC Validated & Copied) ✅\n");

    /* 4. JUMP: the target ACKs after validating the vector, then jumps. */
    precise_delay(CUSTOM_JUMP_DELAY_MS / 1000.0);
    uint8_t jump_payload[1];
    jump_payload[0] = pack_custom_header(CUSTOM_CMD_RX_JUMP, 0);
    ret = send_cmd_frame(sock, jump_payload, 1, &stats);
    if (ret < 0) {
        printf("[CAN] Error: JUMP CMD 송신 실패 (%s)\n", fota_err_str(ret));
        goto out;
    }
    ret = expect_ack(sock, CUSTOM_JUMP_ACK_TIMEOUT_MS, "JUMP", &stats);
    if (ret < 0) goto out;
    printf("[CAN] JUMP ACK 수신. Application으로 전환됨 ✅\n");

out:
    print_stats(fota_start_time, &stats);
    if (ret < 0) {
        printf("[RESULT] FOTA 실패: %s\n", fota_err_str(ret));
    } else {
        printf("[RESULT] FOTA 성공\n");
    }
    return ret;
}
