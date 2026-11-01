#include <errno.h>
#include <net/if.h>
#include <poll.h>
#include <stdint.h>
#include <stdio.h>
#include <string.h>
#include <sys/ioctl.h>
#include <sys/socket.h>
#include <time.h>
#include <unistd.h>
#include <linux/can.h>
#include <linux/can/error.h>
#include <linux/can/raw.h>

#include "can_socket.h"
#include "fota_common.h"
#include "protocol.h"

/* Host-side TX policy (not part of the wire protocol). */
#define CAN_TX_QUEUE_TIMEOUT_MS 100
#define CAN_TX_RETRY_SLEEP_US   500

/* Controller/bus events delivered as CAN error frames (CAN_RAW_ERR_FILTER). */
#define CAN_ERR_RX_MASK (CAN_ERR_TX_TIMEOUT | CAN_ERR_CRTL | CAN_ERR_ACK | \
                         CAN_ERR_BUSOFF | CAN_ERR_RESTARTED)

static unsigned int can_err_ack_count;
static unsigned int can_err_tx_timeout_count;
static uint8_t can_err_last_crtl;

int open_can_socket(const char *interface_name) {
    if (!interface_name || strlen(interface_name) >= IFNAMSIZ) {
        errno = EINVAL;
        return -1;
    }
    int sock = socket(PF_CAN, SOCK_RAW, CAN_RAW);
    if (sock < 0) return -1;

    struct ifreq ifr = {0};
    memcpy(ifr.ifr_name, interface_name, strlen(interface_name) + 1);
    if (ioctl(sock, SIOCGIFINDEX, &ifr) < 0) {
        close(sock);
        return -1;
    }

    /* Best effort: without error frames a dead bus only shows up as a timeout. */
    can_err_mask_t err_mask = CAN_ERR_RX_MASK;
    if (setsockopt(sock, SOL_CAN_RAW, CAN_RAW_ERR_FILTER, &err_mask, sizeof(err_mask)) < 0) {
        perror("[CAN] Warning: CAN_RAW_ERR_FILTER 설정 실패");
    }

    struct sockaddr_can addr = {0};
    addr.can_family = AF_CAN;
    addr.can_ifindex = ifr.ifr_ifindex;
    if (bind(sock, (struct sockaddr *)&addr, sizeof(addr)) < 0) {
        close(sock);
        return -1;
    }
    return sock;
}

/*
 * A successful write() only means the frame is queued in the kernel; it does
 * not prove the target received it. ENOBUFS (TX queue full) is retried until
 * CAN_TX_QUEUE_TIMEOUT_MS elapses, e.g. when no node ACKs and the controller
 * keeps retransmitting.
 */
int send_can_frame(int sock, uint32_t can_id, const uint8_t *data, uint8_t len) {
    if (!data || len > CAN_MAX_DLEN) {
        errno = EINVAL;
        return -FOTA_ERR_INVALID_ARG;
    }
    struct can_frame frame = {0};
    frame.can_id = can_id;
    frame.can_dlc = len;
    memcpy(frame.data, data, len);

    const double deadline = monotonic_now() + CAN_TX_QUEUE_TIMEOUT_MS / 1000.0;
    const struct timespec retry_sleep = {.tv_sec = 0, .tv_nsec = CAN_TX_RETRY_SLEEP_US * 1000L};
    for (;;) {
        ssize_t n = write(sock, &frame, sizeof(frame));
        if (n == (ssize_t)sizeof(frame)) return 0;
        if (n >= 0) {
            errno = EIO; /* short write; not expected for CAN_RAW */
            return -FOTA_ERR_SOCKET;
        }
        if (errno == EINTR) continue;
        if (errno != ENOBUFS) return -FOTA_ERR_SOCKET;
        if (monotonic_now() >= deadline) return -FOTA_ERR_TX_TIMEOUT;
        nanosleep(&retry_sleep, NULL);
    }
}

static int wait_readable(int sock, double timeout) {
    struct pollfd pfd = {.fd = sock, .events = POLLIN};
    return poll(&pfd, 1, timeout > 0.0 ? (int)(timeout * 1000.0) : 0);
}

