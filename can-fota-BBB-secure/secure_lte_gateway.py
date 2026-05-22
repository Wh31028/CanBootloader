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
# 1. 설정 및 커스텀 프로토콜 매크로
# ==========================================
FW_URL            = "https://unbarreled-alayna-eustatic.ngrok-free.dev/boot_can_fw.bin"
SAVE_PATH         = "received_fw.bin"

CAN_ID_RESP         = 0x101
CAN_ID_CMD          = 0x100
CAN_ID_FOTA_REQUEST = 0x200  # App FW에게 FOTA 진입 요청

# [Host -> Target] 명령어 (상위 2비트)
CMD_RX_DATA  = 0x00
CMD_RX_START = 0x01
CMD_RX_END   = 0x02
CMD_RX_JUMP  = 0x03

# [Target -> Host] 응답 코드 (상위 2비트)
CMD_TX_ACK  = 0x00
CMD_TX_NACK = 0x01
CMD_TX_ERR  = 0x02

# ------------------------------------------
# 암호화 키 설정 (Hardcoded for Demo)
# ------------------------------------------
AES_KEY = bytes([0x2b, 0x7e, 0x15, 0x16, 0x28, 0xae, 0xd2, 0xa6, 0xab, 0xf7, 0x15, 0x88, 0x09, 0xcf, 0x4f, 0x3c])
AES_IV  = bytes([0x00, 0x01, 0x02, 0x03, 0x04, 0x05, 0x06, 0x07, 0x08, 0x09, 0x0a, 0x0b, 0x0c, 0x0d, 0x0e, 0x0f])
ECDSA_PRIV_KEY_HEX = "18e14a7b6a307f426a94f8114701e7c8e774e7f9a47e2c2035db29a206321725"
priv_key = SigningKey.from_string(bytes.fromhex(ECDSA_PRIV_KEY_HEX), curve=NIST256p)

def pack_header(cmd, seq):
    return ((cmd & 0x03) << 6) | (seq & 0x3F)

# ==========================================
# 2. 보안 펌웨어 패킹 (Phase 1)
# ==========================================
def prepare_secure_firmware(fw_data):
    print("[Secure FOTA] Phase 1: 펌웨어 암호화 및 서명 조립 시작...")
    
    # 1. SHA-256(plaintext)
    sha256_pt = hashlib.sha256(fw_data).digest()
    
    # 2. ECDSA-Sign(sha256_pt)
    sig_pt = priv_key.sign_digest(sha256_pt)  # 64 bytes (R, S)

    # 3. AES-128-CBC-Encrypt(plaintext)
    # PKCS7 Padding to 16 bytes
    padder = padding.PKCS7(128).padder()
    padded_fw = padder.update(fw_data) + padder.finalize()
    
    cipher = Cipher(algorithms.AES(AES_KEY), modes.CBC(AES_IV), backend=default_backend())
    encryptor = cipher.encryptor()
    enc_fw = encryptor.update(padded_fw) + encryptor.finalize()

    # 4. SHA-256(encrypted)
    sha256_enc = hashlib.sha256(enc_fw).digest()

    # 5. ECDSA-Sign(sha256_enc)
    sig_enc = priv_key.sign_digest(sha256_enc)

    # 6. Build 228-byte Header
    fw_version = 1
    fw_size = len(fw_data)
    
    # Header format: Version(4), Size(4), SHA256_PT(32), SIG_PT(64), SHA256_ENC(32), SIG_ENC(64), IV(16), Padding(24) = 240
    header = struct.pack("<II", fw_version, fw_size)
    header += sha256_pt
    header += sig_pt
    header += sha256_enc
    header += sig_enc
    header += AES_IV
    header += b'\x00' * 24 # 24 bytes padding to 240

    assert len(header) == 240, f"Header size is {len(header)} instead of 240"

    payload = header + enc_fw
    
    # 전송 편의성을 위해 전체 페이로드를 256의 배수로 패딩 (CAN 블록 일치)
    rem = len(payload) % 256
    if rem != 0:
        payload += b'\xFF' * (256 - rem)
        
    print(f"  > 원본 크기: {len(fw_data)} bytes")
    print(f"  > 암호화 후 전체 페이로드 크기: {len(payload)} bytes (256바이트 정렬됨)")
    return payload

