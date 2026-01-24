import can
import time
import os
import struct

# --- 설정 ---
BUS_INTERFACE = 'can0' # can0 또는 can1 (ifconfig로 확인한 이름)
TARGET_ID     = 0x100  # 비글본 -> STM32 (명령)
RESPONSE_ID   = 0x101  # STM32 -> 비글본 (응답)

CMD_FW_START  = 0x10
CMD_FW_DATA   = 0x20
CMD_FW_END    = 0x30

FLASH_PAGE_SIZE = 256  # STM32 플래시 쓰기 단위

def send_packet_with_ack(bus, data, timeout=1.0, retries=3):
    """
    데이터를 보내고 ACK(ID 0x101)를 기다리는 함수
    """
    msg = can.Message(arbitration_id=TARGET_ID, data=data, is_extended_id=True)

    for attempt in range(retries):
        try:
            # 1. 메시지 전송
            bus.send(msg)
            
            # 2. ACK 대기
            # 타임아웃 시간 동안 들어오는 메시지를 계속 확인
            start_time = time.time()
            while (time.time() - start_time) < timeout:
                rx_msg = bus.recv(timeout=0.1) # 0.1초씩 끊어서 확인
                
                if rx_msg and rx_msg.arbitration_id == RESPONSE_ID:
                    # 응답 포맷: [명령어, 결과(0:OK, 1:ERR)]
                    cmd = rx_msg.data[0]
                    result = rx_msg.data[1]
                    
                    if cmd == data[0] and result == 0:
                        return True # 성공
                    elif result != 0:
                        print(f"ERROR: STM32 reported error (Code: {result}). Retrying...")
                        break # 재전송 시도

        except can.CanError:
            print("CAN Bus Error.")
            time.sleep(0.1)

    print("FATAL: Failed to get ACK after max retries.")
    return False

def send_firmware(filename):
    # 0. CAN 버스 초기화
    try:
        bus = can.interface.Bus(channel=BUS_INTERFACE, bustype='socketcan')
        print(f"Connected to {BUS_INTERFACE}")
    except OSError:
        print(f"Error: Could not open {BUS_INTERFACE}. Check 'ifconfig'.")
        return

    # 1. 파일 확인
    if not os.path.exists(filename):
        print(f"Error: {filename} not found.")
        return

    file_size = os.path.getsize(filename)
    with open(filename, "rb") as f:
        firmware_blob = f.read()

    print(f"--- FOTA Start ---")
    print(f"File: {filename}, Size: {file_size} bytes")

    # ---------------------------------------------------------
    # 2. [FW_START] 전송 (파일 크기 포함)
    # ---------------------------------------------------------
    print("1. Sending Start Command & Erasing Flash...")
    
    # 패킷 구조: [CMD(0x10)] + [Reserved(3byte)] + [Size(4byte, Little Endian)]
    # <B: 1byte, 3x: 3byte padding, I: 4byte int
    cmd_start = struct.pack('<B3xI', CMD_FW_START, file_size)
    
    # 지우는 시간 고려하여 타임아웃 길게 설정 (5초)
    if not send_packet_with_ack(bus, list(cmd_start), timeout=5.0):
        print("Failed to start FOTA.")
        return

    # ---------------------------------------------------------
    # 3. [FW_DATA] 데이터 전송 (256바이트 단위 동기화)
    # ---------------------------------------------------------
    print("2. Sending Firmware Data...")
    
    total_sent = 0
    ack_trigger_count = 0 
    
    # 7바이트씩 잘라서 전송
    for i in range(0, len(firmware_blob), 7):
        chunk = firmware_blob[i : i + 7]
        payload = list(chunk)
        
        # 7바이트보다 작으면 뒤에 0으로 채움 (마지막 패킷)
        while len(payload) < 7:
            payload.append(0)

        # 패킷 생성: [CMD(0x20)] + [Data(7bytes)]
        can_data = [CMD_FW_DATA] + payload
        
        # 일반 전송 (ACK 없이 보냄)
        msg = can.Message(arbitration_id=TARGET_ID, data=can_data, is_extended_id=True)
        bus.send(msg)
        
        # --- ACK 확인 로직 ---
        # STM32는 버퍼(256바이트)가 꽉 찰 때마다 Flash에 쓰고 ACK를 보냄.
        # 따라서 우리도 보낸 데이터 누적량이 256을 넘을 때마다 ACK를 확인해야 함.
        total_sent += len(chunk)
        ack_trigger_count += len(chunk)

        if ack_trigger_count >= FLASH_PAGE_SIZE:
            # 256바이트 이상 보냈으니, STM32가 쓰고 ACK를 보냈을 것임.
            # 여기서 ACK를 기다림. (이미 보낸 데이터에 대한 확인)
            print(f"   -> Flashing page... ({total_sent}/{file_size})")
            
            # 주의: send_packet_with_ack 함수는 '보내고' 기다리는 함수임.
            # 여기서는 이미 보냈고 '기다리기만' 해야 하므로 recv 로직만 따로 필요하지만,
            # 코드를 단순화하기 위해 타임아웃 내에 수신 버퍼에서 ACK를 찾는 방식을 사용.
            
            # 간단한 ACK 대기 (재전송 로직 없이 대기만)
            ack_received = False
            start_wait = time.time()
            while time.time() - start_wait < 1.0: # 1초 대기
                rx_msg = bus.recv(timeout=0.1)
                if rx_msg and rx_msg.arbitration_id == RESPONSE_ID:
                    if rx_msg.data[0] == CMD_FW_DATA and rx_msg.data[1] == 0:
                        ack_received = True
                        break
            
            if not ack_received:
                print("Error: Missing ACK for Page Write!")
                return
            
            ack_trigger_count -= FLASH_PAGE_SIZE # 카운터 초기화
            
        time.sleep(0.005) # 전송 안정성을 위한 미세 딜레이

    # ---------------------------------------------------------
    # 4. [FW_END] 전송 (나머지 굽기 & 점프)
    # ---------------------------------------------------------
    print("3. Sending End Command & Jumping...")
    
    cmd_end = [CMD_FW_END, 0, 0, 0, 0, 0, 0, 0]
    
    if send_packet_with_ack(bus, cmd_end, timeout=2.0):
        print("\n[Done] Firmware Update Success! Device should satisfy reboot.")
    else:
        print("\n[Fail] Device did not acknowledge End command.")

if __name__ == "__main__":
    # 테스트용 더미 파일 생성 (없으면)
    dummy_filename = "test_fw.bin"
    if not os.path.exists(dummy_filename):
        print(f"Creating dummy file: {dummy_filename}")
        with open(dummy_filename, "wb") as f:
            # 1KB 짜리 더미 데이터
            for i in range(1024):
                f.write(struct.pack('B', i % 256))
        
    send_firmware(dummy_filename)