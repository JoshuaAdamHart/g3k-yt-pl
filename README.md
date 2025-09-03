# G3K YouTube Playlist Manager

A Vibe-coded Python project by Joshua Adam Hart  
Final project for Stanford Continuing Studies course: **TECH 152 A Crash Course in Artificial Intelligence**  
Instructor: Ronjon Nag | https://continuingstudies.stanford.edu/

A streamlined Python CLI tool that adds videos from multiple YouTube channels to a playlist with intelligent date filtering, quota tracking, and graceful failure handling.

## The Story Behind This Project

I wanted to view YouTube videos in a way similar to a podcast player, where I could consume all videos from a given channel in publication order without having to queue them up individually. This need arose when I decided to watch all of [Numberphile's](https://www.youtube.com/@numberphile) videos from the beginning.

The YouTube app allowed me to sort videos by publication date, but resuming from where I left off meant scrolling past hundreds of previously-watched videos to find the next one. My workaround was adding ~100 videos at a time to my Watch Later playlist, then deleting them as I watched. When I caught up with Numberphile and turned my attention to sister channel [Computerphile](https://www.youtube.com/@Computerphile), I decided I did not want to go through THAT again.

Since I had just started a pilot program using Amazon Q at my employer, and since I was taking this AI course at Stanford Continuing Studies, I thought this would be a perfect use-case for vibe coding. I have read the code but tried not to hand-edit anything. I started with a simple prompt to write a Python script that uses YouTube's API, and iteratively refined it through conversation with AI.

Amazon Q generated a working Python script on the first attempt and provided detailed API key setup instructions. However, I quickly discovered the YouTube API's quota system the hard way - my first run hit the 10,000 daily limit. After learning that adding a single video costs 50 quota points, I realized an 800-video playlist would require 40,000 points (4 days worth). Amazon Q helped me implement caching and graceful quota handling to make multi-day processing viable.

**Technical Note**: This project was developed using Amazon Q Developer, an AI assistant built by Amazon Web Services. Amazon Q provided code generation, debugging assistance, and iterative refinement through natural language conversations. The streamlined version presented here represents the culmination of that AI-assisted development process, demonstrating practical applications of conversational programming and AI-powered software development workflows. Even this project story was co-written with Amazon Q, streamlining an extemporaneous and verbose version of the narrative.

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

### JSON Config Mode (Recommended)
```bash
# Update all playlists from config
./update-all.sh

# Update specific playlist
python g3k-yt-pl.py --config playlists.json --playlist nerds

# Use custom config file
python g3k-yt-pl.py --config my-playlists.json --playlist tech
```

### Basic Usage (Legacy)
```bash
python g3k-yt-pl.py --playlist-title "My Playlist" channel1 channel2
```

### Date Filtering
```bash
# Videos from specific date range
python g3k-yt-pl.py \
  --playlist-title "Recent Tech" \
  --start-date 2024-01-01 \
  --end-date 2024-12-31 \
  "MKBHD" "Linus Tech Tips"

# Videos from last month
python g3k-yt-pl.py \
  --playlist-title "Last Month" \
  --start-date 2024-11-01 \
  "channel1" "channel2"
```

### Channel Input Formats
```bash
# Channel names
python g3k-yt-pl.py -t "Gaming" "PewDiePie" "Markiplier"

# Channel URLs
python g3k-yt-pl.py -t "Tech" \
  "https://www.youtube.com/@MKBHD" \
  "https://www.youtube.com/c/LinusTechTips"

# Channel IDs
python g3k-yt-pl.py -t "Educational" \
  "UC2C_jShtL725hvbm1arSV9w" \
  "UCsXVk37bltHxD1rDPwtNM8Q"
```

## JSON Configuration

Create a `playlists.json` file to define multiple playlists:

```json
{
  "playlists": {
    "tech": {
      "title": "Tech News",
      "channels": ["MKBHD", "Linus Tech Tips"],
      "default_start_date": "2024-01-01"
    },
    "gaming": {
      "title": "Gaming Videos", 
      "channels": ["PewDiePie", "Markiplier"],
      "default_start_date": "2024-06-01"
    }
  }
}
```

The system automatically tracks when each playlist was last updated and uses that timestamp (minus 1 day) as the start date for subsequent runs. The `default_start_date` is only used for the first run of each playlist.

### Makefile Commands
```bash
make setup          # Create venv and install dependencies
make update-all      # Update all playlists from config
make run-config PLAYLIST=name  # Update specific playlist
make run ARGS="..."  # Run with arguments (legacy mode)
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
- `json_cache/cache.json` - Video metadata and timestamps
- `json_cache/channels.json` - Channel name to ID mappings
- `token.json` - Authentication tokens

## Error Handling

- **Quota exceeded**: Stops gracefully, shows progress, suggests retry time
- **Network errors**: Retries with backoff
- **Missing channels**: Skips and continues with others
- **Interrupted execution**: Ctrl+C stops safely, progress is saved

## Files Created

- `token.json` - OAuth tokens (auto-generated)
- `json_cache/cache.json` - Video and channel cache
- `json_cache/playlist_timestamps.json` - Per-playlist last update timestamps
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
python g3k-yt-pl.py \
  --playlist-title "Daily Tech" \
  --start-date 2024-01-01 \
  "MKBHD" "Linus Tech Tips" "Unbox Therapy"

# Subsequent runs - only gets new videos since last run
python g3k-yt-pl.py \
  --playlist-title "Daily Tech" \
  "MKBHD" "Linus Tech Tips" "Unbox Therapy"
```

### Monthly Gaming Highlights
```bash
python g3k-yt-pl.py \
  --playlist-title "Gaming Nov 2024" \
  --start-date 2024-11-01 \
  --end-date 2024-11-30 \
  "PewDiePie" "Markiplier" "GameGrumps"
```
