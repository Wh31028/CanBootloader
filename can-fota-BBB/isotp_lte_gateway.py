import os
import time
import struct
import socket
import urllib.request
import ssl
import zlib
import random  
import can
import isotp

# ==========================================
# FOTA 서버 및 CAN 설정
# ==========================================
FW_URL            = "https://unbarreled-alayna-eustatic.ngrok-free.dev/boot_can_fw.bin"
SAVE_PATH         = "received_fw.bin"

CMD_FW_START      = 0x10
CMD_FW_DATA       = 0x20
CMD_FW_END        = 0x30
CMD_FW_JUMP_TO_FW = 0x40

# ISO-TP ID 설정
CAN_ID_RESP       = 0x7E8 # MCU -> PC
CAN_ID_CMD        = 0x7E0 # PC -> MCU

# 테스트용 패킷 로스율 (필요하다면 유지하지만 ISO-TP에서는 의미가 다를 수 있음)
LOSS_RATE         = 0.05 

# ISO-TP 한번에 보낼 사이즈
MAX_CHUNK_SIZE    = 1000

# ==========================================
# 1. LTE 다운로드 (urllib 사용)
# ==========================================
def download_firmware_via_lte(url, save_path):
    print(f"=============================================")
    print(f" [LTE] FOTA 다운로드 시작 (서버 접속 중...)")
    print(f" URL: {url}")
    print(f"=============================================")
    try:
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
# 2. ISO-TP FOTA 통신
# ==========================================
def wait_ack(stack, expected_cmd, timeout=5.0):
    start_time = time.time()
    while (time.time() - start_time) < timeout:
        stack.process()
        if stack.available():
            rx_payload = stack.recv()
            if rx_payload and len(rx_payload) >= 2:
                cmd = rx_payload[0]
                result = rx_payload[1]
                if cmd == expected_cmd and result == 0:
                    return True, rx_payload
                elif cmd == expected_cmd and result != 0:
                    print(f"[CAN] Error From STM32 : cmd: {hex(cmd)}, result: {hex(result)}")
                    return False, rx_payload
        time.sleep(0.005)
    return False, None

def start_can_fota(firmware_path):
    print(f"[CAN] ISO-TP FOTA Flashing 시작: {firmware_path}")
    # print(f"[TEST] 🚨 결함 주입 모드 활성화 (Loss Rate: {LOSS_RATE*100}%) 🚨") # ISO-TP는 자체 재전송/에러처리가 있어서 기존 패킷 드랍 방식은 다르게 동작합니다.
    
    try:
        bus = can.interface.Bus(channel='can0', bustype='socketcan')
        addr = isotp.Address(isotp.AddressingMode.Normal_11bits, rxid=CAN_ID_RESP, txid=CAN_ID_CMD)
        stack = isotp.CanStack(bus, address=addr)
    except Exception as e:
        print(f"[CAN] 소켓 초기화 실패: {e}")
        return

    with open(firmware_path, "rb") as f:
        fw_data = f.read()
    fw_size = len(fw_data)
    print(f"[CAN] 전송할 펌웨어 크기: {fw_size} bytes")

    # 3. [Start] 명령 전송
    # [CMD_FW_START (1byte)] + [Size (4bytes, Little Endian)]
    cmd_start = bytes([CMD_FW_START]) + struct.pack('<I', fw_size)
    stack.send(cmd_start)
    while stack.transmitting():
        stack.process(); time.sleep(0.002)
    
    # MCU가 전체 플래시를 지우는 데 시간이 오래 걸릴 수 있으므로 넉넉히 15초 대기
    success, rx_payload = wait_ack(stack, CMD_FW_START, timeout=15.0)
    if not success:
        print("[CAN] Error: Erase ACK Timeout/Fail")
        return

    if rx_payload and len(rx_payload) >= 4:
        chunk_size = rx_payload[2] | (rx_payload[3] << 8)
        print(f"[CAN] START 성공! STM32가 {chunk_size} bytes 단위로 보내라고 하네요.")
    else:
        chunk_size = MAX_CHUNK_SIZE
        print(f"[CAN] START 성공! (단, chunk_size 정보 확인 불가, 기본값 {chunk_size} 사용)")

    # 4. [Data] 데이터 전송 (ISO-TP로 분할 전송)
    print("[CAN] Firmware Data 전송 중 (ISO-TP)...")
    for i in range(0, fw_size, chunk_size):
        chunk = fw_data[i : i + chunk_size]
        payload = bytes([CMD_FW_DATA]) + chunk
        
        # 참고: 기존 lte_gateway의 패킷 로스 테스트는 개별 CAN 프레임 드랍이었습니다.
        # ISO-TP 환경에서 중간 프레임을 고의로 떨어뜨리려면 isotp 하위 레이어를 수정하거나 
        # python-can 레벨에서 후킹해야 하므로 이 코드에서는 정상 전송만 수행합니다.
        
        stack.send(payload)
        while stack.transmitting():
            stack.process(); time.sleep(0.002)
            
        success, _ = wait_ack(stack, CMD_FW_DATA, timeout=2.0)
        if not success:
            print(f"[CAN] Error: Data Write ACK Fail at index {i}")
            return

    print("\n[CAN] 데이터 전송 완료")
    print("[CAN] 전체 펌웨어 CRC32 계산 중 (선택사항, STM32가 처리)...")
    
    # 5. [End] 종료명령 (기존 lte_gateway처럼 CRC 값을 보내줄 수 있습니다)
    fw_crc32 = zlib.crc32(fw_data) & 0xFFFFFFFF
    
    # STM32는 payload[1]~[4]로 CRC를 파싱합니다. (Little Endian)
    # [CMD_FW_END (1byte)] + [CRC32 (4bytes)]
    end_data = bytes([CMD_FW_END]) + struct.pack('<I', fw_crc32)
    
    stack.send(end_data)
    while stack.transmitting():
        stack.process(); time.sleep(0.002)
        
    # 플래시에 남은 데이터를 쓰는 시간 + 전체 CRC 계산 시간이 있으므로 넉넉하게 대기
    success, _ = wait_ack(stack, CMD_FW_END, timeout=5.0)
    if not success:
        print("[CAN] ❌ Error: End ACK Fail (CRC 불일치 혹은 타임아웃)")
    else:
        print("[CAN] 펌웨어 무결성 검증 통과 및 플래싱 완료!")

    # 6. [Jump] 앱 실행 명령
    time.sleep(0.5)
    cmd_jump = bytes([CMD_FW_JUMP_TO_FW])
    stack.send(cmd_jump)
    while stack.transmitting():
        stack.process(); time.sleep(0.002)
        
    success, _ = wait_ack(stack, CMD_FW_JUMP_TO_FW)
    if success:
        print("[CAN] 점프 성공! MCU가 재부팅됩니다.")
    else:
        print("[CAN] 점프 명령 보냈으나 응답 없음 (이미 점프했을 수도 있음)")

if __name__ == '__main__':
    # ISO-TP 통신을 위해 can 인터페이스 활성화
    os.system("sudo ip link set can0 down 2>/dev/null")
    os.system("sudo ip link set can0 up type can bitrate 1000000 2>/dev/null")
    
    if download_firmware_via_lte(FW_URL, SAVE_PATH):
        start_can_fota(SAVE_PATH)
    else:
        print("[System] 다운로드 실패로 FOTA를 종료합니다.")
