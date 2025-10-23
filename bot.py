import discord
from discord.ext import commands
from discord import app_commands
import asyncio
import aiohttp
import os
import json
import logging
from datetime import datetime
from typing import Optional, List, Dict, Any
import yt_dlp
import tempfile
import re
from mutagen.easyid3 import EasyID3
from mutagen.id3 import ID3, APIC
import requests

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Bot configuration
DISCORD_TOKEN = os.getenv('DISCORD_TOKEN')
DOWNLOAD_PATH = './downloads'

# Dreamy Night Theme Colors
NIGHT_COLORS = {
    'primary': 0x1a1a2e,      # Deep navy
    'secondary': 0x16213e,    # Dark blue
    'accent': 0x0f3460,       # Midnight blue
    'highlight': 0x533483,    # Purple accent
    'success': 0x4a9eff,      # Electric blue
    'warning': 0xffd700,      # Gold
    'error': 0xff6b6b,        # Coral red
    'gradient_start': 0x1a1a2e,
    'gradient_end': 0x533483
}

# Ensure downloads directory exists
os.makedirs(DOWNLOAD_PATH, exist_ok=True)

class MuzzocBot(commands.Bot):
    def __init__(self):
        intents = discord.Intents.all()
        intents.message_content = True
        intents.voice_states = True
        
        super().__init__(
            command_prefix='/',
            intents=intents,
            help_command=None
        )
        
        self.music_players: Dict[int, 'MusicPlayer'] = {}
        
    async def setup_hook(self):
        """Called when the bot is starting up"""
        logger.info("Setting up Muzzoc Bot...")
        
        # Sync slash commands
        try:
            synced = await self.tree.sync()
            logger.info(f"Synced {len(synced)} command(s)")
        except Exception as e:
            logger.error(f"Failed to sync commands: {e}")
    
    async def on_ready(self):
        """Called when the bot is ready"""
        logger.info(f'{self.user} has connected to Discord!')
        logger.info(f'Bot is in {len(self.guilds)} guilds')
        
    def get_music_player(self, guild_id: int) -> 'MusicPlayer':
        """Get or create a music player for a guild"""
        if guild_id not in self.music_players:
            self.music_players[guild_id] = MusicPlayer(guild_id)
        return self.music_players[guild_id]

