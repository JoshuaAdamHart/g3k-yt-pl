#!/usr/bin/env python3
"""
Watch Later Playlist Dumper
Dumps the complete listing of your YouTube Watch Later playlist,
including information about private, deleted, or hidden videos.
"""

import os
import sys
import json
from datetime import datetime
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
SCOPES = ['https://www.googleapis.com/auth/youtube.readonly']

class WatchLaterDumper:
    def __init__(self, credentials_file: str = 'credentials.json'):
        self.credentials_file = credentials_file
        self.token_file = 'token.json'
        self.youtube = None
        
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
    
    def get_watch_later_playlist_id(self) -> str:
        """Get the Watch Later playlist ID for the authenticated user"""
        try:
            channels_response = self.youtube.channels().list(
                part='contentDetails',
                mine=True
            ).execute()
            
            if not channels_response['items']:
                print("Could not access user's channel information")
                return None
            
            watch_later_id = channels_response['items'][0]['contentDetails']['relatedPlaylists'].get('watchLater')
            
            if not watch_later_id:
                print("Watch Later playlist not found")
                return None
            
            print(f"Found Watch Later playlist ID: {watch_later_id}")
            return watch_later_id
            
        except HttpError as e:
            print(f"Error getting Watch Later playlist ID: {e}")
            return None
    
    def get_video_details(self, video_ids: List[str]) -> Dict[str, Dict]:
        """Get detailed information for a batch of video IDs"""
        video_details = {}
        
        if not video_ids:
            return video_details
        
        try:
            # Batch request for video details (up to 50 at a time)
            videos_response = self.youtube.videos().list(
                part='snippet,status,contentDetails,statistics',
                id=','.join(video_ids)
            ).execute()
            
            for video in videos_response['items']:
                video_id = video['id']
                snippet = video.get('snippet', {})
                status = video.get('status', {})
                content_details = video.get('contentDetails', {})
                statistics = video.get('statistics', {})
                
                video_details[video_id] = {
                    'title': snippet.get('title', 'Unknown Title'),
                    'channel_title': snippet.get('channelTitle', 'Unknown Channel'),
                    'channel_id': snippet.get('channelId', 'Unknown'),
                    'published_at': snippet.get('publishedAt', 'Unknown'),
                    'description': snippet.get('description', '')[:200] + '...' if snippet.get('description') else '',
                    'duration': content_details.get('duration', 'Unknown'),
                    'privacy_status': status.get('privacyStatus', 'Unknown'),
                    'upload_status': status.get('uploadStatus', 'Unknown'),
                    'view_count': statistics.get('viewCount', 'Unknown'),
                    'like_count': statistics.get('likeCount', 'Unknown'),
                    'thumbnail_url': snippet.get('thumbnails', {}).get('medium', {}).get('url', ''),
                    'available': True
                }
            
        except HttpError as e:
            print(f"Error getting video details: {e}")
        
        return video_details
    
    def dump_watch_later(self, output_file: str = None) -> List[Dict[str, Any]]:
        """Dump the complete Watch Later playlist"""
        if not self.authenticate():
            return []
        
        watch_later_id = self.get_watch_later_playlist_id()
        if not watch_later_id:
            return []
        
        print(f"\nFetching Watch Later playlist contents...")
        
        all_items = []
        next_page_token = None
        page_count = 0
        
        try:
            while True:
                page_count += 1
                print(f"  Fetching page {page_count}...")
                
                playlist_response = self.youtube.playlistItems().list(
                    part='snippet,status',
                    playlistId=watch_later_id,
                    maxResults=50,
                    pageToken=next_page_token
                ).execute()
                
                page_items = []
                video_ids_to_fetch = []
                
                for item in playlist_response['items']:
                    video_id = item['snippet']['resourceId']['videoId']
                    
                    # Basic info from playlist item
                    playlist_item = {
                        'position': len(all_items) + len(page_items),
                        'video_id': video_id,
                        'added_to_playlist_at': item['snippet']['publishedAt'],
                        'playlist_item_title': item['snippet'].get('title', 'Unknown'),
                        'playlist_item_channel': item['snippet'].get('videoOwnerChannelTitle', 'Unknown'),
                        'playlist_item_channel_id': item['snippet'].get('videoOwnerChannelId', 'Unknown'),
                        'playlist_privacy_status': item.get('status', {}).get('privacyStatus', 'Unknown'),
                        'available': True,
                        'error_reason': None
                    }
                    
                    # Check if video appears to be deleted/private based on playlist item info
                    if (item['snippet'].get('title') == 'Deleted video' or 
                        item['snippet'].get('title') == 'Private video' or
                        not item['snippet'].get('title')):
                        playlist_item['available'] = False
                        playlist_item['error_reason'] = 'Video appears deleted or private'
                        playlist_item['title'] = item['snippet'].get('title', 'Unknown')
                        playlist_item['channel_title'] = 'Unknown'
                        playlist_item['channel_id'] = 'Unknown'
                        playlist_item['published_at'] = 'Unknown'
                        playlist_item['description'] = ''
                        playlist_item['duration'] = 'Unknown'
                        playlist_item['privacy_status'] = 'Unknown'
                        playlist_item['upload_status'] = 'Unknown'
                        playlist_item['view_count'] = 'Unknown'
                        playlist_item['like_count'] = 'Unknown'
                        playlist_item['thumbnail_url'] = ''
                    else:
                        video_ids_to_fetch.append(video_id)
                    
                    page_items.append(playlist_item)
                
                # Get detailed info for available videos
                if video_ids_to_fetch:
                    video_details = self.get_video_details(video_ids_to_fetch)
                    
                    # Merge detailed info with playlist items
                    for item in page_items:
                        if item['video_id'] in video_details:
                            details = video_details[item['video_id']]
                            item.update(details)
                        elif item['available']:  # Video wasn't returned by videos API
                            item['available'] = False
                            item['error_reason'] = 'Video not accessible via API (may be private/deleted)'
                            item['title'] = item['playlist_item_title']
                            item['channel_title'] = item['playlist_item_channel']
                            item['channel_id'] = item['playlist_item_channel_id']
                            item['published_at'] = 'Unknown'
                            item['description'] = ''
                            item['duration'] = 'Unknown'
                            item['privacy_status'] = 'Unknown'
                            item['upload_status'] = 'Unknown'
                            item['view_count'] = 'Unknown'
                            item['like_count'] = 'Unknown'
                            item['thumbnail_url'] = ''
                
                all_items.extend(page_items)
                
                next_page_token = playlist_response.get('nextPageToken')
                if not next_page_token:
                    break
            
            print(f"\nFound {len(all_items)} total items in Watch Later playlist")
            
            # Count available vs unavailable videos
            available_count = sum(1 for item in all_items if item['available'])
            unavailable_count = len(all_items) - available_count
            
            print(f"  Available videos: {available_count}")
            print(f"  Unavailable/Private/Deleted videos: {unavailable_count}")
            
            # Save to file if requested
            if output_file:
                self.save_to_file(all_items, output_file)
            
            return all_items
            
        except HttpError as e:
            print(f"Error fetching Watch Later playlist: {e}")
            return []
    
    def save_to_file(self, items: List[Dict[str, Any]], filename: str):
        """Save the playlist dump to a JSON file"""
        output_data = {
            'dump_date': datetime.now().isoformat(),
            'total_items': len(items),
            'available_items': sum(1 for item in items if item['available']),
            'unavailable_items': sum(1 for item in items if not item['available']),
            'items': items
        }
        
        try:
            with open(filename, 'w', encoding='utf-8') as f:
                json.dump(output_data, f, indent=2, ensure_ascii=False)
            print(f"\n💾 Saved complete dump to: {filename}")
        except IOError as e:
            print(f"Error saving to file {filename}: {e}")
    
    def print_summary(self, items: List[Dict[str, Any]]):
        """Print a summary of the Watch Later playlist"""
        if not items:
            print("No items found in Watch Later playlist")
            return
        
        print(f"\n📊 Watch Later Playlist Summary:")
        print(f"{'='*50}")
        
        available_items = [item for item in items if item['available']]
        unavailable_items = [item for item in items if not item['available']]
        
        print(f"Total items: {len(items)}")
        print(f"Available videos: {len(available_items)}")
        print(f"Unavailable videos: {len(unavailable_items)}")
        
        if unavailable_items:
            print(f"\n❌ Unavailable Videos:")
            for item in unavailable_items[:10]:  # Show first 10
                print(f"  Position {item['position']}: {item.get('title', 'Unknown')} - {item.get('error_reason', 'Unknown error')}")
            
            if len(unavailable_items) > 10:
                print(f"  ... and {len(unavailable_items) - 10} more unavailable videos")
        
        if available_items:
            print(f"\n✅ Recent Available Videos (last 5):")
            for item in available_items[-5:]:  # Show last 5 added
                print(f"  Position {item['position']}: {item.get('title', 'Unknown')} by {item.get('channel_title', 'Unknown')}")

