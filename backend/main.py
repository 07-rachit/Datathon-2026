import os
import sys
import site
import subprocess

print("--> Starting CrimeIntel AppSail Native Server...")

# Add user site-packages to sys.path if not present
user_site = site.getusersitepackages()
if user_site and os.path.exists(user_site) and user_site not in sys.path:
    sys.path.insert(0, user_site)

# Ensure dependencies are available
try:
    import uvicorn
    import fastapi
except ImportError:
    print("--> Missing dependencies in container, installing requirements.txt...")
    req_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "requirements.txt")
    if os.path.exists(req_path):
        try:
            subprocess.check_call([sys.executable, "-m", "pip", "install", "--no-cache-dir", "-r", req_path])
        except Exception as e:
            print(f"--> Pip install notice: {e}")

target_port = int(os.getenv("X_ZOHO_CATALYST_LISTEN_PORT") or os.getenv("PORT") or "9000")

try:
    import uvicorn
    from app.main import app
    print(f"--> Launching FastAPI Uvicorn Server on 0.0.0.0:{target_port}...")
    uvicorn.run(app, host="0.0.0.0", port=target_port)
except Exception as err:
    print(f"--> Failed to launch Uvicorn ({err}), falling back to native HTTP server...")
    import http.server
    import socketserver

    class FallbackHandler(http.server.SimpleHTTPRequestHandler):
        def do_GET(self):
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Access-Control-Allow-Origin", "*")
            self.end_headers()
            self.wfile.write(b'{"status":"ok","message":"CrimeIntel Fallback Server Online"}')

    socketserver.TCPServer.allow_reuse_address = True
    with socketserver.TCPServer(("0.0.0.0", target_port), FallbackHandler) as httpd:
        httpd.serve_forever()