# ==========================================
# 3. 통신 유틸리티
# ==========================================
def download_firmware_via_lte(url, save_path):
    print(f"=============================================")
    print(f" [LTE] FOTA 다운로드 시작 (서버 접속 중...)")
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

def build_can_frame(can_id, data_list):
    data_bytes = bytes(data_list)
    data_padded = data_bytes + b'\x00' * (8 - len(data_bytes))
    return struct.pack("<IB3x8s", can_id, len(data_bytes), data_padded)

def send_frame_with_enobufs(bus, frame):
    while True:
        try:
            bus.send(frame)
            break
        except OSError as e:
            if getattr(e, 'errno', None) == 105:
                time.sleep(0.0005)
            else:
                raise

def wait_response(bus, timeout=2.0):
    bus.settimeout(timeout)
    start_time = time.time()
    while (time.time() - start_time) < timeout:
        try:
            frame = bus.recv(16)
            if len(frame) == 16:
                rx_id, rx_dlc, rx_data = struct.unpack("<IB3x8s", frame)
                rx_id &= 0x7FF

                if rx_id == CAN_ID_RESP:
                    header = rx_data[0]
                    cmd = (header >> 6) & 0x03

                    if cmd == CMD_TX_ACK or cmd == CMD_TX_ERR:
                        result = header & 0x3F
                        return (cmd, result)
                    elif cmd == CMD_TX_NACK:
                        nack_map = 0
                        for i in range(1, 8):
                            nack_map |= (rx_data[i] << (8 * (i - 1)))
                        return (cmd, nack_map)

        except socket.timeout:
            return None
        except BlockingIOError:
            pass
    return None

def trigger_fota_entry(bus):
    print("[FOTA] STM32 App FW에 FOTA 진입 신호 전송 중...")
    trigger_frame = build_can_frame(CAN_ID_FOTA_REQUEST, [0xDE, 0xAD])
    bus.send(trigger_frame)
    time.sleep(3.0)