class MusicPlayer:
    def __init__(self, guild_id: int):
        self.guild_id = guild_id
        self.voice_client: Optional[discord.VoiceClient] = None
        self.current_song: Optional[Dict] = None
        self.queue: List[Dict] = []
        self.is_playing_flag = False
        self.is_paused_flag = False
        self.volume = 0.8  # Default volume
        self.volume_normalization = True  # Enable volume normalization
        self.is_video_stream = False  # Track if current stream is video
        self.loop_mode = "off"  # Loop modes: "off", "track", "queue"
        
    async def connect(self, voice_channel: discord.VoiceChannel) -> bool:
        """Connect to a voice channel"""
        try:
            if self.voice_client and self.voice_client.is_connected():
                await self.voice_client.move_to(voice_channel)
            else:
                self.voice_client = await voice_channel.connect()
            return True
        except Exception as e:
            logger.error(f"Failed to connect to voice channel: {e}")
            return False
    
    async def disconnect(self):
        """Disconnect from voice channel"""
        if self.voice_client:
            await self.voice_client.disconnect()
            self.voice_client = None
        self.is_playing_flag = False
        self.is_paused_flag = False
        self.current_song = None
    
    async def add_to_queue(self, song: Dict, user: discord.Member, position: Optional[int] = None) -> int:
        """Add a song to the queue"""
        song['added_by'] = user
        song['added_at'] = datetime.now()
        
        if position is None or position >= len(self.queue):
            self.queue.append(song)
            return len(self.queue)
        else:
            self.queue.insert(position, song)
            return position + 1
    
    async def play_next(self):
        """Play the next song in the queue with loop support"""
        if not self.queue and self.loop_mode == "off":
            self.is_playing_flag = False
            self.current_song = None
            return
        
        # Handle loop modes
        if self.loop_mode == "track" and self.current_song:
            # Loop current track - don't change song
            next_song = self.current_song
        elif self.loop_mode == "queue" and not self.queue and self.current_song:
            # Loop entire queue - add current song back to end
            self.queue.append(self.current_song.copy())
            next_song = self.queue.pop(0)
        elif self.queue:
            # Normal queue behavior
            next_song = self.queue.pop(0)
        else:
            self.is_playing_flag = False
            self.current_song = None
            return
            
        self.current_song = next_song
        
        try:
            # Get stream (audio or video) based on stream type
            if self.is_video_stream:
                stream_source = await self.get_video_stream(next_song)
            else:
                stream_source = await self.get_audio_stream(next_song)
                
            if not stream_source:
                logger.error("Failed to get stream")
                await self.play_next()
                return
            
            # Play the stream
            if self.voice_client:
                self.voice_client.play(
                    stream_source,
                    after=lambda e: asyncio.create_task(self._after_playing(e))
                )
                self.is_playing_flag = True
                self.is_paused_flag = False
                
        except Exception as e:
            logger.error(f"Error playing song: {e}")
            await self.play_next()
    
    def _after_playing(self, error):
        """Called after a song finishes playing (sync function to avoid asyncio issues)"""
        if error:
            logger.error(f"Error in audio playback: {error}")
        
        # Schedule the next song to play
        try:
            loop = asyncio.get_event_loop()
            if loop.is_running():
                loop.create_task(self.play_next())
        except Exception as e:
            logger.error(f"Error scheduling next song: {e}")
    
    async def get_audio_stream(self, song: Dict) -> Optional[discord.FFmpegPCMAudio]:
        """Get audio stream using the EXACT same approach as app.py with cookies"""
        try:
            url = song.get('url', '')
            if not url:
                logger.error("No URL found in song data")
                return None
            
            logger.info(f"Getting audio stream for: {song.get('title', 'Unknown')} - {url}")
            
            # Use the EXACT same yt-dlp configuration as app.py + cookies
            ydl_opts = {
                'format': 'bestaudio/best',
                'noplaylist': True,
                'quiet': True,
                'no_warnings': True,
                'cookiefile': 'cookies.txt',  # Use the cookies.txt file
            }
            
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(url, download=False)
                
                if not info:
                    logger.error("Failed to extract info from URL")
                    return None
                
                if 'url' not in info:
                    logger.error(f"No audio URL found in info. Available keys: {list(info.keys())}")
                    return None
                
                audio_url = info['url']
                logger.info(f"Got audio URL: {audio_url[:100]}...")
                
                # Create FFmpeg audio source with enhanced quality and volume normalization
                ffmpeg_options = {
                    'before_options': '-reconnect 1 -reconnect_streamed 1 -reconnect_delay_max 2',
                    'options': '-vn -bufsize 1024k -af "loudnorm=I=-16:TP=-1.5:LRA=11,volume=0.8" -ac 2 -ar 48000'
                }
                
                return discord.FFmpegPCMAudio(audio_url, **ffmpeg_options)
                    
        except Exception as e:
            logger.error(f"Audio stream error: {e}")
            logger.error(f"Song data: {song}")
        return None
    
    async def get_video_stream(self, song: Dict) -> Optional[discord.FFmpegPCMAudio]:
        """Get video stream - extracts audio from video for Discord voice channels"""
        try:
            url = song.get('url', '')
            if not url:
                logger.error("No URL found in song data")
                return None
            
            logger.info(f"Getting video stream for: {song.get('title', 'Unknown')} - {url}")
            
            # Use yt-dlp configuration for video (but extract audio for Discord)
            ydl_opts = {
                'format': 'best[ext=mp4]/best',  # Get video format
                'noplaylist': True,
                'quiet': True,
                'no_warnings': True,
                'cookiefile': 'cookies.txt',  # Use the cookies.txt file
            }
            
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(url, download=False)
                
                if not info:
                    logger.error("Failed to extract info from URL")
                    return None
                
                if 'url' not in info:
                    logger.error(f"No video URL found in info. Available keys: {list(info.keys())}")
                    return None
                
                video_url = info['url']
                logger.info(f"Got video URL: {video_url[:100]}...")
                
                # Create FFmpeg audio source from video (extract audio only for Discord)
                ffmpeg_options = {
                    'before_options': '-reconnect 1 -reconnect_streamed 1 -reconnect_delay_max 2',
                    'options': '-vn -bufsize 1024k -af "loudnorm=I=-16:TP=-1.5:LRA=11,volume=0.8" -ac 2 -ar 48000'
                }
                
                return discord.FFmpegPCMAudio(video_url, **ffmpeg_options)
                    
        except Exception as e:
            logger.error(f"Video stream error: {e}")
            logger.error(f"Song data: {song}")
        return None
    
    async def pause(self):
        """Pause the current song"""
        if self.voice_client and self.voice_client.is_playing():
            self.voice_client.pause()
            self.is_paused_flag = True
            self.is_playing_flag = False
    
    async def resume(self):
        """Resume the current song"""
        if self.voice_client and self.voice_client.is_paused():
            self.voice_client.resume()
            self.is_paused_flag = False
            self.is_playing_flag = True
    
    async def skip(self):
        """Skip the current song"""
        if self.voice_client:
            self.voice_client.stop()
        await self.play_next()
    
    async def stop(self):
        """Stop playing and clear queue"""
        if self.voice_client:
            self.voice_client.stop()
        self.is_playing_flag = False
        self.is_paused_flag = False
        self.current_song = None
        self.queue.clear()
    
    def clear_queue(self):
        """Clear the queue"""
        self.queue.clear()
    
    def get_current_song(self) -> Optional[Dict]:
        """Get the currently playing song"""
        return self.current_song
    
    def get_queue_info(self) -> Dict:
        """Get queue information"""
        return {
            'current_song': self.current_song,
            'queue': self.queue,
            'is_playing': self.is_playing_flag,
            'is_paused': self.is_paused_flag,
            'volume': self.volume,
            'queue_size': len(self.queue)
        }
    
    def get_queue_size(self) -> int:
        """Get the number of songs in the queue"""
        return len(self.queue)
    
    def is_playing_now(self) -> bool:
        """Check if music is currently playing"""
        return self.is_playing_flag and not self.is_paused_flag
    
    def is_paused_now(self) -> bool:
        """Check if music is paused"""
        return self.is_paused_flag
    
    def set_stream_type(self, is_video: bool):
        """Set whether to stream video or audio"""
        self.is_video_stream = is_video
    
    def set_loop_mode(self, mode: str):
        """Set loop mode: off, track, queue"""
        if mode in ["off", "track", "queue"]:
            self.loop_mode = mode
            return True
        return False
    
    def get_loop_mode(self) -> str:
        """Get current loop mode"""
        return self.loop_mode

