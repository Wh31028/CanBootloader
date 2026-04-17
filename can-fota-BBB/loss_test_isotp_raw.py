import sys
import time
import struct
import random
import zlib
import argparse
import can
import os

# 설정
CAN_INTERFACE = 'can0'  # 리눅스 테스트 환경에 맞게 변경 (예: vcan0)
BITRATE = 1000000

# CAN ID 설정 
CAN_ID_CMD  = 0x7E0   # PC -> STM32
CAN_ID_RESP = 0x7E8   # STM32 -> PC

# FOTA 명령어
CMD_FW_START      = 0x10
CMD_FW_DATA       = 0x20
CMD_FW_END        = 0x30
CMD_FW_JUMP_TO_FW = 0x40

total_frames_sent = 0
total_frames_received = 0
retransmitted_frames = 0
total_transmission_time = 0.0

def send_frame_with_enobufs(bus, msg):
    # 하드웨어 CAN 버퍼가 허락하는 한 풀악셀 전송
    while True:
        try:
            bus.send(msg)
            break
        except OSError as e:
            if getattr(e, 'errno', None) == 105: # ENOBUFS
                time.sleep(0.0005)
            else:
                raise

def flush_rx_buffer(bus):
    while bus.recv(timeout=0.0):
        pass

def wait_sf_ack(bus, expected_cmd, timeout=3.0):
    start_time = time.time()
    while time.time() - start_time < timeout:
        resp = bus.recv(timeout=0.1)
        if resp and resp.arbitration_id == CAN_ID_RESP:
            global total_frames_received
            total_frames_received += 1
            # Single Frame 파싱 (0x00 ~ 0x07)
            if resp.dlc > 0 and (resp.data[0] & 0xF0) == 0x00:
                sf_len = resp.data[0] & 0x0F
                if sf_len >= 2 and resp.data[1] == expected_cmd:
                    return resp.data[1:1+sf_len]
    return None

def raw_isotp_send_chunk(bus, payload, loss_rate):
    global total_frames_sent
    payload_len = len(payload)
    
    # 1. First Frame (FF) 전송
    ff_data = bytearray(8)
    ff_data[0] = 0x10 | ((payload_len >> 8) & 0x0F)
    ff_data[1] = payload_len & 0xFF
    ff_data[2:8] = payload[0:6]
    msg = can.Message(arbitration_id=CAN_ID_CMD, data=ff_data, is_extended_id=False)
    send_frame_with_enobufs(bus, msg)
    total_frames_sent += 1
    
    # 2. Flow Control (FC) 대기 (1회 왕복 딜레이 발생 포인트)
    fc_received = False
    start_time = time.time()
    while time.time() - start_time < 1.0:
        resp = bus.recv(timeout=0.1)
        if resp and resp.arbitration_id == CAN_ID_RESP:
            global total_frames_received
            total_frames_received += 1
            if (resp.data[0] & 0xF0) == 0x30:
                # BS=0, STmin=0 이라고 가정하고 진행 (STM32 세팅과 동일)
                fc_received = True
                break
    
    if not fc_received:
        return False
        
    # 3. Consecutive Frames (CF) 풀악셀 전송
    seq = 1
    idx = 6
    while idx < payload_len:
        cf_len = min(7, payload_len - idx)
        cf_data = bytearray(8)
        cf_data[0] = 0x20 | (seq & 0x0F)
        cf_data[1:1+cf_len] = payload[idx:idx+cf_len]
        msg = can.Message(arbitration_id=CAN_ID_CMD, data=cf_data, is_extended_id=False)
        
        # 패킷 고의 유실
        if loss_rate > 0 and random.random() < loss_rate:
            idx += cf_len
            seq = (seq + 1) & 0x0F
            continue
            
        send_frame_with_enobufs(bus, msg)
        total_frames_sent += 1
        idx += cf_len
        seq = (seq + 1) & 0x0F
        
    return True

