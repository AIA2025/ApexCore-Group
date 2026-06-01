#!/usr/bin/env python3
"""
ApexCore Hermes Dispatcher v1
Intent classification and routing layer between callers and workers.

Port: 7071 (default)
Auth: Bearer token via DISPATCHER_TOKEN env var

POST /dispatch     — classify intent, route to worker, return result
GET  /health       — unauthenticated liveness check
GET  /routes       — show intent→worker routing table (authenticated)

Usage:
  python3 hermes_dispatcher.py            # production (requires DISPATCHER_TOKEN)
  python3 hermes_dispatcher.py --dev      # development (no token required)
"""

import json
import os
import sys
import uuid
import urllib.request
import urllib.error
from datetime import datetime, timezone
from http.server import BaseHTTPRequestHandler, HTTPServer
from urllib.parse import urlparse

DEV_MODE = "--dev" in sys.argv

DISPATCHER_TOKEN = os.environ.get("DISPATCHER_TOKEN", "")
PORT = int(os.environ.get("DISPATCHER_PORT", "7071"))

HERMES_URL = os.environ.get("HERMES_API_URL", "http://hermes-agent:4000/v1/chat/completions")
HERMES_KEY = os.environ.get("LITELLM_MASTER_KEY", "")
N8N_TASK_URL = os.environ.get("N8N_TASK_WEBHOOK", "https://n8n.apexcore.group/webhook/task")
N8N_LOG_URL = os.environ.get("N8N_LOG_WEBHOOK", "https://n8n.apexcore.group/webhook/log")
OPENCLAW_URL = os.environ.get("OPENCLAW_API_URL", "http://openclaw:8000/send")
CMD_API_URL = os.environ.get("CMD_API_URL", "http://localhost:7070/status")
CMD_API_TOKEN = os.environ.get("CMD_TOKEN", "")

HERMES_SYSTEM_PROMPT = (
    "Du bist Hermes, der COO und CTO von ApexCore / Creator OS. "
    "Du nimmst Aufgaben an, analysierst sie und gibst strukturierte, direkte Antworten. "
    "Antworte präzise und operativ — kein Chatbot-Stil."
)

INTENT_RULES = [
    ("SYSTEM",   {"status", "health", "check", "ping", "running", "down", "uptime",
                  "system", "services", "container", "docker"}),
    ("RESEARCH",  {"research", "analyze", "analyse", "find", "search", "investigate",
                   "explain", "summarize", "what is", "who is", "how does"}),
    ("PRODUCT",   {"launch", "publish", "product", "release", "create product",
                   "shop", "listing", "price", "variant", "sku"}),
    ("CONTENT",   {"write", "draft", "post", "caption", "copy", "content",
                   "newsletter", "email", "script", "hook", "headline"}),
    ("CLIENT",    {"client", "customer", "contact", "message", "send", "notify",
                   "whatsapp", "telegram", "dm", "reply"}),
    ("ADMIN",     {"workflow", "automation", "cron", "schedule", "sync",
                   "notion", "trigger", "n8n", "pipeline"}),
]


# ─── Structured JSON Logging ──────────────────────────────────────────────────

def _log(level: str, event: str, **kwargs):
    entry = {
        "ts": datetime.now(timezone.utc).isoformat(),
        "level": level,
        "event": event,
        **kwargs,
    }
    print(json.dumps(entry, ensure_ascii=False), flush=True)


def log_info(event: str, **kwargs):
    _log("INFO", event, **kwargs)


def log_warn(event: str, **kwargs):
    _log("WARN", event, **kwargs)


def log_error(event: str, **kwargs):
    _log("ERROR", event, **kwargs)


# ─── HTTP Helpers ─────────────────────────────────────────────────────────────

def _post_json(url: str, payload: dict, headers: dict = None, timeout: int = 60) -> dict:
    data = json.dumps(payload).encode()
    req = urllib.request.Request(url, data=data, method="POST")
    req.add_header("Content-Type", "application/json")
    if headers:
        for k, v in headers.items():
            req.add_header(k, v)
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return json.loads(resp.read().decode())
    except urllib.error.HTTPError as e:
        body = e.read().decode(errors="replace")
        return {"error": f"HTTP {e.code}", "detail": body}
    except Exception as exc:
        return {"error": str(exc)}


