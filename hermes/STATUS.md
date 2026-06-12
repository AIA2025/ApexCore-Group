# Hermes Stack Status

_Last updated by Claude Code — 2026-06-12_

## LiteLLM Proxy (hermes-agent) — FIXED (pending VPS apply)

| Model alias | OpenRouter path | Status |
|---|---|---|
| `hermes-default` | `openrouter/anthropic/claude-sonnet-4-5` | ✅ |
| `claude-sonnet`  | `openrouter/anthropic/claude-sonnet-4-5` | ✅ |
| `claude-opus`    | `openrouter/anthropic/claude-opus-4-5`   | ✅ |
| `kimi`           | `openrouter/moonshotai/kimi-k2`          | ✅ |
| `auto`           | `openrouter/openrouter/auto`             | ✅ fixed (was `openrouter/auto` → invalid) |

**Apply to VPS (one command):**
```bash
bash <(curl -fsSL https://raw.githubusercontent.com/AIA2025/ApexCore-Group/claude/clever-heisenberg-oi9673/hermes/fix-hermes-now.sh)
```

**Required env var in container:** `OPENROUTER_API_KEY` (already confirmed set)

---

## Hermes Gateway (hermes-webui-cxlp-hermes-agent-1) — PARTIAL

| Check | State |
|---|---|
| Health endpoint `/health/liveliness` | ✅ 200 OK |
| Model routing (`openrouter/anthropic/claude-sonnet-4-5`) | ✅ configured |
| Telegram platform | ❌ token `8934032075:***` rejected by Telegram |

**Telegram fix:** Get a valid bot token from [@BotFather](https://t.me/BotFather) and update:
```bash
docker exec hermes-webui-cxlp-hermes-agent-1 \
  sed -i 's/8934032075:.*/NEW_TOKEN/' /home/hermes/.hermes/config.yaml
docker restart hermes-webui-cxlp-hermes-agent-1
```

---

## PR #8 CI
- CI check `deploy`: ✅ passed
- No review comments
