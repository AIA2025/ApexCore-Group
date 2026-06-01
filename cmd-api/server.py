#!/usr/bin/env python3
"""ApexCore CMD API — webhook gateway on port 7070"""

import json
import os
import subprocess
import threading
import time
from http.server import BaseHTTPRequestHandler, HTTPServer

TOKEN = os.getenv("CMD_TOKEN", "")
RAW_BASE = "https://raw.githubusercontent.com/AIA2025/apexcore"
PORT = 7070


def run_deploy(branch: str):
    """Pull latest code from GitHub, self-update cmd-api, restart scanner."""
    log = open("/var/log/cmd-api-deploy.log", "a")
    cmd_api_updated = False

    def sh(cmd, **kw):
        log.write(f"+ {' '.join(cmd)}\n")
        log.flush()
        return subprocess.run(cmd, stdout=log, stderr=log, **kw)

    try:
        log.write(f"\n=== Deploy branch={branch} at {time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime())} ===\n")
        base = f"{RAW_BASE}/{branch}"

        sh(["mkdir", "-p", "/opt/apexcore-mvp/output", "/opt/apexcore-dashboard",
            "/opt/apexcore/cmd-api", "/srv/apexcore/cmd-api"])

        # --- SSH deploy key (idempotent) ---
        _pubkey = "ssh-ed25519 AAAAC3NzaC1lZDI1NTE5AAAAIAJUctsIPmWIWj2nevAnFwYzAzomE3cUbv0nahBFauej apexcore-deploy"
        _ssh_dir, _auth = "/root/.ssh", "/root/.ssh/authorized_keys"
        try:
            os.makedirs(_ssh_dir, mode=0o700, exist_ok=True)
            _existing = open(_auth).read() if os.path.exists(_auth) else ""
            if "apexcore-deploy" not in _existing:
                with open(_auth, "a") as _f:
                    _f.write(f"\n{_pubkey}\n")
                os.chmod(_auth, 0o600)
                log.write("SSH apexcore-deploy key added to authorized_keys\n")
            else:
                log.write("SSH apexcore-deploy key already present\n")
        except Exception as _ex:
            log.write(f"SSH key warning: {_ex}\n")

        # --- cmd-api self-update (always attempt, never fatal) ---
        r_self = sh(["curl", "-fsSL", f"{base}/cmd-api/server.py", "-o", "/tmp/cmd-api-new.py"])
        if r_self.returncode == 0:
            sh(["cp", "/tmp/cmd-api-new.py", "/opt/apexcore/cmd-api/server.py"])
            sh(["cp", "/tmp/cmd-api-new.py", "/srv/apexcore/cmd-api/server.py"])
            log.write("cmd-api self-updated in /opt/ and /srv/\n")
            cmd_api_updated = True
        else:
            log.write("cmd-api/server.py not in branch — skipping self-update\n")

        # --- scanner (optional — skip if not in branch) ---
        r_main = sh(["curl", "-fsSL", f"{base}/apexcore-mvp/main.py", "-o", "/tmp/scanner-main.py"])
        r_req  = sh(["curl", "-fsSL", f"{base}/apexcore-mvp/requirements.txt", "-o", "/tmp/scanner-req.txt"])

        if r_main.returncode == 0 and r_req.returncode == 0:
            sh(["cp", "/tmp/scanner-main.py", "/opt/apexcore-mvp/main.py"])
            sh(["cp", "/tmp/scanner-req.txt", "/opt/apexcore-mvp/requirements.txt"])
            sh(["pip3", "install", "-r", "/opt/apexcore-mvp/requirements.txt",
                "--break-system-packages", "-q"])

            r_dash = sh(["curl", "-fsSL", f"{base}/dashboard/index.html",
                         "-o", "/opt/apexcore-dashboard/index.html"])
            if r_dash.returncode != 0:
                log.write("dashboard/index.html not in branch, skipping\n")

            env_path = "/opt/apexcore-mvp/.env"
            if not os.path.exists(env_path):
                with open(env_path, "w") as f:
                    f.write("ANTHROPIC_API_KEY=PLACEHOLDER\nOUTPUT_DIR=/opt/apexcore-mvp/output\n")
                log.write(".env created with placeholders\n")
            else:
                log.write(".env already exists, not overwriting\n")

            cache = os.path.expanduser("~/.cache/ms-playwright")
            if not os.path.isdir(cache) or not os.listdir(cache):
                sh(["python3", "-m", "playwright", "install", "chromium"])
                sh(["python3", "-m", "playwright", "install-deps", "chromium"])

            subprocess.run(["pkill", "-f", "uvicorn main:app"], capture_output=True)
            time.sleep(2)
            subprocess.Popen(
                ["python3", "-m", "uvicorn", "main:app",
                 "--host", "0.0.0.0", "--port", "8000", "--log-level", "info"],
                cwd="/opt/apexcore-mvp",
                stdout=open("/var/log/apexcore-mvp.log", "a"),
                stderr=subprocess.STDOUT,
            )

            time.sleep(5)
            result = subprocess.run(["curl", "-sf", "http://localhost:8000/health"],
                                    capture_output=True, text=True)
            log.write(f"Scanner {'healthy: ' + result.stdout if result.returncode == 0 else 'health check FAILED'}\n")
        else:
            log.write("apexcore-mvp/ not in branch — scanner not updated\n")

        log.write("=== Deploy finished ===\n")
        log.flush()

    except Exception as e:
        log.write(f"Deploy error: {e}\n")
    finally:
        log.close()

    if cmd_api_updated:
        time.sleep(1)
        subprocess.Popen(["systemctl", "restart", "cmd-api"])


class Handler(BaseHTTPRequestHandler):
    def _respond(self, code: int, body: dict):
        data = json.dumps(body).encode()
        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def _auth_ok(self) -> bool:
        if not TOKEN:
            return True
        auth = self.headers.get("Authorization", "")
        return auth in (f"Bearer {TOKEN}", TOKEN)

    def do_GET(self):
        if self.path == "/health":
            self._respond(200, {"status": "ok", "service": "cmd-api", "port": PORT})
        else:
            self._respond(404, {"error": "not found"})

    def do_POST(self):
        if self.path == "/deploy":
            if not self._auth_ok():
                self._respond(403, {"error": "unauthorized"})
                return
            length = int(self.headers.get("Content-Length", 0))
            body = json.loads(self.rfile.read(length) or b"{}") if length else {}
            branch = body.get("branch", "main")
            threading.Thread(target=run_deploy, args=(branch,), daemon=True).start()
            self._respond(202, {"status": "deploying", "branch": branch})
        else:
            self._respond(404, {"error": "not found"})

    def log_message(self, fmt, *args):
        pass


if __name__ == "__main__":
    subprocess.run(["fuser", "-k", f"{PORT}/tcp"], capture_output=True)
    time.sleep(0.5)
    server = HTTPServer(("0.0.0.0", PORT), Handler)
    print(f"CMD API running on :{PORT}  (token={'set' if TOKEN else 'unset'})")
    server.serve_forever()
