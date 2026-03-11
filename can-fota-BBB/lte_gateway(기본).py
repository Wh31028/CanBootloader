import os
import time
import struct
import socket
import urllib.request # [핵심] requests 대신 파이썬 내장 모듈 사용
import ssl            # HTTPS 인증서 무시용
import zlib

# ==========================================
# FOTA 서버 및 CAN 설정
# ==========================================
FW_URL            = "https://unbarreled-alayna-eustatic.ngrok-free.dev/boot_can_fw.bin"
SAVE_PATH         = "received_fw.bin"

CMD_FW_START      = 0x10
CMD_FW_DATA       = 0x20
CMD_FW_END        = 0x30
CMD_FW_JUMP_TO_FW = 0x40

CAN_ID_RESP       = 0x101 
CAN_ID_CMD        = 0x100 

# ==========================================
# 1. LTE 다운로드 (urllib 사용)
# ==========================================
def download_firmware_via_lte(url, save_path):
    print(f"=============================================")
    print(f" [LTE] FOTA 다운로드 시작 (서버 접속 중...)")
    print(f" URL: {url}")
    print(f"=============================================")
    try:
        # ngrok https 인증서 오류 무시 설정 (verify=False 와 동일)
        ctx = ssl.create_default_context()
        ctx.check_hostname = False
        ctx.verify_mode = ssl.CERT_NONE
        
        req = urllib.request.Request(url)
        with urllib.request.urlopen(req, context=ctx, timeout=10) as response:
            fw_data = response.read()
            with open(save_path, "wb") as f:
                f.write(fw_data)
        
        print(f"[LTE] 펌웨어 다운로드 완료! 크기: {len(fw_data)} bytes\n")
        return True
    except Exception as e:
        print(f"[LTE Error] 다운로드 실패: {e}")
        return False

# ==========================================
# 2. Native SocketCAN 통신 (이하 동일)
# ==========================================
def build_can_frame(can_id, data_list):
    data_bytes = bytes(data_list)
    data_padded = data_bytes + b'\x00' * (8 - len(data_bytes))
    return struct.pack("<IB3x8s", can_id, len(data_bytes), data_padded)

def wait_ack(bus, timeout=2.0):
    bus.settimeout(timeout)
    start_time = time.time()
    while (time.time() - start_time) < timeout:
        try:
            frame = bus.recv(16)
            if len(frame) == 16:
                rx_id, rx_dlc, rx_data = struct.unpack("<IB3x8s", frame)
                rx_id &= 0x7FF 
                if rx_id == CAN_ID_RESP:
                    return rx_data[1] == 0
        except socket.timeout:
            return False
        except BlockingIOError:
            pass
    return False

def start_can_fota(firmware_path):
    print(f"[CAN] Native SocketCAN FOTA Flashing 시작: {firmware_path}")
    try:
        bus = socket.socket(socket.AF_CAN, socket.SOCK_RAW, socket.CAN_RAW)
        bus.bind(('can0',))
    except Exception as e:
        print(f"[CAN] 소켓 초기화 실패: {e}")
        return

    with open(firmware_path, "rb") as f:
        fw_data = f.read()
    fw_size = len(fw_data)
    print(f"[CAN] 전송할 펌웨어 크기: {fw_size} bytes")

    data = [CMD_FW_START, 0x00, 0x00, 0x00]
    data.extend(list(fw_size.to_bytes(4, byteorder='little')))
    bus.send(build_can_frame(CAN_ID_CMD, data))
    print("[CAN] CMD_FW_START 전송 (Erase 대기...)")
    
    if not wait_ack(bus, timeout=5.0):
        print("[CAN] Error: Erase ACK Timeout/Fail")
        return

    idx = 0
    buffer_accumulated = 0 
    while idx < fw_size:
        chunk = fw_data[idx : idx + 7]
        payload = [CMD_FW_DATA] + list(chunk)
        bus.send(build_can_frame(CAN_ID_CMD, payload))
        
        data_len = len(chunk)
        idx += data_len
        buffer_accumulated += data_len
        
        if buffer_accumulated >= 256:
            if not wait_ack(bus):
                print(f"[CAN] Error: Data Write ACK Fail at index {idx}")
                return
            buffer_accumulated = 0 
        time.sleep(0.001)

    print("[CAN] 데이터 전송 완료")
    print("[CAN] 전체 펌웨어 CRC32 계산 중...")
    fw_crc32 = zlib.crc32(fw_data) & 0xFFFFFFFF
    
    end_data = [CMD_FW_END] + list(fw_crc32.to_bytes(4, byteorder='little'))
    bus.send(build_can_frame(CAN_ID_CMD, end_data))
    
    if not wait_ack(bus):
        print("[CAN] Error: CRC 불일치 또는 End ACK Fail!")
        return
    print("[CAN] 펌웨어 무결성 검증 통과 및 플래싱 완료!")

    time.sleep(0.5)
    bus.send(build_can_frame(CAN_ID_CMD, [CMD_FW_JUMP_TO_FW]))
    print("[CAN] 점프 명령 전송 완료!")

if __name__ == '__main__':
    # CAN 인터페이스 활성화
    os.system("sudo ip link set can0 down 2>/dev/null")
    os.system("sudo ip link set can0 up type can bitrate 1000000 2>/dev/null")
    
    if download_firmware_via_lte(FW_URL, SAVE_PATH):
        start_can_fota(SAVE_PATH)
    else:
        print("[System] 다운로드 실패로 FOTA를 종료합니다.")