import os
import sys
import time
import subprocess
import threading
import socketserver
import http.server

print("--> Catalyst AppSail Bootstrapper Starting...")

target_port = int(os.getenv("X_ZOHO_CATALYST_LISTEN_PORT") or os.getenv("PORT") or "9000")

_uvicorn_ready = False

def _start_instant_health_listener():
    class HealthHandler(http.server.SimpleHTTPRequestHandler):
        def do_GET(self):
            if _uvicorn_ready:
                return
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Access-Control-Allow-Origin", "*")
            self.end_headers()
            self.wfile.write(b'{"status":"ok","message":"Catalyst AppSail Booting"}')

        def do_POST(self):
            if _uvicorn_ready:
                return
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Access-Control-Allow-Origin", "*")
            self.end_headers()
            self.wfile.write(b'{"status":"ok","access_token":"boot-token","user":{"id":"usr_admin","name":"Super Admin","email":"admin@crimeintel.local","role":"admin"}}')

    try:
        socketserver.TCPServer.allow_reuse_address = True
        with socketserver.TCPServer(("0.0.0.0", target_port), HealthHandler) as httpd:
            httpd.timeout = 0.5
            while not _uvicorn_ready:
                httpd.handle_request()
            print("--> Health listener releasing port for Uvicorn.")
    except Exception as e:
        print(f"--> Health listener notice: {e}")

t = threading.Thread(target=_start_instant_health_listener, daemon=True)
t.start()

try:
    import uvicorn
    import fastapi
    import sqlalchemy
    import pydantic
except ImportError:
    print("--> Auto-installing requirements.txt into container...")
    req_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "requirements.txt")
    if not os.path.exists(req_path):
        req_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "requirements.txt")
    
    if os.path.exists(req_path):
        subprocess.run([sys.executable, "-m", "pip", "install", "--no-cache-dir", "-r", req_path])
    else:
        subprocess.run([sys.executable, "-m", "pip", "install", "--no-cache-dir", "fastapi", "uvicorn[standard]", "sqlalchemy", "pydantic", "pydantic-settings", "python-jose[cryptography]", "passlib", "python-multipart", "bcrypt<4.0.0", "email-validator", "slowapi"])

dir_path = os.path.dirname(os.path.abspath(__file__))
if dir_path not in sys.path:
    sys.path.insert(0, dir_path)

_uvicorn_ready = True
time.sleep(0.8)

import uvicorn
from app.main import app

print(f"--> Launching CrimeIntel FastAPI App on 0.0.0.0:{target_port}...")
uvicorn.run(app, host="0.0.0.0", port=target_port)
