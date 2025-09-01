#!/bin/bash

# Create json_cache directory if it doesn't exist
mkdir -p json_cache

# Create and activate virtual environment
if [ ! -d "venv" ]; then
    python3 -m venv venv
fi
source venv/bin/activate

# Install requests
pip install requests

# Run the conversation extractor
python youtube_playlist_updater.py "$@"
