import os
import sys
import threading
import socketserver
import http.server

# 1. Add paths
dir_path = os.path.dirname(os.path.abspath(__file__))
backend_path = os.path.join(dir_path, "backend")
if os.path.exists(backend_path) and backend_path not in sys.path:
    sys.path.insert(0, backend_path)
if dir_path not in sys.path:
    sys.path.insert(0, dir_path)

# 2. Multi-port listener for Catalyst health checks
target_port = int(os.getenv("X_ZOHO_CATALYST_LISTEN_PORT") or os.getenv("PORT") or "9000")

def _bind_fallback_port(p):
    if p == target_port:
        return  # Main thread uvicorn will bind target_port
    try:
        class MultiPortHandler(http.server.SimpleHTTPRequestHandler):
            def do_GET(self):
                self.send_response(200)
                self.send_header("Content-Type", "application/json")
                self.send_header("Access-Control-Allow-Origin", "*")
                self.end_headers()
                self.wfile.write(b'{"status":"ok","message":"Catalyst AppSail Multi-Port Active"}')

        socketserver.TCPServer.allow_reuse_address = True
        with socketserver.TCPServer(("0.0.0.0", p), MultiPortHandler) as httpd:
            httpd.serve_forever()
    except Exception:
        pass

for p in {9000, 8000, 8080, 3000}:
    t = threading.Thread(target=_bind_fallback_port, args=(p,), daemon=True)
    t.start()

# 3. Launch full FastAPI application
import uvicorn
from app.main import app

if __name__ == "__main__":
    print(f"--> Launching CrimeIntel FastAPI App on 0.0.0.0:{target_port}...")
    uvicorn.run(app, host="0.0.0.0", port=target_port)