def _get_json(url: str, headers: dict = None, timeout: int = 10) -> dict:
    req = urllib.request.Request(url, method="GET")
    if headers:
        for k, v in headers.items():
            req.add_header(k, v)
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return json.loads(resp.read().decode())
    except Exception as exc:
        return {"error": str(exc)}


# ─── Worker Calls ─────────────────────────────────────────────────────────────

def call_hermes(task: str, model: str = "hermes-default") -> dict:
    payload = {
        "model": model,
        "messages": [
            {"role": "system", "content": HERMES_SYSTEM_PROMPT},
            {"role": "user", "content": task},
        ],
    }
    headers = {"Authorization": f"Bearer {HERMES_KEY}"} if HERMES_KEY else {}
    result = _post_json(HERMES_URL, payload, headers=headers, timeout=90)
    if "error" in result:
        return result
    try:
        return {"response": result["choices"][0]["message"]["content"], "model": result.get("model", model)}
    except (KeyError, IndexError):
        return {"error": "unexpected hermes response", "raw": result}


def call_n8n_task(task: str, intent: str, task_id: str) -> dict:
    return _post_json(N8N_TASK_URL, {"task": task, "intent": intent, "task_id": task_id}, timeout=30)


def call_n8n_log(task_id: str, intent: str, status: str, result: dict) -> None:
    payload = {
        "task_id": task_id,
        "intent": intent,
        "status": status,
        "result": result,
        "result_preview": str(result.get("response", result)).strip()[:500],
        "timestamp": _now(),
    }
    try:
        _post_json(N8N_LOG_URL, payload, timeout=10)
    except Exception as exc:
        log_warn("n8n_log_failed", task_id=task_id, error=str(exc))


def call_system_status() -> dict:
    headers = {"Authorization": f"Bearer {CMD_API_TOKEN}"} if CMD_API_TOKEN else {}
    return _get_json(CMD_API_URL, headers=headers)


def call_openclaw(message: str, channel: str = "telegram") -> dict:
    return _post_json(OPENCLAW_URL, {"message": message, "channel": channel}, timeout=15)


# ─── Intent Classification ────────────────────────────────────────────────────

def classify_intent(text: str) -> str:
    lower = text.lower()
    for intent, keywords in INTENT_RULES:
        if any(kw in lower for kw in keywords):
            return intent
    return "RESEARCH"


# ─── Core Dispatch Logic ──────────────────────────────────────────────────────

def dispatch(task: str, options: dict) -> dict:
    task_id = str(uuid.uuid4())[:8]
    intent = classify_intent(task)
    started = _now()

    log_info("dispatch_received", task_id=task_id, intent=intent,
             task_preview=task[:120])

    result: dict
    worker: str

    if intent == "SYSTEM":
        worker = "cmd-api"
        status_data = call_system_status()
        if "error" in status_data:
            result = {"response": f"System status check failed: {status_data['error']}"}
        else:
            containers = status_data.get("containers", [])
            lines = [f"- {c['name']}: {c['status']}" for c in containers]
            result = {"response": "**System Status**\n" + "\n".join(lines) if lines
                      else "No containers running."}

    elif intent in ("RESEARCH", "CONTENT", "PRODUCT"):
        worker = "hermes-agent"
        model = "kimi" if intent == "RESEARCH" else "hermes-default"
        result = call_hermes(task, model=model)
        if intent == "PRODUCT" and "error" not in result:
            call_n8n_log(task_id, intent, "DONE", result)

    elif intent == "CLIENT":
        worker = "hermes-agent+openclaw"
        result = call_hermes(task)
        if options.get("notify") and "response" in result:
            call_openclaw(result["response"], channel=options.get("channel", "telegram"))

    elif intent == "ADMIN":
        worker = "n8n"
        n8n_result = call_n8n_task(task, intent, task_id)
        result = {"response": "Task routed to n8n.", "n8n": n8n_result}

    else:
        worker = "hermes-agent"
        result = call_hermes(task)

    status = "BLOCKED" if "error" in result else "DONE"

    log_info("dispatch_complete", task_id=task_id, intent=intent,
             worker=worker, status=status)

    call_n8n_log(task_id, intent, status, result)

    return {
        "task_id": task_id,
        "status": status,
        "intent": intent,
        "worker": worker,
        "result": result,
        "started_at": started,
        "completed_at": _now(),
    }


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