# Create bot instance
bot = MuzzocBot()

def sanitize_filename(name):
    """Removes invalid characters for file systems (same as app.py)"""
    return "".join(c for c in name if c.isalnum() or c in " _-").rstrip()

async def search_and_download_youtube(song_name: str) -> Optional[Dict]:
    """Search and get YouTube info using the EXACT same approach as app.py with cookies"""
    try:
        # Use the EXACT same yt-dlp configuration as app.py + cookies
        ydl_opts = {
            'format': 'bestaudio/best',
            'default_search': 'ytsearch1',
            'noplaylist': True,
            'quiet': True,
            'no_warnings': True,
            'extract_flat': False,
            'cookiefile': 'cookies.txt',  # Use the cookies.txt file
        }
        
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(song_name, download=False)
        
        if info:
            # Handle playlist results from ytsearch1
            if 'entries' in info and info['entries']:
                # Get the first entry from the search results
                first_entry = info['entries'][0]
                if first_entry:
                    title = sanitize_filename(first_entry.get("title", song_name))
                    artist = first_entry.get("artist") or first_entry.get("uploader") or "Unknown Artist"
                    album = first_entry.get("album") or "Unknown Album"
                    thumbnail_url = first_entry.get("thumbnail")
                    duration = first_entry.get("duration", 0)
                    url = first_entry.get('webpage_url', first_entry.get('url', ''))
                    
                    logger.info(f"Found song: {title} - {url}")
                    
                    return {
                        'title': title,
                        'artist': artist,
                        'album': album,
                        'thumbnail': thumbnail_url,
                        'duration': duration,
                        'url': url,
                        'uploader': first_entry.get('uploader', 'Unknown'),
                        'provider': 'youtube',
                        'id': first_entry.get('id', ''),
                        'view_count': first_entry.get('view_count', 0)
                    }
            else:
                # Handle direct video results
                title = sanitize_filename(info.get("title", song_name))
                artist = info.get("artist") or info.get("uploader") or "Unknown Artist"
                album = info.get("album") or "Unknown Album"
                thumbnail_url = info.get("thumbnail")
                duration = info.get("duration", 0)
                
                # Get the URL - prefer webpage_url for YouTube
                url = info.get('webpage_url', info.get('url', ''))
                if not url:
                    logger.error(f"No URL found in search result. Available keys: {list(info.keys())}")
                    return None
                
                logger.info(f"Found song: {title} - {url}")
                
                return {
                    'title': title,
                    'artist': artist,
                    'album': album,
                    'thumbnail': thumbnail_url,
                    'duration': duration,
                    'url': url,
                    'uploader': info.get('uploader', 'Unknown'),
                    'provider': 'youtube',
                    'id': info.get('id', ''),
                    'view_count': info.get('view_count', 0)
                }
        
    except Exception as e:
        logger.error(f"Search error: {e}")
    return None

