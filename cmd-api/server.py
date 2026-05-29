#!/usr/bin/env python3
"""ApexCore CMD API — lightweight command gateway on port 7070"""

import json
import os
from http.server import BaseHTTPRequestHandler, HTTPServer


TOKEN = os.getenv("CMD_TOKEN", "")


class Handler(BaseHTTPRequestHandler):
    def _respond(self, code: int, body: dict):
        data = json.dumps(body).encode()
        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def do_GET(self):
        if self.path == "/health":
            self._respond(200, {"status": "ok", "service": "cmd-api", "port": 7070})
        else:
            self._respond(404, {"error": "not found"})

    def log_message(self, fmt, *args):
        pass


if __name__ == "__main__":
    server = HTTPServer(("0.0.0.0", 7070), Handler)
    print("CMD API running on :7070")
    server.serve_forever()
