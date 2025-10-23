import discord
import aiohttp
import asyncio
import yt_dlp
import os
import json
import logging
from typing import Optional, Dict, List, Any, Union
import re
from urllib.parse import urlparse, parse_qs, quote_plus
import tempfile
import subprocess
import base64
import hashlib
import time
import random
import browser_cookie3
import requests
from fake_useragent import UserAgent

logger = logging.getLogger(__name__)

class ProviderManager:
    def __init__(self):
        self.session = None
        self.ua = UserAgent()
        self.cookies = None
        self.cookiefile_path = None
        self.user_agents = [
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:121.0) Gecko/20100101 Firefox/121.0',
            'Mozilla/5.0 (Macintosh; Intel Mac OS X 10.15; rv:121.0) Gecko/20100101 Firefox/121.0'
        ]
        
    async def initialize(self):
        """Initialize all providers with cookie support and better headers"""
        try:
            # Try to get cookies from browser
            self.cookies = self._get_browser_cookies()
        except Exception as e:
            logger.warning(f"Could not load browser cookies: {e}")
            self.cookies = None
        
        # Create session with enhanced headers
        headers = {
            'User-Agent': self.ua.random,
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7',
            'Accept-Language': 'en-US,en;q=0.9',
            'Accept-Encoding': 'gzip, deflate, br',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1',
            'Sec-Fetch-Dest': 'document',
            'Sec-Fetch-Mode': 'navigate',
            'Sec-Fetch-Site': 'none',
            'Sec-Fetch-User': '?1',
            'Cache-Control': 'max-age=0'
        }
        
        # Add cookies if available
        cookie_jar = None
        if self.cookies:
            cookie_jar = aiohttp.CookieJar()
            for cookie in self.cookies:
                cookie_jar.update_cookies({cookie.name: cookie.value})
        
        self.session = aiohttp.ClientSession(
            headers=headers,
            cookie_jar=cookie_jar,
            timeout=aiohttp.ClientTimeout(total=30)
        )
        logger.info("Provider manager initialized with enhanced network-based extraction")

        # Prepare cookies for yt-dlp if available
        try:
            if self.cookies:
                self.cookiefile_path = self._write_cookies_to_file(self.cookies)
        except Exception as e:
            logger.warning(f"Could not persist cookies for yt-dlp: {e}")
    
    def _get_browser_cookies(self):
        """Get cookies from browser for authentication"""
        try:
            # Try Chrome first, then Firefox, then Edge
            for browser in ['chrome', 'firefox', 'edge']:
                try:
                    if browser == 'chrome':
                        return browser_cookie3.chrome(domain_name='youtube.com')
                    elif browser == 'firefox':
                        return browser_cookie3.firefox(domain_name='youtube.com')
                    elif browser == 'edge':
                        return browser_cookie3.edge(domain_name='youtube.com')
                except Exception:
                    continue
            return None
        except Exception as e:
            logger.warning(f"Could not extract browser cookies: {e}")
            return None

    def _write_cookies_to_file(self, cookiejar):
        """Persist cookies to a Netscape cookie file for yt-dlp consumption."""
        try:
            os.makedirs(DOWNLOAD_PATH, exist_ok=True)
            cookie_path = os.path.join(DOWNLOAD_PATH, 'yt_cookies.txt')
            with open(cookie_path, 'w', encoding='utf-8') as f:
                f.write('# Netscape HTTP Cookie File\n')
                # Fields: domain, include_subdomains, path, secure, expires, name, value
                for c in cookiejar:
                    domain = c.domain if hasattr(c, 'domain') and c.domain else '.youtube.com'
                    include_sub = 'TRUE' if (getattr(c, 'domain_initial_dot', False) or str(domain).startswith('.')) else 'FALSE'
                    path = c.path if hasattr(c, 'path') and c.path else '/'
                    secure = 'TRUE' if getattr(c, 'secure', False) else 'FALSE'
                    expires = int(getattr(c, 'expires', 0) or 0)
                    name = c.name
                    value = c.value
                    f.write(f"{domain}\t{include_sub}\t{path}\t{secure}\t{expires}\t{name}\t{value}\n")
            return cookie_path
        except Exception as e:
            logger.warning(f"Failed writing cookies file: {e}")
            return None

    def _build_yt_dlp_opts(self, base_overrides: Optional[Dict] = None) -> Dict:
        """Construct yt-dlp options using the EXACT same approach as app.py"""
        # Copy the EXACT configuration from app.py that works
        opts: Dict[str, Any] = {
            'format': 'bestaudio/best',
            'noplaylist': True,
            'quiet': True,
            'no_warnings': True,
        }

        if base_overrides:
            opts.update(base_overrides)
        return opts
    
    async def search(self, query: str, provider: str = "yt") -> Optional[Dict]:
        """Search for a song using network-based extraction"""
        try:
            if provider.lower() in ["yt", "youtube"]:
                return await self._network_search_youtube(query)
            elif provider.lower() == "spotify":
                return await self._network_search_spotify(query)
            elif provider.lower() == "soundcloud":
                return await self._network_search_soundcloud(query)
            else:
                # Default to YouTube
                return await self._network_search_youtube(query)
        except Exception as e:
            logger.error(f"Network search error for {provider}: {e}")
            return None
    
    async def _network_search_youtube(self, query: str) -> Optional[Dict]:
        """Search YouTube using the EXACT same approach as app.py"""
        try:
            # Use the EXACT same configuration as app.py
            ydl_opts = {
                'format': 'bestaudio/best',
                'default_search': 'ytsearch1',
                'noplaylist': True,
                'quiet': True,
                'no_warnings': True,
                'extract_flat': False,
            }
            
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(query, download=False)
                
                if info:
                    return {
                        'title': info.get('title', 'Unknown'),
                        'url': info.get('webpage_url', info.get('url', '')),
                        'duration': info.get('duration', 0),
                        'thumbnail': info.get('thumbnail', ''),
                        'uploader': info.get('uploader', 'Unknown'),
                        'provider': 'youtube',
                        'id': info.get('id', ''),
                        'view_count': info.get('view_count', 0)
                    }
            
        except Exception as e:
            logger.error(f"YouTube search error: {e}")
        return None
    
    def _extract_video_ids_from_html(self, html_content: str) -> List[str]:
        """Extract video IDs from YouTube search HTML"""
        video_ids = []
        
        # Method 1: Look for video IDs in the HTML
        patterns = [
            r'"videoId":"([a-zA-Z0-9_-]{11})"',
            r'"video_id":"([a-zA-Z0-9_-]{11})"',
            r'data-video-id="([a-zA-Z0-9_-]{11})"',
            r'/watch\?v=([a-zA-Z0-9_-]{11})',
            r'embed/([a-zA-Z0-9_-]{11})'
        ]
        
        for pattern in patterns:
            matches = re.findall(pattern, html_content)
            video_ids.extend(matches)
        
        # Remove duplicates and return first 5 results
        return list(dict.fromkeys(video_ids))[:5]
    
    async def _extract_youtube_video_info(self, video_id: str, query: str) -> Optional[Dict]:
        """Extract video info using network interception"""
        try:
            # Step 1: Get video page
            video_url = f"https://www.youtube.com/watch?v={video_id}"
            
            async with self.session.get(video_url) as response:
                if response.status != 200:
                    return None
                
                html_content = await response.text()
            
            # Step 2: Extract video metadata from HTML
            title = self._extract_title_from_html(html_content)
            duration = self._extract_duration_from_html(html_content)
            thumbnail = f"https://img.youtube.com/vi/{video_id}/maxresdefault.jpg"
            uploader = self._extract_uploader_from_html(html_content)
            
            # Step 3: Extract direct audio/video URLs
            audio_urls = await self._extract_audio_urls(video_id, html_content)
            
            return {
                'title': title or f"Search result for: {query}",
                'url': video_url,
                'duration': duration,
                'thumbnail': thumbnail,
                'uploader': uploader or 'Unknown',
                'provider': 'youtube',
                'id': video_id,
                'audio_urls': audio_urls,
                'view_count': 0
            }
            
        except Exception as e:
            logger.error(f"YouTube video info extraction error: {e}")
        return None
    
    def _extract_title_from_html(self, html_content: str) -> Optional[str]:
        """Extract video title from HTML"""
        patterns = [
            r'<title>([^<]+)</title>',
            r'"title":"([^"]+)"',
            r'<meta property="og:title" content="([^"]+)"'
        ]
        
        for pattern in patterns:
            match = re.search(pattern, html_content)
            if match:
                title = match.group(1).strip()
                # Clean up title
                title = title.replace(' - YouTube', '').replace(' - YouTube', '')
                return title[:100]  # Limit length
        
        return None
    
    def _extract_duration_from_html(self, html_content: str) -> int:
        """Extract video duration from HTML"""
        patterns = [
            r'"lengthSeconds":"(\d+)"',
            r'"duration":"PT(\d+)S"',
            r'<meta property="video:duration" content="(\d+)"'
        ]
        
        for pattern in patterns:
            match = re.search(pattern, html_content)
            if match:
                return int(match.group(1))
        
        return 0
    
    def _extract_uploader_from_html(self, html_content: str) -> Optional[str]:
        """Extract uploader name from HTML"""
        patterns = [
            r'"author":"([^"]+)"',
            r'"uploader":"([^"]+)"',
            r'<meta property="og:video:author" content="([^"]+)"'
        ]
        
        for pattern in patterns:
            match = re.search(pattern, html_content)
            if match:
                return match.group(1).strip()
        
        return None
    
    async def _extract_audio_urls(self, video_id: str, html_content: str) -> List[str]:
        """Extract direct audio URLs using network interception"""
        audio_urls = []
        
        try:
            # Method 1: Look for player URLs in HTML
            player_patterns = [
                r'"url":"([^"]*audio[^"]*)"',
                r'"audioUrl":"([^"]+)"',
                r'"streamUrl":"([^"]+)"'
            ]
            
            for pattern in player_patterns:
                matches = re.findall(pattern, html_content)
                audio_urls.extend(matches)
            
            # Method 2: Use yt-dlp as fallback for direct extraction (with cookies/headers)
            if not audio_urls:
                ydl_opts = self._build_yt_dlp_opts()
                
                with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                    info = ydl.extract_info(f"https://www.youtube.com/watch?v={video_id}", download=False)
                    if info and 'url' in info:
                        audio_urls.append(info['url'])
            
            return audio_urls
            
        except Exception as e:
            logger.error(f"Audio URL extraction error: {e}")
            return []
    
    async def _network_search_spotify(self, query: str) -> Optional[Dict]:
        """Search Spotify using network interception and YouTube fallback"""
        try:
            # Step 1: Search Spotify web interface
            search_url = f"https://open.spotify.com/search/{quote_plus(query)}"
            
            async with self.session.get(search_url) as response:
                if response.status != 200:
                    # Fallback to YouTube search
                    return await self._network_search_youtube(f"{query} music")
                
                html_content = await response.text()
            
            # Step 2: Extract track info from Spotify HTML
            track_info = self._extract_spotify_track_from_html(html_content)
            if track_info:
                # Step 3: Use YouTube fallback for actual audio
                youtube_query = f"{track_info['title']} {track_info['artist']}"
                youtube_result = await self._network_search_youtube(youtube_query)
                
                if youtube_result:
                    # Merge Spotify metadata with YouTube audio
                    youtube_result.update({
                        'artist': track_info['artist'],
                        'album': track_info.get('album', ''),
                        'provider': 'spotify',
                        'spotify_url': track_info.get('url', ''),
                        'preview_url': track_info.get('preview_url', '')
                    })
                    return youtube_result
            
            # Fallback to direct YouTube search
            return await self._network_search_youtube(f"{query} music")
            
        except Exception as e:
            logger.error(f"Spotify network search error: {e}")
            # Fallback to YouTube
            return await self._network_search_youtube(f"{query} music")
    
    def _extract_spotify_track_from_html(self, html_content: str) -> Optional[Dict]:
        """Extract track information from Spotify HTML"""
        try:
            # Look for track data in the HTML
            patterns = [
                r'"name":"([^"]+)"',
                r'"artist":"([^"]+)"',
                r'"album":"([^"]+)"',
                r'"duration_ms":(\d+)',
                r'"preview_url":"([^"]*)"'
            ]
            
            matches = {}
            for i, pattern in enumerate(patterns):
                match = re.search(pattern, html_content)
                if match:
                    if i == 0:  # name
                        matches['title'] = match.group(1)
                    elif i == 1:  # artist
                        matches['artist'] = match.group(1)
                    elif i == 2:  # album
                        matches['album'] = match.group(1)
                    elif i == 3:  # duration
                        matches['duration'] = int(match.group(1)) // 1000
                    elif i == 4:  # preview_url
                        matches['preview_url'] = match.group(1)
            
            return matches if matches else None
            
        except Exception as e:
            logger.error(f"Spotify HTML extraction error: {e}")
            return None
    
    async def _network_search_soundcloud(self, query: str) -> Optional[Dict]:
        """Search SoundCloud using network interception"""
        try:
            # Step 1: Search SoundCloud web interface
            search_url = f"https://soundcloud.com/search?q={quote_plus(query)}"
            
            async with self.session.get(search_url) as response:
                if response.status != 200:
                    # Fallback to YouTube search
                    return await self._network_search_youtube(f"{query} music")
                
                html_content = await response.text()
            
            # Step 2: Extract track info from SoundCloud HTML
            track_info = self._extract_soundcloud_track_from_html(html_content)
            if track_info:
                return track_info
            
            # Fallback to YouTube search
            return await self._network_search_youtube(f"{query} music")
            
        except Exception as e:
            logger.error(f"SoundCloud network search error: {e}")
            # Fallback to YouTube
            return await self._network_search_youtube(f"{query} music")
    
    def _extract_soundcloud_track_from_html(self, html_content: str) -> Optional[Dict]:
        """Extract track information from SoundCloud HTML"""
        try:
            # Look for track data in the HTML
            patterns = [
                r'"title":"([^"]+)"',
                r'"username":"([^"]+)"',
                r'"duration":(\d+)',
                r'"artwork_url":"([^"]*)"',
                r'"permalink_url":"([^"]+)"',
                r'"stream_url":"([^"]+)"'
            ]
            
            matches = {}
            for i, pattern in enumerate(patterns):
                match = re.search(pattern, html_content)
                if match:
                    if i == 0:  # title
                        matches['title'] = match.group(1)
                    elif i == 1:  # username
                        matches['artist'] = match.group(1)
                    elif i == 2:  # duration
                        matches['duration'] = int(match.group(1)) // 1000
                    elif i == 3:  # artwork_url
                        matches['thumbnail'] = match.group(1)
                    elif i == 4:  # permalink_url
                        matches['url'] = match.group(1)
                    elif i == 5:  # stream_url
                        matches['stream_url'] = match.group(1)
            
            if matches:
                matches.update({
                    'provider': 'soundcloud',
                    'id': str(hash(matches.get('title', '')))[:11]  # Generate ID
                })
                return matches
            
            return None
            
        except Exception as e:
            logger.error(f"SoundCloud HTML extraction error: {e}")
            return None
    
    async def get_audio_stream(self, song: Dict) -> Optional[discord.FFmpegPCMAudio]:
        """Get an audio stream for a song using network-extracted URLs"""
        try:
            provider = song.get('provider', 'youtube')
            
            if provider == 'youtube':
                return await self._get_network_youtube_stream(song)
            elif provider == 'spotify':
                return await self._get_network_spotify_stream(song)
            elif provider == 'soundcloud':
                return await self._get_network_soundcloud_stream(song)
            else:
                return await self._get_network_youtube_stream(song)
                
        except Exception as e:
            logger.error(f"Error getting audio stream: {e}")
            return None
    
    async def _get_network_youtube_stream(self, song: Dict) -> Optional[discord.FFmpegPCMAudio]:
        """Get YouTube audio stream using the EXACT same approach as app.py"""
        try:
            # Use the EXACT same configuration as app.py
            url = song.get('url', '')
            if not url:
                return None
            
            ydl_opts = {
                'format': 'bestaudio/best',
                'noplaylist': True,
                'quiet': True,
                'no_warnings': True,
            }
            
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(url, download=False)
                
                if info and 'url' in info:
                    audio_url = info['url']
                    
                    # Create FFmpeg audio source with optimized settings
                    ffmpeg_options = {
                        'before_options': '-reconnect 1 -reconnect_streamed 1 -reconnect_delay_max 2',
                        'options': '-vn -bufsize 512k'
                    }
                    
                    return discord.FFmpegPCMAudio(audio_url, **ffmpeg_options)
                    
        except Exception as e:
            logger.error(f"YouTube network stream error: {e}")
        return None
    
    async def _get_network_spotify_stream(self, song: Dict) -> Optional[discord.FFmpegPCMAudio]:
        """Get Spotify audio stream using YouTube fallback with network extraction"""
        try:
            # For Spotify, we need to search YouTube for the same song
            search_query = f"{song.get('title', '')} {song.get('artist', '')}"
            youtube_result = await self._network_search_youtube(search_query)
            
            if youtube_result:
                return await self._get_network_youtube_stream(youtube_result)
                
        except Exception as e:
            logger.error(f"Spotify network stream error: {e}")
        return None
    
    async def _get_network_soundcloud_stream(self, song: Dict) -> Optional[discord.FFmpegPCMAudio]:
        """Get SoundCloud audio stream using network-extracted URLs"""
        try:
            stream_url = song.get('stream_url', '')
            if not stream_url:
                # Fallback to YouTube search
                search_query = f"{song.get('title', '')} {song.get('artist', '')}"
                youtube_result = await self._network_search_youtube(search_query)
                if youtube_result:
                    return await self._get_network_youtube_stream(youtube_result)
                return None
            
            # Test if stream URL is accessible
            try:
                async with self.session.head(stream_url, timeout=5) as response:
                    if response.status != 200:
                        # Fallback to YouTube
                        search_query = f"{song.get('title', '')} {song.get('artist', '')}"
                        youtube_result = await self._network_search_youtube(search_query)
                        if youtube_result:
                            return await self._get_network_youtube_stream(youtube_result)
                        return None
            except:
                # Fallback to YouTube
                search_query = f"{song.get('title', '')} {song.get('artist', '')}"
                youtube_result = await self._network_search_youtube(search_query)
                if youtube_result:
                    return await self._get_network_youtube_stream(youtube_result)
                return None
            
            ffmpeg_options = {
                'before_options': '-reconnect 1 -reconnect_streamed 1 -reconnect_delay_max 2',
                'options': '-vn -bufsize 512k'
            }
            
            return discord.FFmpegPCMAudio(stream_url, **ffmpeg_options)
            
        except Exception as e:
            logger.error(f"SoundCloud network stream error: {e}")
            # Fallback to YouTube
            try:
                search_query = f"{song.get('title', '')} {song.get('artist', '')}"
                youtube_result = await self._network_search_youtube(search_query)
                if youtube_result:
                    return await self._get_network_youtube_stream(youtube_result)
            except:
                pass
        return None
    
    async def download(self, song: Dict, quality: str = "high", user: discord.Member = None) -> Optional[str]:
        """Download a song to a file with enhanced metadata embedding (inspired by app.py)"""
        try:
            provider = song.get('provider', 'youtube')
            title = song.get('title', 'Unknown')
            artist = song.get('artist', song.get('uploader', 'Unknown Artist'))
            album = song.get('album', 'Unknown Album')
            thumbnail_url = song.get('thumbnail', '')
            
            # Enhanced filename sanitization (inspired by app.py)
            def sanitize_filename(name):
                return "".join(c for c in name if c.isalnum() or c in " _-").rstrip()
            
            safe_title = sanitize_filename(title)
            safe_title = re.sub(r'[-\s]+', '-', safe_title)
            
            # Set quality options
            quality_map = {
                'high': 'bestaudio[ext=m4a]/bestaudio/best',
                'medium': 'bestaudio[height<=480]/bestaudio/best',
                'low': 'bestaudio[height<=360]/bestaudio/best'
            }
            
            format_selector = quality_map.get(quality, quality_map['high'])
            
            # Create download directory if it doesn't exist
            os.makedirs(DOWNLOAD_PATH, exist_ok=True)
            
            # Create final file path
            final_path = os.path.join(DOWNLOAD_PATH, f"{safe_title}.mp3")
            
            # Enhanced download options with progress tracking and thumbnail
            ydl_opts = self._build_yt_dlp_opts({
                'format': format_selector,
                'outtmpl': final_path,
                'writethumbnail': True,  # Download thumbnail like app.py
                'postprocessors': [{
                    'key': 'FFmpegExtractAudio',
                    'preferredcodec': 'mp3',
                    'preferredquality': '192',
                }]
            })
            
            # Add progress tracking (inspired by app.py)
            def progress_hook(d):
                if d['status'] == 'downloading':
                    logger.info(f"Downloading: {d.get('_percent_str', '0%')} - ETA: {d.get('_eta_str', 'Unknown')}")
                elif d['status'] == 'finished':
                    logger.info("Download finished, processing...")
            
            ydl_opts['progress_hooks'] = [progress_hook]
            
            url = song.get('url', '')
            if not url:
                return None
            
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(url, download=True)
            
            # Enhanced metadata embedding (inspired by app.py)
            if os.path.exists(final_path):
                try:
                    # Embed ID3 metadata
                    from mutagen.easyid3 import EasyID3
                    from mutagen.id3 import ID3, APIC
                    
                    try:
                        audio = EasyID3(final_path)
                    except:
                        audio = EasyID3()
                    
                    audio["title"] = title
                    audio["artist"] = artist
                    audio["album"] = album
                    audio.save(final_path)
                    
                    # Embed thumbnail if available
                    if thumbnail_url:
                        try:
                            img_data = requests.get(thumbnail_url, timeout=10).content
                            audio = ID3(final_path)
                            audio['APIC'] = APIC(
                                encoding=3,
                                mime='image/jpeg',
                                type=3,
                                desc='Cover',
                                data=img_data
                            )
                            audio.save(final_path)
                        except Exception as e:
                            logger.warning(f"Could not embed thumbnail: {e}")
                    
                    logger.info(f"Successfully downloaded and embedded metadata for: {title}")
                    return final_path
                    
                except Exception as e:
                    logger.error(f"Metadata embedding error: {e}")
                    return final_path  # Return file even if metadata failed
            else:
                return None
                
        except Exception as e:
            logger.error(f"Download error: {e}")
            if 'final_path' in locals() and os.path.exists(final_path):
                os.remove(final_path)
            return None
    
    async def get_playlist_info(self, url: str) -> Optional[List[Dict]]:
        """Get playlist information from a URL"""
        try:
            # Detect provider from URL
            if 'youtube.com/playlist' in url or 'youtu.be/playlist' in url:
                return await self._get_youtube_playlist(url)
            elif 'spotify.com/playlist' in url:
                return await self._get_spotify_playlist(url)
            elif 'soundcloud.com' in url and '/sets/' in url:
                return await self._get_soundcloud_playlist(url)
                
        except Exception as e:
            logger.error(f"Playlist info error: {e}")
        return None
    
    async def _get_youtube_playlist(self, url: str) -> Optional[List[Dict]]:
        """Get YouTube playlist information"""
        try:
            ydl_opts = {
                'format': 'bestaudio/best',
                'noplaylist': False,
                'quiet': True,
                'no_warnings': True,
                'extract_flat': True
            }
            
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(url, download=False)
                
                if info and 'entries' in info:
                    playlist = []
                    for entry in info['entries']:
                        if entry:
                            playlist.append({
                                'title': entry.get('title', 'Unknown'),
                                'url': entry.get('url', entry.get('webpage_url', '')),
                                'duration': entry.get('duration', 0),
                                'thumbnail': entry.get('thumbnail', ''),
                                'uploader': entry.get('uploader', 'Unknown'),
                                'provider': 'youtube',
                                'id': entry.get('id', '')
                            })
                    return playlist
                    
        except Exception as e:
            logger.error(f"YouTube playlist error: {e}")
        return None
    
    async def _get_spotify_playlist(self, url: str) -> Optional[List[Dict]]:
        """Get Spotify playlist information"""
        try:
            if not self.spotify_client:
                return None
                
            # Extract playlist ID from URL
            playlist_id = url.split('/')[-1].split('?')[0]
            
            results = self.spotify_client.playlist_tracks(playlist_id)
            playlist = []
            
            for item in results['items']:
                if item['track']:
                    track = item['track']
                    playlist.append({
                        'title': track['name'],
                        'artist': ', '.join([artist['name'] for artist in track['artists']]),
                        'album': track['album']['name'],
                        'duration': track['duration_ms'] // 1000,
                        'thumbnail': track['album']['images'][0]['url'] if track['album']['images'] else '',
                        'provider': 'spotify',
                        'id': track['id'],
                        'url': track['external_urls']['spotify']
                    })
            
            return playlist
            
        except Exception as e:
            logger.error(f"Spotify playlist error: {e}")
        return None
    
    async def _get_soundcloud_playlist(self, url: str) -> Optional[List[Dict]]:
        """Get SoundCloud playlist information"""
        try:
            if not self.soundcloud_client:
                return None
                
            # This would require additional SoundCloud API implementation
            # For now, return None
            return None
            
        except Exception as e:
            logger.error(f"SoundCloud playlist error: {e}")
        return None
    
    async def close(self):
        """Close the provider manager"""
        if self.session:
            await self.session.close()
