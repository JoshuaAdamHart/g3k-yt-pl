# YouTube Playlist Manager

A streamlined Python CLI tool that adds videos from multiple YouTube channels to a playlist with intelligent date filtering, quota tracking, and graceful failure handling.

## Features

- **Add videos to playlists** from multiple channels
- **Date range filtering** - specify start/end dates for videos
- **Smart caching** - avoids unnecessary API calls
- **Quota tracking** - monitors API usage and fails gracefully
- **Incremental updates** - checks for new videos since last run
- **Duplicate prevention** - skips videos already in playlist
- **Graceful interruption** - Ctrl+C stops safely

## Quick Start

```bash
# Setup
make setup

# Add recent videos from channels to a playlist
make run ARGS='--playlist-title "Tech News" --start-date 2024-01-01 "MKBHD" "Linus Tech Tips"'
```

## Setup

### 1. Clone and Install
```bash
git clone <repo-url>
cd yt-pl
make setup
```

### 2. Get YouTube API Credentials

1. Go to [Google Cloud Console](https://console.cloud.google.com/)
2. Create a project and enable YouTube Data API v3
3. Create OAuth 2.0 credentials for "Desktop application"
4. Download as `credentials.json` in this directory

## Usage

### Basic Usage
```bash
python youtube_playlist_manager.py --playlist-title "My Playlist" channel1 channel2
```

### Date Filtering
```bash
# Videos from specific date range
python youtube_playlist_manager.py \
  --playlist-title "Recent Tech" \
  --start-date 2024-01-01 \
  --end-date 2024-12-31 \
  "MKBHD" "Linus Tech Tips"

# Videos from last month
python youtube_playlist_manager.py \
  --playlist-title "Last Month" \
  --start-date 2024-11-01 \
  "channel1" "channel2"
```

### Channel Input Formats
```bash
# Channel names
python youtube_playlist_manager.py -t "Gaming" "PewDiePie" "Markiplier"

# Channel URLs
python youtube_playlist_manager.py -t "Tech" \
  "https://www.youtube.com/@MKBHD" \
  "https://www.youtube.com/c/LinusTechTips"

# Channel IDs
python youtube_playlist_manager.py -t "Educational" \
  "UC2C_jShtL725hvbm1arSV9w" \
  "UCsXVk37bltHxD1rDPwtNM8Q"
```

### Makefile Commands
```bash
make setup          # Create venv and install dependencies
make run ARGS="..."  # Run with arguments
make clean           # Remove venv and cache files
make help            # Show available commands
```

## How It Works

1. **Authentication**: Uses OAuth 2.0 to access your YouTube account
2. **Channel Processing**: Converts channel names/URLs to IDs (cached to save quota)
3. **Video Fetching**: Gets all videos from each channel (with date filtering)
4. **Caching**: Stores results locally to avoid repeated API calls
5. **Playlist Management**: Creates playlist or uses existing one
6. **Smart Adding**: Skips duplicates, adds in chronological order
7. **Quota Tracking**: Monitors API usage and stops before hitting limits

## Quota Management

The YouTube API has a daily quota limit (10,000 units). This tool tracks usage:

- Channel search: 100 units
- Get channel info: 1 unit  
- Get playlist videos: 1 unit per page (50 videos)
- Add video to playlist: 50 units
- Create playlist: 50 units

The tool will stop gracefully when approaching quota limits and suggest running again tomorrow.

## Caching System

- **Channel cache**: Maps channel names to IDs (avoids expensive searches)
- **Video cache**: Stores video metadata for 24 hours
- **Last run tracking**: Automatically checks for new videos since last execution

Cache files:
- `cache.json` - Video metadata and timestamps
- `token.json` - Authentication tokens

## Error Handling

- **Quota exceeded**: Stops gracefully, shows progress, suggests retry time
- **Network errors**: Retries with backoff
- **Missing channels**: Skips and continues with others
- **Interrupted execution**: Ctrl+C stops safely, progress is saved

## Files Created

- `token.json` - OAuth tokens (auto-generated)
- `cache.json` - Video and channel cache
- `.gitignore` - Excludes sensitive files from git

## Troubleshooting

**"credentials.json not found"**: Download OAuth credentials from Google Cloud Console

**"Channel not found"**: Try using full URL or channel ID instead of name

**"Quota exceeded"**: Wait until tomorrow or use a different API key

**Authentication errors**: Delete `token.json` and re-run to re-authenticate

## Example Workflows

### Daily Tech News Playlist
```bash
# First run - gets all videos from 2024
python youtube_playlist_manager.py \
  --playlist-title "Daily Tech" \
  --start-date 2024-01-01 \
  "MKBHD" "Linus Tech Tips" "Unbox Therapy"

# Subsequent runs - only gets new videos since last run
python youtube_playlist_manager.py \
  --playlist-title "Daily Tech" \
  "MKBHD" "Linus Tech Tips" "Unbox Therapy"
```

### Monthly Gaming Highlights
```bash
python youtube_playlist_manager.py \
  --playlist-title "Gaming Nov 2024" \
  --start-date 2024-11-01 \
  --end-date 2024-11-30 \
  "PewDiePie" "Markiplier" "GameGrumps"
```