@bot.tree.command(name="play", description="Play music from YouTube")
@app_commands.describe(song="Song name or URL to play")
async def play_command(interaction: discord.Interaction, song: str):
    """Play a song using the same approach as app.py"""
    await interaction.response.defer()
    
    try:
        guild_id = interaction.guild_id
        music_player = bot.get_music_player(guild_id)
        
        # Check if user is in a voice channel
        if not interaction.user.voice:
            await interaction.followup.send("❌ You need to be in a voice channel to use this command!")
            return
            
        # Connect to voice channel if not already connected
        if not interaction.guild.voice_client:
            channel = interaction.user.voice.channel
            await music_player.connect(channel)
        
        # Set stream type to audio
        music_player.set_stream_type(False)
        
        # Search for the song using the same approach as app.py
        search_result = await search_and_download_youtube(song)
        if not search_result:
            await interaction.followup.send("❌ No results found for your search!")
            return
            
        # Add to queue
        queue_position = await music_player.add_to_queue(search_result, interaction.user)
        
        # Create beautiful night theme embed
        embed = discord.Embed(
            title="🌙 Now Playing",
            description=f"**{search_result.get('title', 'Unknown')}**\nby {search_result.get('artist', search_result.get('uploader', 'Unknown'))}",
            color=NIGHT_COLORS['primary']
        )
        
        # Add enhanced metadata
        duration = search_result.get('duration', 0)
        if duration > 0:
            duration_str = f"{duration // 60}:{duration % 60:02d}"
            embed.add_field(name="⏱️ Duration", value=duration_str, inline=True)
        
        embed.add_field(name="📊 Position", value=f"#{queue_position}", inline=True)
        embed.add_field(name="🔊 Volume", value=f"{int(music_player.volume * 100)}%", inline=True)
        embed.add_field(name="🎵 Stream Type", value="Audio", inline=True)
        
        # Add loop mode info
        loop_mode = music_player.get_loop_mode()
        loop_icons = {"off": "⏹️", "track": "🔁", "queue": "🔂"}
        embed.add_field(
            name="🔄 Loop Mode", 
            value=f"{loop_icons.get(loop_mode, '⏹️')} {loop_mode.title()}", 
            inline=True
        )
        
        # Thumbnail
        thumbnail = search_result.get('thumbnail', '')
        if thumbnail:
            embed.set_thumbnail(url=thumbnail)
        
        # Beautiful night theme footer
        embed.set_footer(
            text=f"🌙 Requested by {interaction.user.display_name}",
            icon_url=interaction.user.display_avatar.url
        )
        embed.timestamp = datetime.now()
        
        await interaction.followup.send(embed=embed)
        
        # Start playing if not already playing
        if not music_player.is_playing_now():
            await music_player.play_next()
            
    except Exception as e:
        logger.error(f"Error in play command: {e}")
        await interaction.followup.send(f"❌ An error occurred: {str(e)}")

@bot.tree.command(name="stream", description="Stream video content (audio from video)")
@app_commands.describe(video="Video name or URL to stream")
async def stream_command(interaction: discord.Interaction, video: str):
    """Stream video content by extracting audio from video sources"""
    await interaction.response.defer()
    
    try:
        guild_id = interaction.guild_id
        music_player = bot.get_music_player(guild_id)
        
        # Check if user is in a voice channel
        if not interaction.user.voice:
            await interaction.followup.send("❌ You need to be in a voice channel to use this command!")
            return
            
        # Connect to voice channel if not already connected
        if not interaction.guild.voice_client:
            channel = interaction.user.voice.channel
            await music_player.connect(channel)
        
        # Set stream type to video
        music_player.set_stream_type(True)
        
        # Search for the video using the same approach as app.py
        search_result = await search_and_download_youtube(video)
        if not search_result:
            await interaction.followup.send("❌ No results found for your search!")
            return
            
        # Add to queue
        queue_position = await music_player.add_to_queue(search_result, interaction.user)
        
        # Create beautiful night theme embed for video streaming
        embed = discord.Embed(
            title="🌙 Now Streaming (Video Source)",
            description=f"**{search_result.get('title', 'Unknown')}**\nby {search_result.get('artist', search_result.get('uploader', 'Unknown'))}",
            color=NIGHT_COLORS['highlight']  # Purple accent for video streaming
        )
        
        # Add enhanced metadata
        duration = search_result.get('duration', 0)
        if duration > 0:
            duration_str = f"{duration // 60}:{duration % 60:02d}"
            embed.add_field(name="⏱️ Duration", value=duration_str, inline=True)
        
        embed.add_field(name="📊 Position", value=f"#{queue_position}", inline=True)
        embed.add_field(name="🔊 Volume", value=f"{int(music_player.volume * 100)}%", inline=True)
        embed.add_field(name="📺 Stream Type", value="Video (MP4)", inline=True)
        
        # Thumbnail
        thumbnail = search_result.get('thumbnail', '')
        if thumbnail:
            embed.set_thumbnail(url=thumbnail)
        
        # Beautiful night theme footer
        embed.set_footer(
            text=f"🌙 Requested by {interaction.user.display_name}",
            icon_url=interaction.user.display_avatar.url
        )
        embed.timestamp = datetime.now()
        
        await interaction.followup.send(embed=embed)
        
        # Start playing if not already playing
        if not music_player.is_playing_now():
            await music_player.play_next()
            
    except Exception as e:
        logger.error(f"Error in stream command: {e}")
        await interaction.followup.send(f"❌ An error occurred: {str(e)}")

