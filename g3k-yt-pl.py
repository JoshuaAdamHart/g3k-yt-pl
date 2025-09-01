#!/usr/bin/env ./venv/bin/python
"""
G3K YouTube Playlist Manager
A Vibe-coded Python project by Joshua Adam Hart

Final project for Stanford Continuing Studies course:
TECH 152 A Crash Course in Artificial Intelligence
Instructor: Ronjon Nag
https://continuingstudies.stanford.edu/

Add videos from multiple channels to a playlist with date filtering and quota tracking.
"""

import os
import sys
import json
import argparse
import signal
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional

try:
    from google.auth.transport.requests import Request
    from google.oauth2.credentials import Credentials
    from google_auth_oauthlib.flow import InstalledAppFlow
    from googleapiclient.discovery import build
    from googleapiclient.errors import HttpError
except ImportError:
    print("Required packages not installed. Please run:")
    print("make setup")
    sys.exit(1)

SCOPES = ['https://www.googleapis.com/auth/youtube']
shutdown_requested = False

def signal_handler(signum, frame):
    global shutdown_requested
    print(f"\n🛑 Gracefully shutting down...")
    shutdown_requested = True

class QuotaTracker:
    def __init__(self):
        self.used = 0
        self.limit = 10000  # YouTube API daily quota
        
    def add_cost(self, cost: int):
        self.used += cost
        
    def can_afford(self, cost: int) -> bool:
        return self.used + cost <= self.limit
        
    def remaining(self) -> int:
        return max(0, self.limit - self.used)

