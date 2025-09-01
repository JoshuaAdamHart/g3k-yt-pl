#!/usr/bin/env python3
"""
YouTube Playlist Updater
Incrementally updates YouTube playlists with new videos from specified channels.
Only adds videos published since the last run, with a maximum age of 2 weeks.
"""

import os
import sys
import json
import argparse
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
    print("pip install google-auth google-auth-oauthlib google-auth-httplib2 google-api-python-client")
    sys.exit(1)

# YouTube API scopes
SCOPES = ['https://www.googleapis.com/auth/youtube']

class YouTubePlaylistUpdater:
    def __init__(self, credentials_file: str = 'credentials.json', cache_file: str = 'video_cache.json'):
        self.credentials_file = credentials_file
        self.token_file = 'token.json'
        self.cache_file = cache_file
        self.channel_cache_file = 'channel_cache.json'
        self.run_history_file = 'playlist_updater_history.json'
        self.youtube = None
        self.cache = self._load_cache()
        self.channel_cache = self._load_channel_cache()
        self.run_history = self._load_run_history()
        
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
        
        return {}
    
    def _load_run_history(self) -> Dict[str, Any]:
        """Load run history to track last update times per playlist"""
        if os.path.exists(self.run_history_file):
            try:
                with open(self.run_history_file, 'r', encoding='utf-8') as f:
                    history_data = json.load(f)
                    print(f"Loaded run history for {len(history_data.get('playlists', {}))} playlists")
                    return history_data
            except (json.JSONDecodeError, IOError) as e:
                print(f"Warning: Could not load run history file {self.run_history_file}: {e}")
        
        return {'playlists': {}}
    
    def _save_run_history(self):
        """Save run history to JSON file"""
        try:
            with open(self.run_history_file, 'w', encoding='utf-8') as f:
                json.dump(self.run_history, f, indent=2, ensure_ascii=False)
            print(f"Run history saved to {self.run_history_file}")
        except IOError as e:
            print(f"Warning: Could not save run history file {self.run_history_file}: {e}")
    
    def _save_cache(self):
        """Save video metadata cache to JSON file"""
        try:
            with open(self.cache_file, 'w', encoding='utf-8') as f:
                json.dump(self.cache, f, indent=2, ensure_ascii=False)
            print(f"Video cache saved to {self.cache_file}")
        except IOError as e:
            print(f"Warning: Could not save cache file {self.cache_file}: {e}")
    
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

    def authenticate(self):
        """Authenticate with YouTube API"""
        creds = None
        
        # Load existing token
        if os.path.exists(self.token_file):
            creds = Credentials.from_authorized_user_file(self.token_file, SCOPES)
        
        # If there are no (valid) credentials available, let the user log in
        if not creds or not creds.valid:
            if creds and creds.expired and creds.refresh_token:
                creds.refresh(Request())
            else:
                if not os.path.exists(self.credentials_file):
                    print(f"Error: {self.credentials_file} not found!")
                    print("Please download your OAuth credentials from Google Cloud Console")
                    sys.exit(1)
                
                flow = InstalledAppFlow.from_client_secrets_file(self.credentials_file, SCOPES)
                creds = flow.run_local_server(port=0)
            
            # Save the credentials for the next run
            with open(self.token_file, 'w') as token:
                token.write(creds.to_json())
        
        self.youtube = build('youtube', 'v3', credentials=creds)
        print("Successfully authenticated with YouTube API")

    def get_channel_id(self, channel_input: str) -> Optional[str]:
        """Get channel ID from various input formats"""
        # Check cache first
        if channel_input in self.channel_cache:
            print(f"Found channel ID in cache: {channel_input} -> {self.channel_cache[channel_input]}")
            return self.channel_cache[channel_input]
        
        # If it's already a channel ID (starts with UC and is 24 chars)
        if channel_input.startswith('UC') and len(channel_input) == 24:
            self.channel_cache[channel_input] = channel_input
            self._save_channel_cache()
            return channel_input
        
        # Extract from URL
        if 'youtube.com' in channel_input:
            if '/channel/' in channel_input:
                channel_id = channel_input.split('/channel/')[-1].split('/')[0].split('?')[0]
                if channel_id.startswith('UC') and len(channel_id) == 24:
                    self.channel_cache[channel_input] = channel_id
                    self._save_channel_cache()
                    return channel_id
            elif '/@' in channel_input:
                username = channel_input.split('/@')[-1].split('/')[0].split('?')[0]
                return self._search_channel_by_username(username, channel_input)
            elif '/c/' in channel_input:
                custom_name = channel_input.split('/c/')[-1].split('/')[0].split('?')[0]
                return self._search_channel_by_name(custom_name, channel_input)
        
        # Search by channel name
        return self._search_channel_by_name(channel_input, channel_input)
    
    def _search_channel_by_username(self, username: str, original_input: str) -> Optional[str]:
        """Search for channel by @username"""
        try:
            print(f"Searching for channel by username: @{username}")
            request = self.youtube.channels().list(
                part='id',
                forHandle=username
            )
            response = request.execute()
            
            if response['items']:
                channel_id = response['items'][0]['id']
                print(f"Found channel: @{username} -> {channel_id}")
                self.channel_cache[original_input] = channel_id
                self._save_channel_cache()
                return channel_id
            else:
                print(f"Channel not found: @{username}")
                return None
                
        except HttpError as e:
            print(f"Error searching for channel @{username}: {e}")
            return None
    
    def _search_channel_by_name(self, channel_name: str, original_input: str) -> Optional[str]:
        """Search for channel by name"""
        try:
            print(f"Searching for channel: {channel_name}")
            request = self.youtube.search().list(
                part='snippet',
                q=channel_name,
                type='channel',
                maxResults=5
            )
            response = request.execute()
            
            for item in response['items']:
                if item['snippet']['title'].lower() == channel_name.lower():
                    channel_id = item['snippet']['channelId']
                    print(f"Found exact match: {channel_name} -> {channel_id}")
                    self.channel_cache[original_input] = channel_id
                    self._save_channel_cache()
                    return channel_id
            
            # If no exact match, use the first result
            if response['items']:
                channel_id = response['items'][0]['snippet']['channelId']
                found_name = response['items'][0]['snippet']['title']
                print(f"Using closest match: {found_name} -> {channel_id}")
                self.channel_cache[original_input] = channel_id
                self._save_channel_cache()
                return channel_id
            else:
                print(f"No channels found for: {channel_name}")
                return None
                
        except HttpError as e:
            print(f"Error searching for channel {channel_name}: {e}")
            return None

    def get_playlist_by_name(self, playlist_name: str) -> Optional[str]:
        """Find existing playlist by name or create new one"""
        try:
            # Search for existing playlists
            request = self.youtube.playlists().list(
                part='snippet',
                mine=True,
                maxResults=50
            )
            response = request.execute()
            
            for item in response['items']:
                if item['snippet']['title'] == playlist_name:
                    playlist_id = item['id']
                    print(f"Found existing playlist: {playlist_name} -> {playlist_id}")
                    return playlist_id
            
            # Create new playlist if not found
            print(f"Creating new playlist: {playlist_name}")
            request = self.youtube.playlists().insert(
                part='snippet,status',
                body={
                    'snippet': {
                        'title': playlist_name,
                        'description': f'Auto-updated playlist created by YouTube Playlist Updater'
                    },
                    'status': {
                        'privacyStatus': 'private'
                    }
                }
            )
            response = request.execute()
            playlist_id = response['id']
            print(f"Created new playlist: {playlist_name} -> {playlist_id}")
            return playlist_id
            
        except HttpError as e:
            print(f"Error managing playlist {playlist_name}: {e}")
            return None

    def get_playlist_videos(self, playlist_id: str) -> List[Dict[str, Any]]:
        """Get all videos currently in the playlist"""
        videos = []
        next_page_token = None
        
        try:
            while True:
                request = self.youtube.playlistItems().list(
                    part='snippet',
                    playlistId=playlist_id,
                    maxResults=50,
                    pageToken=next_page_token
                )
                response = request.execute()
                
                for item in response['items']:
                    video_data = {
                        'video_id': item['snippet']['resourceId']['videoId'],
                        'title': item['snippet']['title'],
                        'published_at': item['snippet']['publishedAt'],
                        'position': item['snippet']['position']
                    }
                    videos.append(video_data)
                
                next_page_token = response.get('nextPageToken')
                if not next_page_token:
                    break
            
            print(f"Found {len(videos)} existing videos in playlist")
            return videos
            
        except HttpError as e:
            print(f"Error fetching playlist videos: {e}")
            return []

    def get_channel_videos_since(self, channel_id: str, since_date: datetime, max_age_days: int = 14) -> List[Dict[str, Any]]:
        """Get videos from channel published since the given date, with maximum age limit"""
        # Calculate the earliest date we should consider (max age limit)
        earliest_date = datetime.now() - timedelta(days=max_age_days)
        
        # Ensure both dates are timezone-naive for comparison
        if since_date.tzinfo is not None:
            since_date = since_date.replace(tzinfo=None)
        if earliest_date.tzinfo is not None:
            earliest_date = earliest_date.replace(tzinfo=None)
        
        # Use the later of the two dates (since_date or earliest_date)
        effective_since_date = max(since_date, earliest_date)
        
        print(f"Fetching videos from channel {channel_id} since {effective_since_date.strftime('%Y-%m-%d %H:%M:%S')}")
        
        videos = []
        next_page_token = None
        
        try:
            while True:
                request = self.youtube.search().list(
                    part='snippet',
                    channelId=channel_id,
                    type='video',
                    order='date',
                    publishedAfter=effective_since_date.strftime('%Y-%m-%dT%H:%M:%SZ'),
                    maxResults=50,
                    pageToken=next_page_token
                )
                response = request.execute()
                
                for item in response['items']:
                    published_at_str = item['snippet']['publishedAt']
                    published_at = datetime.fromisoformat(published_at_str.replace('Z', '+00:00'))
                    
                    # Convert to timezone-naive for comparison
                    published_at_naive = published_at.replace(tzinfo=None)
                    
                    # Only include videos published after our since_date
                    if published_at_naive > since_date:
                        video_data = {
                            'video_id': item['id']['videoId'],
                            'title': item['snippet']['title'],
                            'published_at': published_at_str,  # Keep original string format
                            'channel_title': item['snippet']['channelTitle'],
                            'channel_id': channel_id,
                            'description': item['snippet']['description'],
                            'thumbnail_url': item['snippet']['thumbnails']['default']['url']
                        }
                        videos.append(video_data)
                
                next_page_token = response.get('nextPageToken')
                if not next_page_token:
                    break
            
            print(f"Found {len(videos)} new videos from channel {channel_id}")
            return videos
            
        except HttpError as e:
            print(f"Error fetching videos from channel {channel_id}: {e}")
            return []

    def add_video_to_playlist(self, playlist_id: str, video_id: str, position: Optional[int] = None) -> bool:
        """Add a video to playlist at specified position"""
        try:
            body = {
                'snippet': {
                    'playlistId': playlist_id,
                    'resourceId': {
                        'kind': 'youtube#video',
                        'videoId': video_id
                    }
                }
            }
            
            if position is not None:
                body['snippet']['position'] = position
            
            request = self.youtube.playlistItems().insert(
                part='snippet',
                body=body
            )
            response = request.execute()
            return True
            
        except HttpError as e:
            if 'videoNotFound' in str(e) or 'forbidden' in str(e).lower():
                print(f"  Skipping video {video_id}: {e}")
                return False
            else:
                print(f"  Error adding video {video_id}: {e}")
                return False

    def update_playlist(self, playlist_name: str, channel_names: List[str]) -> bool:
        """Update playlist with new videos from specified channels"""
        print(f"\n=== Updating playlist: {playlist_name} ===")
        
        # Get or create playlist
        playlist_id = self.get_playlist_by_name(playlist_name)
        if not playlist_id:
            print(f"Failed to get/create playlist: {playlist_name}")
            return False
        
        # Get existing videos in playlist
        existing_videos = self.get_playlist_videos(playlist_id)
        existing_video_ids = {video['video_id'] for video in existing_videos}
        
        # Determine the cutoff date for new videos
        cutoff_date = self._get_cutoff_date(playlist_name, existing_videos)
        print(f"Looking for videos published after: {cutoff_date.strftime('%Y-%m-%d %H:%M:%S')}")
        
        # Collect new videos from all channels
        all_new_videos = []
        
        for channel_name in channel_names:
            print(f"\nProcessing channel: {channel_name}")
            channel_id = self.get_channel_id(channel_name)
            
            if not channel_id:
                print(f"Could not find channel: {channel_name}")
                continue
            
            # Get new videos from this channel
            new_videos = self.get_channel_videos_since(channel_id, cutoff_date)
            
            # Filter out videos already in playlist
            filtered_videos = [v for v in new_videos if v['video_id'] not in existing_video_ids]
            print(f"  {len(filtered_videos)} new videos to add (filtered {len(new_videos) - len(filtered_videos)} duplicates)")
            
            all_new_videos.extend(filtered_videos)
        
        if not all_new_videos:
            print(f"\nNo new videos to add to playlist: {playlist_name}")
            self._update_run_history(playlist_name, channel_names)
            return True
        
        # Sort all new videos by publication date (oldest first)
        all_new_videos.sort(key=lambda x: x['published_at'])
        
        print(f"\nAdding {len(all_new_videos)} new videos to playlist...")
        
        # Add videos to playlist
        added_count = 0
        for i, video in enumerate(all_new_videos):
            print(f"  Adding ({i+1}/{len(all_new_videos)}): {video['title']}")
            
            if self.add_video_to_playlist(playlist_id, video['video_id']):
                added_count += 1
            
            # Small delay to respect rate limits
            import time
            time.sleep(0.1)
        
        print(f"\nSuccessfully added {added_count}/{len(all_new_videos)} videos to playlist: {playlist_name}")
        
        # Update run history
        self._update_run_history(playlist_name, channel_names)
        
        return True

    def _get_cutoff_date(self, playlist_name: str, existing_videos: List[Dict[str, Any]]) -> datetime:
        """Determine the cutoff date for new videos"""
        # Check run history first
        if playlist_name in self.run_history['playlists']:
            last_run = self.run_history['playlists'][playlist_name].get('last_run')
            if last_run:
                last_run_date = datetime.fromisoformat(last_run)
                # Make timezone-naive if needed
                if last_run_date.tzinfo is not None:
                    last_run_date = last_run_date.replace(tzinfo=None)
                print(f"Last run for this playlist: {last_run_date.strftime('%Y-%m-%d %H:%M:%S')}")
        
        # If playlist has existing videos, use the most recent video's publication date
        if existing_videos:
            # Sort by publication date and get the most recent
            existing_videos.sort(key=lambda x: x['published_at'], reverse=True)
            most_recent_date_str = existing_videos[0]['published_at']
            most_recent_date = datetime.fromisoformat(most_recent_date_str.replace('Z', '+00:00'))
            # Make timezone-naive
            most_recent_date = most_recent_date.replace(tzinfo=None)
            print(f"Most recent video in playlist: {most_recent_date.strftime('%Y-%m-%d %H:%M:%S')}")
            return most_recent_date
        
        # If no existing videos and no run history, use 2 weeks ago as default
        default_date = datetime.now() - timedelta(days=14)
        print(f"No existing videos or run history, using default: {default_date.strftime('%Y-%m-%d %H:%M:%S')}")
        return default_date

    def _update_run_history(self, playlist_name: str, channel_names: List[str]):
        """Update run history for this playlist"""
        if 'playlists' not in self.run_history:
            self.run_history['playlists'] = {}
        
        self.run_history['playlists'][playlist_name] = {
            'last_run': datetime.now().isoformat(),
            'channels': channel_names
        }
        
        self._save_run_history()

def main():
    parser = argparse.ArgumentParser(description='YouTube Playlist Updater - Add new videos since last run')
    parser.add_argument('playlist_name', help='Name of the playlist to update')
    parser.add_argument('channels', nargs='+', help='YouTube channel names, URLs, or IDs')
    parser.add_argument('--credentials', '-c', default='credentials.json', help='Path to credentials file')
    parser.add_argument('--cache-file', default='video_cache.json', help='Path to video cache file')
    
    args = parser.parse_args()
    
    updater = YouTubePlaylistUpdater(args.credentials, args.cache_file)
    
    try:
        updater.authenticate()
        success = updater.update_playlist(args.playlist_name, args.channels)
        
        if success:
            print(f"\n✅ Successfully updated playlist: {args.playlist_name}")
        else:
            print(f"\n❌ Failed to update playlist: {args.playlist_name}")
            sys.exit(1)
            
    except KeyboardInterrupt:
        print("\n\nOperation cancelled by user")
        sys.exit(1)
    except Exception as e:
        print(f"\nUnexpected error: {e}")
        sys.exit(1)

if __name__ == '__main__':
    main()
