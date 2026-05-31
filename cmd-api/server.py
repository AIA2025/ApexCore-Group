#!/usr/bin/env python3
"""
ApexCore Command API — v2
Lightweight HTTP control endpoint for deployment hooks and status checks.
Port: 7070  |  Auth: Bearer token via CMD_TOKEN env var

GET  /health            — unauthenticated liveness check
GET  /status            — container status summary (authenticated)
POST /deploy            — pull latest code + apply config + restart services (authenticated, async → 202)
POST /caddy/reload      — reload Caddy config (authenticated)
POST /exec              — run whitelisted shell commands (authenticated)
"""

import os
import re
import json
import glob
import shutil
import subprocess
import threading
import time
from datetime import datetime
from http.server import HTTPServer, BaseHTTPRequestHandler
from urllib.parse import urlparse

CMD_TOKEN = os.environ.get("CMD_TOKEN", "")
PORT = int(os.environ.get("CMD_API_PORT", "7070"))
APEXCORE_DIR = "/srv/apexcore"
DEPLOY_LOG = "/var/log/apexcore-deploy.log"

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


def _run(args, log_fh, timeout=60, **kwargs):
    result = subprocess.run(
        args, stdout=log_fh, stderr=log_fh, timeout=timeout, **kwargs
    )
    log_fh.flush()
    return result


def _deploy_background(branch: str):
    with open(DEPLOY_LOG, "a") as f:
        f.write(f"\n=== Deploy: {branch} @ {datetime.now().isoformat()} ===\n")
        try:
            # ── Pull latest code ──────────────────────────────────────────
            _run(["git", "-C", APEXCORE_DIR, "fetch", "origin"], f, timeout=30)
            _run(["git", "-C", APEXCORE_DIR, "checkout", branch], f, timeout=10)
            _run(["git", "-C", APEXCORE_DIR, "pull", "origin", branch], f, timeout=30)

            scripts = glob.glob(f"{APEXCORE_DIR}/scripts/*.sh")
            if scripts:
                subprocess.run(["chmod", "+x"] + scripts, stdout=f, stderr=f)

            # ── nginx vhost ───────────────────────────────────────────────
            src = f"{APEXCORE_DIR}/infra-compose/nginx-vhost.conf"
            dst = "/etc/nginx/sites-available/apexcore.conf"
            link = "/etc/nginx/sites-enabled/apexcore.conf"
            if os.path.exists(src) and shutil.which("nginx"):
                shutil.copy(src, dst)
                os.makedirs("/etc/nginx/sites-enabled", exist_ok=True)
                if not os.path.lexists(link):
                    os.symlink(dst, link)
                t = subprocess.run(["nginx", "-t"], capture_output=True, text=True)
                if t.returncode == 0:
                    _run(["nginx", "-s", "reload"], f, timeout=10)
                    f.write("nginx: reloaded\n")
                else:
                    f.write(f"nginx -t failed: {t.stderr}\n")

            # ── Static assets ─────────────────────────────────────────────
            os.makedirs("/opt/apexcore-dashboard", exist_ok=True)
            idx = f"{APEXCORE_DIR}/dashboard/index.html"
            if os.path.exists(idx):
                shutil.copy(idx, "/opt/apexcore-dashboard/index.html")

            # ── Restart dispatcher ────────────────────────────────────────
            env_file = f"{APEXCORE_DIR}/cmd-api/.env.dispatcher"
            if os.path.exists(env_file):
                subprocess.run(["pkill", "-f", "hermes_dispatcher.py"],
                               stdout=f, stderr=f)
                time.sleep(1)
                env_vars = {}
                with open(env_file) as ef:
                    for line in ef:
                        line = line.strip()
                        if line and not line.startswith("#") and "=" in line:
                            k, v = line.split("=", 1)
                            env_vars[k.strip()] = v.strip()
                subprocess.Popen(
                    ["python3", f"{APEXCORE_DIR}/cmd-api/hermes_dispatcher.py"],
                    env={**os.environ, **env_vars},
                    stdout=open("/var/log/apexcore-dispatcher.log", "a"),
                    stderr=subprocess.STDOUT,
                )
                f.write("dispatcher: restarted\n")

            # ── n8n_data volume guard ─────────────────────────────────────
            r = subprocess.run(["docker", "volume", "inspect", "n8n_data"],
                               capture_output=True)
            if r.returncode != 0:
                _run(["docker", "volume", "create", "n8n_data"], f)

            # ── Compose stacks ────────────────────────────────────────────
            ai_net = subprocess.run(
                ["docker", "network", "inspect", "ai_net"], capture_output=True
            )
            if ai_net.returncode == 0:
                for cf in [
                    "ai-stack/docker-compose.yml",
                    "automation-stack/docker-compose.yml",
                    "infra-compose/docker-compose.yml",
                ]:
                    _run(
                        ["docker", "compose", "-f", f"{APEXCORE_DIR}/{cf}",
                         "up", "-d", "--remove-orphans"],
                        f, timeout=120
                    )
                f.write("compose: stacks refreshed\n")
            else:
                f.write("compose: ai_net not found — run stack-start.sh first\n")

            f.write(f"=== Deploy complete: {datetime.now().isoformat()} ===\n")
        except Exception as e:
            f.write(f"Deploy error: {e}\n")


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

        if path == "/deploy":
            body = self.read_body()
            branch = body.get("branch", "main").strip()
            # Permit only safe branch names — no shell injection
            if not re.match(r'^[a-zA-Z0-9_/.-]+$', branch) or ".." in branch:
                self.send_json(400, {"error": "invalid branch name"})
                return
            threading.Thread(
                target=_deploy_background, args=(branch,), daemon=True
            ).start()
            self.send_json(202, {
                "status": "accepted",
                "branch": branch,
                "log": DEPLOY_LOG,
            })
            return

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
                    cmd.split(), capture_output=True, text=True, timeout=60
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
