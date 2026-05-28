#!/usr/bin/env python3
"""
ApexCore Command API — v2
Lightweight HTTP control endpoint for deployment hooks and status checks.
Port: 7070  |  Auth: Bearer token via CMD_TOKEN env var

GET  /health            — unauthenticated liveness check
GET  /status            — container status summary (authenticated)
POST /caddy/reload      — reload Caddy config (authenticated)
POST /exec              — run whitelisted shell commands (authenticated)
"""

import os
import json
import subprocess
from http.server import HTTPServer, BaseHTTPRequestHandler
from urllib.parse import urlparse

CMD_TOKEN = os.environ.get("CMD_TOKEN", "")
PORT = int(os.environ.get("CMD_API_PORT", "7070"))

# Whitelist of allowed command prefixes — prevents arbitrary shell execution
ALLOWED_COMMANDS = [
    "docker compose",
    "docker ps",
    "docker logs",
    "docker inspect",
    "systemctl status",
]


def is_allowed(cmd: str) -> bool:
    return any(cmd.strip().startswith(prefix) for prefix in ALLOWED_COMMANDS)


class Handler(BaseHTTPRequestHandler):
    def log_message(self, format, *args):
        print(f"[cmd-api] {self.address_string()} {format % args}", flush=True)

    def send_json(self, code: int, data: dict):
        body = json.dumps(data).encode()
        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def authenticated(self) -> bool:
        if not CMD_TOKEN:
            return False
        auth = self.headers.get("Authorization", "")
        token = auth.removeprefix("Bearer ").strip()
        # Legacy support: X-Token header
        if not token:
            token = self.headers.get("X-Token", "").strip()
        return token == CMD_TOKEN

    def read_body(self) -> dict:
        length = int(self.headers.get("Content-Length", 0))
        if length == 0:
            return {}
        try:
            return json.loads(self.rfile.read(length))
        except Exception:
            return {}

    def do_GET(self):
        path = urlparse(self.path).path

        if path == "/health":
            self.send_json(200, {"status": "ok", "service": "cmd-api"})
            return

        if not self.authenticated():
            self.send_json(401, {"error": "unauthorized"})
            return

        if path == "/status":
            try:
                result = subprocess.run(
                    ["docker", "ps", "--format", "{{.Names}}\t{{.Status}}\t{{.Image}}"],
                    capture_output=True, text=True, timeout=10
                )
                containers = []
                for line in result.stdout.strip().splitlines():
                    parts = line.split("\t")
                    if len(parts) == 3:
                        containers.append({
                            "name": parts[0],
                            "status": parts[1],
                            "image": parts[2],
                        })
                self.send_json(200, {"containers": containers})
            except Exception as e:
                self.send_json(500, {"error": str(e)})
            return

        self.send_json(404, {"error": "not found"})

    def do_POST(self):
        if not self.authenticated():
            self.send_json(401, {"error": "unauthorized"})
            return

        path = urlparse(self.path).path

        if path == "/caddy/reload":
            try:
                result = subprocess.run(
                    ["docker", "exec", "caddy", "caddy", "reload",
                     "--config", "/etc/caddy/Caddyfile"],
                    capture_output=True, text=True, timeout=30
                )
                if result.returncode == 0:
                    self.send_json(200, {"status": "reloaded"})
                else:
                    self.send_json(500, {"error": result.stderr.strip()})
            except Exception as e:
                self.send_json(500, {"error": str(e)})
            return

        if path == "/exec":
            body = self.read_body()
            cmd = body.get("cmd", "").strip()
            if not cmd:
                self.send_json(400, {"error": "missing 'cmd' field"})
                return
            if not is_allowed(cmd):
                self.send_json(403, {"error": "command not in whitelist"})
                return
            try:
                result = subprocess.run(
                    cmd, shell=False, capture_output=True, text=True,
                    timeout=60, args=cmd.split()
                )
                self.send_json(200, {
                    "stdout": result.stdout,
                    "stderr": result.stderr,
                    "rc": result.returncode,
                })
            except Exception as e:
                self.send_json(500, {"error": str(e)})
            return

        self.send_json(404, {"error": "not found"})


if __name__ == "__main__":
    if not CMD_TOKEN:
        print("[cmd-api] WARNING: CMD_TOKEN not set — authenticated endpoints are disabled",
              flush=True)
    server = HTTPServer(("0.0.0.0", PORT), Handler)
    print(f"[cmd-api] Listening on :{PORT}", flush=True)
    server.serve_forever()
