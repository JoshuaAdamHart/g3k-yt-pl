# YouTube Playlist Manager

A minimal Python command-line application that authenticates with your Google account and creates YouTube playlists from ALL videos across multiple channels, sorted chronologically (oldest first). **Now with intelligent caching to avoid unnecessary API calls!**

## Setup

### 1. Install Dependencies
```bash
pip install -r requirements.txt
```

### 2. Get YouTube API Credentials

1. Go to the [Google Cloud Console](https://console.cloud.google.com/)
2. Create a new project or select an existing one
3. Enable the YouTube Data API v3:
   - Go to "APIs & Services" > "Library"
   - Search for "YouTube Data API v3"
   - Click on it and press "Enable"
4. Create credentials:
   - Go to "APIs & Services" > "Credentials"
   - Click "Create Credentials" > "OAuth client ID"
   - Choose "Desktop application"
   - Download the JSON file and save it as `credentials.json` in the same directory as the script

### 3. Make the Script Executable (Optional)
```bash
chmod +x youtube_playlist_manager.py
```

## Usage

### Basic Usage
```bash
python youtube_playlist_manager.py --playlist-title "My Playlist" channel1 channel2 channel3
```

### Examples

**Using channel names:**
```bash
python youtube_playlist_manager.py --playlist-title "Tech Videos" "Linus Tech Tips" "MKBHD" "Unbox Therapy"
```

**Using channel URLs:**
```bash
python youtube_playlist_manager.py --playlist-title "Gaming Content" \
  "https://www.youtube.com/@PewDiePie" \
  "https://www.youtube.com/c/Markiplier"
```

**Using channel IDs:**
```bash
python youtube_playlist_manager.py --playlist-title "Educational" \
  "UC2C_jShtL725hvbm1arSV9w" \
  "UCsXVk37bltHxD1rDPwtNM8Q"
```

### Cache Management

**Show cache information:**
```bash
python youtube_playlist_manager.py --show-cache
```

**Clear video metadata cache:**
```bash
python youtube_playlist_manager.py --clear-cache
```

**Clear channel ID cache:**
```bash
python youtube_playlist_manager.py --clear-channel-cache
```

**Repopulate channel cache from video cache:**
```bash
python youtube_playlist_manager.py --repopulate-channel-cache
```

**Force refresh specific channels (ignore cache):**
```bash
python youtube_playlist_manager.py --force-refresh --playlist-title "Fresh Data" "MKBHD" "Linus Tech Tips"
```

**Force creation of new playlist:**
```bash
python youtube_playlist_manager.py --force-new-playlist --playlist-title "Tech Videos" "MKBHD" "Linus Tech Tips"
```

**Custom cache settings:**
```bash
python youtube_playlist_manager.py --cache-hours 336 --cache-file "my_cache.json" --playlist-title "My Playlist" channel1
```

### Command Line Options

- `channels`: One or more YouTube channels (names, URLs, or IDs)
- `--playlist-title, -t`: Title for the new playlist (required for creating playlists)
- `--credentials, -c`: Path to credentials file (default: credentials.json)
- `--cache-file`: Path to video cache file (default: video_cache.json)
- `--cache-hours`: Cache expiry time in hours (default: 168 = 1 week)
- `--clear-cache`: Clear the video metadata cache
- `--clear-channel-cache`: Clear the channel ID cache
- `--repopulate-channel-cache`: Repopulate channel cache from video cache
- `--show-cache`: Show cache information
- `--force-refresh`: Force refresh cache for specified channels
- `--force-new-playlist`: Create new playlist even if one with same name exists

## Features

- **Google OAuth Authentication**: Secure authentication with your Google account
- **Multiple Channel Support**: Add videos from multiple channels at once
- **All Videos**: Fetches ALL videos from each specified channel (no limits)
- **Flexible Channel Input**: Accepts channel names, URLs, or IDs
- **Chronological Sorting**: All videos are sorted by publication date (oldest first)
- **Simple Insertion**: Videos are added to the end of the playlist in publication order
- **Rate Limiting**: Built-in delays to respect YouTube API limits
- **Error Handling**: Graceful handling of missing channels or API errors
- **Progress Tracking**: Shows progress while adding videos
- **🆕 Intelligent Caching**: Caches video metadata to avoid repeated API calls
- **🆕 Cache Management**: Tools to view, clear, and refresh cached data
- **🆕 Enhanced Metadata**: Stores additional video information (descriptions, thumbnails)
- **🆕 Smart Playlist Management**: Uses existing playlists instead of creating duplicates
- **🆕 Duplicate Prevention**: Skips videos already in the target playlist
- **🆕 Quota-Conscious**: Simplified insertion logic to minimize API quota usage

## Caching System

The application now includes an intelligent caching system that:

- **Saves API calls**: Stores video metadata locally to avoid re-fetching the same data
- **Configurable expiry**: Cache expires after 1 week by default (customizable)
- **Automatic refresh**: Expired cache is automatically refreshed when needed
- **Cache persistence**: Data is stored in `video_cache.json` and persists between runs
- **Enhanced metadata**: Caches additional information like descriptions and thumbnails
- **Smart validation**: Only fetches new data when cache is expired or missing
- **🆕 Channel ID caching**: Separate cache for channel IDs to avoid expensive search API calls
- **🆕 Manual editing**: Edit `channel_cache.json` to add channel mappings by hand

### Channel ID Cache

To avoid expensive API search calls (100 quota units each!), the script maintains a separate `channel_cache.json` file that maps channel names/URLs to channel IDs. You can edit this file manually:

```json
{
  "_comment": "This file maps channel names/URLs to channel IDs to avoid expensive API searches.",
  "_instructions": "Add entries like: 'Channel Name': 'UC1234567890abcdef'",
  "MKBHD": "UCBJycsmduvYEL83R_U4JriQ",
  "Linus Tech Tips": "UCXuqSBlHAE6Xw-yeJA0Tunw",
  "https://www.youtube.com/@PewDiePie": "UC-lHJZR3Gqxm24_Vd_AJ5Yw"
}
```

### Cache File Structure
```json
{
  "channels": {
    "UC_channel_id": [
      {
        "video_id": "video123",
        "title": "Video Title",
        "published_at": "2023-01-01T12:00:00Z",
        "channel_title": "Channel Name",
        "channel_id": "UC_channel_id",
        "description": "Video description...",
        "thumbnail_url": "https://..."
      }
    ]
  },
  "last_updated": {
    "UC_channel_id": "2023-01-01T12:00:00.000000"
  }
}
```

## First Run

On the first run, the script will:
1. Open your web browser for Google authentication
2. Ask for permission to manage your YouTube account
3. Save authentication tokens for future use (in `token.json`)
4. Create a cache file (`video_cache.json`) to store video metadata

## Notes

- The created playlist will be private by default
- The script fetches ALL videos from each channel (no video count limits)
- Videos are added to the end of the playlist in chronological order by publish date
- The script respects YouTube API rate limits with built-in delays
- Individual video insertions (50 quota units each) are done sequentially
- If a channel can't be found, it will be skipped with a warning
- The script will continue processing other channels even if one fails
- **Videos are added directly to the end of the playlist** (simplified insertion logic)
- **Duplicate videos are automatically skipped to avoid re-adding existing content**
- **Cached data significantly reduces API usage and improves performance on subsequent runs**
- Cache automatically expires and refreshes to ensure data freshness

## Troubleshooting

**"credentials.json not found"**: Make sure you've downloaded the OAuth credentials from Google Cloud Console

**"Channel not found"**: Try using the full channel URL or channel ID instead of just the name

**Rate limiting errors**: The script includes delays, but if you hit limits, wait a few minutes and try again

**Authentication errors**: Delete `token.json` and re-run to re-authenticate

**Large channels**: For channels with thousands of videos, the process may take several minutes to complete

**Cache issues**: Use `--clear-cache` to reset cached data or `--show-cache` to inspect cache status

**Stale data**: Use `--force-refresh` to ignore cache and fetch fresh data from YouTube API

**Quota exhaustion**: The simplified insertion logic uses fewer API calls, but large operations may still hit daily quotas
