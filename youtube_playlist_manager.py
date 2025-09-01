#!/usr/bin/env python3
"""
YouTube Playlist Manager
A minimal CLI tool to authenticate with YouTube and add videos from channels to a playlist.
"""

import os
import sys
import json
import argparse
import signal
from datetime import datetime, timedelta
from typing import List, Dict, Any

try:
    from google.auth.transport.requests import Request
    from google.oauth2.credentials import Credentials
    from google_auth_oauthlib.flow import InstalledAppFlow
    from googleapiclient.discovery import build
    from googleapiclient.errors import HttpError
except ImportError:
    print("Required packages not installed. Please run:")
    print("pip install google-auth google-auth-oauthlib google-auth-httplib2 google-api-python-client")
    sys.exit(1)

# YouTube API scopes
SCOPES = ['https://www.googleapis.com/auth/youtube']

# Global variable to track graceful shutdown
shutdown_requested = False

def signal_handler(signum, frame):
    """Handle Ctrl+C gracefully"""
    global shutdown_requested
    print(f"\n\n🛑 Received interrupt signal (Ctrl+C)")
    print("📝 Gracefully shutting down...")
    print("💾 Any progress made so far has been saved.")
    shutdown_requested = True

class YouTubePlaylistManager:
    def __init__(self, credentials_file: str = 'credentials.json', cache_file: str = 'video_cache.json', cache_hours: int = 168):  # 1 week = 168 hours
        self.credentials_file = credentials_file
        self.token_file = 'token.json'
        self.cache_file = cache_file
        self.channel_cache_file = 'channel_cache.json'
        self.cache_hours = cache_hours
        self.youtube = None
        self.cache = self._load_cache()
        self.channel_cache = self._load_channel_cache()
        
    def _load_cache(self) -> Dict[str, Any]:
        """Load video metadata cache from JSON file"""
        if os.path.exists(self.cache_file):
            try:
                with open(self.cache_file, 'r', encoding='utf-8') as f:
                    cache_data = json.load(f)
                    print(f"Loaded video cache with {len(cache_data.get('channels', {}))} channels")
                    return cache_data
            except (json.JSONDecodeError, IOError) as e:
                print(f"Warning: Could not load cache file {self.cache_file}: {e}")
        
        return {'channels': {}, 'last_updated': {}}
    
    def _load_channel_cache(self) -> Dict[str, str]:
        """Load channel ID cache from JSON file"""
        if os.path.exists(self.channel_cache_file):
            try:
                with open(self.channel_cache_file, 'r', encoding='utf-8') as f:
                    channel_data = json.load(f)
                    # Filter out comment/instruction keys
                    filtered_data = {k: v for k, v in channel_data.items() if not k.startswith('_')}
                    print(f"Loaded channel cache with {len(filtered_data)} channel mappings")
                    return filtered_data
            except (json.JSONDecodeError, IOError) as e:
                print(f"Warning: Could not load channel cache file {self.channel_cache_file}: {e}")
        
        # Create initial channel cache file with examples and prepopulate from video cache
        initial_cache = {
            "_comment": "This file maps channel names/URLs to channel IDs to avoid expensive API searches.",
            "_instructions": "Add entries like: 'Channel Name': 'UC1234567890abcdef', or 'https://youtube.com/@username': 'UC1234567890abcdef'",
            "_examples": {
                "MKBHD": "UCBJycsmduvYEL83R_U4JriQ",
                "Linus Tech Tips": "UCXuqSBlHAE6Xw-yeJA0Tunw",
                "https://www.youtube.com/@PewDiePie": "UC-lHJZR3Gqxm24_Vd_AJ5Yw"
            }
        }
        
        # Prepopulate with channel data from video cache
        prepopulated_channels = self._prepopulate_from_video_cache()
        initial_cache.update(prepopulated_channels)
        
        try:
            with open(self.channel_cache_file, 'w', encoding='utf-8') as f:
                json.dump(initial_cache, f, indent=2, ensure_ascii=False)
            if prepopulated_channels:
                print(f"Created channel cache file: {self.channel_cache_file}")
                print(f"Prepopulated with {len(prepopulated_channels)} channels from video cache")
            else:
                print(f"Created channel cache file: {self.channel_cache_file}")
            print("You can edit this file to add more channel ID mappings and avoid API search calls")
        except IOError as e:
            print(f"Warning: Could not create channel cache file: {e}")
        
        return prepopulated_channels
    
    def _prepopulate_from_video_cache(self) -> Dict[str, str]:
        """Extract channel names and IDs from existing video cache"""
        prepopulated = {}
        
        if not self.cache or 'channels' not in self.cache:
            return prepopulated
        
        for channel_id, videos in self.cache['channels'].items():
            if videos and len(videos) > 0:
                # Get channel title from the first video
                channel_title = videos[0].get('channel_title', '')
                if channel_title:
                    prepopulated[channel_title] = channel_id
        
        if prepopulated:
            print(f"Found {len(prepopulated)} channels in video cache to prepopulate:")
            for title, channel_id in prepopulated.items():
                print(f"  '{title}' -> {channel_id}")
        
        return prepopulated
    
    def _save_channel_cache(self):
        """Save channel ID cache to JSON file"""
        # Preserve comments and instructions when saving
        save_data = {}
        if os.path.exists(self.channel_cache_file):
            try:
                with open(self.channel_cache_file, 'r', encoding='utf-8') as f:
                    existing_data = json.load(f)
                    # Keep comment/instruction keys
                    save_data = {k: v for k, v in existing_data.items() if k.startswith('_')}
            except:
                pass
        
        # Add current channel mappings
        save_data.update(self.channel_cache)
        
        try:
            with open(self.channel_cache_file, 'w', encoding='utf-8') as f:
                json.dump(save_data, f, indent=2, ensure_ascii=False)
        except IOError as e:
            print(f"Warning: Could not save channel cache file {self.channel_cache_file}: {e}")
    
    def _save_cache(self):
        """Save video metadata cache to JSON file"""
        try:
            with open(self.cache_file, 'w', encoding='utf-8') as f:
                json.dump(self.cache, f, indent=2, ensure_ascii=False)
            print(f"Video cache saved to {self.cache_file}")
        except IOError as e:
            print(f"Warning: Could not save cache file {self.cache_file}: {e}")
    
    def _is_cache_valid(self, channel_id: str) -> bool:
        """Check if cached data for a channel is still valid"""
        if channel_id not in self.cache['last_updated']:
            return False
        
        last_updated = datetime.fromisoformat(self.cache['last_updated'][channel_id])
        cache_expiry = last_updated + timedelta(hours=self.cache_hours)
        
        is_valid = datetime.now() < cache_expiry
        if is_valid:
            print(f"Using cached data for channel {channel_id} (cached {last_updated.strftime('%Y-%m-%d %H:%M:%S')})")
        else:
            print(f"Cache expired for channel {channel_id} (cached {last_updated.strftime('%Y-%m-%d %H:%M:%S')})")
        
        return is_valid
    
    def _cache_channel_videos(self, channel_id: str, videos: List[Dict[str, Any]]):
        """Cache video metadata for a channel"""
        self.cache['channels'][channel_id] = videos
        self.cache['last_updated'][channel_id] = datetime.now().isoformat()
        self._save_cache()
    
    def _get_cached_videos(self, channel_id: str) -> List[Dict[str, Any]]:
        """Get cached videos for a channel"""
        return self.cache['channels'].get(channel_id, [])
        
    def authenticate(self):
        """Authenticate with Google/YouTube API"""
        creds = None
        
        # Load existing token
        if os.path.exists(self.token_file):
            creds = Credentials.from_authorized_user_file(self.token_file, SCOPES)
        
        # If no valid credentials, get new ones
        if not creds or not creds.valid:
            if creds and creds.expired and creds.refresh_token:
                creds.refresh(Request())
            else:
                if not os.path.exists(self.credentials_file):
                    print(f"Error: {self.credentials_file} not found!")
                    print("Please download your OAuth 2.0 credentials from Google Cloud Console")
                    print("and save them as 'credentials.json' in the current directory.")
                    return False
                
                flow = InstalledAppFlow.from_client_secrets_file(
                    self.credentials_file, SCOPES)
                creds = flow.run_local_server(port=0)
            
            # Save credentials for next run
            with open(self.token_file, 'w') as token:
                token.write(creds.to_json())
        
        self.youtube = build('youtube', 'v3', credentials=creds)
        print("Successfully authenticated with YouTube API")
        return True
    
    def get_channel_id(self, channel_input: str) -> str:
        """Get channel ID from channel name or URL (with caching)"""
        try:
            # If it's already a channel ID
            if channel_input.startswith('UC') and len(channel_input) == 24:
                return channel_input
            
            # Check channel cache first
            if channel_input in self.channel_cache:
                cached_id = self.channel_cache[channel_input]
                print(f"Using cached channel ID for '{channel_input}': {cached_id}")
                return cached_id
            
            print(f"Channel ID not cached, searching via API: {channel_input}")
            
            # If it's a channel URL
            if 'youtube.com' in channel_input:
                if '/channel/' in channel_input:
                    channel_id = channel_input.split('/channel/')[-1].split('/')[0]
                    # Cache the result
                    self.channel_cache[channel_input] = channel_id
                    self._save_channel_cache()
                    return channel_id
                elif '/c/' in channel_input or '/@' in channel_input:
                    # Handle custom URLs - need to search (expensive!)
                    username = channel_input.split('/')[-1].replace('@', '')
                    response = self.youtube.search().list(
                        part='snippet',
                        q=username,
                        type='channel',
                        maxResults=1
                    ).execute()
                    
                    if response['items']:
                        channel_id = response['items'][0]['snippet']['channelId']
                        # Cache the result
                        self.channel_cache[channel_input] = channel_id
                        self._save_channel_cache()
                        print(f"Found and cached channel ID: {channel_id}")
                        return channel_id
            
            # Search by channel name (expensive!)
            print(f"WARNING: Using expensive search API for channel: {channel_input}")
            print(f"Consider adding this to {self.channel_cache_file} to avoid future API calls")
            
            response = self.youtube.search().list(
                part='snippet',
                q=channel_input,
                type='channel',
                maxResults=1
            ).execute()
            
            if response['items']:
                channel_id = response['items'][0]['snippet']['channelId']
                # Cache the result
                self.channel_cache[channel_input] = channel_id
                self._save_channel_cache()
                print(f"Found and cached channel ID: {channel_id}")
                return channel_id
            
            raise ValueError(f"Channel not found: {channel_input}")
            
        except Exception as e:
            print(f"Error finding channel {channel_input}: {e}")
            return None
    
    def get_channel_videos(self, channel_id: str) -> List[Dict[str, Any]]:
        """Get all videos from a channel (with caching)"""
        # Check if we have valid cached data
        if self._is_cache_valid(channel_id):
            cached_videos = self._get_cached_videos(channel_id)
            if cached_videos:
                print(f"Using {len(cached_videos)} cached videos")
                return cached_videos
        
        print(f"Fetching fresh data from YouTube API for channel {channel_id}")
        videos = []
        
        try:
            # Get uploads playlist ID
            channel_response = self.youtube.channels().list(
                part='contentDetails,snippet',
                id=channel_id
            ).execute()
            
            if not channel_response['items']:
                print(f"Channel not found: {channel_id}")
                return videos
            
            channel_info = channel_response['items'][0]
            channel_title = channel_info['snippet']['title']
            uploads_playlist_id = channel_info['contentDetails']['relatedPlaylists']['uploads']
            
            print(f"Fetching videos from: {channel_title}")
            
            # Get ALL videos from uploads playlist
            next_page_token = None
            page_count = 0
            video_ids_batch = []
            
            while True:
                page_count += 1
                print(f"  Fetching page {page_count}...")
                
                try:
                    playlist_response = self.youtube.playlistItems().list(
                        part='snippet',
                        playlistId=uploads_playlist_id,
                        maxResults=50,
                        pageToken=next_page_token
                    ).execute()
                except HttpError as e:
                    error_details = e.error_details[0] if e.error_details else {}
                    error_reason = error_details.get('reason', 'unknown')
                    
                    if error_reason == 'quotaExceeded':
                        print(f"\n⚠️  YouTube API quota exceeded while fetching channel videos!")
                        print("Returning videos fetched so far. Try again tomorrow for complete data.")
                        break
                    else:
                        raise e
                
                # Collect video IDs and basic info from playlist
                page_video_data = []
                for item in playlist_response['items']:
                    video_id = item['snippet']['resourceId']['videoId']
                    video_ids_batch.append(video_id)
                    
                    # Store basic info (we'll get the real published_at later)
                    video_data = {
                        'video_id': video_id,
                        'title': item['snippet']['title'],
                        'published_at': item['snippet']['publishedAt'],  # This will be overwritten
                        'channel_title': item['snippet']['channelTitle'],
                        'channel_id': channel_id,
                        'description': item['snippet'].get('description', '')[:200] + '...' if item['snippet'].get('description', '') else '',
                        'thumbnail_url': item['snippet']['thumbnails'].get('medium', {}).get('url', '')
                    }
                    page_video_data.append(video_data)
                
                # Get actual publication dates for this batch of videos
                if video_ids_batch:
                    try:
                        # Fetch actual video details to get real publication dates
                        videos_response = self.youtube.videos().list(
                            part='snippet',
                            id=','.join(video_ids_batch[-len(page_video_data):])  # Last batch of IDs
                        ).execute()
                        
                        # Create a mapping of video_id to actual published_at
                        actual_dates = {}
                        for video_item in videos_response['items']:
                            actual_dates[video_item['id']] = video_item['snippet']['publishedAt']
                        
                        # Update the video data with actual publication dates
                        for video_data in page_video_data:
                            if video_data['video_id'] in actual_dates:
                                video_data['published_at'] = actual_dates[video_data['video_id']]
                        
                    except HttpError as e:
                        error_details = e.error_details[0] if e.error_details else {}
                        error_reason = error_details.get('reason', 'unknown')
                        
                        if error_reason == 'quotaExceeded':
                            print(f"\n⚠️  YouTube API quota exceeded while fetching video details!")
                            print("Using playlist dates instead of actual publication dates.")
                        else:
                            print(f"Warning: Could not fetch actual publication dates: {error_reason}")
                
                videos.extend(page_video_data)
                
                next_page_token = playlist_response.get('nextPageToken')
                if not next_page_token:
                    break
            
            print(f"Found {len(videos)} videos from {channel_title}")
            
            # Cache the results (even if incomplete due to quota)
            self._cache_channel_videos(channel_id, videos)
            
        except HttpError as e:
            error_details = e.error_details[0] if e.error_details else {}
            error_reason = error_details.get('reason', 'unknown')
            
            if error_reason == 'quotaExceeded':
                print(f"\n⚠️  YouTube API quota exceeded while fetching channel {channel_id}!")
                print("Try again tomorrow or use cached data if available.")
            else:
                print(f"Error fetching videos from channel {channel_id}: {e}")
        
        return videos
    
    def find_existing_playlist(self, title: str) -> str:
        """Find an existing playlist by title"""
        try:
            # Get all playlists for the authenticated user
            playlists_response = self.youtube.playlists().list(
                part='snippet',
                mine=True,
                maxResults=50
            ).execute()
            
            # Search through all pages of playlists
            while True:
                for playlist in playlists_response['items']:
                    if playlist['snippet']['title'] == title:
                        playlist_id = playlist['id']
                        print(f"Found existing playlist: '{title}' (ID: {playlist_id})")
                        return playlist_id
                
                # Check if there are more pages
                next_page_token = playlists_response.get('nextPageToken')
                if not next_page_token:
                    break
                
                playlists_response = self.youtube.playlists().list(
                    part='snippet',
                    mine=True,
                    maxResults=50,
                    pageToken=next_page_token
                ).execute()
            
            print(f"No existing playlist found with title: '{title}'")
            return None
            
        except HttpError as e:
            print(f"Error searching for existing playlist: {e}")
            return None
    
    def get_playlist_video_count(self, playlist_id: str) -> int:
        """Get the current number of videos in a playlist"""
        try:
            playlist_response = self.youtube.playlists().list(
                part='contentDetails',
                id=playlist_id
            ).execute()
            
            if playlist_response['items']:
                return playlist_response['items'][0]['contentDetails']['itemCount']
            return 0
            
        except HttpError as e:
            print(f"Error getting playlist video count: {e}")
            return 0
    
    def get_existing_playlist_videos_with_dates(self, playlist_id: str) -> List[Dict[str, Any]]:
        """Get existing playlist videos with their publish dates"""
        existing_videos = []
        
        try:
            next_page_token = None
            
            while True:
                playlist_items_response = self.youtube.playlistItems().list(
                    part='snippet',
                    playlistId=playlist_id,
                    maxResults=50,
                    pageToken=next_page_token
                ).execute()
                
                for item in playlist_items_response['items']:
                    video_data = {
                        'video_id': item['snippet']['resourceId']['videoId'],
                        'title': item['snippet']['title'],
                        'published_at': item['snippet']['publishedAt']
                    }
                    existing_videos.append(video_data)
                
                next_page_token = playlist_items_response.get('nextPageToken')
                if not next_page_token:
                    break
            
            print(f"Found {len(existing_videos)} existing videos in playlist")
            
        except HttpError as e:
            print(f"Error getting existing playlist videos with dates: {e}")
        
        return existing_videos

    def get_existing_playlist_videos(self, playlist_id: str) -> set:
        """Get existing playlist video IDs to avoid duplicates"""
        existing_video_ids = set()
        
        try:
            next_page_token = None
            
            while True:
                playlist_items_response = self.youtube.playlistItems().list(
                    part='snippet',
                    playlistId=playlist_id,
                    maxResults=50,
                    pageToken=next_page_token
                ).execute()
                
                for item in playlist_items_response['items']:
                    existing_video_ids.add(item['snippet']['resourceId']['videoId'])
                
                next_page_token = playlist_items_response.get('nextPageToken')
                if not next_page_token:
                    break
            
            print(f"Found {len(existing_video_ids)} existing videos in playlist")
            
        except HttpError as e:
            print(f"Error getting existing playlist videos: {e}")
        
        return existing_video_ids
    
    def get_watch_later_videos(self) -> set:
        """Get video IDs from Watch Later playlist"""
        watch_later_ids = set()
        
        try:
            # Get the user's playlists to find Watch Later
            channels_response = self.youtube.channels().list(
                part='contentDetails',
                mine=True
            ).execute()
            
            if not channels_response['items']:
                print("Could not access user's playlists")
                return watch_later_ids
            
            watch_later_playlist_id = channels_response['items'][0]['contentDetails']['relatedPlaylists'].get('watchLater')
            
            if not watch_later_playlist_id:
                print("Watch Later playlist not found")
                return watch_later_ids
            
            next_page_token = None
            
            while True:
                playlist_items_response = self.youtube.playlistItems().list(
                    part='snippet',
                    playlistId=watch_later_playlist_id,
                    maxResults=50,
                    pageToken=next_page_token
                ).execute()
                
                for item in playlist_items_response['items']:
                    watch_later_ids.add(item['snippet']['resourceId']['videoId'])
                
                next_page_token = playlist_items_response.get('nextPageToken')
                if not next_page_token:
                    break
            
            print(f"Found {len(watch_later_ids)} videos in Watch Later playlist")
            
        except HttpError as e:
            print(f"Error getting Watch Later videos: {e}")
        
        return watch_later_ids
    
    def get_liked_videos(self) -> set:
        """Get video IDs from Liked Videos playlist"""
        liked_video_ids = set()
        
        try:
            # Get the user's playlists to find Liked Videos
            channels_response = self.youtube.channels().list(
                part='contentDetails',
                mine=True
            ).execute()
            
            if not channels_response['items']:
                print("Could not access user's playlists")
                return liked_video_ids
            
            liked_playlist_id = channels_response['items'][0]['contentDetails']['relatedPlaylists'].get('likes')
            
            if not liked_playlist_id:
                print("Liked Videos playlist not found")
                return liked_video_ids
            
            next_page_token = None
            
            while True:
                playlist_items_response = self.youtube.playlistItems().list(
                    part='snippet',
                    playlistId=liked_playlist_id,
                    maxResults=50,
                    pageToken=next_page_token
                ).execute()
                
                for item in playlist_items_response['items']:
                    liked_video_ids.add(item['snippet']['resourceId']['videoId'])
                
                next_page_token = playlist_items_response.get('nextPageToken')
                if not next_page_token:
                    break
            
            print(f"Found {len(liked_video_ids)} liked videos")
            
        except HttpError as e:
            print(f"Error getting liked videos: {e}")
        
        return liked_video_ids
    def create_playlist(self, title: str, description: str = "") -> str:
        """Create a new playlist"""
        try:
            playlist_response = self.youtube.playlists().insert(
                part='snippet,status',
                body={
                    'snippet': {
                        'title': title,
                        'description': description
                    },
                    'status': {
                        'privacyStatus': 'private'
                    }
                }
            ).execute()
            
            playlist_id = playlist_response['id']
            print(f"Created new playlist: '{title}' (ID: {playlist_id})")
            return playlist_id
            
        except HttpError as e:
            print(f"Error creating playlist: {e}")
            return None
    
    def get_or_create_playlist(self, title: str, description: str = "", force_new: bool = False) -> str:
        """Get existing playlist by title or create a new one"""
        if not force_new:
            # First, try to find an existing playlist
            playlist_id = self.find_existing_playlist(title)
            
            if playlist_id:
                # Show current video count
                current_count = self.get_playlist_video_count(playlist_id)
                print(f"Playlist currently has {current_count} videos")
                return playlist_id
        
        # Create a new playlist if none exists or force_new is True
        if force_new:
            print("Creating new playlist (--force-new-playlist specified)")
        return self.create_playlist(title, description)
    
    def add_video_to_playlist(self, playlist_id: str, video_id: str) -> tuple[bool, bool]:
        """Add a single video to the end of a playlist
        
        Returns:
            tuple: (success, quota_exceeded)
                - success: True if video was added successfully
                - quota_exceeded: True if quota was exceeded
        """
        try:
            self.youtube.playlistItems().insert(
                part='snippet',
                body={
                    'snippet': {
                        'playlistId': playlist_id,
                        'resourceId': {
                            'kind': 'youtube#video',
                            'videoId': video_id
                        }
                    }
                }
            ).execute()
            return True, False
            
        except HttpError as e:
            error_details = e.error_details[0] if e.error_details else {}
            error_reason = error_details.get('reason', 'unknown')
            
            # Check for quota exceeded error
            if error_reason == 'quotaExceeded':
                print(f"\n⚠️  YouTube API quota exceeded! Stopping video additions.")
                print("You've hit your daily API limit. Try again tomorrow or use a different API key.")
                return False, True
            
            # Other errors - don't print for common expected errors
            if error_reason not in ['videoNotFound', 'forbidden', 'playlistItemsNotAccessible', 'videoNotPlayable']:
                print(f"Error adding video {video_id}: {error_reason}")
            return False, False
            
        except Exception as e:
            print(f"Unexpected error adding video {video_id}: {e}")
            return False, False
    
    def add_videos_to_playlist_batch(self, playlist_id: str, videos: List[Dict[str, Any]], skip_watched: bool = False, use_playlist_watermark: bool = False, min_date: str = None) -> int:
        """Add multiple videos to the end of a playlist with rate limiting and error handling"""
        import time
        from datetime import datetime
        global shutdown_requested
        
        # Get existing playlist videos to avoid duplicates
        existing_video_ids = self.get_existing_playlist_videos(playlist_id)
        
        # Determine the cutoff date - either from min_date or playlist watermark
        cutoff_date = None
        cutoff_source = None
        
        if min_date:
            # Use the specified minimum date (overrides watermark)
            cutoff_date = min_date
            cutoff_source = "specified minimum date"
            print(f"Using specified minimum date: {min_date[:10]}")
            print(f"Only videos published after {min_date[:10]} will be added")
            
        elif use_playlist_watermark:
            # Use playlist watermark logic
            existing_videos_with_dates = self.get_existing_playlist_videos_with_dates(playlist_id)
            if existing_videos_with_dates:
                # Find the OLDEST video still in the playlist - this is our watermark
                oldest_video = min(existing_videos_with_dates, key=lambda x: x['published_at'])
                newest_video = max(existing_videos_with_dates, key=lambda x: x['published_at'])
                cutoff_date = oldest_video['published_at']
                cutoff_source = "playlist watermark (oldest video)"
                
                print(f"Using playlist watermark: will skip videos older than the OLDEST video currently in playlist")
                print(f"Playlist date range: {oldest_video['published_at'][:10]} to {newest_video['published_at'][:10]}")
                print(f"Watermark (oldest video): '{oldest_video['title']}' ({oldest_video['published_at'][:10]})")
                print(f"Only videos newer than {oldest_video['published_at'][:10]} will be added")
        
        # Optionally get watched videos to skip
        watched_video_ids = set()
        if skip_watched:
            print("Checking for watched videos...")
            # Try to get Watch Later and Liked videos as proxies for "watched"
            watch_later_ids = self.get_watch_later_videos()
            liked_ids = self.get_liked_videos()
            watched_video_ids = watch_later_ids.union(liked_ids)
            
            if watched_video_ids:
                print(f"Will skip {len(watched_video_ids)} videos from Watch Later and Liked Videos")
        
        # Filter out videos that are already in the playlist, watched, or older than cutoff date
        videos_to_add = []
        date_skipped = 0
        
        for video in videos:
            if video['video_id'] in existing_video_ids:
                continue  # Skip duplicates
            if skip_watched and video['video_id'] in watched_video_ids:
                continue  # Skip watched videos
            
            # Check cutoff date - skip videos older than or equal to the cutoff
            if cutoff_date:
                video_date = video['published_at']
                
                # Handle both 'Z' and '+00:00' timezone formats for comparison
                video_date_clean = video_date.replace('Z', '+00:00')
                cutoff_date_clean = cutoff_date.replace('Z', '+00:00')
                
                try:
                    video_datetime = datetime.fromisoformat(video_date_clean)
                    cutoff_datetime = datetime.fromisoformat(cutoff_date_clean)
                except ValueError:
                    # Fallback for older Python versions
                    video_datetime = datetime.strptime(video_date.replace('Z', ''), '%Y-%m-%dT%H:%M:%S')
                    cutoff_datetime = datetime.strptime(cutoff_date.replace('Z', ''), '%Y-%m-%dT%H:%M:%S')
                
                if video_datetime <= cutoff_datetime:
                    date_skipped += 1
                    continue  # Skip videos older than or equal to the cutoff date
            
            videos_to_add.append(video)
        
        if not videos_to_add:
            message = "All videos are already in the playlist"
            if cutoff_date and date_skipped > 0:
                message += f" or older than the {cutoff_source} ({date_skipped} older videos skipped)"
            if skip_watched:
                message += " or have been watched"
            message += " - nothing to add!"
            print(message)
            return 0
        
        # Sort videos by publication date (oldest first) for better organization
        videos_to_add.sort(key=lambda x: x['published_at'])
        
        skipped_count = len(videos) - len(videos_to_add)
        message = f"Found {len(videos_to_add)} new videos to add (skipping {skipped_count} total: duplicates"
        if cutoff_date and date_skipped > 0:
            message += f", {date_skipped} older than {cutoff_source}"
        if skip_watched:
            message += ", watched videos"
        message += ")"
        print(message)
        
        success_count = 0
        failed_videos = []
        quota_exceeded = False
        interrupted = False
        
        print(f"Adding {len(videos_to_add)} videos to playlist...")
        print("💡 Press Ctrl+C to stop gracefully at any time")
        
        # Add videos one by one with proper error handling and rate limiting
        for i, video in enumerate(videos_to_add, 1):
            # Check for graceful shutdown request
            if shutdown_requested:
                interrupted = True
                print(f"\n⏸️  Interrupted by user after adding {success_count} videos.")
                print(f"Stopped at video {i} of {len(videos_to_add)}: '{video['title']}'")
                break
            
            video_id = video['video_id']
            
            success, quota_hit = self.add_video_to_playlist(playlist_id, video_id)
            
            if quota_hit:
                quota_exceeded = True
                print(f"\n🛑 Quota exceeded after adding {success_count} videos.")
                print(f"Stopped at video {i} of {len(videos_to_add)}: '{video['title']}'")
                break
            
            if success:
                success_count += 1
                print(f"  Added '{video['title']}' ({video['published_at'][:10]})")
            else:
                failed_videos.append(video_id)
            
            # Show progress every 25 videos or at the end
            if i % 25 == 0 or i == len(videos_to_add):
                print(f"  Progress: {i}/{len(videos_to_add)} videos processed ({success_count} successful)")
            
            # Rate limiting: delay between requests to avoid quota exhaustion
            if i % 10 == 0:
                time.sleep(1)  # Longer pause every 10 videos
            else:
                time.sleep(0.2)  # Short pause between each video
        
        # Summary of results
        if interrupted:
            remaining_videos = len(videos_to_add) - i + 1
            print(f"\n📊 Summary (Interrupted):")
            print(f"  ✅ Successfully added: {success_count} videos")
            print(f"  ⏸️  Remaining (interrupted): {remaining_videos} videos")
            print(f"  ❌ Failed (other errors): {len(failed_videos)} videos")
            print(f"\n💡 Tip: Run the script again to continue adding the remaining {remaining_videos} videos!")
        elif quota_exceeded:
            remaining_videos = len(videos_to_add) - i
            print(f"\n📊 Summary:")
            print(f"  ✅ Successfully added: {success_count} videos")
            print(f"  ⏸️  Remaining due to quota: {remaining_videos} videos")
            print(f"  ❌ Failed (other errors): {len(failed_videos)} videos")
            print(f"\n💡 Tip: Run the script again tomorrow to add the remaining {remaining_videos} videos!")
        elif failed_videos:
            print(f"\nFailed to add {len(failed_videos)} videos (may be private, deleted, or restricted)")
        
        return success_count
    
    def process_channels(self, channel_list: List[str], playlist_title: str, force_new_playlist: bool = False, skip_watched: bool = False, use_playlist_watermark: bool = False, min_date: str = None):
        """Main function to process channels and create playlist"""
        if not self.authenticate():
            return
        
        all_videos = []
        
        # Collect videos from all channels
        for channel_input in channel_list:
            print(f"\nProcessing channel: {channel_input}")
            channel_id = self.get_channel_id(channel_input)
            
            if not channel_id:
                print(f"Skipping {channel_input} - could not find channel")
                continue
            
            videos = self.get_channel_videos(channel_id)
            all_videos.extend(videos)
        
        if not all_videos:
            print("No videos found from any channels")
            return
        
        # Sort videos by publication date (oldest first)
        all_videos.sort(key=lambda x: x['published_at'])
        
        print(f"\nTotal videos collected: {len(all_videos)}")
        print(f"Date range: {all_videos[0]['published_at'][:10]} to {all_videos[-1]['published_at'][:10]}")
        
        # Get or create playlist
        playlist_description = f"Videos from channels: {', '.join(channel_list)}\nCreated on {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
        playlist_id = self.get_or_create_playlist(playlist_title, playlist_description, force_new_playlist)
        
        if not playlist_id:
            return
        
        # Add videos to playlist at the end, avoiding duplicates and optionally watched videos
        filter_description = "Adding videos to playlist in publication order"
        if min_date:
            filter_description += f" (minimum date: {min_date[:10]})"
        elif use_playlist_watermark:
            filter_description += " (skipping videos older than oldest in playlist)"
        if skip_watched:
            filter_description += " (skipping watched videos)"
        
        print(f"\n{filter_description}...")
        
        success_count = self.add_videos_to_playlist_batch(playlist_id, all_videos, skip_watched, use_playlist_watermark, min_date)
        
        print(f"\nCompleted! Added {success_count} new videos to playlist '{playlist_title}'")
        print(f"Videos were added to the end of the playlist in publication order")
        
        if success_count == 0:
            print("No new videos were added")
        elif success_count < len(all_videos):
            # Count how many were actually new (not duplicates)
            existing_video_ids = self.get_existing_playlist_videos(playlist_id)
            new_video_count = len([v for v in all_videos if v['video_id'] not in existing_video_ids])
            failed_count = new_video_count - success_count
            if failed_count > 0:
                print(f"Note: {failed_count} videos failed to add (may be private, deleted, or restricted)")
    
    def clear_cache(self):
        """Clear the video metadata cache"""
        self.cache = {'channels': {}, 'last_updated': {}}
        self._save_cache()
        print("Video cache cleared successfully")
    
    def clear_channel_cache(self):
        """Clear the channel ID cache"""
        self.channel_cache = {}
        self._save_channel_cache()
        print("Channel cache cleared successfully")
    
    def repopulate_channel_cache(self):
        """Repopulate channel cache from video cache data"""
        prepopulated = self._prepopulate_from_video_cache()
        
        if prepopulated:
            # Merge with existing cache
            self.channel_cache.update(prepopulated)
            self._save_channel_cache()
            print(f"Added {len(prepopulated)} channels to channel cache from video cache")
        else:
            print("No channels found in video cache to add")
    
    def show_cache_info(self):
        """Display information about the current cache"""
        print(f"Video cache file: {self.cache_file}")
        print(f"Channel cache file: {self.channel_cache_file}")
        print(f"Cache expiry: {self.cache_hours} hours ({self.cache_hours/24:.1f} days)")
        
        # Video cache info
        if not self.cache['channels']:
            print("Video cache is empty")
        else:
            print(f"Video cache: {len(self.cache['channels'])} channels")
            
            for channel_id, last_updated_str in self.cache['last_updated'].items():
                last_updated = datetime.fromisoformat(last_updated_str)
                video_count = len(self.cache['channels'].get(channel_id, []))
                age_hours = (datetime.now() - last_updated).total_seconds() / 3600
                status = "Valid" if age_hours < self.cache_hours else "Expired"
                
                print(f"  {channel_id}: {video_count} videos, updated {last_updated.strftime('%Y-%m-%d %H:%M:%S')} ({status})")
        
        # Channel cache info
        if not self.channel_cache:
            print("Channel cache is empty")
        else:
            print(f"Channel cache: {len(self.channel_cache)} mappings")
            for channel_input, channel_id in self.channel_cache.items():
                print(f"  '{channel_input}' -> {channel_id}")

