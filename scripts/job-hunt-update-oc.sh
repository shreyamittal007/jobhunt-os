#!/bin/bash
# Job-Hunt Daily Brief — runs once/day.

set -u

JH_DIR="${JH_DIR:-$HOME/Documents/Job hunt}"
TODAY="$(date +%Y-%m-%d)"
LOCK_FILE="/tmp/job-hunt-update-$TODAY.lock"
LOG_FILE="/tmp/job-hunt-update.log"
BRIEF_DIR="$JH_DIR/briefs"
BRIEF_FILE="$BRIEF_DIR/$TODAY.md"
PROMPT_FILE="$JH_DIR/routine-prompt.md"

if [ -f "$LOCK_FILE" ]; then
    echo "$(date): Already ran today, skipping." >> "$LOG_FILE"
    exit 0
fi
if [ -f "$BRIEF_FILE" ]; then
    echo "$(date): Brief already exists for $TODAY — skipping." >> "$LOG_FILE"
    exit 0
fi
touch "$LOCK_FILE"

mkdir -p "$BRIEF_DIR"

echo "$(date): Starting job-hunt update..." >> "$LOG_FILE"

cd "$JH_DIR"

claude --print --dangerously-skip-permissions -p "$(cat "$PROMPT_FILE")" >> "$LOG_FILE" 2>&1

NOW_TS=$(date +%s)
TWO_HOURS_AGO=$((NOW_TS - 7200))

# macOS-compatible file modification time check
if [ -f "$BRIEF_FILE" ] && [ "$(stat -f %m "$BRIEF_FILE" 2>/dev/null)" -gt "$TWO_HOURS_AGO" ]; then
    echo "$(date): Brief written: $BRIEF_FILE" >> "$LOG_FILE"
else
    echo "$(date): No fresh brief — quiet day." >> "$LOG_FILE"
fi

echo "$(date): Done." >> "$LOG_FILE"

find /tmp -maxdepth 1 -name "job-hunt-update-*.lock" -mtime +3 -delete 2>/dev/null || true
