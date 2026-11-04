# pyrefly: ignore [missing-import]
from fastapi import FastAPI, Request, UploadFile, File, WebSocket, WebSocketDisconnect
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates

import os
import re
import asyncio
import socket
import struct
import time

app = FastAPI()

active_connections = []

CUSTOM_CAN_ID_CMD = 0x100
CUSTOM_CAN_ID_RESP = 0x101
CUSTOM_CAN_ID_FOTA_REQUEST = 0x200
CUSTOM_CMD_RX_DATA = 0
CUSTOM_CMD_TX_ACK = 0
CUSTOM_CMD_TX_NACK = 1
CUSTOM_CMD_TX_ERR = 2
CUSTOM_ERR_NAMES = {0x06: "CRC mismatch, image rejected"}

CAN_BATCH_INTERVAL_S = 0.2
CAN_BATCH_MAX_FRAMES = 50
CAN_BATCH_MAX_PRIORITY = 50

# Matches the flasher's log line for an injected drop; the frame never reaches the bus.
DROP_LOG_PATTERN = re.compile(r"\[FAULT\] DATA 프레임 드롭 주입 \(seq (\d+)\)")

def decode_custom_event(can_id, data, block_max_seq):
    """Classifies one Custom FOTA frame; returns (event, text, block_max_seq).

    block_max_seq is the highest DATA seq seen in the current block, or -1.
    A seq at or below it was already sent, so the frame is a retransmission.
    """
    if not data:
        return None, None, block_max_seq

    command = data[0] >> 6
    if can_id == CUSTOM_CAN_ID_CMD:
        if command != CUSTOM_CMD_RX_DATA:
            return None, None, -1
        seq = data[0] & 0x3F
        if seq <= block_max_seq:
            return "retx", f"RETX seq {seq}", block_max_seq
        return None, None, seq

    if can_id == CUSTOM_CAN_ID_RESP:
        if command == CUSTOM_CMD_TX_ACK:
            return None, None, -1
        if command == CUSTOM_CMD_TX_NACK and len(data) == 8:
            # A NACK only follows the block's last frame, so block_max_seq bounds the block.
            bitmap = int.from_bytes(data[1:8], "little")
            missing = [str(s) for s in range(block_max_seq + 1) if not bitmap & (1 << s)]
            return "nack", "NACK missing: " + ", ".join(missing), block_max_seq
        if command == CUSTOM_CMD_TX_ERR:
            code = data[0] & 0x3F
            name = CUSTOM_ERR_NAMES.get(code, "target error")
            return "err", f"ERR 0x{code:02X} ({name})", block_max_seq

    return None, None, block_max_seq

def is_priority_frame(can_id, data, event):
    """Protocol milestones and fault events are always shown; first-pass DATA is sampled."""
    if event is not None or can_id in (CUSTOM_CAN_ID_RESP, CUSTOM_CAN_ID_FOTA_REQUEST):
        return True
    return can_id == CUSTOM_CAN_ID_CMD and bool(data) and data[0] >> 6 != CUSTOM_CMD_RX_DATA

async def flush_can_batches(state):
    """Sends on a timer so the last frames of a transfer are not held back."""
    while True:
        await asyncio.sleep(CAN_BATCH_INTERVAL_S)
        if not state["frames"] and state["count"] == 0:
            continue
        msg = {"type": "can_frames", "frames": state["frames"], "count": state["count"]}
        state["frames"] = []
        state["count"] = 0
        state["priority"] = 0
        for conn in list(active_connections):
            try:
                await conn.send_json(msg)
            except Exception:
                pass

async def can_sniffer_task():
    try:
        s = socket.socket(socket.AF_CAN, socket.SOCK_RAW, socket.CAN_RAW)
        s.bind(('can0',))
        s.setblocking(False)
    except Exception as e:
        print(f"CAN Sniffer init failed: {e}")
        return

    loop = asyncio.get_event_loop()
    state = {"frames": [], "count": 0, "priority": 0}
    block_max_seq = -1
    frames_processed = 0
    asyncio.create_task(flush_can_batches(state))

    while True:
        try:
            frame = await loop.sock_recv(s, 16)
            if len(frame) == 16:
                state["count"] += 1
                frames_processed += 1

                raw_id, can_dlc, raw_data = struct.unpack("<IB3x8s", frame)
                can_id = raw_id & 0x1FFFFFFF # remove EFF/RTR/ERR flags
                data = raw_data[:can_dlc]
                event, text, block_max_seq = decode_custom_event(can_id, data, block_max_seq)

                # First-pass DATA is sampled to save BBB CPU; priority frames have their own budget.
                priority = is_priority_frame(can_id, data, event)
                if priority:
                    keep = state["priority"] < CAN_BATCH_MAX_PRIORITY
                else:
                    keep = len(state["frames"]) - state["priority"] < CAN_BATCH_MAX_FRAMES
                if keep:
                    row = {
                        "id": f"0x{can_id:03X}",
                        "dlc": can_dlc,
                        "data": " ".join(f"{b:02X}" for b in data)
                    }
                    if event is not None:
                        row["event"] = event
                        row["text"] = text
                    if priority:
                        state["priority"] += 1
                    state["frames"].append(row)

                # Force yield every 50 frames so we don't starve the web server!
                if frames_processed % 50 == 0:
                    await asyncio.sleep(0)

        except BlockingIOError:
            await asyncio.sleep(0.01)
        except Exception as e:
            await asyncio.sleep(1)

@app.on_event("startup")
async def startup_event():
    asyncio.create_task(can_sniffer_task())

# Setup templates directory
templates_dir = os.path.join(os.path.dirname(__file__), "templates")
templates = Jinja2Templates(directory=templates_dir)

