# Hermes Flow — Technical Reference V1

> Paperclip Projekt: `00-Runbooks` / Issue: APE-1
> Stand: 2026-06-01

---

## Überblick

Hermes ist der **HTTP-Execution-Layer** des ApexCore Multi-Agent-Systems. Er nimmt
Dispatch-Aufrufe vom Paperclip Control Plane entgegen und routet sie an den realen
Execution Backend (Claude Code CLI, Bash-Tasks, VPS-Workloads).

```
Paperclip (Control Plane)
  └── HTTP Adapter
        └── POST /dispatch  ──►  Hermes Dispatcher (:7071)
                                        ├── claude_code  (Claude Code CLI)
                                        ├── bash         (Shell-Executor)
                                        └── default      (Fallback / Logging)
```

---

## Endpunkte

| Methode | Pfad        | Auth   | Beschreibung                         |
|---------|-------------|--------|--------------------------------------|
| GET     | `/health`   | —      | Heartbeat-Probe; gibt `{"status":"ok"}` |
| HEAD    | `/`         | —      | Paperclip Adapter-Health-Probe       |
| POST    | `/dispatch` | Bearer | Empfängt Command-JSON von Paperclip  |

---

## Authentifizierung

Jede POST-Anfrage muss den Header enthalten:

```
Authorization: Bearer <DISPATCHER_TOKEN>
```

`DISPATCHER_TOKEN` wird über die Environment-Variable gesetzt und **niemals** in
plain-text committet. Als Company-Secret in Paperclip hinterlegen.

---

## Command-JSON Format (Dispatch Payload)

```json
{
  "source": "paperclip",
  "kind": "dispatch",
  "agentId": "<agent-uuid>",
  "runId": "<run-uuid>",
  "context": {
    "goal": "Beschreibung des Ziels",
    "project": "00-Runbooks",
    "input": "Freitext oder strukturierte Daten",
    "backend": "claude_code"
  }
}
```

Das Feld `context.backend` entscheidet, an welchen Handler Hermes routet.
Fehlt es, greift `default` (Logging).

---

## Umgebungsvariablen

| Variable           | Pflicht | Default | Beschreibung                         |
|--------------------|---------|---------|--------------------------------------|
| `DISPATCHER_TOKEN` | ✅      | —       | Shared secret mit Paperclip          |
| `HERMES_PORT`      | —       | `7071`  | TCP-Port des Dispatch-Service        |
| `NODE_ENV`         | —       | —       | `production` für Prod-Deployment     |

---

## systemd Service

```
/etc/systemd/system/hermes.service
```

Starten / Status prüfen:

```bash
systemctl status hermes
journalctl -u hermes -f
```

---

## Routing erweitern

Neue Backends in `hermes/dispatcher.js` im `handlers`-Objekt registrieren:

```js
handlers['my_backend'] = async (payload) => {
  // Ausführungslogik
  return { accepted: true, backend: 'my_backend', runId: payload.runId };
};
```

---

## Fehlerbehandlung

| HTTP-Status | Bedeutung                           |
|-------------|-------------------------------------|
| 200         | Dispatch akzeptiert                 |
| 401         | Ungültiger oder fehlender Token     |
| 400         | Ungültiges JSON im Request-Body     |
| 404         | Unbekannter Pfad                    |

Paperclip wertet jeden Nicht-2xx als Fehler und markiert den Run entsprechend.
