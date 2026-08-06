# G3K YouTube Playlist Manager - AGENTS Configuration

G3K YouTube Playlist Manager (`g3k-yt-pl`) is a personal Python CLI tool that automatically adds videos from multiple YouTube channels to YouTube playlists, with intelligent date filtering, API quota tracking, and graceful failure handling. It was built as a "vibe-coded" final project for Stanford Continuing Studies course TECH 152 (A Crash Course in Artificial Intelligence). Development was started as an experiment with Amazon Q Developer (now Kiro) and has since switched to using Google's Antigravity IDE for ongoing AI-assisted pair programming. The tool solves the problem of consuming YouTube content in chronological publication order — similar to a podcast player — without manually queuing videos.

The project is intentionally minimal: a single Python file (`g3k-yt-pl.py`) with supporting infrastructure files. All logic lives in one place. There is no package structure, no test suite, and no CI/CD pipeline.

## Technology Stack

**Primary Language:** Python 3.13+ — the shebang line `#!/usr/bin/env ./venv/bin/python` requires the project's own venv to be present and uses Python 3.13 features (f-strings, type hints with `Optional`, `List`, `Dict`, `Any` from `typing`).

**Core Runtime Dependencies** (pinned in `requirements.txt`):
- `google-api-python-client==2.108.0` — YouTube Data API v3 client (`googleapiclient.discovery.build`)
- `google-auth-oauthlib==1.1.0` — OAuth 2.0 flow via `InstalledAppFlow`
- `google-auth==2.23.4` — credential management and token refresh
- `pytz==2023.3` — timezone conversion (UTC → US/Pacific for display)
- `requests==2.32.4` — HTTP (transitive dependency, not called directly in application code)

**Build/Environment Toolchain:**
- `.venv/` — primary virtual environment (created by `make setup`, referenced by shebang and all Makefile targets)
- `make` — all standard operations use the `Makefile`; no `pyproject.toml`, `setup.py`, or `setup.cfg`

