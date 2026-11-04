#ifndef CUSTOM_FOTA_H
#define CUSTOM_FOTA_H

#include <stdbool.h>
#include <stddef.h>
#include <stdint.h>

/* Software fault injection for demonstrations. All zero means a normal update. */
typedef struct {
    double data_loss_pct; /* Chance of dropping each DATA frame before it is sent. */
    bool corrupt_image;   /* Flip one byte on the wire; END still carries the true CRC. */
} custom_fault_t;

int start_custom_fota(int sock, const uint8_t *fw_data, size_t fw_size, const custom_fault_t *fault);

#endif
