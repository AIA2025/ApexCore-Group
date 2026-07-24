#!/bin/bash
set -euo pipefail

if [ "${CLAUDE_CODE_REMOTE:-}" != "true" ]; then
  exit 0
fi

cd "$CLAUDE_PROJECT_DIR"

# apexcore-mvp: FastAPI dossier pipeline + tests
if [ -f apexcore-mvp/requirements.txt ]; then
  pip3 install --disable-pip-version-check -q -r apexcore-mvp/requirements.txt
fi

# hermes: Node dispatcher
if [ -f hermes/package.json ]; then
  (cd hermes && npm install --no-fund --no-audit)
fi