/* Returns -FOTA_ERR_BUS on bus-off, otherwise records the event and returns 0. */
static int handle_can_error_frame(const struct can_frame *frame) {
    if (frame->can_id & CAN_ERR_BUSOFF) {
        printf("\n[CAN Error] Controller bus-off\n");
        return -FOTA_ERR_BUS;
    }
    if (frame->can_id & CAN_ERR_ACK) can_err_ack_count++;
    if (frame->can_id & CAN_ERR_TX_TIMEOUT) can_err_tx_timeout_count++;
    if ((frame->can_id & CAN_ERR_CRTL) && frame->can_dlc >= 2 &&
        frame->data[1] != can_err_last_crtl) {
        can_err_last_crtl = frame->data[1];
        printf("\n[CAN Warning] Controller state 0x%02X%s%s%s\n", can_err_last_crtl,
               (can_err_last_crtl & (CAN_ERR_CRTL_RX_PASSIVE | CAN_ERR_CRTL_TX_PASSIVE)) ? " (error-passive)" : "",
               (can_err_last_crtl & (CAN_ERR_CRTL_RX_WARNING | CAN_ERR_CRTL_TX_WARNING)) ? " (warning)" : "",
               (can_err_last_crtl & CAN_ERR_CRTL_ACTIVE) ? " (error-active)" : "");
    }
    if (frame->can_id & CAN_ERR_RESTARTED) {
        printf("\n[CAN Warning] Controller restarted\n");
    }
    return 0;
}

/*
 * Drops stale data frames before START. Error frames are still recorded so
 * that a bus state change during the entry wait is not lost.
 */
int flush_rx_buffer(int sock) {
    struct can_frame frame;
    int flushed = 0;
    int ret = 0;
    while (recv(sock, &frame, sizeof(frame), MSG_DONTWAIT) == sizeof(frame)) {
        if (frame.can_id & CAN_ERR_FLAG) {
            if (handle_can_error_frame(&frame) < 0) ret = -FOTA_ERR_BUS;
            continue;
        }
        flushed++;
    }
    if (flushed > 0) printf("[FOTA] 스테일 RX 데이터 %d개 폐기\n", flushed);
    return ret;
}

void print_can_error_stats(void) {
    printf("[CAN] Error frames: ACK error %u, TX timeout %u, last controller state 0x%02X\n",
           can_err_ack_count, can_err_tx_timeout_count, can_err_last_crtl);
}

int wait_custom_response(int sock, double timeout, uint8_t *cmd, uint64_t *args) {
    struct can_frame frame;
    const double start = monotonic_now();
    for (;;) {
        double elapsed = monotonic_now() - start;
        if (elapsed >= timeout) return -FOTA_ERR_RESP_TIMEOUT;
        int ready = wait_readable(sock, timeout - elapsed);
        if (ready < 0) {
            if (errno == EINTR) continue;
            return -FOTA_ERR_SOCKET;
        }
        if (ready == 0) return -FOTA_ERR_RESP_TIMEOUT;
        if (recv(sock, &frame, sizeof(frame), MSG_DONTWAIT) != sizeof(frame)) continue;
        if (frame.can_id & CAN_ERR_FLAG) {
            int ret = handle_can_error_frame(&frame);
            if (ret < 0) return ret;
            continue;
        }
        if ((frame.can_id & CAN_SFF_MASK) != CUSTOM_CAN_ID_RESP) continue;
        if (frame.can_dlc < 1) continue;

        uint8_t header = frame.data[0];
        *cmd = (header >> 6) & 0x03;
        if (*cmd == CUSTOM_CMD_TX_ACK || *cmd == CUSTOM_CMD_TX_ERR) {
            *args = header & 0x3F;
            return 0;
        }
        if (*cmd == CUSTOM_CMD_TX_NACK) {
            if (frame.can_dlc != CAN_MAX_DLEN) continue; /* bitmap needs 7 bytes */
            *args = 0;
            for (int i = 1; i < 8; i++) *args |= (uint64_t)frame.data[i] << (8 * (i - 1));
            return 0;
        }
    }
}

int wait_isotp_sf_ack(int sock, uint8_t expected_cmd, double timeout,
                      uint8_t *rx_payload, uint8_t *rx_len) {
    struct can_frame frame;
    struct timespec start, now;
    clock_gettime(CLOCK_MONOTONIC, &start);
    for (;;) {
        clock_gettime(CLOCK_MONOTONIC, &now);
        double elapsed = (now.tv_sec - start.tv_sec) +
                         (now.tv_nsec - start.tv_nsec) / 1000000000.0;
        if (elapsed >= timeout) return -1;
        if (wait_readable(sock, timeout - elapsed) <= 0) return -1;
        if (recv(sock, &frame, sizeof(frame), MSG_DONTWAIT) != sizeof(frame)) continue;
        if (frame.can_id & CAN_ERR_FLAG) continue; /* error frames are not responses */
        if ((frame.can_id & CAN_SFF_MASK) != ISOTP_CAN_ID_RESP) continue;
        if ((frame.data[0] & 0xF0) != 0x00) continue;
        uint8_t sf_len = frame.data[0] & 0x0F;
        if (sf_len < 2 || sf_len > 7 || frame.data[1] != expected_cmd) continue;
        *rx_len = sf_len;
        memcpy(rx_payload, &frame.data[1], sf_len);
        return 0;
    }
}