**External API:**
- YouTube Data API v3 — OAuth 2.0 scope: `https://www.googleapis.com/auth/youtube` (full read/write access to the authenticated user's YouTube account)
- Daily quota: 10,000 units (Google-imposed hard limit, shared across all API usage for the project's GCP project)

## Project Structure

```
g3k-yt-pl/
├── g3k-yt-pl.py              # ONLY source file — ~1000 lines, all application logic
├── requirements.txt           # Pinned dependencies (22 packages including transitive)
├── Makefile                   # All standard operations (setup, run, clean, help)
├── update-all.sh              # Batch runner: calls ./g3k-yt-pl.py directly via shebang
├── README.md                  # User-facing documentation with examples
├── SAGE.md                    # AI assistant configuration (predecessor to this file)
├── .gitignore                 # Excludes venv/, .venv/, json_cache/, credentials.json, token.json
│
├── .venv/                     # Primary Python venv (git-ignored, created by make setup)
│
├── credentials.json           # OAuth 2.0 client secrets — user must download from GCP (git-ignored)
├── token.json                 # Auto-generated OAuth token after first auth (git-ignored)
│
└── json_cache/                # Runtime data directory (auto-created, git-ignored)
    ├── channels.json          # Channel name/URL → channel ID mappings (permanent cache)
    ├── added_videos.json      # Per-playlist sets of video IDs already added (duplicate prevention)
    └── playlist_timestamps.json  # Per-playlist ISO timestamps of last successful run
```

**Critical structural note:** The entire application is in `g3k-yt-pl.py`. When making changes, there is only one file to edit. All classes, helper functions, and `main()` are in this single file.

## Development Workflow

### Common Commands

```bash
# Initial setup — creates venv/ and installs all pinned dependencies
make setup

# Install/reinstall dependencies into existing environment
make install

# ─── PRIMARY USAGE (config mode) ───────────────────────────────────────────

# Update ALL enabled playlists from json_cache/playlists.json
make update-all
# or equivalently:
./update-all.sh

# Update a specific playlist by its config key name
make run-config PLAYLIST=tech
make run-config PLAYLIST=nerds

# Update a specific playlist using a custom config file
make run-config PLAYLIST=tech CONFIG=my-custom-config.json

# ─── LEGACY USAGE (direct CLI arguments) ───────────────────────────────────

# Run with explicit channels and playlist title
make run ARGS='--playlist-title "Tech News" --start-date 2024-01-01 "MKBHD" "Linus Tech Tips"'

# Run with date range
make run ARGS='--playlist-title "Gaming Nov 2024" --start-date 2024-11-01 --end-date 2024-11-30 "PewDiePie"'

# ─── DIRECT PYTHON EXECUTION ───────────────────────────────────────────────

# Must use .venv Python — NOT system python or `python3`
./.venv/bin/python g3k-yt-pl.py --config json_cache/playlists.json --playlist tech
./.venv/bin/python g3k-yt-pl.py --playlist-title "My Playlist" "Channel Name"

# Add a channel to an existing playlist config (modifies json_cache/playlists.json)
./.venv/bin/python g3k-yt-pl.py --add-channel "New Channel Name" --playlist tech

# ─── MAINTENANCE ───────────────────────────────────────────────────────────

# Show all Makefile targets with descriptions
make help

# Remove venv/, json_cache/, and token.json (full reset — credentials.json preserved)
make clean
```

**IMPORTANT:** Never run `python g3k-yt-pl.py` or `python3 g3k-yt-pl.py` directly — the script requires packages installed in `.venv/`. Always use `./.venv/bin/python g3k-yt-pl.py` or `make` commands.

### Three Operating Modes

The `main()` function dispatches to one of three modes based on arguments:

1. **`--add-channel` mode** — Modifies `json_cache/playlists.json` to add a channel to an existing playlist entry. Requires `--playlist`. Does NOT authenticate or call the API.

2. **Legacy mode** — Triggered when both positional `channels` args AND `--playlist-title` are provided. Processes a one-off operation without a config file.

3. **Config mode** (default/recommended) — Reads `json_cache/playlists.json`, processes all enabled playlists (or the one specified with `--playlist`). Uses `json_cache/playlist_timestamps.json` for incremental updates.

### Development Environment Setup

```bash
# Prerequisites: Python 3.13+, make, git
# Verify Python version
python3 --version  # Must be 3.13+

# Clone and set up
git clone <repo-url>
cd g3k-yt-pl
make setup

# Obtain credentials.json from Google Cloud Console:
# 1. Create/select a GCP project at https://console.cloud.google.com/
# 2. Enable "YouTube Data API v3" in APIs & Services > Library
# 3. Create OAuth 2.0 credentials: APIs & Services > Credentials > Create Credentials > OAuth client ID
# 4. Application type: Desktop app
# 5. Download JSON → save as credentials.json in the project root

# First run triggers browser OAuth flow, creates token.json automatically
make run-config PLAYLIST=your_playlist_name
```

**No environment variables are used.** All configuration is via JSON files and CLI arguments. Secrets (`credentials.json`, `token.json`) live in the project root and are git-ignored.

## Code Conventions

### Architecture — Single File, Class-Based

The entire application is organized within `g3k-yt-pl.py` with this structure:

```
signal_handler()          # Global SIGINT handler, sets shutdown_requested flag
QuotaTracker              # Tracks API quota: used, limit(10000), can_afford(), remaining()
G3kYouTubePlaylistManager # Main class — all YouTube API interactions
  __init__()              # Creates json_cache/, initializes all cache files
  authenticate()          # OAuth flow, builds self.youtube API client
  get_channel_id()        # Resolves name/URL/ID/handle → channel ID (with caching)
  get_channel_videos()    # Fetches uploads playlist (with live fetch + date filtering)
  get_video_durations()   # Batch fetches ISO 8601 durations, converts to MM:SS/HH:MM:SS
  _parse_duration()       # Converts PT4M13S → "4:13" format
  get_or_create_playlist()# Finds existing or creates new YouTube playlist
  get_existing_videos()   # Returns set of video IDs already in target playlist
  add_videos_to_playlist()# Adds new videos in chronological order, 0.5s rate limit
  process_channels()      # Orchestrates full workflow for one playlist
load_playlist_config()    # Reads JSON config, exits on error
save_playlist_config()    # Writes JSON config
add_channel_to_playlist() # Modifies config to add a channel
load_playlist_timestamps()# Reads per-playlist last-run timestamps
save_playlist_timestamps()# Writes per-playlist last-run timestamps
main()                    # Argument parsing, mode dispatch, summary output
```

### Channel ID Resolution Logic

The `get_channel_id()` method uses this priority chain (important to understand when debugging channel-not-found issues):

1. **Direct channel ID**: If input starts with `UC` AND is exactly 24 characters → return as-is, no API call
2. **Cache lookup**: Check `json_cache/channels.json` → return cached ID if found
3. **URL with `/channel/` path**: Extract ID from URL directly, cache it, no API call
4. **Handle lookup (`@handle` or `youtube.com/@handle`)**: Calls `youtube.channels().list(forHandle=handle)` costing **1 quota unit**, result cached permanently
5. **Channel name search**: `youtube.search().list()` call costing 100 units, result cached permanently

### Caching Architecture

All cache files are JSON, stored in `json_cache/`, auto-created on first run:

| `channels.json` | channel input string | Permanent | Channel name/URL → ID mapping |
| `added_videos.json` | playlist title (string) | Permanent | Video IDs added to prevent duplicates |
| `playlist_timestamps.json` | playlist config key | Updated on success | Last successful run time per playlist |

**Note on video fetching:** Video metadata caching (`cache.json`) has been eliminated. The script always queries the live YouTube API for uploads since `since_date`. Because API responses return newest videos first, queries stop as soon as a video older than `since_date` is encountered (costing only 1 quota unit for normal incremental runs).

**`added_videos.json` serialization note:** In-memory values are `Dict[str, set]` but JSON cannot serialize sets — they are converted to lists on write and back to sets on read. Do not break this pattern.

### Quota Management Pattern

Every API call follows this pattern — always check `quota.can_afford(cost)` before calling, then `quota.add_cost(cost)` after:

```python
if not self.quota.can_afford(100):
    print(f"⚠️ Not enough quota for channel search: {channel_input}")
    return None
# ... make API call ...
self.quota.add_cost(100)
```

**Quota costs (from actual code):**
- `youtube.search().list()` — 100 units (channel name search)
- `youtube.channels().list(forHandle=...)` — 1 unit (channel handle lookup)
- `youtube.channels().list(id=...)` — 1 unit
- `youtube.playlistItems().list()` — 1 unit per page (50 items/page)
- `youtube.playlists().list()` — 1 unit
- `youtube.playlists().insert()` — 50 units (create playlist)
- `youtube.playlistItems().insert()` — 50 units (add one video)
- `youtube.videos().list()` — 1 unit per batch of 50 (duration lookup)

**Quota exhaustion behavior:** When quota is exceeded during video addition, `process_channels()` returns `(False, added_videos)`. The `False` return value prevents `playlist_timestamps.json` from being updated, so the next run will re-process from the same start date.

### Error Handling Patterns

- All `HttpError` exceptions check for `'quotaExceeded' in str(e)` — this is the consistent pattern throughout
- Cache load failures use bare `except:` (intentional — any failure falls back to empty dict)
- Cache save failures use `except Exception as e:` with a warning print (non-fatal)
- Invalid JSON in config file causes `sys.exit(1)` (fatal)
- Missing `credentials.json` causes `authenticate()` to return `False` (graceful)
- `signal.SIGINT` sets the global `shutdown_requested = True` flag, checked in the video-addition loop

### Output/Logging Style

The tool uses emoji-prefixed `print()` statements throughout — no Python `logging` module. Emoji conventions:
- ✅ Success / authenticated
- ❌ Error / failed
- ⚠️ Warning / quota issue
- 📦 Cache hit
- 📺 Fetching from channel
- 🎯 Target playlist
- 📊 Statistics/counts
- 📅 Date information
- 🎵 Playlist processing
- 🔍 Processing channel
- ➕ Adding videos
- 🎉 Completion
- 💾 Caching new data
- 🛑 Graceful shutdown

All timestamps are displayed in **US/Pacific timezone** using `pytz.timezone('US/Pacific')`, regardless of the system timezone.

### Type Hints

All methods use Python typing annotations: `List[str]`, `Dict[str, Any]`, `Optional[str]`, etc. imported from `typing`. This is for documentation/IDE support only — no runtime type checking.

## Testing Strategy

**There is no automated test suite.** This is an intentional characteristic of the project (AI-assisted rapid prototyping / "vibe coding").

**Manual testing approach:**
- Test against real YouTube API with a personal Google account
- Use playlists with small channel sets to minimize quota consumption during testing
- Test quota exhaustion by using channels with many videos
- Test cache behavior by deleting specific cache files and re-running
- Test authentication by deleting `token.json` and re-running

**Quota-conscious testing tips:**
- Channel IDs (starting with `UC`, 24 chars) are free — use them instead of channel names
- The `--end-date` flag limits video fetching to a small date range
- `json_cache/channels.json` caches channel lookups permanently — populate it first
- A single test run adding 1 video costs ~53 quota units (1 playlist lookup + 1 existing videos check + 1 video add)

## Important Notes

### Authentication Requirements

- `credentials.json` must exist in the project root before first run — download from Google Cloud Console as an OAuth 2.0 "Desktop app" credential
- First run opens a browser window for Google account authorization
- `token.json` is auto-created after successful authorization and refreshed automatically
- The OAuth scope `https://www.googleapis.com/auth/youtube` grants full YouTube account access — this is required to create playlists and add videos
- To re-authenticate: delete `token.json` and run again

### `json_cache/playlists.json` Configuration Format

This file must be created manually before using config mode. Full schema:

```json
{
  "playlists": {
    "config_key": {
      "title": "YouTube Playlist Display Name",
      "channels": [
        "Channel Name",
        "https://www.youtube.com/@handle",
        "https://www.youtube.com/channel/UCxxxxxxxxxxxxxxxxxxxxxxxx",
        "UCxxxxxxxxxxxxxxxxxxxxxxxx"
      ],
      "default_start_date": "2024-01-01",
      "disabled": false
    }
  }
}
```

- `config_key` — used with `--playlist config_key` to target this playlist specifically
- `title` — must exactly match the YouTube playlist title (used for lookup and duplicate tracking)
- `channels` — list of channels in any supported format (mixed formats OK)
- `default_start_date` — only used on the very first run; subsequent runs use `playlist_timestamps.json`
- `disabled` — when `true`, skipped during `make update-all` but still runs with `--playlist config_key`

**Fallback default:** If no `default_start_date` is in the config AND no timestamp exists, the code defaults to `'2025-08-01'` (hardcoded in `main()`).

### Incremental Update Logic

When running in config mode without `--start-date`:
1. Check `json_cache/playlist_timestamps.json` for the playlist's last successful run time
2. If found: use `(last_update - 24 hours)` as the start date (to catch any videos that might have been missed)
3. If not found: use `default_start_date` from `playlists.json`
4. Timestamps are only saved if the run completes successfully (no quota exhaustion)

### Common Gotchas and Troubleshooting

| Problem | Cause | Fix |
|---------|-------|-----|
| `credentials.json not found` | File not downloaded | Download from Google Cloud Console → APIs & Services → Credentials |
| `Channel not found` | Name search failed or handle URL used | Use `/channel/UCxxx` URL or bare channel ID (`UCxxx...`) |
| `Not enough quota for channel search` | Quota nearly exhausted | Run tomorrow; pre-populate `channels.json` with known IDs |
| `Quota exceeded` | Hit 10,000 unit daily limit | Wait until midnight Pacific; tool will resume from last timestamp |
| Authentication errors | `token.json` expired/corrupted | Delete `token.json`, re-run to trigger fresh OAuth flow |
| Import errors on run | `venv/` not set up | Run `make setup` |
| Duplicate videos not prevented | `added_videos.json` corrupted | Delete `json_cache/added_videos.json` (will re-check against live playlist) |
| Wrong start date used | Timestamp file has stale entry | Delete the key from `json_cache/playlist_timestamps.json` or use `--start-date` |
| `./g3k-yt-pl.py: Permission denied` | Shebang script not executable | Run `chmod +x g3k-yt-pl.py` |

### Performance Characteristics

- **Channel search** (name/handle): 100 quota units, cached permanently after first lookup
- **Video fetching**: 1 unit per 50 videos; live fetch with early-stop when videos older than `since_date` are encountered (typically 1 unit per channel for incremental updates)
- **Video addition**: 50 units each + 0.5s sleep = ~100 videos/day maximum within quota
- **Large backlogs**: An 800-video backlog requires 40,000 quota units = 4 days of processing
- **Batch processing**: `get_video_durations()` fetches durations in batches of 50 (API maximum) for the end-of-run summary

### Virtual Environment

The project uses `.venv/` as its virtual environment. The Makefile, shebang line, and `update-all.sh` all use `.venv/`. Always use `.venv/` for this project — never a bare `venv/` or system Python.

### Files Never to Commit

`.gitignore` excludes: `.venv/`, `venv/`, `env/`, `json_cache/`, `token.json`, `credentials.json`, `__pycache__/`, `*.pyc`, `.DS_Store`, `.vscode/`, `.idea/`

Never add these to git — `credentials.json` and `token.json` contain sensitive OAuth secrets.

### No Linting or Formatting Configuration

There is no `pyproject.toml`, `.flake8`, `.pylintrc`, `mypy.ini`, or `black` configuration. No code quality tools are enforced. When modifying code, follow the existing style: 4-space indentation, f-strings for formatting, type hints on all method signatures, emoji-prefixed `print()` for user output.