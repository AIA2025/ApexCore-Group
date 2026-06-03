# Security & Merge Report — ApexCore-Group

Status: Completed by Copilot
Date: 2026-06-03

Summary
- I resolved deployment/conflict issues and sanitized scripts to remove hard-coded secrets.
- Key scripts updated and hardened: deploy.sh, setup-complete.sh, deploy-all.sh
- Changes were committed and pushed to `main`.
- A fix branch `pr-2/resolve-deploy-conflicts` exists and was used as source for the fixes.

Commits of interest
- chore(pr-2): sanitize secrets and prepare conflict-resolve updates
  - https://github.com/AIA2025/ApexCore-Group/commit/604227beb88dd981937d785f223ee1762276cd23
- chore(pr-2): merge resolved scripts into main, sanitize secrets
  - https://github.com/AIA2025/ApexCore-Group/commit/7caada18b567a5bbf2ca4342bac01b80521f708e

What I changed (high level)
- Removed hard-coded plaintext secrets and replaced them with environment variable placeholders (e.g. N8N_PASSWORD, CMD_API_TOKEN, PORKBUN_*).
- Added defensive guards so scripts fail safe and print clear instructions when secrets are missing.
- Added validation steps (caddy validate) and checks for optional tools (pandoc/wkhtmltopdf) in deploy scripts.
- Ensured no real secrets were written into commits.

Immediate required actions (must be done now)
1. Rotate all compromised keys/tokens (you posted them earlier in chat):
   - GitHub PATs, Stripe keys, Anthropic/OpenRouter/Perplexity/FAL/Moonshot keys, Porkbun keys, Notion, Supabase, Google OAuth client secret, VPS SSH keys, etc.
   - Revoke the exposed keys in each provider's dashboard and create new ones.
2. On GitHub: set the following repository Secrets (Settings → Secrets & variables → Actions):
   - N8N_PASSWORD
   - CMD_API_TOKEN
   - PORKBUN_APIKEY
   - PORKBUN_SECRETKEY
   - VPS_DEPLOY_KEY (SSH private key for CI/Actions)
   - ANTHROPIC_API_KEY, NOTION_TOKEN, OPENROUTER_API_KEY, STRIPE_SECRET_KEY, etc.
3. On the VPS (76.13.138.73): rotate SSH keys, remove any suspicious authorized_keys, and secure root access.

Smoke tests to run after secrets are rotated
- caddy validate --config /etc/caddy/Caddyfile && systemctl reload caddy
- curl -sf http://76.13.138.73:7070/health
- curl -sf http://76.13.138.73:8000/health
- curl -sf http://76.13.138.73:9090
- n8n login test (using N8N_PASSWORD)

Notes & next steps I can perform (still waiting on rotated secrets / collaborator invite)
- Create a PR from `pr-2/resolve-deploy-conflicts` → `main` (I prepared content and branch). I can create the PR and then close the original PR #2, or you can run the provided GH CLI commands locally.
- If you want history scrubbing (remove secrets from git history), I can perform a filter-repo / BFG cleanup and force-push (destructive) — I will only run that after you confirm and coordinate with your team.

Contact
- If you want me to continue (create PR, close PR #2, run smoke tests, or run history-scrub), reply with the specific action now or grant collaborator access to `copilot`. I will not use any secrets you exposed; please rotate them immediately.
