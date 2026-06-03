#!/usr/bin/env bash
# autodeploy.sh — triggered by systemd timer every 5 minutes
# Pulls latest code and redeploys changed stacks.
set -euo pipefail

APEXCORE_DIR="/srv/apexcore"
LOG="/tmp/apexcore-autodeploy.log"
BRANCH=$(git -C "$APEXCORE_DIR" rev-parse --abbrev-ref HEAD 2>/dev/null || echo "main")

exec >> "$LOG" 2>&1
echo "=== autodeploy $(date '+%Y-%m-%dT%H:%M:%SZ') branch=$BRANCH ==="

# Check for new commits
git -C "$APEXCORE_DIR" fetch origin --quiet
LOCAL=$(git -C "$APEXCORE_DIR" rev-parse HEAD)
REMOTE=$(git -C "$APEXCORE_DIR" rev-parse "origin/$BRANCH")

if [ "$LOCAL" = "$REMOTE" ]; then
    echo "up-to-date ($LOCAL), nothing to do"
    exit 0
fi

echo "new commits: $LOCAL → $REMOTE — deploying"

git -C "$APEXCORE_DIR" stash push -m "autodeploy-$(date +%s)" 2>/dev/null || true
git -C "$APEXCORE_DIR" pull origin "$BRANCH" --quiet

# nginx vhost
VHOST="$APEXCORE_DIR/infra-compose/nginx-vhost.conf"
if [ -f "$VHOST" ] && command -v nginx &>/dev/null; then
    cp "$VHOST" /etc/nginx/sites-available/apexcore.conf
    mkdir -p /etc/nginx/sites-enabled
    [ -L /etc/nginx/sites-enabled/apexcore.conf ] || \
        ln -sf /etc/nginx/sites-available/apexcore.conf /etc/nginx/sites-enabled/apexcore.conf
    nginx -t -q && nginx -s reload && echo "nginx: reloaded"
fi

# static dashboard
mkdir -p /opt/apexcore-dashboard
[ -f "$APEXCORE_DIR/dashboard/index.html" ] && \
    cp "$APEXCORE_DIR/dashboard/index.html" /opt/apexcore-dashboard/index.html

# update cmd-api binary + restart
NEW_SRV="$APEXCORE_DIR/cmd-api/server.py"
if [ -f "$NEW_SRV" ]; then
    cp "$NEW_SRV" /opt/apexcore/cmd-api/server.py
    systemctl restart cmd-api && echo "cmd-api: restarted"
fi

# docker stacks (only if ai_net exists)
if docker network inspect ai_net &>/dev/null; then
    docker volume inspect n8n_data &>/dev/null || docker volume create n8n_data
    for cf in \
        "ai-stack/docker-compose.yml" \
        "automation-stack/docker-compose.yml" \
        "infra-compose/docker-compose.yml"; do
        FULL="$APEXCORE_DIR/$cf"
        [ -f "$FULL" ] && docker compose -f "$FULL" up -d --remove-orphans --quiet-pull \
            && echo "compose: $cf refreshed"
    done
fi

# dispatcher
ENV_FILE="$APEXCORE_DIR/cmd-api/.env.dispatcher"
if [ -f "$ENV_FILE" ] && [ -f "$APEXCORE_DIR/cmd-api/hermes_dispatcher.py" ]; then
    pkill -f "hermes_dispatcher.py" 2>/dev/null || true
    sleep 1
    set -a; source "$ENV_FILE"; set +a
    nohup python3 "$APEXCORE_DIR/cmd-api/hermes_dispatcher.py" \
        >> /tmp/apexcore-dispatcher.log 2>&1 &
    echo "dispatcher: restarted"
fi

echo "=== autodeploy done ==="
