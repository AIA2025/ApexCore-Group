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
GROUP_BASE = "https://raw.githubusercontent.com/AIA2025/ApexCore-Group"
PORT = 7070


def run_deploy(branch: str, cmd_token: str = ""):
    """Pull latest code from GitHub, self-update cmd-api, restart scanner."""
    log = open("/var/log/cmd-api-deploy.log", "a")
    cmd_api_updated = False

    def sh(cmd, **kw):
        log.write(f"+ {' '.join(cmd)}\n")
        log.flush()
        return subprocess.run(cmd, stdout=log, stderr=log, **kw)

    try:
        log.write(f"\n=== Deploy branch={branch} at {time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime())} ===\n")
        base  = f"{RAW_BASE}/{branch}"       # AIA2025/apexcore  — scanner, dashboard
        gbase = f"{GROUP_BASE}/{branch}"     # AIA2025/ApexCore-Group — hermes, paperclip, caddy, scripts

        sh(["mkdir", "-p", "/opt/apexcore-mvp/output", "/opt/apexcore-dashboard",
            "/opt/apexcore/cmd-api", "/srv/apexcore/cmd-api",
            "/opt/apexcore/hermes", "/opt/apexcore/paperclip"])

        # --- persist CMD_TOKEN to systemd override (only if changed) ---
        if cmd_token:
            try:
                _token_conf = "/etc/systemd/system/cmd-api.service.d/token.conf"
                _new_content = f'[Service]\nEnvironment="CMD_TOKEN={cmd_token}"\n'
                _existing_content = open(_token_conf).read() if os.path.exists(_token_conf) else ""
                if _existing_content != _new_content:
                    os.makedirs("/etc/systemd/system/cmd-api.service.d", exist_ok=True)
                    with open(_token_conf, "w") as tf:
                        tf.write(_new_content)
                    log.write("CMD_TOKEN updated in systemd override\n")
                    cmd_api_updated = True
                else:
                    log.write("CMD_TOKEN unchanged — no restart needed\n")
            except Exception as te:
                log.write(f"CMD_TOKEN write warning: {te}\n")

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

        # --- cmd-api self-update (from apexcore-group) ---
        r_self = sh(["curl", "-fsSL", f"{gbase}/cmd-api/server.py", "-o", "/tmp/cmd-api-new.py"])
        if r_self.returncode == 0:
            sh(["cp", "/tmp/cmd-api-new.py", "/opt/apexcore/cmd-api/server.py"])
            sh(["cp", "/tmp/cmd-api-new.py", "/srv/apexcore/cmd-api/server.py"])
            log.write("cmd-api self-updated in /opt/ and /srv/\n")
            cmd_api_updated = True
        else:
            log.write("cmd-api/server.py not in branch — skipping self-update\n")

        # --- poller (pull-based deploy agent, idempotent) ---
        r_poll = sh(["curl", "-fsSL", f"{gbase}/cmd-api/poller.sh", "-o", "/tmp/poller.sh"])
        r_psvc = sh(["curl", "-fsSL", f"{gbase}/cmd-api/apexcore-poller.service", "-o", "/tmp/apexcore-poller.service"])
        r_ptmr = sh(["curl", "-fsSL", f"{gbase}/cmd-api/apexcore-poller.timer",   "-o", "/tmp/apexcore-poller.timer"])
        if r_poll.returncode == 0:
            sh(["cp", "/tmp/poller.sh", "/opt/apexcore/cmd-api/poller.sh"])
            sh(["chmod", "+x", "/opt/apexcore/cmd-api/poller.sh"])
            if r_psvc.returncode == 0:
                sh(["cp", "/tmp/apexcore-poller.service", "/etc/systemd/system/apexcore-poller.service"])
            if r_ptmr.returncode == 0:
                sh(["cp", "/tmp/apexcore-poller.timer",   "/etc/systemd/system/apexcore-poller.timer"])
                sh(["systemctl", "daemon-reload"])
                sh(["systemctl", "enable", "--now", "apexcore-poller.timer"])
            log.write("Poller deployed and timer enabled\n")
        else:
            log.write("poller.sh not in branch — skipping\n")

        r_main = sh(["curl", "-fsSL", f"{base}/apexcore-mvp/main.py", "-o", "/tmp/scanner-main.py"])
        r_req  = sh(["curl", "-fsSL", f"{base}/apexcore-mvp/requirements.txt", "-o", "/tmp/scanner-req.txt"])
        if r_main.returncode == 0 and r_req.returncode == 0:
            sh(["cp", "/tmp/scanner-main.py", "/opt/apexcore-mvp/main.py"])
            sh(["cp", "/tmp/scanner-req.txt", "/opt/apexcore-mvp/requirements.txt"])
            sh(["pip3", "install", "-r", "/opt/apexcore-mvp/requirements.txt", "--break-system-packages", "-q"])
            r_dash = sh(["curl", "-fsSL", f"{base}/dashboard/index.html", "-o", "/opt/apexcore-dashboard/index.html"])
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
            subprocess.Popen(["python3", "-m", "uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000", "--log-level", "info"],
                             cwd="/opt/apexcore-mvp", stdout=open("/var/log/apexcore-mvp.log", "a"), stderr=subprocess.STDOUT)
            time.sleep(5)
            result = subprocess.run(["curl", "-sf", "http://localhost:8000/health"], capture_output=True, text=True)
            log.write(f"Scanner {'healthy: ' + result.stdout if result.returncode == 0 else 'health check FAILED'}\n")
        else:
            log.write("apexcore-mvp/ not in branch — scanner not updated\n")

        r_hjs = sh(["curl", "-fsSL", f"{gbase}/hermes/dispatcher.js", "-o", "/tmp/hermes-dispatcher.js"])
        r_hpk = sh(["curl", "-fsSL", f"{gbase}/hermes/package.json", "-o", "/tmp/hermes-package.json"])
        r_hsv = sh(["curl", "-fsSL", f"{gbase}/hermes/hermes.service", "-o", "/tmp/hermes.service"])
        if r_hjs.returncode == 0:
            sh(["cp", "/tmp/hermes-dispatcher.js", "/opt/apexcore/hermes/dispatcher.js"])
            if r_hpk.returncode == 0:
                sh(["cp", "/tmp/hermes-package.json", "/opt/apexcore/hermes/package.json"])
                subprocess.run(["npm", "install", "--omit=dev", "--quiet"], cwd="/opt/apexcore/hermes", stdout=log, stderr=log)
            if r_hsv.returncode == 0:
                sh(["cp", "/tmp/hermes.service", "/etc/systemd/system/hermes.service"])
                sh(["systemctl", "daemon-reload"])
                sh(["systemctl", "enable", "hermes"])
                sh(["systemctl", "restart", "hermes"])
            log.write("Hermes Dispatcher deployed\n")
        else:
            log.write("hermes/ not in branch — skipping\n")

        r_seed = sh(["curl", "-fsSL", f"{gbase}/paperclip/seed.sh", "-o", "/tmp/paperclip-seed.sh"])
        r_areg = sh(["curl", "-fsSL", f"{gbase}/paperclip/agent-registration.json", "-o", "/tmp/paperclip-agent-reg.json"])
        if r_seed.returncode == 0:
            sh(["cp", "/tmp/paperclip-seed.sh", "/opt/apexcore/paperclip/seed.sh"])
            sh(["chmod", "+x", "/opt/apexcore/paperclip/seed.sh"])
            if r_areg.returncode == 0:
                sh(["cp", "/tmp/paperclip-agent-reg.json", "/opt/apexcore/paperclip/agent-registration.json"])
            log.write("Paperclip seeds updated\n")
        else:
            log.write("paperclip/ not in branch — skipping\n")

        # --- Paperclip server (install + seed, idempotent) ---
        r_psetup = sh(["curl", "-fsSL", f"{gbase}/scripts/setup-paperclip.sh", "-o", "/tmp/setup-paperclip.sh"])
        if r_psetup.returncode == 0:
            sh(["chmod", "+x", "/tmp/setup-paperclip.sh"])
            sh(["bash", "/tmp/setup-paperclip.sh", "/var/log/paperclip-setup.log"])
            log.write("Paperclip server setup complete\n")
        else:
            log.write("scripts/setup-paperclip.sh not in branch — skipping\n")

        # --- Caddy: add paperclip.apexcore.group reverse proxy (idempotent) ---
        r_pcaddy = sh(["curl", "-fsSL", f"{gbase}/caddy/paperclip.caddy", "-o", "/tmp/paperclip.caddy"])
        if r_pcaddy.returncode == 0:
            caddyfile = "/opt/openclaw/reverse-proxy/Caddyfile"
            snippet = open("/tmp/paperclip.caddy").read().strip()
            try:
                existing = open(caddyfile).read() if os.path.exists(caddyfile) else ""
                if "paperclip.apexcore.group" not in existing:
                    with open(caddyfile, "a") as cf:
                        cf.write(f"\n{snippet}\n")
                    subprocess.run(["docker", "exec", "caddy", "caddy", "reload",
                                    "--config", "/etc/caddy/Caddyfile"],
                                   stdout=log, stderr=log)
                    log.write("Caddy: paperclip.apexcore.group added and reloaded\n")
                else:
                    log.write("Caddy: paperclip.apexcore.group already in Caddyfile\n")
            except Exception as ce:
                log.write(f"Caddy update warning: {ce}\n")
        else:
            log.write("caddy/paperclip.caddy not in branch — skipping\n")

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
            cmd_token = body.get("cmd_token", "")
            threading.Thread(target=run_deploy, args=(branch, cmd_token), daemon=True).start()
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
