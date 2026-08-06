# G3K YouTube Playlist Manager

A Vibe-coded Python project by Joshua Adam Hart  
Final project for Stanford Continuing Studies course: **TECH 152 A Crash Course in Artificial Intelligence**  
Instructor: Ronjon Nag | https://continuingstudies.stanford.edu/

A streamlined Python CLI tool that adds videos from multiple YouTube channels to a playlist with intelligent date filtering, quota tracking, and graceful failure handling.

## The Story Behind This Project

I wanted to view YouTube videos in a way similar to a podcast player, where I could consume all videos from a given channel in publication order without having to queue them up individually. This need arose when I decided to watch all of [Numberphile's](https://www.youtube.com/@numberphile) videos from the beginning.

The YouTube app allowed me to sort videos by publication date, but resuming from where I left off meant scrolling past hundreds of previously-watched videos to find the next one. My workaround was adding ~100 videos at a time to my Watch Later playlist, then deleting them as I watched. When I caught up with Numberphile and turned my attention to sister channel [Computerphile](https://www.youtube.com/@Computerphile), I decided I did not want to go through THAT again.

Since I had just started a pilot program using Amazon Q at my employer, and since I was taking this AI course at Stanford Continuing Studies, I thought this would be a perfect use-case for vibe coding. I started with a simple prompt to write a Python script that uses YouTube's API, and iteratively refined it through conversation with AI.

This project was started as an experiment with Amazon Q (now Kiro), but has since switched to using Google's Antigravity IDE for ongoing AI-assisted development and pair programming.

Amazon Q generated a working Python script on the first attempt and provided detailed API key setup instructions. However, I quickly discovered the YouTube API's quota system the hard way - my first run hit the 10,000 daily limit. After learning that adding a single video costs 50 quota points, I realized an 800-video playlist would require 40,000 points (4 days worth). AI assistance helped implement smart channel ID caching, duplicate tracking, and graceful quota handling to make multi-day processing viable.

**Technical Note**: This project was initially developed using Amazon Q Developer (now Kiro) and subsequently evolved using Google's Antigravity IDE. These AI assistants provided code generation, debugging assistance, and iterative refinement through natural language conversations. The streamlined version presented here represents the culmination of that AI-assisted development process, demonstrating practical applications of conversational programming and AI-powered software development workflows.

## Features

- **Add videos to playlists** from multiple channels
- **Date range filtering** - specify start/end dates for videos
- **Per-channel duration & title filters** - filter out shorts or videos matching regex patterns
- **Smart channel caching** - caches channel handle and ID resolutions to avoid expensive searches
- **Quota tracking** - monitors API usage and fails gracefully
- **Incremental updates** - automatically checks for new videos since last run
- **Duplicate prevention** - tracks added video IDs (with 7-day TTL pruning) and skips videos already in playlist
- **CSV logging** - logs all added videos to `json_cache/added_videos.csv`
- **Graceful interruption** - Ctrl+C stops safely

## Quick Start

```bash
# Setup
make setup

# Update all playlists from json_cache/playlists.json
make update-all

# Or run specific playlist from config
make run-config PLAYLIST=tech

# Run with explicit channels (legacy CLI mode)
make run ARGS='--playlist-title "Tech News" --start-date 2024-01-01 "MKBHD" "Linus Tech Tips"'
```

## Setup

### 1. Clone and Install
```bash
git clone <repo-url>
cd g3k-yt-pl
make setup
```

### 2. Get YouTube API Credentials

1. Go to [Google Cloud Console](https://console.cloud.google.com/)
2. Create a project and enable YouTube Data API v3
3. Create OAuth 2.0 credentials for "Desktop application"
4. Download as `credentials.json` in this directory

## Usage

### JSON Config Mode (Recommended)
```bash
# Update all playlists from config
./update-all.sh

# Update specific playlist
./.venv/bin/python g3k-yt-pl.py --config json_cache/playlists.json --playlist nerds

# Use custom config file
./.venv/bin/python g3k-yt-pl.py --config my-playlists.json --playlist tech
```

### Basic Usage (Legacy CLI Mode)
```bash
./.venv/bin/python g3k-yt-pl.py --playlist-title "My Playlist" channel1 channel2
```

### Date Filtering
```bash
# Videos from specific date range
./.venv/bin/python g3k-yt-pl.py \
  --playlist-title "Recent Tech" \
  --start-date 2024-01-01 \
  --end-date 2024-12-31 \
  "MKBHD" "Linus Tech Tips"

# Videos from last month
./.venv/bin/python g3k-yt-pl.py \
  --playlist-title "Last Month" \
  --start-date 2024-11-01 \
  "channel1" "channel2"
```

### Channel Input Formats
```bash
# Channel handles (cost only 1 quota unit)
./.venv/bin/python g3k-yt-pl.py -t "Tech" "@MKBHD" "https://www.youtube.com/@Computerphile"

# Channel URLs
./.venv/bin/python g3k-yt-pl.py -t "Tech" \
  "https://www.youtube.com/channel/UC2C_jShtL725hvbm1arSV9w"

# Direct Channel IDs (free — 0 lookup cost)
./.venv/bin/python g3k-yt-pl.py -t "Educational" \
  "UC2C_jShtL725hvbm1arSV9w" \
  "UCsXVk37bltHxD1rDPwtNM8Q"
```

## JSON Configuration

Create a `json_cache/playlists.json` file to define multiple playlists:

```json
{
  "playlists": {
    "tech": {
      "title": "Tech News",
      "channels": [
        "MKBHD",
        "https://www.youtube.com/@LinusTechTips",
        {
          "name": "@Computerphile",
          "min_duration": "10m",
          "max_duration": "1h30m",
          "allow_regex": "Podcast",
          "exclude_regex": "Shorts"
        }
      ],
      "default_start_date": "2024-01-01"
    },
    "gaming": {
      "title": "Gaming Videos", 
      "channels": ["PewDiePie", "Markiplier"],
      "default_start_date": "2024-06-01",
      "disabled": true
    }
  }
}
```

The system automatically tracks when each playlist was last updated and uses that timestamp (minus 24 hours) as the start date for subsequent runs. The `default_start_date` is only used for the first run of each playlist.

**Optional flags:**
- `disabled`: Set to `true` to skip this playlist during batch processing (`update-all.sh`). It will only be processed when explicitly specified with `--playlist`.
- **Per-channel filter rules (dict format):**
  - `min_duration` / `max_duration`: Filter by video length (supports integer seconds `600`, MM:SS `"10:00"`, or duration strings `"10m"`, `"1h30m"`).
  - `allow_regex` / `exclude_regex`: Filter videos by title matching regex patterns.

### Makefile Commands
```bash
make setup          # Create .venv and install dependencies
make update-all     # Update all playlists from config
make run-config PLAYLIST=name  # Update specific playlist
make run ARGS="..."  # Run with arguments (legacy mode)
make clean          # Remove .venv and runtime cache files
make help           # Show available commands
```

## How It Works

1. **Authentication**: Uses OAuth 2.0 to access your YouTube account
2. **Channel Processing**: Resolves handles, URLs, and names to Channel IDs (cached in `channels.json` to save quota)
3. **Video Fetching**: Queries YouTube API for uploads since `since_date` (stops fetching as soon as older videos are reached)
4. **Playlist Management**: Creates playlist or finds existing one
5. **Smart Adding**: Skips duplicate/previously added videos, adds in chronological order with 0.5s rate limiting
6. **Quota Tracking**: Monitors API usage and stops before hitting the daily 10,000 unit limit

## Quota Management

The YouTube API has a daily quota limit (10,000 units). This tool tracks usage:

- Channel name search: 100 units
- Channel handle lookup (`@handle`): 1 unit
- Get channel info: 1 unit  
- Get playlist items / uploads: 1 unit per page (50 videos)
- Add video to playlist: 50 units
- Create playlist: 50 units
- Duration lookup: 1 unit per 50 videos

The tool stops gracefully when approaching quota limits and resumes on subsequent runs.

## Cache & Data Files

- `json_cache/channels.json` - Permanent cache mapping channel handles/names to Channel IDs
- `json_cache/added_videos.json` - Per-playlist tracking of added video IDs (with 7-day TTL pruning)
- `json_cache/playlist_timestamps.json` - Per-playlist last successful execution timestamps
- `json_cache/added_videos.csv` - Detailed CSV log of added videos
- `json_cache/quota.json` - Daily API quota tracking
- `token.json` - Authentication tokens (auto-generated)

## Error Handling

- **Quota exceeded**: Stops gracefully, shows progress, saves state for next run
- **Missing channels**: Skips and continues with others
- **Interrupted execution**: Ctrl+C stops safely, added videos are tracked
