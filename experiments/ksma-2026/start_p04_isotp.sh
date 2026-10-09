#!/bin/sh
set -eu
cd /home/debian/p04-f407-500k-20261009
run_dir=isotp-120-entry-v1
test ! -e "$run_dir"
nohup candump -L can0 > "$run_dir.candump.log" 2>&1 &
echo $! > "$run_dir.candump.pid"
nohup python3 experiment_runner.py --config config-isotp-entry-v1.json --run-dir "$run_dir" > "$run_dir.stdout.log" 2> "$run_dir.stderr.log" &
echo $! > "$run_dir.runner.pid"
