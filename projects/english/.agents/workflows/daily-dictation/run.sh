#!/bin/bash
# run.sh — Daily orchestrator for DailyDictation tracking.
#
# Usage:
#   ./run.sh                          # Uses DD_USER_ID from env
#   ./run.sh --user-id 12345          # Explicit user ID
#   ./run.sh --user-id 12345 --topic "IELTS Listening"
#
# Designed to be called by launchd/cron daily.

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../../.." && pwd)"

# Source .env if it exists
if [ -f "$PROJECT_ROOT/.env" ]; then
    set -a
    source "$PROJECT_ROOT/.env"
    set +a
fi

cd "$SCRIPT_DIR"

USER_ID="${DD_USER_ID:-}"
TOPIC=""
EXTRA_ARGS=()

while [[ $# -gt 0 ]]; do
    case "$1" in
        --user-id) USER_ID="$2"; shift 2 ;;
        --topic)   TOPIC="$2"; shift 2 ;;
        *)         EXTRA_ARGS+=("$1"); shift ;;
    esac
done

if [ -z "$USER_ID" ]; then
    echo "Error: DD_USER_ID not set. Use --user-id or export DD_USER_ID=xxx"
    exit 1
fi

TODAY=$(date +%Y-%m-%d)
YESTERDAY=$(date -v-1d +%Y-%m-%d 2>/dev/null || date -d "yesterday" +%Y-%m-%d)

echo "=== DailyDictation Tracker: $TODAY ==="

# Step 1: Take snapshot
echo "[1/3] Taking snapshot..."
python3 snapshot.py --user-id "$USER_ID" --date "$TODAY"

# Step 2: Diff vs yesterday
echo "[2/3] Computing diff..."
set +e
DIFF_JSON=$(python3 diff.py --auto --json 2>&1)
DIFF_EXIT=$?
set -e
if [ "$DIFF_EXIT" -ne 0 ]; then
    echo "  ⚠️  Diff failed (maybe first run, no yesterday snapshot). Skipping record."
    echo "$DIFF_JSON"
    exit 0
fi

# Step 3: Record to database
echo "[3/4] Recording to study_log..."
TOPIC_ARG=""
if [ -n "$TOPIC" ]; then
    TOPIC_ARG="--topic $TOPIC"
fi
echo "$DIFF_JSON" | python3 record.py $TOPIC_ARG

# Step 4: Notify Discord via agent
echo "[4/4] Sending to Discord (agent)..."
bash notify_agent.sh

echo "Done."
