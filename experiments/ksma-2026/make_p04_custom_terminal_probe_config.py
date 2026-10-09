import json

losses = [0.0, 0.0001, 0.0005, 0.001]
trials = []
for i, loss in enumerate(losses):
    for rep in range(1, 31):
        trials.append({
            "attempt_id": f"p04-terminal-probe-v1-custom-l{int(loss * 1000000):04d}-r{rep:02d}",
            "protocol": "Custom",
            "loss_rate": loss,
            "seed": 202610091000 + i * 30 + rep,
        })

config = {
    "schema": "p04-f407-500k-terminal-probe-v1",
    "firmware_path": "/home/debian/p04-f407-500k-20261009/boot_can_fw-65536-ff-correct.bin",
    "firmware_sha256": "1badd29c53120916c2f2b0f2e773c6af953960bedeb1c199b66021096b9870e1",
    "bootloader_sha256": "280410bf713630b66f16f233989486de60387a648cfa9b1ae6b1a201826e9391",
    "host_source_fingerprint": "fota_sender_p02=620ffba37e818282beeac26a1722c79c02794310575ad9c3067df17d6d0b46b1;fota_p01=d7a01c04e18237eac9d3008fdc86dc4984e9e02e8805f0bfb7a94dbbba3b0e82;fota_p02=7e8f53322b01e967ac101518cba86adc1afb7c6cade2c897b298de462f083d0a;custom=a67eb727db49e1c1855e23183c3f16308ceb838b67037f61d795b2778a2b1628",
    "runner_timeout_sec": 140,
    "max_custom_probe_attempts": 4,
    "planned_trials": trials,
}

with open("config-custom-terminal-probe-v1.json", "w", encoding="utf-8") as handle:
    json.dump(config, handle, indent=2)
    handle.write("\n")