# ==========================================
# 4. Custom FOTA 메인 전송 로직
# ==========================================
def start_can_fota(firmware_path):
    print(f"=============================================")
    print(f"[CAN] SECURE FOTA (ECDSA+AES) 시작!")
    print(f"=============================================")
    try:
        bus = socket.socket(socket.AF_CAN, socket.SOCK_RAW, socket.CAN_RAW)
        bus.bind(('can0',))
    except Exception as e:
        print(f"[CAN] 소켓 초기화 실패: {e}")
        return

    trigger_fota_entry(bus)

    with open(firmware_path, "rb") as f:
        raw_fw_data = f.read()

    # 1. 펌웨어 보안 패킹 수행
    fw_data = prepare_secure_firmware(raw_fw_data)
    fw_size = len(fw_data)

    fota_start_time = time.time()
    total_tx_frames = 0
    total_rx_frames = 0
    retransmitted_frames = 0

    # ----------------------------------------------------------
    # 2. START 전송
    # ----------------------------------------------------------
    payload_start = [pack_header(CMD_RX_START, 0)] + list(fw_size.to_bytes(4, byteorder='little'))
    frame = build_can_frame(CAN_ID_CMD, payload_start)
    send_frame_with_enobufs(bus, frame)
    total_tx_frames += 1
    print("[CAN] CMD_RX_START 전송 (Flash 지우기 대기 중... ⏳)")

    resp = wait_response(bus, timeout=10.0)
    if not resp or resp[0] != CMD_TX_ACK:
        print(f"[CAN] Error: Erase ACK 실패. 응답: {resp}")
        return
    total_rx_frames += 1
    print("[CAN] Erase 완료! 본격 암호화 데이터 전송 시작 🚀")

    # ----------------------------------------------------------
    # 3. DATA 전송 (256B 블록 + 비트맵 NACK)
    # ----------------------------------------------------------
    idx = 0
    while idx < fw_size:
        block_data = fw_data[idx : idx + 256]
        frames = []

        for seq in range(0, len(block_data), 7):
            chunk = block_data[seq : seq + 7]
            seq_num = seq // 7
            header = pack_header(CMD_RX_DATA, seq_num)
            payload = [header] + list(chunk)
            frames.append((seq_num, payload))

        expected_frames = len(frames)

        for seq_num, payload in frames:
            total_tx_frames += 1
            frame = build_can_frame(CAN_ID_CMD, payload)
            send_frame_with_enobufs(bus, frame)

        # 수신 대기 (타임아웃을 1초 정도로 여유있게 주어 타겟 보드의 서명 검증/AES 복호화 딜레이를 흡수!)
        # 기존 프로토콜의 STmin 없이도 완벽히 대기
        while True:
            response = wait_response(bus, timeout=1.5)  # STM32 연산 시간을 충분히 기다림
            if response:
                total_rx_frames += 1

            if not response:
                print("\n[CAN Warning] 응답 타임아웃! (STM32 암호화 연산 중일 수도 있으나 타임아웃 처리) 꼬리 프레임 단독 송출!")
                last_seq = expected_frames - 1
                frame = build_can_frame(CAN_ID_CMD, frames[last_seq][1])
                send_frame_with_enobufs(bus, frame)
                total_tx_frames += 1
                retransmitted_frames += 1
                continue

            cmd, args = response

            if cmd == CMD_TX_ACK:
                idx += len(block_data)
                print(f"\r[CAN] 진행률: {idx}/{fw_size} bytes ({(idx/fw_size)*100:.1f}%)", end='', flush=True)
                break
            elif cmd == CMD_TX_NACK:
                nack_map = args
                missing_seqs = [seq for seq in range(expected_frames) if (nack_map & (1 << seq)) == 0]
                print(f"\n[CAN Recovery] 손실 프레임 {len(missing_seqs)}개. 선별 재전송 실행!")
                for seq_num in missing_seqs:
                    total_tx_frames += 1
                    retransmitted_frames += 1
                    frame = build_can_frame(CAN_ID_CMD, frames[seq_num][1])
                    send_frame_with_enobufs(bus, frame)
            elif cmd == CMD_TX_ERR:
                print(f"\n[CAN Error] 타겟 보드 보안 검증 또는 플래시 에러! 코드: {args}")
                return

    print("\n[CAN] 암호화 펌웨어 전체 전송 완료!")

    # ----------------------------------------------------------
    # 4. END 전송
    # ----------------------------------------------------------
    print("[CAN] 전체 통신 CRC32 비교 전송 (통신 무결성 점검)...")
    fw_crc32 = zlib.crc32(fw_data) & 0xFFFFFFFF
    payload_end = [pack_header(CMD_RX_END, 0)] + list(fw_crc32.to_bytes(4, byteorder='little'))
    frame = build_can_frame(CAN_ID_CMD, payload_end)
    send_frame_with_enobufs(bus, frame)
    total_tx_frames += 1

    resp = wait_response(bus, timeout=3.0)
    if not resp or resp[0] != CMD_TX_ACK:
        print(f"[CAN] Error: 무결성 검증 실패! 응답: {resp}")
        return
    total_rx_frames += 1
    print("[CAN] 펌웨어 무결성 및 암호학적 검증 최종 통과! ✅")

    total_time = time.time() - fota_start_time
    overhead_pct = (retransmitted_frames / total_tx_frames * 100) if total_tx_frames > 0 else 0.0
    print(f"=============================================")
    print(f"[RESULT] 총 소요 시간: {total_time:.2f} 초")
    print(f"=============================================")

    time.sleep(0.5)
    payload_jump = [pack_header(CMD_RX_JUMP, 0)]
    frame = build_can_frame(CAN_ID_CMD, payload_jump)
    send_frame_with_enobufs(bus, frame)
    print("[CAN] JUMP 명령 전송 완료. 디바이스 재부팅 확인 요망!")

if __name__ == '__main__':
    os.system("sudo ip link set can0 down 2>/dev/null")
    os.system("sudo ip link set can0 up type can bitrate 1000000 2>/dev/null")

    if len(sys.argv) > 1:
        local_path = sys.argv[1]
        start_can_fota(local_path)
    elif os.path.exists(SAVE_PATH):
        start_can_fota(SAVE_PATH)
    elif download_firmware_via_lte(FW_URL, SAVE_PATH):
        start_can_fota(SAVE_PATH)
    else:
        print("[System] 취소됨.")
