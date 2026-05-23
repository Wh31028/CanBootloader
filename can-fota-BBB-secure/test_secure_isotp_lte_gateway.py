import os
import time
import struct
import socket
import urllib.request
import ssl
import zlib
import sys
import hashlib
try:
    from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
    from cryptography.hazmat.primitives import padding
    from cryptography.hazmat.backends import default_backend
    from ecdsa import SigningKey, NIST256p
except ImportError:
    print("Please install requirements: pip install cryptography ecdsa")
    sys.exit(1)

# ==========================================
# FOTA 서버 및 CAN 설정
# ==========================================
FW_URL            = "https://unbarreled-alayna-eustatic.ngrok-free.dev/boot_can_fw.bin"
SAVE_PATH         = "received_fw.bin"

CMD_FW_START      = 0x10
CMD_FW_DATA       = 0x20
CMD_FW_END        = 0x30
CMD_FW_JUMP_TO_FW = 0x40

# CAN ID 설정 (ISO-TP)
CAN_ID_RESP         = 0x7E8  # MCU -> PC
CAN_ID_CMD          = 0x7E0  # PC -> MCU
CAN_ID_FOTA_REQUEST = 0x200  # App FW에게 FOTA 진입 요청

# ------------------------------------------
# 암호화 키 설정 (Hardcoded for Demo)
# ------------------------------------------
AES_KEY = bytes([0x2b, 0x7e, 0x15, 0x16, 0x28, 0xae, 0xd2, 0xa6, 0xab, 0xf7, 0x15, 0x88, 0x09, 0xcf, 0x4f, 0x3c])
AES_IV  = bytes([0x00, 0x01, 0x02, 0x03, 0x04, 0x05, 0x06, 0x07, 0x08, 0x09, 0x0a, 0x0b, 0x0c, 0x0d, 0x0e, 0x0f])
ECDSA_PRIV_KEY_HEX = "18e14a7b6a307f426a94f8114701e7c8e774e7f9a47e2c2035db29a206321725"
priv_key = SigningKey.from_string(bytes.fromhex(ECDSA_PRIV_KEY_HEX), curve=NIST256p)

# ==========================================
# 보안 펌웨어 패킹 (Phase 1)
# ==========================================
def prepare_secure_firmware(fw_data):
    print("[Secure FOTA] Phase 1: 펌웨어 암호화 및 서명 조립 시작...")
    t0 = time.time()
    
    # [BUG FIX] 해시 계산 및 암호화 이전에 원본 펌웨어를 256바이트로 미리 패딩!
    # 이렇게 하면 PKCS7(16바이트) + Header(240바이트) = 256바이트가 추가되어 전체 페이로드가 항상 256의 배수가 됩니다.
    rem = len(fw_data) % 256
    if rem != 0:
        fw_data += b'\xFF' * (256 - rem)

    t_start = time.time()
    sha256_pt = hashlib.sha256(fw_data).digest()
    t_sha256_pt = time.time() - t_start
    
    t_start = time.time()
    sig_pt = priv_key.sign_digest(sha256_pt) 
    t_sig_pt = time.time() - t_start

    t_start = time.time()
    padder = padding.PKCS7(128).padder()
    padded_fw = padder.update(fw_data) + padder.finalize()
    
    cipher = Cipher(algorithms.AES(AES_KEY), modes.CBC(AES_IV), backend=default_backend())
    encryptor = cipher.encryptor()
    enc_fw = encryptor.update(padded_fw) + encryptor.finalize()
    t_aes = time.time() - t_start

    t_start = time.time()
    sha256_enc = hashlib.sha256(enc_fw).digest()
    t_sha256_enc = time.time() - t_start
    
    t_start = time.time()
    sig_enc = priv_key.sign_digest(sha256_enc)
    t_sig_enc = time.time() - t_start

    fw_version = 1
    fw_size = len(fw_data)
    
    header = struct.pack("<II", fw_version, fw_size)
    header += sha256_pt
    header += sig_pt
    header += sha256_enc
    header += sig_enc
    header += AES_IV
    header += b'\x00' * 24 # 24 bytes padding to 240

    assert len(header) == 240, f"Header size is {len(header)} instead of 240"

    payload = header + enc_fw
        
    t_total_pack = time.time() - t0
    print(f"  > 원본 크기: {len(fw_data)} bytes")
    print(f"  > 암호화 후 전체 페이로드 크기: {len(payload)} bytes (256바이트 정렬됨)")
    print(f"  [Timing] SHA256(PT): {t_sha256_pt*1000:.2f}ms")
    print(f"  [Timing] ECDSA(PT): {t_sig_pt*1000:.2f}ms")
    print(f"  [Timing] AES-128-CBC: {t_aes*1000:.2f}ms")
    print(f"  [Timing] SHA256(ENC): {t_sha256_enc*1000:.2f}ms")
    print(f"  [Timing] ECDSA(ENC): {t_sig_enc*1000:.2f}ms")
    print(f"  [Timing] Total Packing Time: {t_total_pack*1000:.2f}ms")
    timings = (t_sha256_pt, t_sig_pt, t_aes, t_sha256_enc, t_sig_enc, t_total_pack)
    return payload, timings

