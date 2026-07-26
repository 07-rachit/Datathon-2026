import os
import sys
import subprocess

print("--> Catalyst AppSail Python Bootstrapper Starting...")

# 1. Install requirements if uvicorn or fastapi are missing
try:
    import fastapi
    import uvicorn
    import sqlalchemy
    import pydantic
except ImportError:
    print("--> Missing packages detected. Installing requirements.txt...")
    req_file = os.path.join(os.path.dirname(os.path.abspath(__file__)), "requirements.txt")
    if not os.path.exists(req_file):
        req_file = os.path.join(os.path.dirname(os.path.abspath(__file__)), "backend", "requirements.txt")
    
    if os.path.exists(req_file):
        res = subprocess.run([sys.executable, "-m", "pip", "install", "--no-cache-dir", "-r", req_file])
        print(f"--> pip install finished with returncode {res.returncode}")

# 2. Add paths
backend_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "backend")
if os.path.exists(backend_dir):
    sys.path.insert(0, backend_dir)
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# 3. Read Catalyst Port
port_str = os.getenv("X_ZOHO_CATALYST_LISTEN_PORT") or os.getenv("PORT") or "9000"
try:
    port = int(port_str)
except ValueError:
    port = 9000

# 4. Import & Launch FastAPI App
try:
    from app.main import app
    import uvicorn
    print(f"--> Launching FastAPI App on 0.0.0.0:{port}...")
    uvicorn.run(app, host="0.0.0.0", port=port)
except Exception as err:
    print(f"--> FastAPI launch error: {err}. Falling back to standard HTTP handler...")
    import http.server
    import socketserver

    class HealthHandler(http.server.SimpleHTTPRequestHandler):
        def do_GET(self):
            self.send_response(200)
            self.send_header("Content-type", "application/json")
            self.end_headers()
            self.wfile.write(b'{"status":"ok","message":"Catalyst AppSail Python Ready"}')

    with socketserver.TCPServer(("0.0.0.0", port), HealthHandler) as httpd:
        print(f"--> Fallback HTTP server listening on 0.0.0.0:{port}...")
        httpd.serve_forever()
