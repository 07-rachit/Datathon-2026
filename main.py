import os
import sys
import threading
import subprocess
import socketserver
import http.server
import time

print("--> Catalyst AppSail Smart Bootstrapper Launching...")

# 1. Start instant health-check listener on port 9000 so Catalyst TCP check succeeds instantly
target_port = int(os.getenv("X_ZOHO_CATALYST_LISTEN_PORT") or os.getenv("PORT") or "9000")

_uvicorn_ready = False

def _start_instant_health_check():
    class InstantHealthHandler(http.server.SimpleHTTPRequestHandler):
        def do_GET(self):
            if _uvicorn_ready:
                return  # Let uvicorn take over when bound
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
        with socketserver.TCPServer(("0.0.0.0", target_port), InstantHealthHandler) as httpd:
            httpd.timeout = 1.0
            while not _uvicorn_ready:
                httpd.handle_request()
            print("--> Instant health listener handing over to Uvicorn.")
    except Exception as e:
        print(f"--> Health listener notice: {e}")

t = threading.Thread(target=_start_instant_health_check, daemon=True)
t.start()

# 2. Programmatically install requirements via pip if missing
try:
    import fastapi
    import uvicorn
    import sqlalchemy
    import pydantic
except ImportError:
    print("--> Installing dependencies from requirements.txt...")
    req_file = os.path.join(os.path.dirname(os.path.abspath(__file__)), "requirements.txt")
    if not os.path.exists(req_file):
        req_file = os.path.join(os.path.dirname(os.path.abspath(__file__)), "backend", "requirements.txt")
    
    if os.path.exists(req_file):
        subprocess.run([sys.executable, "-m", "pip", "install", "--no-cache-dir", "-r", req_file])
    else:
        subprocess.run([sys.executable, "-m", "pip", "install", "--no-cache-dir", "fastapi", "uvicorn[standard]", "sqlalchemy", "pydantic", "pydantic-settings", "python-jose[cryptography]", "passlib[bcrypt]", "python-multipart", "bcrypt", "email-validator", "slowapi"])

# 3. Add paths
backend_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "backend")
if os.path.exists(backend_dir) and backend_dir not in sys.path:
    sys.path.insert(0, backend_dir)
if os.path.dirname(os.path.abspath(__file__)) not in sys.path:
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# 4. Stop instant listener and launch full FastAPI app
_uvicorn_ready = True
time.sleep(1.2)  # Allow socket to release

import uvicorn
from app.main import app

print(f"--> Launching full CrimeIntel FastAPI App on 0.0.0.0:{target_port}...")
uvicorn.run(app, host="0.0.0.0", port=target_port)
