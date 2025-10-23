import discord
from discord.ext import commands
import asyncio
import aiohttp
import json
import os
from typing import Optional, List, Dict, Any, Union
import logging
from datetime import datetime, timedelta
from voice_fallback import VoiceFallback

logger = logging.getLogger(__name__)

class MusicPlayer:
    def __init__(self, guild_id: int, provider_manager):
        self.guild_id = guild_id
        self.provider_manager = provider_manager
        self.voice_client: Optional[discord.VoiceClient] = None
        self.voice_fallback = VoiceFallback()
        self.current_song: Optional[Dict] = None
        self.queue: List[Dict] = []
        self.is_playing_flag = False
        self.is_paused_flag = False
        self.volume = 0.5
        self.loop_mode = "off"  # off, single, queue
        self.shuffle = False
        self.playlists: Dict[str, List[Dict]] = {}
        self.playlist_owners: Dict[str, int] = {}
        
    async def connect(self, voice_channel: discord.VoiceChannel) -> bool:
        """Connect to a voice channel"""
        try:
            if not self.voice_fallback.pynacl_available:
                logger.error("Cannot connect to voice - PyNaCl is required")
                return False
                
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
        """Play the next song in the queue"""
        if not self.queue:
            self.is_playing = False
            self.current_song = None
            return
        
        # Handle loop modes
        if self.loop_mode == "single" and self.current_song:
            # Keep playing the same song
            pass
        elif self.loop_mode == "queue" and not self.queue:
            # Restart the queue
            self.queue = [self.current_song] if self.current_song else []
        else:
            # Get next song from queue
            if self.shuffle and len(self.queue) > 1:
                import random
                next_song = self.queue.pop(random.randint(0, len(self.queue) - 1))
            else:
                next_song = self.queue.pop(0)
            
            self.current_song = next_song
        
        if not self.current_song:
            return
        
        try:
            # Get audio stream from provider
            audio_source = await self.provider_manager.get_audio_stream(self.current_song)
            if not audio_source:
                logger.error("Failed to get audio stream")
                await self.play_next()
                return
            
            # Play the audio
            if self.voice_client:
                self.voice_client.play(
                    audio_source,
                    after=lambda e: asyncio.create_task(self._after_playing(e))
                )
                self.is_playing_flag = True
                self.is_paused_flag = False
                
        except Exception as e:
            logger.error(f"Error playing song: {e}")
            await self.play_next()
    
    async def _after_playing(self, error):
        """Called after a song finishes playing"""
        if error:
            logger.error(f"Error in audio playback: {error}")
        
        # Handle loop modes
        if self.loop_mode == "single":
            # Keep the current song in the queue
            if self.current_song:
                self.queue.insert(0, self.current_song)
        elif self.loop_mode == "queue":
            # Add current song to end of queue
            if self.current_song:
                self.queue.append(self.current_song)
        
        # Play next song
        await self.play_next()
    
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
    
    def set_volume(self, volume: float):
        """Set the volume (0.0 to 1.0)"""
        self.volume = max(0.0, min(1.0, volume))
        if self.voice_client and self.voice_client.source:
            self.voice_client.source.volume = self.volume
    
    def set_loop_mode(self, mode: str):
        """Set loop mode (off, single, queue)"""
        if mode in ["off", "single", "queue"]:
            self.loop_mode = mode
    
    def toggle_shuffle(self):
        """Toggle shuffle mode"""
        self.shuffle = not self.shuffle
    
    def get_current_song(self) -> Optional[Dict]:
        """Get the currently playing song"""
        return self.current_song
    
    def get_queue_info(self) -> Dict:
        """Get queue information"""
        return {
            'current_song': self.current_song,
            'queue': self.queue,
            'is_playing': self.is_playing,
            'is_paused': self.is_paused,
            'volume': self.volume,
            'loop_mode': self.loop_mode,
            'shuffle': self.shuffle,
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
    
    # Playlist management
    async def create_playlist(self, name: str, user: discord.Member):
        """Create a new playlist"""
        playlist_key = f"{user.id}_{name}"
        if playlist_key not in self.playlists:
            self.playlists[playlist_key] = []
            self.playlist_owners[playlist_key] = user.id
    
    async def add_to_playlist(self, name: str, song: Dict, user: discord.Member):
        """Add a song to a playlist"""
        playlist_key = f"{user.id}_{name}"
        if playlist_key in self.playlists:
            self.playlists[playlist_key].append(song)
        else:
            # Create playlist if it doesn't exist
            await self.create_playlist(name, user)
            self.playlists[playlist_key].append(song)
    
    async def play_playlist(self, name: str, user: discord.Member):
        """Play a playlist"""
        playlist_key = f"{user.id}_{name}"
        if playlist_key in self.playlists:
            # Add all songs from playlist to queue
            for song in self.playlists[playlist_key]:
                await self.add_to_queue(song, user)
            
            # Start playing if not already playing
            if not self.is_playing():
                await self.play_next()
    
    async def get_user_playlists(self, user: discord.Member) -> List[str]:
        """Get user's playlists"""
        user_playlists = []
        for key in self.playlists.keys():
            if key.startswith(f"{user.id}_"):
                playlist_name = key.split("_", 1)[1]
                user_playlists.append(playlist_name)
        return user_playlists
    
    async def delete_playlist(self, name: str, user: discord.Member) -> bool:
        """Delete a playlist"""
        playlist_key = f"{user.id}_{name}"
        if playlist_key in self.playlists:
            del self.playlists[playlist_key]
            del self.playlist_owners[playlist_key]
            return True
        return False
