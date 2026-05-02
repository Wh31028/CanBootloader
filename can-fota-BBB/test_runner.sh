#!/bin/bash
echo "============================================="
echo "   FOTA Packet Loss Benchmarking Script"
echo "   (Custom vs RAW ISO-TP)"
echo "============================================="
echo "Make sure the STM32 is in Bootloader mode before each test."
echo ""

run_test() {
    local protocol=$1
    local script=$2
    local size=$3
    local trials=$4

    for loss in 0.0 0.001 0.005 0.01; do
        for trial in $(seq 1 $trials); do
            echo "------------------------------------------------------"
            echo " Protocol : $protocol"
            echo " Loss Rate: $loss  |  Trial: $trial / $trials"
            echo "------------------------------------------------------"
            read -p "Press Enter when STM32 is in bootloader mode..."
            python3 $script --loss $loss --size_kb $size
            echo ""
        done
    done
}

echo "Enter Target Firmware Size in KB (e.g., 64, 128, 256)."
echo "Enter 0 to use the original file size (~38KB):"
read -p "Size (KB): " target_size

echo ""
echo "How many trials per loss rate? (Monte Carlo, recommended: 3~5)"
read -p "Trials: " trials

echo ""
echo "Which protocol do you want to test?"
echo "1) Custom Protocol (Selective NACK)"
echo "2) RAW ISO-TP (Bare-metal Python)"
echo "3) Both (Custom first, then RAW ISO-TP)"
read -p "Choice (1/2/3): " choice

echo ""

if [ "$choice" == "1" ]; then
    run_test "Custom" "loss_test_custom.py" "$target_size" "$trials"
elif [ "$choice" == "2" ]; then
    run_test "RAW ISO-TP" "loss_test_isotp_raw.py" "$target_size" "$trials"
elif [ "$choice" == "3" ]; then
    echo ">>> [1/2] Custom Protocol 테스트 시작"
    run_test "Custom" "loss_test_custom.py" "$target_size" "$trials"
    echo ""
    echo ">>> [2/2] RAW ISO-TP 테스트 시작"
    run_test "RAW ISO-TP" "loss_test_isotp_raw.py" "$target_size" "$trials"
else
    echo "Invalid choice."
fi

echo "============================================="
echo "   All tests complete!"
echo "============================================="
