#!/bin/bash
set -euo pipefail

if [ "${CLAUDE_CODE_REMOTE:-}" != "true" ]; then
  exit 0
fi

cd "$CLAUDE_PROJECT_DIR"

# Python backend deps
uv sync

# Desktop (Electron) deps
if [ -d desktop ]; then
  (cd desktop && npm install)
fi

# Claude Code CLI, for reviewing/using this project's Jarvis assistant against Claude
npm install -g @anthropic-ai/claude-code
