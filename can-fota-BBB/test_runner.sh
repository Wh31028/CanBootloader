#!/bin/bash
echo "============================================="
echo "   FOTA Packet Loss Benchmarking Script"
echo "============================================="
echo "Make sure the STM32 is in Bootloader mode before running each step."
echo ""

run_test() {
    local protocol=$1
    local script=$2
    local size=$3
    shift 3

    for loss in 0.0 0.0001 0.001 0.005 0.01; do
        echo "------------------------------------------------------"
        read -p "Press Enter to start $protocol Test with $loss Loss Rate (ensure node is in bootloader)..."
        python3 $script --loss $loss --size_kb $size
        echo ""
    done
}

echo "Enter Target Firmware Size in KB (e.g., 64, 128, 256, 512)."
echo "Enter 0 to use the original file size (~38KB): " 
read -p "Size (KB): " target_size

echo "Which protocol do you want to test?"
echo "1) Custom Protocol"
echo "2) ISO-TP Protocol (Standard Library)"
echo "3) Raw ISO-TP (Bare-metal Python)"
read -p "Choice (1/2/3): " choice

if [ "$choice" == "1" ]; then
    run_test "Custom" "loss_test_custom.py" "$target_size"
elif [ "$choice" == "2" ]; then
    run_test "ISO-TP" "loss_test_isotp.py" "$target_size"
elif [ "$choice" == "3" ]; then
    run_test "RAW ISO-TP" "loss_test_isotp_raw.py" "$target_size"
else
    echo "Invalid choice."
fi
