import json

losses = [0.0, 0.0001, 0.0005, 0.001]
trials = []
for i, loss in enumerate(losses):
    for rep in range(1, 31):
        trials.append({
            "attempt_id": f"p04-entry-v1-isotp-l{int(loss * 1000000):04d}-r{rep:02d}",
            "protocol": "RAW_ISO-TP",
            "loss_rate": loss,
            "seed": 202610090000 + i * 30 + rep,
        })

config = {
    "schema": "p04-f407-500k-v1",
    "firmware_path": "/home/debian/p04-f407-500k-20261009/boot_can_fw-65536-ff-correct.bin",
    "firmware_sha256": "1badd29c53120916c2f2b0f2e773c6af953960bedeb1c199b66021096b9870e1",
    "bootloader_sha256": "7f9412a488186b0567c2c57a377fb9a8256cbc2aff4aafb45a343dcd647ae5eb",
    "host_source_fingerprint": "fota_sender_p02=ba304d5f212f4bac15d7890e09800e0f2b43db3f82c4d819ecb045753fa1044e;fota_p01=d7a01c04e18237eac9d3008fdc86dc4984e9e02e8805f0bfb7a94dbbba3b0e82;fota_p02=7e8f53322b01e967ac101518cba86adc1afb7c6cade2c897b298de462f083d0a;isotp=1f06f46df4a0459bca23c82ac151b6eb2b18ef32ebcc621a051e3776be4356ab",
    "runner_timeout_sec": 140,
    "planned_trials": trials,
}

with open("config-isotp-entry-v1.json", "w", encoding="utf-8") as handle:
    json.dump(config, handle, indent=2)
    handle.write("\n")
