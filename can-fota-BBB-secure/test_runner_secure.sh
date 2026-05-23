#!/bin/bash

# ==============================================================================
# Secure FOTA Benchmark Runner
# Usage: ./test_runner_secure.sh <fw_path> <iterations> [target_kb] [protocol]
# Protocol: custom (default) | isotp
# ==============================================================================

if [ -z "$1" ] || [ -z "$2" ]; then
    echo "Usage: ./test_runner_secure.sh <fw_path> <iterations> [target_kb] [custom|isotp]"
    echo "Example (original size): ./test_runner_secure.sh boot_can_fw.bin 5 0 custom"
    echo "Example (pad to 128KB): ./test_runner_secure.sh boot_can_fw.bin 5 128 custom"
    exit 1
fi

FW_PATH=$1
ITERATIONS=$2
TARGET_KB=${3:-0}
PROTOCOL=${4:-custom}

if [ "$TARGET_KB" == "custom" ] || [ "$TARGET_KB" == "isotp" ]; then
    PROTOCOL=$TARGET_KB
    TARGET_KB=0
fi

CSV_FILE="fota_benchmark_result_${PROTOCOL}.csv"

echo "Protocol,FW_Size(bytes),Total_Time(s),TX_Frames,RX_Frames,Retransmitted,Packing_Time(s),SHA256_PT(ms),ECDSA_PT(ms),AES_CBC(ms),SHA256_ENC(ms),ECDSA_ENC(ms),STM32_Erase(s),STM32_Transfer(s),STM32_Verify(s)" > $CSV_FILE

echo "=========================================================="
echo " Starting $PROTOCOL FOTA Benchmark ($ITERATIONS iterations)"
echo " Results will be saved to: $CSV_FILE"
echo "=========================================================="

# Select target script
if [ "$PROTOCOL" == "isotp" ]; then
    SCRIPT="test_secure_isotp_lte_gateway.py"
else
    SCRIPT="test_secure_lte_gateway.py"
fi

for ((i=1; i<=ITERATIONS; i++))
do
    echo " "
    echo "▶▶▶ Running Iteration $i / $ITERATIONS ..."
    
    # Run python script and grep for the CSV result line
    OUTPUT=$(python3 $SCRIPT $FW_PATH $TARGET_KB)
    
    # Check if the transmission was successful
    if echo "$OUTPUT" | grep -q "csv_result"; then
        CSV_LINE=$(echo "$OUTPUT" | grep "csv_result" | sed 's/csv_result,//')
        echo "$CSV_LINE" >> $CSV_FILE
        echo "✅ Iteration $i completed successfully."
        echo "   Result: $CSV_LINE"
    else
        echo "❌ Iteration $i failed!"
        echo "$OUTPUT"
        echo "FAIL" >> $CSV_FILE
    fi
    
    # Sleep to allow STM32 to reboot and stabilize before the next test
    sleep 3
done

echo "=========================================================="
echo " Benchmark finished!"
echo " Result Summary:"
cat $CSV_FILE
echo "=========================================================="
