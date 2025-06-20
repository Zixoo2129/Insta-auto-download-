import os
import requests
import json
import time
from dotenv import load_dotenv # Keep this import even if not using .env file directly, as it doesn't harm
import re
import asyncio

load_dotenv() # This will attempt to load .env, but won't cause issue if vars are from Render env

# --- Configuration from your provided details ---
IG_COOKIES = os.getenv("IG_COOKIES")
OWNER_ID = os.getenv("OWNER_ID")
INSTAGRAM_PROFILES_TO_MONITOR_STR = os.getenv("INSTAGRAM_PROFILES_TO_MONITOR")
# Convert comma-separated string to a list of usernames
INSTAGRAM_PROFILES_TO_MONITOR = [u.strip() for u in INSTAGRAM_PROFILES_TO_MONITOR_STR.split(',')] if INSTAGRAM_PROFILES_TO_MONITOR_STR else []

# Headers to mimic a browser for scraping
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/100.0.4896.127 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.9",
    "Accept-Language": "en-US,en;q=0.9",
    "Cookie": IG_COOKIES # Use your cookies for scraping
}

# Directory to save downloaded media
DOWNLOAD_DIR = "downloads"
os.makedirs(DOWNLOAD_DIR, exist_ok=True)

class InstagramMonitor:
    def __init__(self, target_usernames: list, bot_instance, owner_id):
        self.target_usernames = target_usernames
        self.last_post_ids = {} # Store last seen post ID for each user
        self.bot_instance = bot_instance # Telegram bot instance to send messages back
        self.owner_id = owner_id
        self._load_last_post_ids()

    def _load_last_post_ids(self):
        # A very basic persistence. For production, consider a small database.
        try:
            if os.path.exists("last_post_ids.json"):
                with open("last_post_ids.json", "r") as f:
                    self.last_post_ids = json.load(f)
                print(f"Loaded last post IDs: {self.last_post_ids}")
            else:
                print("last_post_ids.json not found. Starting fresh.")
        except json.JSONDecodeError:
            print("Error decoding last_post_ids.json. Starting fresh.")
            self.last_post_ids = {}
        except Exception as e:
            print(f"Unexpected error loading last post IDs: {e}")
            self.last_post_ids = {}

    def _save_last_post_ids(self):
        try:
            with open("last_post_ids.json", "w") as f:
                json.dump(self.last_post_ids, f)
            print(f"Saved last post IDs: {self.last_post_ids}")
        except Exception as e:
            print(f"Error saving last post IDs: {e}")

    async def _send_status_message(self, message: str):
        if self.bot_instance and self.owner_id:
            try:
                await self.bot_instance.send_message(chat_id=self.owner_id, text=message)
            except Exception as e:
                print(f"Error sending status message to owner: {e}")

    async def fetch_profile_data(self, username):
        # Using Instagram's JSON endpoint. This is subject to change/block by Instagram.
        url = f"https://www.instagram.com/{username}/?__a=1&__d=1"
        try:
            response = requests.get(url, headers=HEADERS, timeout=15) # Increased timeout
            response.raise_for_status() # Raise an exception for HTTP errors (4xx or 5xx)
            data = response.json()
            return data
        except requests.exceptions.RequestException as e:
            error_msg = f"❌ Instagram: Error fetching profile for {username} (HTTP {response.status_code if 'response' in locals() else 'N/A'}): {e}"
            await self._send_status_message(error_msg)
            print(error_msg)
            if 'response' in locals():
                if response.status_code == 404:
                    print(f"Profile {username} not found.")
                elif response.status_code == 429:
                    print("Rate limited by Instagram.")
                    await self._send_status_message("⚠️ Instagram: Rate limited. Will try again later.")
                elif response.status_code == 403:
                    print("Forbidden. Cookies might be invalid or IP blocked.")
                    await self._send_status_message("⚠️ Instagram: Forbidden (403). Cookies or IP might be invalid.")
            return None
        except json.JSONDecodeError:
            error_msg = f"❌ Instagram: Error decoding JSON for {username}. Page content might have changed or cookies invalid."
            await self._send_status_message(error_msg)
            print(error_msg)
            if 'response' in locals():
                print("Response content (first 500 chars):", response.text[:500])
            return None


    async def download_media(self, media_url, filename):
        try:
            response = requests.get(media_url, stream=True, timeout=60) # Increased timeout for large videos
            response.raise_for_status()
            file_path = os.path.join(DOWNLOAD_DIR, filename)
            with open(file_path, 'wb') as f:
                for chunk in response.iter_content(chunk_size=8192):
                    f.write(chunk)
            print(f"Downloaded {filename}")
            return file_path
        except requests.exceptions.RequestException as e:
            await self._send_status_message(f"❌ Instagram: Error downloading media {filename}: {e}")
            print(f"Error downloading media {filename}: {e}")
            return None

    async def check_for_new_posts(self):
        print("Checking for new Instagram posts...")
        await self._send_status_message("🔍 Checking Instagram for new posts...")

        for username in self.target_usernames:
            data = await self.fetch_profile_data(username)
            if not data:
                continue

            try:
                edges = data['graphql']['user']['edge_owner_to_timeline_media']['edges']
            except KeyError as e:
                print(f"Could not parse Instagram JSON for {username}: {e}. Structure might have changed.")
                await self._send_status_message(f"❌ Instagram: JSON structure changed for {username}. Check code.")
                continue

            new_posts_details = []
            for edge in edges:
                node = edge['node']
                post_id = node['id']
                
                # Check if it's a carousel (sidecar)
                if node['__typename'] == 'GraphSidecar':
                    # For sidecar posts, iterate through children to find first image/video
                    media_url = None
                    is_video = False
                    file_ext = ""
                    for child_edge in node['edge_sidecar_to_children']['edges']:
                        child_node = child_edge['node']
                        if child_node['is_video']:
                            media_url = child_node.get('video_url')
                            is_video = True
                            file_ext = ".mp4"
                        else:
                            media_url = child_node.get('display_url')
                            is_video = False
                            file_ext = ".jpg"
                        if media_url:
                            break # Found first media in carousel, use it
                    if not media_url: # If no media found in sidecar
                        print(f"No media found in sidecar post {post_id}")
                        continue
                else: # Single image or video post
                    is_video = node['is_video']
                    if is_video:
                        media_url = node.get('video_url')
                        file_ext = ".mp4"
                    else:
                        media_url = node.get('display_url')
                        file_ext = ".jpg" # Default to JPG for images

                # Extracting caption
                caption_edges = node['edge_media_to_caption']['edges']
                caption = caption_edges[0]['node']['text'] if caption_edges else ""

                if post_id == self.last_post_ids.get(username):
                    print(f"No new posts for {username}. Last known post ID: {self.last_post_ids.get(username)}")
                    break # Reached the last known post, stop

                if media_url:
                    filename = f"{username}_{post_id}{file_ext}"
                    local_path = await self.download_media(media_url, filename)
                    if local_path:
                        new_posts_details.append({
                            "path": local_path,
                            "caption": caption,
                            "is_reel": is_video, # This includes regular videos and reels
                            "id": post_id 
                        })
                else:
                    print(f"No media URL found for post {post_id} by {username}")

            # Process new posts from newest to oldest (order returned by Instagram is newest first)
            # Process in reverse order to ensure oldest new post is handled first if needed,
            # but for last_post_ids update, we care about the newest post found.
            for post in reversed(new_posts_details):
                print(f"New post detected from {username}: {post['path']}")
                await self._send_status_message(f"✨ New post detected from {username}! Processing '{os.path.basename(post['path'])}'...")
                
                # Import handle_processing from main_processor.py dynamically
                from main_processor import handle_processing 
                await handle_processing(post['path'], post['caption'], is_reel=post['is_reel'])
                
                # Update last_post_id after successful processing.
                # This ensures if something fails mid-way, it tries again next time.
                self.last_post_ids[username] = post['id']
                self._save_last_post_ids()
                await asyncio.sleep(2) # Small delay between processing posts to be gentle


            if new_posts_details:
                # After processing all new posts, ensure the last_post_id is the absolute newest one
                # from the original fetch (which is at index 0 before reversal).
                self.last_post_ids[username] = new_posts_details[0]['id'] 
                self._save_last_post_ids()
                await self._send_status_message(f"✅ Processed {len(new_posts_details)} new posts from {username}.")
            else:
                print(f"No new posts found for {username}")
                await self._send_status_message(f"ℹ️ No new posts for {username}.")
                
        await self._send_status_message("😴 Finished checking Instagram posts for all profiles.")