# ─── Routing Table ────────────────────────────────────────────────────────────

ROUTING_TABLE = [
    {"intent": "RESEARCH",  "worker": "hermes-agent",           "model": "kimi",           "trigger_words": "research, analyze, find, explain"},
    {"intent": "SYSTEM",    "worker": "cmd-api (/status)",       "model": "—",              "trigger_words": "status, health, check, running"},
    {"intent": "PRODUCT",   "worker": "hermes-agent + n8n log",  "model": "hermes-default", "trigger_words": "launch, publish, product, release"},
    {"intent": "CONTENT",   "worker": "hermes-agent",            "model": "hermes-default", "trigger_words": "write, draft, content, caption"},
    {"intent": "CLIENT",    "worker": "hermes-agent + openclaw", "model": "hermes-default", "trigger_words": "client, message, send, notify"},
    {"intent": "ADMIN",     "worker": "n8n (webhook/task)",      "model": "—",              "trigger_words": "workflow, automation, sync, cron"},
]


# ─── HTTP Handler ─────────────────────────────────────────────────────────────

class Handler(BaseHTTPRequestHandler):
    def log_message(self, format, *args):
        log_info("http_request", client=self.address_string(),
                 msg=format % args)

    def send_json(self, code: int, data: dict):
        body = json.dumps(data, ensure_ascii=False).encode()
        self.send_response(code)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def authenticated(self) -> bool:
        if DEV_MODE:
            return True
        if not DISPATCHER_TOKEN:
            return False
        auth = self.headers.get("Authorization", "")
        token = auth.removeprefix("Bearer ").strip()
        if not token:
            token = self.headers.get("X-Token", "").strip()
        return token == DISPATCHER_TOKEN

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
            self.send_json(200, {
                "status": "ok",
                "service": "hermes-dispatcher",
                "mode": "dev" if DEV_MODE else "production",
                "auth_enabled": bool(DISPATCHER_TOKEN),
            })
            return

        if not self.authenticated():
            self.send_json(401, {"error": "unauthorized"})
            return

        if path == "/routes":
            self.send_json(200, {"routing_table": ROUTING_TABLE})
            return

        self.send_json(404, {"error": "not found"})

    def do_POST(self):
        if not self.authenticated():
            self.send_json(401, {"error": "unauthorized"})
            return

        path = urlparse(self.path).path

        if path == "/dispatch":
            body = self.read_body()
            task = body.get("task", "").strip()
            if not task:
                self.send_json(400, {"error": "missing 'task' field"})
                return
            options = body.get("options", {})
            result = dispatch(task, options)
            self.send_json(200, result)
            return

        self.send_json(404, {"error": "not found"})


# ─── Startup ──────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    if not DISPATCHER_TOKEN and not DEV_MODE:
        print(json.dumps({
            "ts": datetime.now(timezone.utc).isoformat(),
            "level": "ERROR",
            "event": "startup_failed",
            "reason": "DISPATCHER_TOKEN is not set. Run with --dev to bypass (development only).",
        }), flush=True)
        sys.exit(1)

    missing_warn = []
    if not HERMES_KEY:
        missing_warn.append("LITELLM_MASTER_KEY")
    if not CMD_API_TOKEN:
        missing_warn.append("CMD_TOKEN (SYSTEM intent will fail without it)")

    log_info("startup", port=PORT, dev_mode=DEV_MODE,
             auth_enabled=bool(DISPATCHER_TOKEN),
             missing_vars=missing_warn if missing_warn else None)

    if DEV_MODE:
        log_warn("dev_mode_active",
                 msg="Authentication is DISABLED. Do not run in production without DISPATCHER_TOKEN.")

    server = HTTPServer(("0.0.0.0", PORT), Handler)
    log_info("listening", port=PORT)
    server.serve_forever()