class G3kYouTubePlaylistManager:
    def __init__(self, credentials_file: str = 'credentials.json'):
        self.credentials_file = credentials_file
        self.token_file = 'token.json'
        os.makedirs('json_cache', exist_ok=True)
        self.cache_file = 'json_cache/cache.json'
        self.channel_cache_file = 'json_cache/channels.json'
        self.youtube = None
        self.quota = QuotaTracker()
        self.cache = self._load_cache()
        self.channel_cache = self._load_channel_cache()
        
    def _load_cache(self) -> Dict[str, Any]:
        if os.path.exists(self.cache_file):
            try:
                with open(self.cache_file, 'r') as f:
                    return json.load(f)
            except:
                pass
        return {'channels': {}, 'last_run': None}
    
    def _load_channel_cache(self) -> Dict[str, str]:
        if os.path.exists(self.channel_cache_file):
            try:
                with open(self.channel_cache_file, 'r') as f:
                    return json.load(f)
            except:
                pass
        return {}
    
    def _save_cache(self):
        try:
            with open(self.cache_file, 'w') as f:
                json.dump(self.cache, f, indent=2)
        except Exception as e:
            print(f"Warning: Could not save cache: {e}")
    
    def _save_channel_cache(self):
        try:
            with open(self.channel_cache_file, 'w') as f:
                json.dump(self.channel_cache, f, indent=2)
        except Exception as e:
            print(f"Warning: Could not save channel cache: {e}")
    
    def authenticate(self) -> bool:
        creds = None
        
        if os.path.exists(self.token_file):
            creds = Credentials.from_authorized_user_file(self.token_file, SCOPES)
        
        if not creds or not creds.valid:
            if creds and creds.expired and creds.refresh_token:
                creds.refresh(Request())
            else:
                if not os.path.exists(self.credentials_file):
                    print(f"Error: {self.credentials_file} not found!")
                    return False
                
                flow = InstalledAppFlow.from_client_secrets_file(self.credentials_file, SCOPES)
                creds = flow.run_local_server(port=0)
            
            with open(self.token_file, 'w') as token:
                token.write(creds.to_json())
        
        self.youtube = build('youtube', 'v3', credentials=creds)
        print("✅ Authenticated with YouTube API")
        return True
    
    def get_channel_id(self, channel_input: str) -> Optional[str]:
        # Already a channel ID
        if channel_input.startswith('UC') and len(channel_input) == 24:
            return channel_input
        
        # Check cache first
        if channel_input in self.channel_cache:
            print(f"📦 Using cached channel ID for: {channel_input}")
            return self.channel_cache[channel_input]
        
        # Extract from URL
        if 'youtube.com' in channel_input:
            if '/channel/' in channel_input:
                channel_id = channel_input.split('/channel/')[-1].split('/')[0]
                self.channel_cache[channel_input] = channel_id
                self._save_channel_cache()
                return channel_id
        
        # Search by name (expensive - 100 quota units)
        if not self.quota.can_afford(100):
            print(f"⚠️ Not enough quota for channel search: {channel_input}")
            return None
            
        try:
            response = self.youtube.search().list(
                part='snippet',
                q=channel_input,
                type='channel',
                maxResults=1
            ).execute()
            self.quota.add_cost(100)
            
            if response['items']:
                channel_id = response['items'][0]['snippet']['channelId']
                # Cache the result
                self.channel_cache[channel_input] = channel_id
                self._save_channel_cache()
                print(f"💾 Cached channel mapping: {channel_input} -> {channel_id}")
                return channel_id
        except HttpError as e:
            if 'quotaExceeded' in str(e):
                print("⚠️ API quota exceeded during channel search")
                return None
            print(f"Error finding channel {channel_input}: {e}")
        
        return None
    
    def get_channel_videos(self, channel_id: str, since_date: Optional[str] = None) -> List[Dict[str, Any]]:
        # Check cache first
        cache_key = f"{channel_id}_{since_date or 'all'}"
        if cache_key in self.cache['channels']:
            cached_data = self.cache['channels'][cache_key]
            cache_time = datetime.fromisoformat(cached_data['timestamp'])
            if datetime.now() - cache_time < timedelta(hours=24):  # 24 hour cache
                print(f"📦 Using cached data for channel {channel_id}")
                return cached_data['videos']
        
        if not self.quota.can_afford(1):
            print(f"⚠️ Not enough quota to fetch channel videos")
            return []
        
        videos = []
        try:
            # Get uploads playlist (1 quota unit)
            channel_response = self.youtube.channels().list(
                part='contentDetails,snippet',
                id=channel_id
            ).execute()
            self.quota.add_cost(1)
            
            if not channel_response['items']:
                return videos
            
            channel_info = channel_response['items'][0]
            channel_title = channel_info['snippet']['title']
            uploads_playlist_id = channel_info['contentDetails']['relatedPlaylists']['uploads']
            
            print(f"📺 Fetching videos from: {channel_title}")
            
            # Get videos from uploads playlist (1 quota unit per page)
            next_page_token = None
            page_count = 0
            
            while True:
                if not self.quota.can_afford(1):
                    print(f"⚠️ Quota limit reached, stopping at page {page_count}")
                    break
                
                page_count += 1
                
                playlist_response = self.youtube.playlistItems().list(
                    part='snippet',
                    playlistId=uploads_playlist_id,
                    maxResults=50,
                    pageToken=next_page_token
                ).execute()
                self.quota.add_cost(1)
                
                for item in playlist_response['items']:
                    video_date = item['snippet']['publishedAt']
                    
                    # Filter by date if specified
                    if since_date:
                        if video_date < since_date:
                            continue
                    
                    videos.append({
                        'video_id': item['snippet']['resourceId']['videoId'],
                        'title': item['snippet']['title'],
                        'published_at': video_date,
                        'channel_title': channel_title,
                        'channel_id': channel_id
                    })
                
                next_page_token = playlist_response.get('nextPageToken')
                if not next_page_token:
                    break
            
            print(f"📊 Found {len(videos)} videos")
            
            # Cache the results
            self.cache['channels'][cache_key] = {
                'videos': videos,
                'timestamp': datetime.now().isoformat()
            }
            self._save_cache()
            
        except HttpError as e:
            if 'quotaExceeded' in str(e):
                print("⚠️ API quota exceeded while fetching videos")
            else:
                print(f"Error fetching videos: {e}")
        
        return videos
    
    def get_or_create_playlist(self, title: str) -> Optional[str]:
        if not self.quota.can_afford(1):
            print("⚠️ Not enough quota to search for playlists")
            return None
        
        try:
            # Search for existing playlist (1 quota unit)
            playlists_response = self.youtube.playlists().list(
                part='snippet',
                mine=True,
                maxResults=50
            ).execute()
            self.quota.add_cost(1)
            
            for playlist in playlists_response['items']:
                if playlist['snippet']['title'] == title:
                    playlist_id = playlist['id']
                    print(f"📋 Found existing playlist: {title}")
                    return playlist_id
            
            # Create new playlist (50 quota units)
            if not self.quota.can_afford(50):
                print("⚠️ Not enough quota to create new playlist")
                return None
            
            playlist_response = self.youtube.playlists().insert(
                part='snippet,status',
                body={
                    'snippet': {
                        'title': title,
                        'description': f"Created by YouTube Playlist Manager on {datetime.now().strftime('%Y-%m-%d')}"
                    },
                    'status': {'privacyStatus': 'private'}
                }
            ).execute()
            self.quota.add_cost(50)
            
            playlist_id = playlist_response['id']
            print(f"✨ Created new playlist: {title}")
            return playlist_id
            
        except HttpError as e:
            if 'quotaExceeded' in str(e):
                print("⚠️ API quota exceeded during playlist operations")
            else:
                print(f"Error with playlist operations: {e}")
            return None
    
    def get_existing_videos(self, playlist_id: str) -> set:
        existing_ids = set()
        
        if not self.quota.can_afford(1):
            print("⚠️ Not enough quota to check existing videos")
            return existing_ids
        
        try:
            next_page_token = None
            
            while True:
                if not self.quota.can_afford(1):
                    break
                
                response = self.youtube.playlistItems().list(
                    part='snippet',
                    playlistId=playlist_id,
                    maxResults=50,
                    pageToken=next_page_token
                ).execute()
                self.quota.add_cost(1)
                
                for item in response['items']:
                    existing_ids.add(item['snippet']['resourceId']['videoId'])
                
                next_page_token = response.get('nextPageToken')
                if not next_page_token:
                    break
            
            print(f"📊 Found {len(existing_ids)} existing videos in playlist")
            
        except HttpError as e:
            if 'quotaExceeded' in str(e):
                print("⚠️ API quota exceeded while checking existing videos")
            else:
                print(f"Error checking existing videos: {e}")
        
        return existing_ids
    
    def add_videos_to_playlist(self, playlist_id: str, videos: List[Dict[str, Any]], existing_ids: set) -> int:
        global shutdown_requested
        import time
        
        # Filter out existing videos and sort by date
        new_videos = [v for v in videos if v['video_id'] not in existing_ids]
        new_videos.sort(key=lambda x: x['published_at'])
        
        if not new_videos:
            print("📝 No new videos to add")
            return 0
        
        print(f"➕ Adding {len(new_videos)} new videos...")
        
        added_count = 0
        
        for i, video in enumerate(new_videos, 1):
            if shutdown_requested:
                print(f"\n⏸️ Stopped by user after adding {added_count} videos")
                break
            
            if not self.quota.can_afford(50):
                print(f"\n⚠️ Quota limit reached after adding {added_count} videos")
                print(f"💡 Run again tomorrow to add remaining {len(new_videos) - i + 1} videos")
                break
            
            try:
                self.youtube.playlistItems().insert(
                    part='snippet',
                    body={
                        'snippet': {
                            'playlistId': playlist_id,
                            'resourceId': {
                                'kind': 'youtube#video',
                                'videoId': video['video_id']
                            }
                        }
                    }
                ).execute()
                self.quota.add_cost(50)
                
                added_count += 1
                print(f"  ✅ {video['title']} ({video['published_at'][:10]})")
                
                # Progress update
                if i % 10 == 0:
                    print(f"    📊 Progress: {i}/{len(new_videos)} ({added_count} successful)")
                
                # Rate limiting
                time.sleep(0.5)
                
            except HttpError as e:
                if 'quotaExceeded' in str(e):
                    print(f"\n⚠️ API quota exceeded after adding {added_count} videos")
                    break
                else:
                    print(f"  ❌ Failed to add: {video['title']} ({e})")
        
        return added_count
    
    def process_channels(self, channels: List[str], playlist_title: str, 
                        start_date: Optional[str] = None, end_date: Optional[str] = None):
        
        if not self.authenticate():
            return
        
        # Convert dates to ISO format if needed
        since_date = None
        if start_date:
            try:
                if len(start_date) == 10:  # YYYY-MM-DD
                    since_date = start_date + 'T00:00:00Z'
                else:
                    since_date = start_date
                print(f"📅 Filtering videos from: {start_date}")
            except:
                print(f"❌ Invalid start date format: {start_date}")
                return
        
        # Check for new videos since last run
        if not start_date and self.cache.get('last_run'):
            since_date = self.cache['last_run']
            print(f"📅 Checking for new videos since last run: {since_date[:10]}")
        
        print(f"🎯 Target playlist: {playlist_title}")
        print(f"📊 Starting quota: {self.quota.remaining()}")
        
        # Get or create playlist
        playlist_id = self.get_or_create_playlist(playlist_title)
        if not playlist_id:
            return
        
        # Get existing videos to avoid duplicates
        existing_ids = self.get_existing_videos(playlist_id)
        
        # Collect videos from all channels
        all_videos = []
        for channel_input in channels:
            print(f"\n🔍 Processing: {channel_input}")
            
            channel_id = self.get_channel_id(channel_input)
            if not channel_id:
                print(f"❌ Could not find channel: {channel_input}")
                continue
            
            videos = self.get_channel_videos(channel_id, since_date)
            
            # Filter by end date if specified
            if end_date:
                videos = [v for v in videos if v['published_at'] <= end_date + 'T23:59:59Z']
            
            all_videos.extend(videos)
            
            if shutdown_requested:
                break
        
        if not all_videos:
            print("📝 No videos found")
            return
        
        # Sort by publication date and add to playlist
        all_videos.sort(key=lambda x: x['published_at'])
        print(f"\n📊 Total videos found: {len(all_videos)}")
        if all_videos:
            print(f"📅 Date range: {all_videos[0]['published_at'][:10]} to {all_videos[-1]['published_at'][:10]}")
        
        added_count = self.add_videos_to_playlist(playlist_id, all_videos, existing_ids)
        
        # Update last run timestamp
        self.cache['last_run'] = datetime.now().isoformat()
        self._save_cache()
        
        print(f"\n🎉 Complete! Added {added_count} videos to '{playlist_title}'")
        print(f"📊 Quota used: {self.quota.used}/{self.quota.limit} ({self.quota.remaining()} remaining)")

def main():
    signal.signal(signal.SIGINT, signal_handler)
    
    parser = argparse.ArgumentParser(description='G3K YouTube Playlist Manager')
    parser.add_argument('channels', nargs='+', help='YouTube channels (names, URLs, or IDs)')
    parser.add_argument('--playlist-title', '-t', required=True, help='Playlist title')
    parser.add_argument('--start-date', help='Start date (YYYY-MM-DD)')
    parser.add_argument('--end-date', help='End date (YYYY-MM-DD)')
    parser.add_argument('--credentials', default='credentials.json', help='Credentials file path')
    
    args = parser.parse_args()
    
    try:
        manager = G3kYouTubePlaylistManager(args.credentials)
        manager.process_channels(args.channels, args.playlist_title, args.start_date, args.end_date)
    except KeyboardInterrupt:
        print("\n👋 Stopped gracefully")
    except Exception as e:
        print(f"\n❌ Error: {e}")
        sys.exit(1)

if __name__ == '__main__':
    main()
