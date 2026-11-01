#ifndef FOTA_COMMON_H
#define FOTA_COMMON_H

#include <stddef.h>
#include <stdint.h>

/*
 * Host-side result codes. Functions return 0 on success or the negated code
 * (e.g. -FOTA_ERR_TX_TIMEOUT) on failure, and main() uses the positive code as
 * the process exit status. A plain -1 from older code maps to FOTA_ERR_FAILED.
 */
typedef enum {
    FOTA_OK = 0,
    FOTA_ERR_FAILED,          /* unspecified failure, usage or file error */
    FOTA_ERR_INVALID_ARG,     /* bad parameter passed by the caller */
    FOTA_ERR_TX_TIMEOUT,      /* SocketCAN TX queue stayed full (ENOBUFS) */
    FOTA_ERR_SOCKET,          /* other socket error, e.g. ENETDOWN */
    FOTA_ERR_RESP_TIMEOUT,    /* no expected response within the timeout */
    FOTA_ERR_TARGET,          /* target replied ERR or an unexpected response */
    FOTA_ERR_BUS,             /* CAN controller reported bus-off */
    FOTA_ERR_RETRY_EXHAUSTED, /* block retry cap or transfer deadline reached */
} fota_err_t;

const char *fota_err_str(int err);

uint32_t calculate_crc32(const uint8_t *data, size_t length);
void precise_delay(double seconds);
double monotonic_now(void);
int trigger_fota_entry(int sock, uint32_t request_id);

#endif
