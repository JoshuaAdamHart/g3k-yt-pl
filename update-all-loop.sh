#!/usr/bin/env bash
set -euo pipefail

# Continuous loop script for g3k-yt-pl
# Updates playlists during daytime hours (06:00 - 21:59) every 3 hours and runs a single
# nightly run at 11:55 PM (23:55) to maximize usage of remaining daily API quota.

FORCE=""
NIGHTLY_DONE_DATE=""
DEFAULT_SLEEP_SECS=${DEFAULT_SLEEP_SECS:-10800} # 3 hours

# Helper function to invoke g3k-hr if available, else fallback to horizontal line
hr() {
    if command -v g3k-hr &>/dev/null; then
        g3k-hr
    else
        echo "----------------------------------------"
    fi
}

# Helper function to invoke g3k-sleep if available, else standard sleep
do_sleep() {
    local secs="$1"
    if command -v g3k-sleep &>/dev/null; then
        g3k-sleep "$secs" 1 || FORCE=1
    else
        sleep "$secs" || FORCE=1
    fi
    echo "" # Clear prompt line from g3k-sleep
}

# Helper function to calculate sleep duration for the next cycle
get_sleep_secs() {
    local sleep_secs=$DEFAULT_SLEEP_SECS
    local now_epoch
    now_epoch=$(date +%s)
    
    # Target 23:55:05 today using BSD date (macOS) syntax to ensure sleep lands comfortably past 23:55:00
    local target_2355
    target_2355=$(date -v23H -v55M -v05S +%s 2>/dev/null || echo "")
    
    if [[ -n "$target_2355" ]]; then
        local diff_2355=$(( target_2355 - now_epoch ))
        # If 23:55 is coming up within the next 3 hours (10800s), cap sleep duration to land at 23:55:05
        if [[ $diff_2355 -gt 0 && $diff_2355 -lt $DEFAULT_SLEEP_SECS ]]; then
            sleep_secs=$diff_2355
        fi
    fi
    echo "$sleep_secs"
}

# Start with countdown on launch. Pressing key during countdown sets FORCE=1 to run immediately.
SLEEP_SECS=$(get_sleep_secs)
hr
echo -n "[YT-LOOP] $(date)..."
do_sleep "$SLEEP_SECS"

while true; do
    hr
    echo "[YT-LOOP] $(date)"
    
    TODAY=$(date +%Y-%m-%d)
    
    RAW_HOUR=$(date +%H)
    HOUR=$(( 10#$RAW_HOUR ))
    
    RAW_MIN=$(date +%M)
    MINUTE=$(( 10#$RAW_MIN ))
    
    # Execution conditions:
    # 1. Manual interrupt/force (FORCE is non-empty)
    # 2. Daytime active window (6:00 AM to 9:59 PM: 6 <= HOUR < 22)
    # 3. Nightly run at ~11:55 PM (23:54 to 23:59) if not already completed today
    IS_DAYTIME=0
    if [[ $HOUR -ge 6 && $HOUR -lt 22 ]]; then
        IS_DAYTIME=1
    fi
    
    IS_NIGHTLY_TIME=0
    if [[ $HOUR -eq 23 && $MINUTE -ge 54 && "$NIGHTLY_DONE_DATE" != "$TODAY" ]]; then
        IS_NIGHTLY_TIME=1
    fi

    if [[ -n "${FORCE}" || $IS_DAYTIME -eq 1 || $IS_NIGHTLY_TIME -eq 1 ]]; then
        echo "[YT-LOOP] Updating..."
        ./update-all.sh
        if [[ $IS_NIGHTLY_TIME -eq 1 ]]; then
            NIGHTLY_DONE_DATE="$TODAY"
        fi
    else
        echo "[YT-LOOP] Skipping..."
    fi
    
    hr
    echo -n "[YT-LOOP] $(date)..."
    FORCE=""
    
    SLEEP_SECS=$(get_sleep_secs)
    do_sleep "$SLEEP_SECS"
done