# Absolute paths
BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
FIRMWARE_SAVE_PATH = os.path.join(BASE_DIR, "received_fw.bin")

# The flasher argument stays "custom"; the poster and UI call this protocol "Proposed".
PROTOCOL_LABELS = {"custom": "PROPOSED", "isotp": "ISO-TP"}

# Demo fault presets; only these fixed arguments ever reach the flasher.
DEMO_FAULT_ARGS = {
    "none": [],
    "loss1": ["--loss", "1"],
    "loss2": ["--loss", "2"],
    "loss5": ["--loss", "5"],
    "crc": ["--corrupt-image"],
}

@app.get("/", response_class=HTMLResponse)
async def get_dashboard(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})

@app.post("/upload")
async def upload_firmware(file: UploadFile = File(...)):
    try:
        content = await file.read()
        with open(FIRMWARE_SAVE_PATH, "wb") as f:
            f.write(content)
        return {"status": "success", "filename": file.filename, "size": len(content)}
    except Exception as e:
        return {"status": "error", "message": str(e)}

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    active_connections.append(websocket)
    process = None
    try:
        while True:
            data = await websocket.receive_json()
            action = data.get("action")
            
            if action == "start_update":
                protocol = data.get("protocol", "custom")
                board = data.get("board", "f407")
                bitrate = data.get("bitrate", "500000")
                fault_args = DEMO_FAULT_ARGS.get(data.get("fault", "none"))

                if fault_args is None or (fault_args and protocol != "custom"):
                    await websocket.send_json({"type": "log", "data": "[Error] Fault demo is only available with the Proposed protocol."})
                    await websocket.send_json({"type": "status", "data": "FAILED"})
                    continue

                await websocket.send_json({"type": "status", "data": "UPDATING"})
                
                # 1. Configure CAN Interface Bitrate
                await websocket.send_json({"type": "log", "data": f"Configuring CAN interface to {int(bitrate)//1000} kbps..."})
                try:
                    proc_down = await asyncio.create_subprocess_shell("sudo ip link set can0 down")
                    await proc_down.wait()
                    proc_up = await asyncio.create_subprocess_shell(f"sudo ip link set can0 up type can bitrate {bitrate}")
                    await proc_up.wait()
                    
                    if proc_up.returncode == 0:
                        await websocket.send_json({"type": "log", "data": "CAN interface configured successfully."})
                    else:
                        await websocket.send_json({"type": "log", "data": "[Warning] CAN config failed (check sudo privileges). Using existing settings."})
                except Exception as e:
                    await websocket.send_json({"type": "log", "data": f"[Error] CAN config exception: {e}"})

                # 2. Determine and invoke compiled C flasher binary
                binary_path = os.path.join(BASE_DIR, "can_fota_flasher")
                if not os.path.exists(binary_path):
                    # Fallback to local subdirectory if not in base directory
                    binary_path = os.path.join(os.path.dirname(__file__), "can_fota_flasher")

                if not os.path.exists(binary_path):
                    await websocket.send_json({"type": "log", "data": "[Error] Compiled C binary 'can_fota_flasher' not found. Run make first."})
                    continue

                await websocket.send_json({"type": "log", "data": f"Starting C Flasher FOTA update ({PROTOCOL_LABELS.get(protocol, protocol.upper())}) on {board.upper()}..."})
                
                # Executing: ./can_fota_flasher <protocol> <firmware_path> can0 [fault options]
                process = await asyncio.create_subprocess_exec(
                    binary_path, protocol, FIRMWARE_SAVE_PATH, "can0", *fault_args,
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.STDOUT,
                    cwd=BASE_DIR
                )
                
                # Stream logs unbuffered
                buffer = ""
                while True:
                    chunk = await process.stdout.read(1024)
                    if not chunk:
                        if buffer.strip():
                            decoded_line = buffer.strip()
                            if "진행률:" in decoded_line or "Progress:" in decoded_line:
                                await websocket.send_json({"type": "progress_update", "data": decoded_line})
                            else:
                                await websocket.send_json({"type": "log", "data": decoded_line})
                        break
                    
                    buffer += chunk.decode('utf-8', errors='ignore')
                    parts = re.split(r'[\r\n]', buffer)
                    buffer = parts.pop()
                    
                    for part in parts:
                        decoded_line = part.strip()
                        if decoded_line:
                            # If it's a progress update, only update the circular bar (avoids terminal spam)
                            if "진행률:" in decoded_line or "Progress:" in decoded_line:
                                await websocket.send_json({"type": "progress_update", "data": decoded_line})
                            else:
                                await websocket.send_json({"type": "log", "data": decoded_line})
                                drop = DROP_LOG_PATTERN.search(decoded_line)
                                if drop:
                                    await websocket.send_json({"type": "can_frames", "count": 0, "frames": [{
                                        "id": "0x100", "dlc": "-", "data": "", "event": "drop",
                                        "text": f"seq {drop.group(1)} DROPPED (not on bus)"
                                    }]})
                
                await process.wait()
                if process.returncode == 0:
                    await websocket.send_json({"type": "log", "data": "Update completed successfully."})
                    await websocket.send_json({"type": "status", "data": "COMPLETED"})
                else:
                    await websocket.send_json({"type": "log", "data": f"Update failed with return code {process.returncode}."})
                    await websocket.send_json({"type": "status", "data": "FAILED"})
                    
            elif action == "stop_update":
                if process and process.returncode is None:
                    process.terminate()
                    await websocket.send_json({"type": "log", "data": "Update forcefully stopped."})
                    await websocket.send_json({"type": "status", "data": "STOPPED"})

    except WebSocketDisconnect:
        active_connections.remove(websocket)
        if process and process.returncode is None:
            process.terminate()
        print("Client disconnected")