# ==========================================
# 유틸리티
# ==========================================
def build_can_frame(can_id, data_bytes):
    data_padded = data_bytes + b'\x00' * (8 - len(data_bytes))
    return struct.pack("<IB3x8s", can_id, len(data_bytes), data_padded)

def send_frame_with_enobufs(bus, payload):
    frame = build_can_frame(CAN_ID_CMD, payload)
    while True:
        try:
            bus.send(frame)
            break
        except OSError as e:
            if getattr(e, 'errno', None) == 105:
                time.sleep(0.0005)
            else:
                raise

def flush_rx_buffer(bus):
    bus.settimeout(0.0)
    while True:
        try:
            bus.recv(16)
        except BlockingIOError:
            break
        except Exception:
            break

def trigger_fota_entry(bus):
    print("[FOTA] STM32 App FW에 FOTA 진입 신호 전송 중...")
    frame = build_can_frame(CAN_ID_FOTA_REQUEST, bytes([0xDE, 0xAD]))
    bus.send(frame)
    time.sleep(3.0)
    flush_rx_buffer(bus)

def wait_sf_ack(bus, expected_cmd, timeout=3.0):
    bus.settimeout(timeout)
    start_time = time.time()
    while time.time() - start_time < timeout:
        try:
            frame = bus.recv(16)
            if len(frame) == 16:
                rx_id, rx_dlc, rx_data = struct.unpack("<IB3x8s", frame)
                rx_id &= 0x7FF
                if rx_id == CAN_ID_RESP:
                    if (rx_data[0] & 0xF0) == 0x00:
                        sf_len = rx_data[0] & 0x0F
                        if sf_len >= 2 and rx_data[1] == expected_cmd:
                            return rx_data[1:1 + sf_len]
        except socket.timeout:
            return None
        except BlockingIOError:
            pass
    return None

def raw_isotp_send_chunk(bus, payload):
    payload_len = len(payload)

    ff_data = bytearray(8)
    ff_data[0] = 0x10 | ((payload_len >> 8) & 0x0F)
    ff_data[1] = payload_len & 0xFF
    ff_data[2:8] = payload[0:6]
    send_frame_with_enobufs(bus, ff_data)

    fc_received = False
    stmin_sec = 0.0
    bus.settimeout(1.0)
    start_time = time.time()
    while time.time() - start_time < 1.0:
        try:
            frame = bus.recv(16)
            if len(frame) == 16:
                rx_id, rx_dlc, rx_data = struct.unpack("<IB3x8s", frame)
                rx_id &= 0x7FF
                if rx_id == CAN_ID_RESP and (rx_data[0] & 0xF0) == 0x30:
                    fc_received = True
                    stmin_val = rx_data[2]
                    if stmin_val <= 0x7F:
                        stmin_sec = stmin_val / 1000.0
                    elif 0xF1 <= stmin_val <= 0xF9:
                        stmin_sec = (stmin_val - 0xF0) / 10000.0
                    else:
                        stmin_sec = 0.127 
                    break
        except socket.timeout:
            break
        except BlockingIOError:
            pass

    if not fc_received:
        return False

    seq = 1
    idx = 6
    while idx < payload_len:
        cf_len = min(7, payload_len - idx)
        cf_data = bytearray(8)
        cf_data[0] = 0x20 | (seq & 0x0F)
        cf_data[1:1 + cf_len] = payload[idx:idx + cf_len]
        send_frame_with_enobufs(bus, cf_data)
        
        if stmin_sec > 0:
            time.sleep(stmin_sec)
            
        idx += cf_len
        seq = (seq + 1) & 0x0F

    return True