@bot.tree.command(name="loop", description="Set loop mode for music")
@app_commands.describe(mode="Loop mode: off, track, or queue")
async def loop_command(interaction: discord.Interaction, mode: str):
    """Set loop mode with beautiful night theme"""
    await interaction.response.defer()
    
    try:
        guild_id = interaction.guild_id
        music_player = bot.get_music_player(guild_id)
        
        # Validate loop mode
        if mode.lower() not in ["off", "track", "queue"]:
            embed = discord.Embed(
                title="🌙 Invalid Loop Mode",
                description="Please choose: `off`, `track`, or `queue`",
                color=NIGHT_COLORS['error']
            )
            embed.add_field(
                name="Available Modes",
                value="• `off` - No looping\n• `track` - Loop current song\n• `queue` - Loop entire queue",
                inline=False
            )
            await interaction.followup.send(embed=embed)
            return
        
        # Set loop mode
        success = music_player.set_loop_mode(mode.lower())
        
        if success:
            # Create beautiful night theme embed
            embed = discord.Embed(
                title="🌙 Loop Mode Updated",
                color=NIGHT_COLORS['primary']
            )
            
            # Mode-specific styling
            if mode.lower() == "off":
                embed.description = "✨ Loop disabled - music will play normally"
                embed.color = NIGHT_COLORS['secondary']
                loop_icon = "⏹️"
            elif mode.lower() == "track":
                embed.description = "🔄 Current track will loop infinitely"
                embed.color = NIGHT_COLORS['highlight']
                loop_icon = "🔁"
            else:  # queue
                embed.description = "🎵 Entire queue will loop when finished"
                embed.color = NIGHT_COLORS['accent']
                loop_icon = "🔂"
            
            embed.add_field(
                name=f"{loop_icon} Mode",
                value=f"**{mode.title()}**",
                inline=True
            )
            
            # Add current song info if playing
            current_song = music_player.get_current_song()
            if current_song:
                embed.add_field(
                    name="🎶 Now Playing",
                    value=f"**{current_song.get('title', 'Unknown')}**",
                    inline=True
                )
            
            # Add queue info
            queue_size = music_player.get_queue_size()
            embed.add_field(
                name="📋 Queue",
                value=f"{queue_size} song(s)",
                inline=True
            )
            
            # Beautiful footer with night theme
            embed.set_footer(
                text=f"🌙 Requested by {interaction.user.display_name}",
                icon_url=interaction.user.display_avatar.url
            )
            embed.timestamp = datetime.now()
            
            await interaction.followup.send(embed=embed)
        else:
            await interaction.followup.send("❌ Failed to set loop mode!")
            
    except Exception as e:
        logger.error(f"Error in loop command: {e}")
        await interaction.followup.send(f"❌ An error occurred: {str(e)}")

@bot.tree.command(name="pause", description="Pause the current song")
async def pause_command(interaction: discord.Interaction):
    """Pause the current song"""
    await interaction.response.defer()
    
    try:
        guild_id = interaction.guild_id
        music_player = bot.get_music_player(guild_id)
        
        if not music_player.is_playing_now():
            await interaction.followup.send("❌ Nothing is currently playing!")
            return
            
        await music_player.pause()
        await interaction.followup.send("⏸️ Music paused!")
        
    except Exception as e:
        logger.error(f"Error in pause command: {e}")
        await interaction.followup.send(f"❌ An error occurred: {str(e)}")

@bot.tree.command(name="resume", description="Resume the current song")
async def resume_command(interaction: discord.Interaction):
    """Resume the current song"""
    await interaction.response.defer()
    
    try:
        guild_id = interaction.guild_id
        music_player = bot.get_music_player(guild_id)
        
        if not music_player.is_paused_now():
            await interaction.followup.send("❌ Music is not paused!")
            return
            
        await music_player.resume()
        await interaction.followup.send("▶️ Music resumed!")
        
    except Exception as e:
        logger.error(f"Error in resume command: {e}")
        await interaction.followup.send(f"❌ An error occurred: {str(e)}")

@bot.tree.command(name="skip", description="Skip the current song")
async def skip_command(interaction: discord.Interaction):
    """Skip the current song"""
    await interaction.response.defer()
    
    try:
        guild_id = interaction.guild_id
        music_player = bot.get_music_player(guild_id)
        
        if not music_player.is_playing_now():
            await interaction.followup.send("❌ Nothing is currently playing!")
            return
            
        skipped_song = music_player.get_current_song()
        await music_player.skip()
        
        if skipped_song:
            await interaction.followup.send(f"⏭️ Skipped: **{skipped_song['title']}**")
        else:
            await interaction.followup.send("⏭️ Song skipped!")
        
    except Exception as e:
        logger.error(f"Error in skip command: {e}")
        await interaction.followup.send(f"❌ An error occurred: {str(e)}")

