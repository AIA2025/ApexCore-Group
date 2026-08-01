#!/bin/bash
# macOS iMac — Daemon Command Server
# Startet lokalen HTTP-Server für Remote Command Execution
# EINMALIGES Setup — danach läuft alles automatisch!

sudo python3 << 'PYEOF'
from http.server import HTTPServer, BaseHTTPRequestHandler
import subprocess
import json
import sys

class CommandExecutor(BaseHTTPRequestHandler):
    def log_message(self, format, *args):
        pass  # Silent

    def do_POST(self):
        try:
            content_length = int(self.headers.get('Content-Length', 0))
            body = self.rfile.read(content_length).decode('utf-8')
            request = json.loads(body)

            cmd = request.get('cmd', '')

            # Execute command
            result = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=30)

            # Send response
            self.send_response(200)
            self.send_header('Content-type', 'application/json')
            self.end_headers()

            response = {
                'status': 'ok',
                'stdout': result.stdout,
                'stderr': result.stderr,
                'returncode': result.returncode
            }

            self.wfile.write(json.dumps(response).encode())

        except Exception as e:
            self.send_response(500)
            self.send_header('Content-type', 'application/json')
            self.end_headers()
            self.wfile.write(json.dumps({'status': 'error', 'message': str(e)}).encode())

# Start server
try:
    server = HTTPServer(('127.0.0.1', 9999), CommandExecutor)
    print("✅ Command Server started on localhost:9999")
    print("🔄 Listening for remote commands...")
    server.serve_forever()
except KeyboardInterrupt:
    print("\n🛑 Server stopped")
    sys.exit(0)
PYEOF