def start_can_fota(firmware_path):
    global total_frames_sent, retransmitted_frames, total_transmission_time
    
    try:
        bus = can.interface.Bus(channel=CAN_INTERFACE, bustype='socketcan', bitrate=BITRATE)
    except Exception as e:
        print(f"[CAN] 소켓 초기화 실패: {e}")
        return

    with open(firmware_path, "rb") as f:
        fw_data = f.read()
        
    if TARGET_SIZE_KB > 0:
        target_bytes = TARGET_SIZE_KB * 1024
        if len(fw_data) < target_bytes:
            padding_len = target_bytes - len(fw_data)
            fw_data += bytes((i % 256) for i in range(padding_len))
            print(f"[CAN] 테스트용 패턴 패딩 완료: {TARGET_SIZE_KB}KB 로 확장됨")
            
    fw_size = len(fw_data)
    print(f"[CAN] 전송할 펌웨어 크기: {fw_size} bytes")
    print(f"[CAN] RAW ISO-TP 측정 시작 (Packet Loss: {LOSS_RATE*100}%)")

    fota_start_time = time.time()
    flush_rx_buffer(bus)
    
    # 3. [Start] 명령 전송 (Single Frame)
    sf_data = bytearray(8)
    sf_data[0] = 0x05
    sf_data[1] = CMD_FW_START
    sf_data[2:6] = struct.pack('<I', fw_size)
    msg = can.Message(arbitration_id=CAN_ID_CMD, data=sf_data, is_extended_id=False)
    send_frame_with_enobufs(bus, msg)
    
    rx_payload = wait_sf_ack(bus, CMD_FW_START, timeout=15.0)
    if not rx_payload:
        print("[CAN] Error: Start ACK Timeout")
        return
        
    if len(rx_payload) >= 4:
        chunk_size = rx_payload[2] | (rx_payload[3] << 8)
    else:
        chunk_size = 256
        
    # 4. [Data] 데이터 전송 (직접 구현한 ISO-TP로 쪼개어 전송)
    for i in range(0, fw_size, chunk_size):
        chunk = fw_data[i : i + chunk_size]
        payload = bytes([CMD_FW_DATA]) + chunk
        
        retry_count = 0
        success = False
        while retry_count < 3:
            if retry_count > 0:
                print(f"\n[CAN] Block {i//chunk_size} 재전송 (ISO-TP Go-Back-N, 256바이트 통째로 시도 중!)")
                # 실패한 블록을 통째로 다시 쏘는 비용 가산 (37프레임 낭비)
                retransmitted_frames += ((len(payload) + 6) // 7)  
                
            flush_rx_buffer(bus)
            if raw_isotp_send_chunk(bus, payload, LOSS_RATE):
                ack = wait_sf_ack(bus, CMD_FW_DATA, timeout=3.0)
                if ack and ack[1] == 0:  # BOOT_OK
                    success = True
                    break
            retry_count += 1
            
        if not success:
            print("\n[CAN] 치명적 에러: 지속적인 패킷 유실로 인해 STM32가 응답하지 않음. 타임아웃 발생.")
            return

        idx = min(i + chunk_size, fw_size)
        print(f"\r[CAN] 진행률: {idx}/{fw_size} bytes ({(idx/fw_size)*100:.1f}%)", end='', flush=True)

    print("\n\n[CAN] 데이터 전송 완료")
    # 5. [End] 명령 전송
    fw_crc32 = zlib.crc32(fw_data) & 0xFFFFFFFF
    sf_data = bytearray(8)
    sf_data[0] = 0x05
    sf_data[1] = CMD_FW_END
    sf_data[2:6] = struct.pack('<I', fw_crc32)
    msg = can.Message(arbitration_id=CAN_ID_CMD, data=sf_data, is_extended_id=False)
    send_frame_with_enobufs(bus, msg)
    
    ack = wait_sf_ack(bus, CMD_FW_END, timeout=3.0)
    if ack and ack[1] == 0:
        print("[CAN] 펌웨어 무결성 최종 통과! (CRC Validated) ✅")
    else:
        print("[CAN] CRC 검증 실패")
        return

    # 6. [Jump] 명령 전송
    time.sleep(0.5)
    sf_data = bytearray(8)
    sf_data[0] = 0x02   # length 2
    sf_data[1] = CMD_FW_JUMP_TO_FW
    sf_data[2] = 0x00
    msg = can.Message(arbitration_id=CAN_ID_CMD, data=sf_data, is_extended_id=False)
    send_frame_with_enobufs(bus, msg)
    print("[CAN] JUMP 명령 전송 완료.")

    total_transmission_time = time.time() - fota_start_time
    overhead_pct = (retransmitted_frames / total_frames_sent) * 100 if total_frames_sent > 0 else 0
    
    print(f"=============================================")
    print(f"[RESULT] 총 소요 시간 (Loss {LOSS_RATE*100}%): {total_transmission_time:.2f} 초")
    print(f"[RESULT] 송신 프레임 (TX): {total_frames_sent} 프레임")
    print(f"[RESULT] 수신 프레임 (RX): {total_frames_received} 프레임")
    print(f"[RESULT] 총 통신 프레임 (TX+RX 합산): {total_frames_sent + total_frames_received} 프레임")
    print(f"[RESULT] 트래픽 오버헤드: 재전송 {retransmitted_frames} 프레임 ({overhead_pct:.2f}% 통신 낭비)")
    print(f"=============================================")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='RAW ISO-TP CAN FOTA Loss Test')
    parser.add_argument('--loss', type=float, default=0.0, help='Packet Loss Rate (0.0~1.0)')
    parser.add_argument('--size_kb', type=int, default=64, help='Target firmware size in KB (padding)')
    args = parser.parse_args()
    
    LOSS_RATE = args.loss
    TARGET_SIZE_KB = args.size_kb
    SAVE_PATH = "received_fw.bin"

    if not os.path.exists(SAVE_PATH):
        print(f"[WARN] {SAVE_PATH} 파일이 없습니다. Fake FOTA를 위해 최소 1회 기존 스크립트를 실행해 다운로드해주세요.")
        sys.exit(1)

    start_can_fota(SAVE_PATH)
