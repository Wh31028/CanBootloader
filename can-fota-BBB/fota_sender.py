import can
import time
import os
import struct

# --- 설정 ---
BUS_INTERFACE = 'can0'
TARGET_ID = 0x100      # STM32가 수신할 ID
CHUNK_SIZE = 7         # 한 번에 보낼 데이터 크기 (CMD 제외)
DELAY = 0.05           # 패킷 간 딜레이

# --- 프로토콜 정의 ---
CMD_FW_START = 0x10
CMD_FW_DATA  = 0x20
CMD_FW_END   = 0x30

def send_firmware(filename):
    # 1. 파일 열기
    if not os.path.exists(filename):
        print("Error: {} not found.".format(filename)) # 수정됨
        return

    file_size = os.path.getsize(filename)
    with open(filename, "rb") as f:
        firmware_blob = f.read()

    # 2. CAN 버스 연결
    bus = can.interface.Bus(channel=BUS_INTERFACE, bustype='socketcan')
    print("[Start] Sending firmware: {} ({} bytes)".format(filename, file_size)) # 수정됨

    # 3. [FW_START] 전송
    msg = can.Message(arbitration_id=TARGET_ID, data=[CMD_FW_START, 0, 0, 0, 0, 0, 0, 0], is_extended_id=False)
    bus.send(msg)
    time.sleep(1.0) 

    # 4. [FW_DATA] 데이터 루프
    total_chunks = (file_size + CHUNK_SIZE - 1) // CHUNK_SIZE
    
    for i in range(0, len(firmware_blob), CHUNK_SIZE):
        chunk = firmware_blob[i : i + CHUNK_SIZE]
        payload = list(chunk)
        
        # Padding
        while len(payload) < 7:
            payload.append(0)

        # [CMD] + [DATA]
        can_data = [CMD_FW_DATA] + payload
        
        msg = can.Message(arbitration_id=TARGET_ID, data=can_data, is_extended_id=False)
        bus.send(msg)
        
        # 진행률 표시
        current_chunk = i // CHUNK_SIZE
        if current_chunk % 10 == 0:
            print("Sending chunk {}/{}...".format(current_chunk, total_chunks)) # 수정됨

        time.sleep(DELAY) 

    # 5. [FW_END] 전송
    time.sleep(0.5)
    msg = can.Message(arbitration_id=TARGET_ID, data=[CMD_FW_END, 0, 0, 0, 0, 0, 0, 0], is_extended_id=False)
    bus.send(msg)
    
    print("[Done] Firmware transfer complete!")

if __name__ == "__main__":
    # 테스트용 파일 생성
    dummy_filename = "test_fw.bin"
    if not os.path.exists(dummy_filename):
        with open(dummy_filename, "wb") as f:
            f.write(b'\xAA\xBB' * 50) 
        
    send_firmware(dummy_filename)
    