#!/bin/bash
set -euo pipefail

# Only run in remote (Claude Code on the web) environments
if [ "${CLAUDE_CODE_REMOTE:-}" != "true" ]; then
  exit 0
fi

echo '{"async": true, "asyncTimeout": 300000}'

# Install Python backend dependencies
echo "Installing Python dependencies..."
pip install -r "$CLAUDE_PROJECT_DIR/requirements.txt" --quiet

# Install React frontend dependencies
echo "Installing frontend dependencies..."
npm install --prefix "$CLAUDE_PROJECT_DIR/frontend" --prefer-offline

echo "Dependencies installed successfully."