@bot.tree.command(name="queue", description="Show the current queue")
async def queue_command(interaction: discord.Interaction):
    """Show the current queue"""
    await interaction.response.defer()
    
    try:
        guild_id = interaction.guild_id
        music_player = bot.get_music_player(guild_id)
        
        queue_info = music_player.get_queue_info()
        embed = discord.Embed(
            title="🌙 Music Queue",
            color=NIGHT_COLORS['primary']
        )
        
        current_song = queue_info.get('current_song')
        queue = queue_info.get('queue', [])
        
        # Current song with enhanced info
        if current_song:
            title = current_song.get('title', 'Unknown')
            artist = current_song.get('artist', current_song.get('uploader', 'Unknown'))
            duration = current_song.get('duration', 0)
            status = "▶️ Playing" if music_player.is_playing_now() else "⏸️ Paused"
            
            embed.add_field(
                name="🎵 Now Playing",
                value=f"**{title}**\nby {artist}",
                inline=False
            )
            
            if duration > 0:
                duration_str = f"{duration // 60}:{duration % 60:02d}"
                embed.add_field(name="⏱️ Duration", value=duration_str, inline=True)
            
            embed.add_field(name="📊 Status", value=status, inline=True)
            embed.add_field(name="🔊 Volume", value=f"{int(music_player.volume * 100)}%", inline=True)
            
            # Show stream type
            stream_type = "📺 Video" if music_player.is_video_stream else "🎵 Audio"
            embed.add_field(name="📺 Stream Type", value=stream_type, inline=True)
            
            # Thumbnail
            thumbnail = current_song.get('thumbnail', '')
            if thumbnail:
                embed.set_thumbnail(url=thumbnail)
        
        # Enhanced queue display
        if queue:
            queue_text = ""
            for i, song in enumerate(queue[:10], 1):  # Show first 10 songs
                title = song.get('title', 'Unknown')
                duration = song.get('duration', 0)
                duration_str = f"{duration // 60}:{duration % 60:02d}" if duration > 0 else "Unknown"
                queue_text += f"**{i}.** {title} `{duration_str}`\n"
            
            if len(queue) > 10:
                queue_text += f"\n*... and {len(queue) - 10} more songs*"
            
            embed.add_field(name="📋 Up Next", value=queue_text, inline=False)
        else:
            embed.add_field(name="📋 Up Next", value="No songs in queue", inline=False)
        
        # Add loop mode info
        loop_mode = music_player.get_loop_mode()
        loop_icons = {"off": "⏹️", "track": "🔁", "queue": "🔂"}
        embed.add_field(
            name="🔄 Loop Mode", 
            value=f"{loop_icons.get(loop_mode, '⏹️')} {loop_mode.title()}", 
            inline=True
        )
        
        # Add total queue info with night theme
        total_songs = len(queue) + (1 if current_song else 0)
        embed.set_footer(
            text=f"🌙 Total: {total_songs} song(s) • Volume: {int(music_player.volume * 100)}%",
            icon_url=interaction.user.display_avatar.url
        )
        embed.timestamp = datetime.now()
        
        await interaction.followup.send(embed=embed)
        
    except Exception as e:
        logger.error(f"Error in queue command: {e}")
        await interaction.followup.send(f"❌ An error occurred: {str(e)}")

@bot.tree.command(name="shuffle", description="Shuffle the current queue")
async def shuffle_command(interaction: discord.Interaction):
    """Shuffle the queue with beautiful night theme"""
    await interaction.response.defer()
    
    try:
        guild_id = interaction.guild_id
        music_player = bot.get_music_player(guild_id)
        
        if not music_player.queue:
            embed = discord.Embed(
                title="🌙 Empty Queue",
                description="No songs in queue to shuffle!",
                color=NIGHT_COLORS['warning']
            )
            await interaction.followup.send(embed=embed)
            return
        
        # Shuffle the queue
        import random
        random.shuffle(music_player.queue)
        
        # Create beautiful night theme embed
        embed = discord.Embed(
            title="🌙 Queue Shuffled",
            description=f"✨ Shuffled {len(music_player.queue)} song(s) in queue",
            color=NIGHT_COLORS['success']
        )
        
        # Show first few shuffled songs
        if music_player.queue:
            preview_text = ""
            for i, song in enumerate(music_player.queue[:5], 1):
                title = song.get('title', 'Unknown')
                preview_text += f"**{i}.** {title}\n"
            
            if len(music_player.queue) > 5:
                preview_text += f"\n*... and {len(music_player.queue) - 5} more songs*"
            
            embed.add_field(name="🎵 Shuffled Queue", value=preview_text, inline=False)
        
        # Add loop mode info
        loop_mode = music_player.get_loop_mode()
        loop_icons = {"off": "⏹️", "track": "🔁", "queue": "🔂"}
        embed.add_field(
            name="🔄 Loop Mode", 
            value=f"{loop_icons.get(loop_mode, '⏹️')} {loop_mode.title()}", 
            inline=True
        )
        
        # Beautiful footer
        embed.set_footer(
            text=f"🌙 Shuffled by {interaction.user.display_name}",
            icon_url=interaction.user.display_avatar.url
        )
        embed.timestamp = datetime.now()
        
        await interaction.followup.send(embed=embed)
        
    except Exception as e:
        logger.error(f"Error in shuffle command: {e}")
        await interaction.followup.send(f"❌ An error occurred: {str(e)}")

