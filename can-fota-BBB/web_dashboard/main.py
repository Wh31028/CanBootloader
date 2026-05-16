from fastapi import FastAPI, Request, UploadFile, File, WebSocket, WebSocketDisconnect
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles
import os
import subprocess
import asyncio
import sys
import socket
import struct
import time

app = FastAPI()

active_connections = []

async def can_sniffer_task():
    try:
        s = socket.socket(socket.AF_CAN, socket.SOCK_RAW, socket.CAN_RAW)
        s.bind(('can0',))
        s.setblocking(False)
    except Exception as e:
        print(f"CAN Sniffer init failed: {e}")
        return

    loop = asyncio.get_event_loop()
    batch = []
    last_send = time.time()
    
    while True:
        try:
            frame = await loop.sock_recv(s, 16)
            if len(frame) == 16:
                can_id, can_dlc, data = struct.unpack("<IB3x8s", frame)
                can_id &= 0x1FFFFFFF # remove EFF/RTR/ERR flags
                data_hex = " ".join(f"{b:02X}" for b in data[:can_dlc])
                
                batch.append({
                    "id": f"0x{can_id:03X}",
                    "dlc": can_dlc,
                    "data": data_hex
                })
                
                # Send batch every 20 frames or 100ms to avoid overloading the websocket
                if len(batch) >= 20 or (time.time() - last_send) > 0.1:
                    if active_connections:
                        msg = {"type": "can_frames", "frames": batch}
                        for conn in active_connections:
                            try:
                                await conn.send_json(msg)
                            except:
                                pass
                    batch = []
                    last_send = time.time()
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
                
                script_name = "custom_lte_gateway.py" if protocol == "custom" else "isotp_lte_gateway.py"
                script_path = os.path.join(BASE_DIR, script_name)
                
                if not os.path.exists(script_path):
                    await websocket.send_json({"type": "log", "data": f"[Error] Script {script_name} not found."})
                    continue

                await websocket.send_json({"type": "status", "data": "UPDATING"})
                await websocket.send_json({"type": "log", "data": f"Starting {protocol.upper()} FOTA update..."})
                
                # Using sys.executable to run with current python, passing FIRMWARE_SAVE_PATH
                process = await asyncio.create_subprocess_exec(
                    sys.executable, script_path, FIRMWARE_SAVE_PATH,
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.STDOUT,
                    cwd=BASE_DIR
                )
                
                # Stream logs
                while True:
                    line = await process.stdout.readline()
                    if not line:
                        break
                    
                    decoded_line = line.decode('utf-8').strip()
                    if decoded_line:
                        await websocket.send_json({"type": "log", "data": decoded_line})
                        
                        # Very simple progress extraction example (if script prints "Progress: X%")
                        if "Progress:" in decoded_line or "%" in decoded_line:
                            await websocket.send_json({"type": "progress_update", "data": decoded_line})
                
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
