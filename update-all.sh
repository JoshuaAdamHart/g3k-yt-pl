#!/usr/bin/env bash
set -euo pipefail
# Update all playlists defined in playlists.json

echo "🎵 Updating all playlists..."
./g3k-yt-pl.py --config playlists.json