@bot.tree.command(name="volume", description="Set or get the current volume")
@app_commands.describe(level="Volume level (0-100)")
async def volume_command(interaction: discord.Interaction, level: Optional[int] = None):
    """Set or get the current volume"""
    await interaction.response.defer()
    
    try:
        guild_id = interaction.guild_id
        music_player = bot.get_music_player(guild_id)
        
        if level is not None:
            if 0 <= level <= 100:
                music_player.volume = level / 100.0
                if music_player.voice_client and music_player.voice_client.source:
                    music_player.voice_client.source.volume = music_player.volume
                
                embed = discord.Embed(
                    title="🌙 Volume Set",
                    description=f"Volume set to **{level}%**",
                    color=NIGHT_COLORS['success']
                )
                await interaction.followup.send(embed=embed)
            else:
                await interaction.followup.send("❌ Volume must be between 0 and 100!")
        else:
            current_volume = int(music_player.volume * 100)
            embed = discord.Embed(
                title="🌙 Current Volume",
                description=f"Volume is set to **{current_volume}%**",
                color=NIGHT_COLORS['primary']
            )
        await interaction.followup.send(embed=embed)
        
    except Exception as e:
        logger.error(f"Error in volume command: {e}")
        await interaction.followup.send(f"❌ An error occurred: {str(e)}")

@bot.tree.command(name="nowplaying", description="Show currently playing song")
async def nowplaying_command(interaction: discord.Interaction):
    """Show currently playing song with enhanced UI"""
    await interaction.response.defer()
    
    try:
        guild_id = interaction.guild_id
        music_player = bot.get_music_player(guild_id)
        
        current_song = music_player.get_current_song()
        if not current_song:
            embed = discord.Embed(
                title="🌙 Nothing Playing",
                description="No music is currently playing",
                color=NIGHT_COLORS['secondary']
            )
            await interaction.followup.send(embed=embed)
            return
        
        # Create beautiful night theme now playing embed
        embed = discord.Embed(
            title="🌙 Now Playing",
            color=NIGHT_COLORS['primary']
        )
        
        # Song info with better formatting
        title = current_song.get('title', 'Unknown')
        artist = current_song.get('artist', current_song.get('uploader', 'Unknown'))
        duration = current_song.get('duration', 0)
        
        embed.add_field(
            name="🎶 Track",
            value=f"**{title}**\nby {artist}",
            inline=False
        )
        
        if duration > 0:
            duration_str = f"{duration // 60}:{duration % 60:02d}"
            embed.add_field(name="⏱️ Duration", value=duration_str, inline=True)
        
        # Volume and status
        current_volume = int(music_player.volume * 100)
        status = "▶️ Playing" if music_player.is_playing_now() else "⏸️ Paused"
        embed.add_field(name="🔊 Volume", value=f"{current_volume}%", inline=True)
        embed.add_field(name="📊 Status", value=status, inline=True)
        
        # Show stream type
        stream_type = "📺 Video" if music_player.is_video_stream else "🎵 Audio"
        embed.add_field(name="📺 Stream Type", value=stream_type, inline=True)
        
        # Queue info
        queue_size = len(music_player.queue)
        if queue_size > 0:
            embed.add_field(name="📋 Queue", value=f"{queue_size} song(s) queued", inline=True)
        
        # Thumbnail
        thumbnail = current_song.get('thumbnail', '')
        if thumbnail:
            embed.set_thumbnail(url=thumbnail)
        
        # Beautiful night theme footer with requester
        added_by = current_song.get('added_by')
        if added_by:
            if isinstance(added_by, (discord.Member, discord.User)):
                requester = added_by.display_name or added_by.name
            else:
                requester = added_by.get('display_name', added_by.get('name', 'Unknown'))
            embed.set_footer(
                text=f"🌙 Requested by {requester}",
                icon_url=interaction.user.display_avatar.url
            )
        
        await interaction.followup.send(embed=embed)
        
    except Exception as e:
        logger.error(f"Error in nowplaying command: {e}")
        await interaction.followup.send(f"❌ An error occurred: {str(e)}")

@bot.tree.command(name="test", description="Test search and audio stream")
@app_commands.describe(song="Song name to test")
async def test_command(interaction: discord.Interaction, song: str):
    """Test search and audio stream functionality"""
    await interaction.response.defer()
    
    try:
        logger.info(f"Testing search for: {song}")
        
        # Test search
        search_result = await search_and_download_youtube(song)
        if not search_result:
            await interaction.followup.send("❌ Search failed - no results found!")
            return
        
        # Test audio stream
        guild_id = interaction.guild_id
        music_player = bot.get_music_player(guild_id)
        
        audio_stream = await music_player.get_audio_stream(search_result)
        if not audio_stream:
            await interaction.followup.send("❌ Audio stream failed!")
            return
        
        embed = discord.Embed(
            title="✅ Test Successful",
            description=f"**{search_result.get('title', 'Unknown')}**\nby {search_result.get('artist', 'Unknown')}",
            color=0x00ff00
        )
        embed.add_field(name="URL", value=search_result.get('url', 'N/A'), inline=False)
        embed.add_field(name="Duration", value=f"{search_result.get('duration', 0)}s", inline=True)
        embed.add_field(name="Audio Stream", value="✅ Working", inline=True)
        
        await interaction.followup.send(embed=embed)
        
    except Exception as e:
        logger.error(f"Test error: {e}")
        await interaction.followup.send(f"❌ Test failed: {str(e)}")

