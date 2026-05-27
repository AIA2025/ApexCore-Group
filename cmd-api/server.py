#!/usr/bin/env python3
import http.server, subprocess, json, os, hashlib

TOKEN = os.environ.get("CMD_TOKEN", "")
PORT = int(os.environ.get("PORT", "7070"))

class Handler(http.server.BaseHTTPRequestHandler):
    def log_message(self, *args): pass

    def do_POST(self):
        if not TOKEN:
            self._respond(403, {"error": "CMD_TOKEN not set"})
            return
        if self.headers.get("X-Token") != TOKEN:
            self._respond(403, {"error": "Unauthorized"})
            return
        length = int(self.headers.get("Content-Length", 0))
        body = self.rfile.read(length)
        try:
            data = json.loads(body)
            cmd = data.get("cmd", "")
            if not cmd:
                self._respond(400, {"error": "No cmd"})
                return
            result = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=60)
            self._respond(200, {"stdout": result.stdout, "stderr": result.stderr, "rc": result.returncode})
        except Exception as e:
            self._respond(500, {"error": str(e)})

    def _respond(self, code, data):
        body = json.dumps(data).encode()
        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", len(body))
        self.end_headers()
        self.wfile.write(body)

http.server.HTTPServer(("0.0.0.0", PORT), Handler).serve_forever()