def download_firmware_via_lte(url, save_path):
    print(f"=============================================")
    print(f" [LTE] FOTA 다운로드 시작")
    try:
        ctx = ssl.create_default_context()
        ctx.check_hostname = False
        ctx.verify_mode = ssl.CERT_NONE
        req = urllib.request.Request(url)
        with urllib.request.urlopen(req, context=ctx, timeout=10) as response:
            fw_data = response.read()
            with open(save_path, "wb") as f:
                f.write(fw_data)
        print(f"[LTE] 다운로드 완료! 크기: {len(fw_data)} bytes\n")
        return True
    except Exception as e:
        print(f"[LTE Error] 다운로드 실패: {e}")
        return False

# ==========================================
# ISO-TP FOTA 메인 전송 로직
# ==========================================
def start_can_fota(firmware_path, target_kb=0):
    print(f"[CAN] SECURE ISO-TP FOTA Flashing 시작: {firmware_path}")

    try:
        bus = socket.socket(socket.AF_CAN, socket.SOCK_RAW, socket.CAN_RAW)
        bus.bind(('can0',))
    except Exception as e:
        print(f"[CAN] 소켓 초기화 실패: {e}")
        return

    trigger_fota_entry(bus)

    with open(firmware_path, "rb") as f:
        raw_fw_data = f.read()

    if target_kb > 0:
        target_bytes = target_kb * 1024
        if len(raw_fw_data) < target_bytes:
            raw_fw_data += b'\xFF' * (target_bytes - len(raw_fw_data))
            print(f"[Dummy Padding] 펌웨어를 {target_kb}KB({target_bytes} bytes)로 강제 패딩했습니다!")

    fw_data, timings = prepare_secure_firmware(raw_fw_data)
    t_sha256_pt, t_sig_pt, t_aes, t_sha256_enc, t_sig_enc, t_total_pack = timings
    fw_size = len(fw_data)

    fota_start_time = time.time()
    total_tx_frames = 0
    total_rx_frames = 0
    retransmitted_frames = 0

    flush_rx_buffer(bus)

    # 1. START
    t_erase_start = time.time()
    sf_data = bytearray(8)
    sf_data[0] = 0x05
    sf_data[1] = CMD_FW_START
    sf_data[2:6] = struct.pack('<I', fw_size)
    send_frame_with_enobufs(bus, sf_data)
    total_tx_frames += 1

    rx_payload = wait_sf_ack(bus, CMD_FW_START, timeout=15.0)
    t_erase = time.time() - t_erase_start

    if not rx_payload:
        print("[CAN] Error: Erase ACK Timeout")
        return
    total_rx_frames += 1

    if len(rx_payload) >= 4:
        chunk_size = rx_payload[2] | (rx_payload[3] << 8)
        print(f"[CAN] START 성공! STM32가 {chunk_size} bytes 단위로 보내라고 하네요.")
    else:
        chunk_size = 256

    # 2. DATA
    print("[CAN] Firmware Data 전송 중 (Raw ISO-TP)...")
    t_transfer_start = time.time()

    for i in range(0, fw_size, chunk_size):
        chunk = fw_data[i: i + chunk_size]
        payload = bytes([CMD_FW_DATA]) + chunk

        retry_count = 0
        success = False

        while retry_count < 3:
            if retry_count > 0:
                retransmitted_frames += (len(payload) + 6) // 7
                flush_rx_buffer(bus)

            if raw_isotp_send_chunk(bus, payload):
                # ISO-TP에서는 STM32가 복호화하고 서명을 검증하는 동안 타임아웃이 발생할 수 있음
                ack = wait_sf_ack(bus, CMD_FW_DATA, timeout=1.5)
                if ack and ack[1] == 0:  
                    total_rx_frames += 1
                    success = True
                    break

            retry_count += 1

        if not success:
            print("\n[CAN] 치명적 에러: STM32가 응답하지 않음. (ISO-TP 오버런 발생 가능성 큼!)")
            return

        idx = min(i + chunk_size, fw_size)
        print(f"\r[CAN] 진행률: {idx}/{fw_size} bytes ({(idx/fw_size)*100:.1f}%)", end='', flush=True)

    t_transfer = time.time() - t_transfer_start
    print("\n[CAN] 데이터 전송 완료")

    # 3. END
    t_verify_start = time.time()
    fw_crc32 = zlib.crc32(fw_data) & 0xFFFFFFFF
    sf_data = bytearray(8)
    sf_data[0] = 0x05
    sf_data[1] = CMD_FW_END
    sf_data[2:6] = struct.pack('<I', fw_crc32)
    send_frame_with_enobufs(bus, sf_data)
    total_tx_frames += 1

    ack = wait_sf_ack(bus, CMD_FW_END, timeout=10.0)
    t_verify = time.time() - t_verify_start
    if ack and ack[1] == 0:
        total_rx_frames += 1
        print("\n[CAN] 무결성 검증 통과 및 플래싱 완료! ✅")
    else:
        if ack is None:
            print("\n[CAN] ❌ Error: End ACK Timeout!")
            print("         👉 원인 분석: STM32가 응답하지 않습니다. (타임아웃 10초 초과)")
            print("         👉 데이터 전송 중에 CAN 프레임을 잃어버려서 STM32가 아직도 데이터를 기다리는 상태(수신 랙)에 빠졌을 확률이 높습니다.")
        else:
            print(f"\n[CAN] ❌ Error: End ACK Fail (응답 코드: {ack[1]})")
        return

    total_time = time.time() - fota_start_time
    overhead_pct = (retransmitted_frames / total_tx_frames * 100) if total_tx_frames > 0 else 0.0
    print(f"=============================================")
    print(f"[RESULT] 총 소요 시간: {total_time:.2f} 초")
    print(f"  - STM32 플래시 Erase 소요 시간: {t_erase:.3f} 초")
    print(f"  - STM32 데이터 수신 및 AES 해독/쓰기 시간: {t_transfer:.3f} 초")
    print(f"  - STM32 ECDSA 서명 검증 소요 시간: {t_verify:.3f} 초")
    print(f"=============================================")
    print(f"csv_result,ISOTP,{fw_size},{total_time:.3f},{total_tx_frames},{total_rx_frames},{retransmitted_frames},{t_total_pack:.3f},{t_sha256_pt*1000:.2f},{t_sig_pt*1000:.2f},{t_aes*1000:.2f},{t_sha256_enc*1000:.2f},{t_sig_enc*1000:.2f},{t_erase:.3f},{t_transfer:.3f},{t_verify:.3f}")

    # 4. JUMP
    time.sleep(0.5)
    sf_data = bytearray(8)
    sf_data[0] = 0x02
    sf_data[1] = CMD_FW_JUMP_TO_FW
    sf_data[2] = 0x00
    send_frame_with_enobufs(bus, sf_data)

if __name__ == '__main__':
    os.system("sudo ip link set can0 down 2>/dev/null")
    os.system("sudo ip link set can0 up type can bitrate 1000000 2>/dev/null")

    target_kb = 0
    if len(sys.argv) > 2:
        try:
            target_kb = int(sys.argv[2])
        except ValueError:
            target_kb = 0

    if len(sys.argv) > 1:
        local_path = sys.argv[1]
        start_can_fota(local_path, target_kb)
    elif os.path.exists(SAVE_PATH):
        start_can_fota(SAVE_PATH, target_kb)
    elif download_firmware_via_lte(FW_URL, SAVE_PATH):
        start_can_fota(SAVE_PATH, target_kb)
    else:
        print("[System] 취소됨.")
