#!/usr/bin/env python3
"""Regenerate P05 tables and SVG figures from the two approved P04 run directories.

Only isotp-120-entry-v1 and custom-120-entry-v2 are inputs.  The script never
modifies raw evidence; it writes derived files beneath its --output directory.
"""
import argparse
import csv
import hashlib
import json
import math
from collections import Counter, defaultdict
from pathlib import Path
from statistics import mean, stdev

REQUIRED = {
    "attempt_id", "timestamp_utc", "protocol", "loss_rate", "seed",
    "firmware_sha256", "transaction_status", "boot_status", "failure_stage",
    "elapsed_sec", "send_attempts", "software_drops", "socket_send_success",
    "send_errors", "protocol_rx", "invalid_protocol_rx", "retransmit_attempts",
    "retransmit_send_success", "drop_events_json", "note",
}
DEFAULT_ISOTP_RUN = "isotp-120-entry-v1"
DEFAULT_CUSTOM_RUN = "custom-120-terminal-probe-v1"
# Two-sided 95% Student-t critical values for every possible successful n here.
T975 = {24: 2.068658, 25: 2.063899, 26: 2.059539, 29: 2.048407, 30: 2.045230}


def sha256(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def fail(message):
    raise ValueError(message)


def load_run(root, expected_protocol, name):
    run_dir = root / name
    csv_path, events_path, manifest_path = (run_dir / x for x in ("raw.csv", "events.jsonl", "manifest.json"))
    if not all(x.is_file() for x in (csv_path, events_path, manifest_path)):
        fail(f"{name}: raw.csv/events.jsonl/manifest.json missing")
    with csv_path.open(encoding="utf-8", newline="") as f:
        rows = list(csv.DictReader(f))
    if not rows or set(rows[0]) != REQUIRED:
        fail(f"{name}: CSV schema differs from P02 schema")
    events = [json.loads(line) for line in events_path.read_text(encoding="utf-8").splitlines() if line]
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    trials = manifest.get("trials")
    if len(rows) != 120 or len(events) != 120 or not isinstance(trials, list) or len(trials) != 120:
        fail(f"{name}: expected 120 CSV, JSONL, and manifest trial records")
    ids = [r["attempt_id"] for r in rows]
    if len(ids) != len(set(ids)):
        fail(f"{name}: duplicate CSV attempt_id")
    if {r["protocol"] for r in rows} != {expected_protocol}:
        fail(f"{name}: unexpected protocol")
    config = manifest.get("config", {})
    event_by_id = {x.get("attempt_id"): x for x in events}
    trial_by_id = {x.get("attempt_id"): x for x in trials}
    planned = config.get("planned_trials", [])
    planned_by_id = {x.get("attempt_id"): x for x in planned}
    if len(event_by_id) != 120 or len(trial_by_id) != 120 or len(planned_by_id) != 120 or set(ids) != set(event_by_id) != set(trial_by_id) or set(ids) != set(planned_by_id):
        fail(f"{name}: CSV/JSONL/manifest attempt_id correspondence failed")
    for row in rows:
        event, trial, plan = event_by_id[row["attempt_id"]], trial_by_id[row["attempt_id"]], planned_by_id[row["attempt_id"]]
        for key in ("protocol", "seed", "firmware_sha256", "transaction_status", "elapsed_sec"):
            if str(event.get(key)) != row[key]:
                fail(f"{name}: JSONL mismatch for {row['attempt_id']} field {key}")
        if trial.get("state") != "EXITED":
            fail(f"{name}: non-exited manifest trial {row['attempt_id']}")
        # Sender failure is intentionally represented by exit 1; it must agree
        # with raw.csv rather than being discarded as a runner failure.
        if (row["transaction_status"] == "OK") != (trial.get("exit_code") == 0):
            fail(f"{name}: manifest exit code disagrees with raw status for {row['attempt_id']}")
        if trial.get("protocol") != expected_protocol or plan.get("protocol") != expected_protocol or str(plan.get("seed")) != row["seed"] or float(plan.get("loss_rate")) != float(row["loss_rate"]):
            fail(f"{name}: manifest protocol/seed mismatch for {row['attempt_id']}")
        if float(row["loss_rate"]) not in (0, 0.0001, 0.0005, 0.001):
            fail(f"{name}: unplanned loss rate")
    if len({r["firmware_sha256"] for r in rows}) != 1 or config.get("firmware_sha256") != rows[0]["firmware_sha256"]:
        fail(f"{name}: mixed firmware hash")
    return rows, {"run": name, "raw_csv_sha256": sha256(csv_path), "events_jsonl_sha256": sha256(events_path),
                  "manifest_sha256": sha256(manifest_path), "firmware_sha256": rows[0]["firmware_sha256"],
                  "bootloader_sha256": config.get("bootloader_sha256"), "host_source_fingerprint": config.get("host_source_fingerprint"),
                  "manifest_exit_codes": dict(Counter(str(x.get("exit_code")) for x in trials))}


def t_critical(n):
    if n not in T975:
        fail(f"No fixed t critical value for successful n={n}")
    return T975[n]


def summarize(rows):
    groups = defaultdict(list)
    for row in rows:
        groups[(row["protocol"], float(row["loss_rate"]))].append(row)
    output = []
    for (protocol, loss), group in sorted(groups.items(), key=lambda x: (x[0][0] != "RAW_ISO-TP", x[0][1])):
        ok = [r for r in group if r["transaction_status"] == "OK"]
        elapsed = [float(r["elapsed_sec"]) for r in ok]
        n = len(group)
        sd = stdev(elapsed) if len(elapsed) > 1 else 0.0
        half = t_critical(len(ok)) * sd / math.sqrt(len(ok)) if len(ok) > 1 else 0.0
        counts = {key: sum(int(r[key]) for r in group) for key in (
            "send_attempts", "software_drops", "socket_send_success", "send_errors",
            "retransmit_attempts", "retransmit_send_success")}
        failures = Counter(r["transaction_status"] for r in group if r["transaction_status"] != "OK")
        output.append({"protocol": protocol, "loss_rate": loss, "attempts": n, "successes": len(ok),
                       "failures": n-len(ok), "failure_types": "; ".join(f"{k}:{v}" for k,v in sorted(failures.items())) or "-",
                       "success_rate_pct": 100*len(ok)/n, "success_elapsed_mean_sec": mean(elapsed),
                       "success_elapsed_sd_sec": sd, "success_elapsed_ci95_low_sec": mean(elapsed)-half,
                       "success_elapsed_ci95_high_sec": mean(elapsed)+half, "successful_n": len(ok), **counts,
                       "retransmit_overhead_pct": 100*counts["retransmit_attempts"]/counts["send_attempts"],
                       "software_omission_pct": 100*counts["software_drops"]/counts["send_attempts"]})
    return output


def write_csv(path, records):
    with path.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=list(records[0]))
        writer.writeheader(); writer.writerows(records)


