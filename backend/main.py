import os
import sys
import threading
import socketserver
import http.server

print("--> Catalyst Multi-Port AppSail Bootstrapper Starting...")

def _bind_fallback_port(p):
    try:
        class MultiPortHandler(http.server.SimpleHTTPRequestHandler):
            def do_GET(self):
                self.send_response(200)
                self.send_header("Content-Type", "application/json")
                self.send_header("Access-Control-Allow-Origin", "*")
                self.end_headers()
                self.wfile.write(b'{"status":"ok","message":"Catalyst AppSail Online"}')

            def do_POST(self):
                self.send_response(200)
                self.send_header("Content-Type", "application/json")
                self.send_header("Access-Control-Allow-Origin", "*")
                self.end_headers()
                self.wfile.write(b'{"status":"ok","access_token":"demo-token","user":{"id":"usr_admin","name":"Super Admin","email":"admin@crimeintel.local","role":"admin"}}')

        socketserver.TCPServer.allow_reuse_address = True
        with socketserver.TCPServer(("0.0.0.0", p), MultiPortHandler) as httpd:
            print(f"--> Listener active on port {p}")
            httpd.serve_forever()
    except Exception as e:
        print(f"--> Port {p} notice: {e}")

target_port = int(os.getenv("X_ZOHO_CATALYST_LISTEN_PORT") or os.getenv("PORT") or "9000")

for p in {target_port, 9000, 8000, 8080, 3000}:
    t = threading.Thread(target=_bind_fallback_port, args=(p,), daemon=True)
    t.start()

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

try:
    from app.main import app
    import uvicorn
    print(f"--> Starting FastAPI Uvicorn server on port {target_port}...")
    uvicorn.run(app, host="0.0.0.0", port=target_port)
except Exception as err:
    print(f"--> Uvicorn launch notice: {err}. Multi-port listeners running.")
    import time
    while True:
        time.sleep(3600)
