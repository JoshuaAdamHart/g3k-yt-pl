# G3K YouTube Playlist Manager

A Vibe-coded Python project by Joshua Adam Hart  
Final project for Stanford Continuing Studios course: **TECH 152 A Crash Course in Artificial Intelligence**  
Instructor: Ronjon Nag | https://continuingstudies.stanford.edu/

A streamlined Python CLI tool that adds videos from multiple YouTube channels to a playlist with intelligent date filtering, quota tracking, and graceful failure handling.

## The Story Behind This Project

I wanted to view YouTube videos in a way similar to a podcast player, where I could consume all videos from a given channel in publication order without having to queue them up individually. This need arose when I decided to watch all of Numberphile's videos from the beginning.

The YouTube app allowed me to sort videos by publication date, but resuming from where I left off meant scrolling past hundreds of previously-watched videos to find the next one. My workaround was adding ~100 videos at a time to my Watch Later playlist (the least friction in the app UI), then deleting them as I watched. When the list got low, I'd return to the channel, scroll to find where I left off, and manually add another 100 videos one by one. This process didn't allow me to interleave Numberphile2 videos that were being posted contemporaneously, so I just wrote those off as not watchable.

When I caught up with Numberphile and turned my attention to sister channel Computerphile, I decided I did not want to go through THAT again. Since I had just started a pilot program using Amazon Q at my employer, and since I was taking this AI course at Stanford Continuing Studios, I thought this would be a perfect use-case for vibe coding. I have read the code but tried not to hand-edit anything. I started with a simple prompt to write a Python script that uses the prevailing method of communicating with YouTube's API, and iteratively refined it through conversation with AI.

Amazon Q was able to generate a minimal Python script that successfully connected to the YouTube API, and on the first go it provided detailed, but slightly outdated, instructions on how to generate the API key I needed to get it working. It was simple enough to figure out how to fill the gaps with old-fashioned Google searching and before I knew it, I was up and running with a v1. But I quickly hit another snag - during my very first run, the API calls started getting rejected. I looked into it, and discovered that I had already hit my daily API call limit. My first instinct was that Amazon Q had generated code that was making wasteful calls, so I asked it to cache the JSON output, which it did. I couldn't check until the next day (when the quota reset) but I was able to figure out the daily max in the meantime: 10,000 calls. How was this code making 10,000 calls to build a playlist with ~800 videos? I just assumed there was some crazy loop that was wasting API calls by re-fetching data it already had. Since Amazon Q hadn't been caching calls, that seemed plausible as the cause (but still out of control). So I ran the revised script the next day and it ran out of the quota again! Okay, after further prompting Amazon Q told me that some API calls cost more than others and adding a single video to a playlist cost 50 points! So an 800-video playlist would cost 40,000 API points and take 4 days to complete even if no other API calls were made. After more back and forth, I decided this was fine as long as the code could be resumed day after day (after all, I wasn't watching the videos fast enough to ever run out of what could be added with 10,000 points). After a few days I had my perfect Computerphile playlist and I turned my attention to fine-tuning this Python script to allow me to mix-and-match multiple channels by just putting them all in a chronological playlist. And that is where it is now.

**Technical Note**: This project was developed using Amazon Q Developer, an AI assistant built by Amazon Web Services. Amazon Q provided code generation, debugging assistance, and iterative refinement through natural language conversations. The streamlined version presented here represents the culmination of that AI-assisted development process, demonstrating practical applications of conversational programming and AI-powered software development workflows.

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