def svg_chart(path, title, rows, field, ylabel, ymax, error=None):
    width, height, left, bottom = 900, 440, 90, 65
    colors = {"RAW_ISO-TP": "#2369a6", "Custom": "#d36b25"}
    pieces = [f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}">',
              '<style>text{font-family:Arial,sans-serif;fill:#202124}.axis{stroke:#555}.grid{stroke:#ddd}.iso{stroke:#2369a6;fill:none;stroke-width:3}.custom{stroke:#d36b25;fill:none;stroke-width:3}</style>',
              f'<text x="{width/2}" y="28" text-anchor="middle" font-size="19">{title}</text>']
    plot_h, plot_w = height-bottom-55, width-left-50
    for i in range(6):
        value = ymax*i/5; y = height-bottom-plot_h*i/5
        pieces += [f'<line class="grid" x1="{left}" y1="{y:.1f}" x2="{width-50}" y2="{y:.1f}"/>',
                   f'<text x="{left-10}" y="{y+4:.1f}" text-anchor="end" font-size="12">{value:.1f}</text>']
    pieces += [f'<line class="axis" x1="{left}" y1="55" x2="{left}" y2="{height-bottom}"/>', f'<line class="axis" x1="{left}" y1="{height-bottom}" x2="{width-50}" y2="{height-bottom}"/>']
    losses = [0, .0001, .0005, .001]
    for i, loss in enumerate(losses):
        x = left + plot_w*i/(len(losses)-1); pieces.append(f'<text x="{x:.1f}" y="{height-bottom+23}" text-anchor="middle" font-size="12">{loss*100:.02f}%</text>')
    for protocol in ("RAW_ISO-TP", "Custom"):
        points=[]
        for i, loss in enumerate(losses):
            row = next(r for r in rows if r["protocol"] == protocol and r["loss_rate"] == loss)
            x=left+plot_w*i/(len(losses)-1); y=height-bottom-plot_h*row[field]/ymax; points.append(f"{x:.1f},{y:.1f}")
            if error:
                lo=height-bottom-plot_h*row[error[0]]/ymax; hi=height-bottom-plot_h*row[error[1]]/ymax
                pieces.append(f'<line stroke="{colors[protocol]}" x1="{x:.1f}" y1="{lo:.1f}" x2="{x:.1f}" y2="{hi:.1f}"/>')
            pieces.append(f'<circle fill="{colors[protocol]}" cx="{x:.1f}" cy="{y:.1f}" r="5"/>')
        pieces.append(f'<polyline class="{"iso" if protocol == "RAW_ISO-TP" else "custom"}" points="{" ".join(points)}"/>')
    pieces += [f'<text x="{width/2}" y="{height-10}" text-anchor="middle" font-size="13">software omission rate</text>', f'<text transform="translate(18 {height/2}) rotate(-90)" text-anchor="middle" font-size="13">{ylabel}</text>', '<rect x="620" y="45" width="12" height="12" fill="#2369a6"/><text x="638" y="56" font-size="12">RAW_ISO-TP</text><rect x="760" y="45" width="12" height="12" fill="#d36b25"/><text x="778" y="56" font-size="12">Custom</text>', '</svg>']
    path.write_text("\n".join(pieces), encoding="utf-8")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--input-root", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--isotp-run", default=DEFAULT_ISOTP_RUN)
    parser.add_argument("--custom-run", default=DEFAULT_CUSTOM_RUN)
    args = parser.parse_args(); args.output.mkdir(parents=True, exist_ok=True)
    runs = (("RAW_ISO-TP", args.isotp_run), ("Custom", args.custom_run))
    rows, provenance = [], []
    for protocol, name in runs:
        loaded, record = load_run(args.input_root, protocol, name); rows += loaded; provenance.append(record)
    if len({r["attempt_id"] for r in rows}) != 240:
        fail("duplicate attempt_id across approved runs")
    summary = summarize(rows)
    write_csv(args.output / "p05-summary-by-protocol-loss.csv", summary)
    (args.output / "p05-validation.json").write_text(json.dumps({"validation": "PASS", "approved_runs_only": [x[1] for x in runs], "records": provenance, "total_trials": len(rows), "raw_status_counts": dict(Counter(r["transaction_status"] for r in rows))}, indent=2)+"\n", encoding="utf-8")
    svg_chart(args.output / "p05-success-time.svg", "Successful transaction time (95% t CI)", summary, "success_elapsed_mean_sec", "seconds", 35, ("success_elapsed_ci95_low_sec", "success_elapsed_ci95_high_sec"))
    svg_chart(args.output / "p05-success-rate.svg", "Transaction success rate", summary, "success_rate_pct", "percent", 100)
    svg_chart(args.output / "p05-retransmit-overhead.svg", "Retransmission overhead (all attempts denominator)", summary, "retransmit_overhead_pct", "percent", 4)
    print(f"PASS: validated {len(rows)} approved trials; wrote {args.output}")


if __name__ == "__main__":
    main()