def main():
    # Set up signal handler for graceful shutdown
    signal.signal(signal.SIGINT, signal_handler)
    
    parser = argparse.ArgumentParser(description='YouTube Playlist Manager with Caching')
    parser.add_argument('channels', nargs='*', help='YouTube channel names, URLs, or IDs')
    parser.add_argument('--playlist-title', '-t', help='Title for the new playlist')
    parser.add_argument('--credentials', '-c', default='credentials.json', help='Path to credentials file')
    parser.add_argument('--cache-file', default='video_cache.json', help='Path to video cache file (default: video_cache.json)')
    parser.add_argument('--cache-hours', type=int, default=168, help='Cache expiry time in hours (default: 168 = 1 week)')
    parser.add_argument('--clear-cache', action='store_true', help='Clear the video metadata cache')
    parser.add_argument('--clear-channel-cache', action='store_true', help='Clear the channel ID cache')
    parser.add_argument('--repopulate-channel-cache', action='store_true', help='Repopulate channel cache from video cache')
    parser.add_argument('--show-cache', action='store_true', help='Show cache information')
    parser.add_argument('--force-refresh', action='store_true', help='Force refresh cache (ignore existing cache)')
    parser.add_argument('--force-new-playlist', action='store_true', help='Create new playlist even if one with same name exists')
    parser.add_argument('--skip-watched', action='store_true', help='Skip videos that are in Watch Later or Liked Videos (proxy for watched)')
    parser.add_argument('--use-playlist-watermark', action='store_true', help='Skip videos older than the oldest video already in the playlist')
    parser.add_argument('--min-date', help='Minimum publication date (YYYY-MM-DD or ISO format). Overrides playlist watermark if specified.')
    
    args = parser.parse_args()
    
    # Validate min_date format if provided
    min_date_iso = None
    if args.min_date:
        try:
            # Try to parse the date to validate format
            if len(args.min_date) == 10:  # YYYY-MM-DD format
                from datetime import datetime
                parsed_date = datetime.strptime(args.min_date, '%Y-%m-%d')
                min_date_iso = parsed_date.isoformat() + 'Z'
            else:  # Assume ISO format
                from datetime import datetime
                # Handle various ISO formats
                date_clean = args.min_date.replace('Z', '+00:00') if args.min_date.endswith('Z') else args.min_date
                parsed_date = datetime.fromisoformat(date_clean)
                min_date_iso = args.min_date if args.min_date.endswith('Z') else args.min_date + 'Z'
            
            print(f"Using minimum date filter: {args.min_date}")
            if args.use_playlist_watermark:
                print("Note: --min-date overrides --use-playlist-watermark")
                
        except ValueError as e:
            parser.error(f"Invalid date format for --min-date: {args.min_date}. Use YYYY-MM-DD or ISO format (e.g., 2024-01-15 or 2024-01-15T00:00:00Z)")
    
    try:
        manager = YouTubePlaylistManager(args.credentials, args.cache_file, args.cache_hours)
        
        # Handle cache operations
        if args.clear_cache:
            manager.clear_cache()
            return
        
        if args.clear_channel_cache:
            manager.clear_channel_cache()
            return
        
        if args.repopulate_channel_cache:
            manager.repopulate_channel_cache()
            return
        
        if args.show_cache:
            manager.show_cache_info()
            return
        
        # Force refresh by clearing cache for specified channels
        if args.force_refresh and args.channels:
            if not manager.authenticate():
                return
            for channel_input in args.channels:
                channel_id = manager.get_channel_id(channel_input)
                if channel_id and channel_id in manager.cache['channels']:
                    del manager.cache['channels'][channel_id]
                    del manager.cache['last_updated'][channel_id]
                    print(f"Cleared video cache for channel: {channel_input}")
            manager._save_cache()
        
        # Require channels and playlist title for main operation
        if not args.channels or not args.playlist_title:
            parser.error("channels and --playlist-title are required for creating playlists")
        
        # Use min_date if specified, otherwise use playlist watermark setting
        use_watermark = args.use_playlist_watermark and not min_date_iso
        
        manager.process_channels(args.channels, args.playlist_title, args.force_new_playlist, args.skip_watched, use_watermark, min_date_iso)
        
    except KeyboardInterrupt:
        # This shouldn't be reached due to signal handler, but just in case
        print(f"\n\n🛑 Script interrupted by user")
        print("💾 Any progress made has been saved.")
    except Exception as e:
        print(f"\n❌ An unexpected error occurred: {e}")
        print("💾 Any progress made has been saved.")
        sys.exit(1)
    
    # Check if we were interrupted
    if shutdown_requested:
        print("👋 Script stopped gracefully. You can run it again to continue where you left off.")
        sys.exit(0)

if __name__ == '__main__':
    main()