def main():
    import argparse
    
    parser = argparse.ArgumentParser(description='Dump YouTube Watch Later playlist')
    parser.add_argument('--credentials', '-c', default='credentials.json', 
                       help='Path to credentials file (default: credentials.json)')
    parser.add_argument('--output', '-o', 
                       help='Output JSON file (default: watch_later_dump_YYYY-MM-DD.json)')
    parser.add_argument('--summary-only', action='store_true',
                       help='Only show summary, don\'t save to file')
    
    args = parser.parse_args()
    
    # Generate default output filename if not specified
    if not args.output and not args.summary_only:
        timestamp = datetime.now().strftime('%Y-%m-%d')
        args.output = f'watch_later_dump_{timestamp}.json'
    
    dumper = WatchLaterDumper(args.credentials)
    
    print("🎬 YouTube Watch Later Playlist Dumper")
    print("=====================================")
    
    items = dumper.dump_watch_later(args.output if not args.summary_only else None)
    
    if items:
        dumper.print_summary(items)
        
        if not args.summary_only:
            print(f"\n💡 Use 'python dump_watch_later.py --summary-only' to just see the summary")
            print(f"💡 Full data saved to: {args.output}")
    else:
        print("❌ Failed to dump Watch Later playlist")

if __name__ == '__main__':
    main()
