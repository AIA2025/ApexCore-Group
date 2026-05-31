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


def run_deploy(branch: str):
    """Pull latest code from GitHub and restart the scanner."""
    log = open("/var/log/cmd-api-deploy.log", "a")

    def sh(cmd, **kw):
        log.write(f"+ {' '.join(cmd)}\n")
        log.flush()
        return subprocess.run(cmd, stdout=log, stderr=log, **kw)

    try:
        log.write(f"\n=== Deploy branch={branch} at {time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime())} ===\n")

        base = f"{RAW_BASE}/{branch}"

        sh(["mkdir", "-p", "/opt/apexcore-mvp/output", "/opt/apexcore-dashboard", "/opt/apexcore/cmd-api"])

        # scanner
        sh(["curl", "-fsSL", f"{base}/apexcore-mvp/main.py", "-o", "/opt/apexcore-mvp/main.py"], check=True)
        sh(["curl", "-fsSL", f"{base}/apexcore-mvp/requirements.txt", "-o", "/opt/apexcore-mvp/requirements.txt"], check=True)
        sh(["pip3", "install", "-r", "/opt/apexcore-mvp/requirements.txt",
            "--break-system-packages", "-q"], check=True)

        # dashboard
        r = sh(["curl", "-fsSL", f"{base}/dashboard/index.html", "-o", "/opt/apexcore-dashboard/index.html"])
        if r.returncode != 0:
            log.write("dashboard/index.html not in branch, skipping\n")

        # create .env if missing
        env_path = "/opt/apexcore-mvp/.env"
        if not os.path.exists(env_path):
            with open(env_path, "w") as f:
                f.write("ANTHROPIC_API_KEY=PLACEHOLDER\nOUTPUT_DIR=/opt/apexcore-mvp/output\n")
            log.write(".env created with placeholders\n")
        else:
            log.write(".env already exists, not overwriting\n")

        # install playwright chromium if missing
        cache = os.path.expanduser("~/.cache/ms-playwright")
        if not os.path.isdir(cache) or not os.listdir(cache):
            sh(["python3", "-m", "playwright", "install", "chromium"])
            sh(["python3", "-m", "playwright", "install-deps", "chromium"])

        # restart scanner
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
        if result.returncode == 0:
            log.write(f"Scanner healthy: {result.stdout}\n")
        else:
            log.write("Scanner health check failed\n")

        log.write("=== Deploy finished ===\n")
    except Exception as e:
        log.write(f"Deploy error: {e}\n")
    finally:
        log.close()


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
            self._respond(200, {"status": "ok", "service": "cmd-api", "port": 7070})
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
    server = HTTPServer(("0.0.0.0", 7070), Handler)
    print(f"CMD API running on :7070  (token={'set' if TOKEN else 'unset'})")
    server.serve_forever()