@bot.tree.command(name="download", description="Download a song")
@app_commands.describe(
    song="Song name or URL to download",
    quality="Download quality (high, medium, low)"
)
async def download_command(
    interaction: discord.Interaction,
    song: str,
    quality: str = "high"
):
    """Download a song using the same approach as app.py"""
    await interaction.response.defer()
    
    try:
        # Search for the song
        search_result = await search_and_download_youtube(song)
        if not search_result:
            await interaction.followup.send("❌ No results found for your search!")
            return
            
        # Send initial progress message
        progress_embed = discord.Embed(
            title="⬇️ Downloading...",
            description=f"**{search_result.get('title', 'Unknown')}**\nby {search_result.get('artist', search_result.get('uploader', 'Unknown'))}",
            color=0xffa500
        )
        progress_embed.add_field(name="Status", value="🔍 Searching and preparing download...", inline=False)
        progress_message = await interaction.followup.send(embed=progress_embed)
        
        # Download the song using the same approach as app.py
        download_path = await download_song(search_result, quality)
        
        if download_path:
            # Update progress message to show completion
            progress_embed.title = "✅ Download Complete!"
            progress_embed.color = 0x00ff00
            progress_embed.set_field_at(0, name="Status", value="🎵 Ready to send!", inline=False)
            await progress_message.edit(embed=progress_embed)
            
            # Send the file to the user
            file = discord.File(download_path, filename=f"{search_result['title']}.mp3")
            embed = discord.Embed(
                title="⬇️ Download Complete",
                color=0x00ff00
            )
            embed.add_field(
                name="Track",
                value=f"**{search_result.get('title', 'Unknown')}**\n"
                      f"by {search_result.get('artist', search_result.get('uploader', 'Unknown'))}",
                inline=False
            )
            embed.add_field(name="Quality", value=quality.title(), inline=True)
            
            duration = search_result.get('duration', 0)
            if duration > 0:
                duration_str = f"{duration // 60}:{duration % 60:02d}"
                embed.add_field(name="Duration", value=duration_str, inline=True)
            
            await interaction.followup.send(embed=embed, file=file)
            
            # Clean up the file
            os.remove(download_path)
        else:
            # Update progress message to show failure
            progress_embed.title = "❌ Download Failed"
            progress_embed.color = 0xff0000
            progress_embed.set_field_at(0, name="Status", value="❌ Download failed!", inline=False)
            await progress_message.edit(embed=progress_embed)
        
    except Exception as e:
        logger.error(f"Error in download command: {e}")
        await interaction.followup.send(f"❌ An error occurred: {str(e)}")

async def download_song(song: Dict, quality: str = "high") -> Optional[str]:
    """Download a song using the EXACT same approach as app.py"""
    try:
        title = song.get('title', 'Unknown')
        artist = song.get('artist', song.get('uploader', 'Unknown Artist'))
        album = song.get('album', 'Unknown Album')
        thumbnail_url = song.get('thumbnail', '')
        
        # Sanitize filename (same as app.py)
        safe_title = sanitize_filename(title)
        safe_title = re.sub(r'[-\s]+', '-', safe_title)
        
        # Set quality options
        quality_map = {
            'high': 'bestaudio[ext=m4a]/bestaudio/best',
            'medium': 'bestaudio[height<=480]/bestaudio/best',
            'low': 'bestaudio[height<=360]/bestaudio/best'
        }
        
        format_selector = quality_map.get(quality, quality_map['high'])
        
        # Create final file path
        final_path = os.path.join(DOWNLOAD_PATH, f"{safe_title}.mp3")
        
        # Use the EXACT same yt-dlp configuration as app.py + cookies
        ydl_opts = {
            'format': format_selector,
            'outtmpl': final_path,
            'quiet': True,
            'no_warnings': True,
            'writethumbnail': True,  # downloads thumbnail like app.py
            'cookiefile': 'cookies.txt',  # Use the cookies.txt file
            'postprocessors': [{
                'key': 'FFmpegExtractAudio',
                'preferredcodec': 'mp3',
                'preferredquality': '192',
            }]
        }
        
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
        
        # Enhanced metadata embedding (same as app.py)
        if os.path.exists(final_path):
            try:
                # Embed ID3 metadata
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

if __name__ == "__main__":
    bot.run("MTE4Nzc3Njk2NTYwNDgxOTExNA.GqG78r.2qWUnjSCzS4o_oORC08_ksLRTwL7klMfyUZuKg")
