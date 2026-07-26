import os
import sys
import threading
import socketserver
import http.server

dir_path = os.path.dirname(os.path.abspath(__file__))
if dir_path not in sys.path:
    sys.path.insert(0, dir_path)

target_port = int(os.getenv("X_ZOHO_CATALYST_LISTEN_PORT") or os.getenv("PORT") or "9000")

def _bind_auxiliary_port(p):
    if p == target_port:
        return
    try:
        class AuxiliaryHandler(http.server.SimpleHTTPRequestHandler):
            def do_GET(self):
                self.send_response(200)
                self.send_header("Content-Type", "application/json")
                self.send_header("Access-Control-Allow-Origin", "*")
                self.end_headers()
                self.wfile.write(b'{"status":"ok","message":"Catalyst AppSail Auxiliary Listener"}')

        socketserver.TCPServer.allow_reuse_address = True
        with socketserver.TCPServer(("0.0.0.0", p), AuxiliaryHandler) as httpd:
            httpd.serve_forever()
    except Exception:
        pass

for p in {9000, 8000, 8080, 3000, 5000}:
    t = threading.Thread(target=_bind_auxiliary_port, args=(p,), daemon=True)
    t.start()

import uvicorn
from app.main import app

if __name__ == "__main__":
    print(f"--> Launching CrimeIntel FastAPI App on 0.0.0.0:{target_port}...")
    uvicorn.run(app, host="0.0.0.0", port=target_port)
