import discord
from discord.ext import commands
from discord import app_commands
import asyncio
import aiohttp
import os
from typing import Optional, List, Dict, Any
import json
import logging

from config import *
from music_player import MusicPlayer
from providers import ProviderManager
from ui_components import MusicUI
from voice_fallback import VoiceFallback

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class MuzzocBot(commands.Bot):
    def __init__(self):
        intents = discord.Intents.all()
        intents.message_content = True
        intents.voice_states = True
        
        super().__init__(
            command_prefix=BOT_PREFIX,
            intents=intents,
            help_command=None
        )
        
        self.music_players: Dict[int, MusicPlayer] = {}
        self.provider_manager = ProviderManager()
        self.ui = MusicUI()
        self.voice_fallback = VoiceFallback()
        
    async def setup_hook(self):
        """Called when the bot is starting up"""
        logger.info("Setting up Muzzoc Bot...")
        
        # Ensure downloads directory exists
        os.makedirs(DOWNLOAD_PATH, exist_ok=True)
        
        # Initialize provider manager
        await self.provider_manager.initialize()
        
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
        
    def get_music_player(self, guild_id: int) -> MusicPlayer:
        """Get or create a music player for a guild"""
        if guild_id not in self.music_players:
            self.music_players[guild_id] = MusicPlayer(guild_id, self.provider_manager)
        return self.music_players[guild_id]

# Create bot instance
bot = MuzzocBot()

@bot.tree.command(name="play", description="Play music from various providers")
@app_commands.describe(
    song="Song name or URL to play",
    provider="Music provider (yt, spotify, soundcloud)",
    position="Position in queue (optional)"
)
async def play_command(
    interaction: discord.Interaction,
    song: str,
    provider: str = "yt",
    position: Optional[int] = None
):
    """Play a song from the specified provider"""
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
            await channel.connect()
        
        # Search for the song
        search_result = await bot.provider_manager.search(song, provider)
        if not search_result:
            await interaction.followup.send("❌ No results found for your search!")
            return
            
        # Add to queue
        queue_position = await music_player.add_to_queue(
            search_result, 
            interaction.user, 
            position
        )
        
        # Create and send UI
        embed = bot.ui.create_now_playing_embed(search_result, queue_position)
        view = bot.ui.create_player_controls(music_player)
        
        await interaction.followup.send(embed=embed, view=view)
        
        # Start playing if not already playing
        if not music_player.is_playing():
            await music_player.play_next()
            
    except Exception as e:
        logger.error(f"Error in play command: {e}")
        await interaction.followup.send(f"❌ An error occurred: {str(e)}")

@bot.tree.command(name="pause", description="Pause the current song")
async def pause_command(interaction: discord.Interaction):
    """Pause the current song"""
    await interaction.response.defer()
    
    try:
        guild_id = interaction.guild_id
        music_player = bot.get_music_player(guild_id)
        
        if not music_player.is_playing():
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
        
        if not music_player.is_paused():
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
        
        if not music_player.is_playing():
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

@bot.tree.command(name="clearqueue", description="Clear the music queue")
async def clearqueue_command(interaction: discord.Interaction):
    """Clear the music queue"""
    await interaction.response.defer()
    
    try:
        guild_id = interaction.guild_id
        music_player = bot.get_music_player(guild_id)
        
        queue_size = music_player.get_queue_size()
        music_player.clear_queue()
        
        await interaction.followup.send(f"🗑️ Cleared {queue_size} songs from the queue!")
        
    except Exception as e:
        logger.error(f"Error in clearqueue command: {e}")
        await interaction.followup.send(f"❌ An error occurred: {str(e)}")

@bot.tree.command(name="addtoqueue", description="Add a song to the queue")
@app_commands.describe(
    song="Song name or URL to add",
    provider="Music provider (yt, spotify, soundcloud)",
    position="Position in queue (optional)"
)
async def addtoqueue_command(
    interaction: discord.Interaction,
    song: str,
    provider: str = "yt",
    position: Optional[int] = None
):
    """Add a song to the queue"""
    await interaction.response.defer()
    
    try:
        guild_id = interaction.guild_id
        music_player = bot.get_music_player(guild_id)
        
        # Search for the song
        search_result = await bot.provider_manager.search(song, provider)
        if not search_result:
            await interaction.followup.send("❌ No results found for your search!")
            return
            
        # Add to queue
        queue_position = await music_player.add_to_queue(
            search_result, 
            interaction.user, 
            position
        )
        
        embed = bot.ui.create_queue_added_embed(search_result, queue_position)
        await interaction.followup.send(embed=embed)
        
    except Exception as e:
        logger.error(f"Error in addtoqueue command: {e}")
        await interaction.followup.send(f"❌ An error occurred: {str(e)}")

@bot.tree.command(name="playlist", description="Manage playlists")
@app_commands.describe(
    action="Playlist action (create, add, play, list, delete)",
    name="Playlist name",
    song="Song to add (for add action)"
)
async def playlist_command(
    interaction: discord.Interaction,
    action: str,
    name: Optional[str] = None,
    song: Optional[str] = None
):
    """Manage playlists"""
    await interaction.response.defer()
    
    try:
        guild_id = interaction.guild_id
        music_player = bot.get_music_player(guild_id)
        
        if action == "create":
            if not name:
                await interaction.followup.send("❌ Please provide a playlist name!")
                return
            await music_player.create_playlist(name, interaction.user)
            await interaction.followup.send(f"✅ Created playlist: **{name}**")
            
        elif action == "add":
            if not name or not song:
                await interaction.followup.send("❌ Please provide playlist name and song!")
                return
            search_result = await bot.provider_manager.search(song, "yt")
            if search_result:
                await music_player.add_to_playlist(name, search_result, interaction.user)
                await interaction.followup.send(f"✅ Added **{search_result['title']}** to **{name}**")
            else:
                await interaction.followup.send("❌ Song not found!")
                
        elif action == "play":
            if not name:
                await interaction.followup.send("❌ Please provide a playlist name!")
                return
            await music_player.play_playlist(name, interaction.user)
            await interaction.followup.send(f"🎵 Playing playlist: **{name}**")
            
        elif action == "list":
            playlists = await music_player.get_user_playlists(interaction.user)
            if playlists:
                embed = bot.ui.create_playlist_list_embed(playlists)
                await interaction.followup.send(embed=embed)
            else:
                await interaction.followup.send("❌ No playlists found!")
                
        elif action == "delete":
            if not name:
                await interaction.followup.send("❌ Please provide a playlist name!")
                return
            success = await music_player.delete_playlist(name, interaction.user)
            if success:
                await interaction.followup.send(f"🗑️ Deleted playlist: **{name}**")
            else:
                await interaction.followup.send("❌ Playlist not found!")
        
    except Exception as e:
        logger.error(f"Error in playlist command: {e}")
        await interaction.followup.send(f"❌ An error occurred: {str(e)}")

@bot.tree.command(name="download", description="Download a song")
@app_commands.describe(
    song="Song name or URL to download",
    provider="Music provider (yt, spotify, soundcloud)",
    quality="Download quality (high, medium, low)"
)
async def download_command(
    interaction: discord.Interaction,
    song: str,
    provider: str = "yt",
    quality: str = "high"
):
    """Download a song"""
    await interaction.response.defer()
    
    try:
        # Search for the song
        search_result = await bot.provider_manager.search(song, provider)
        if not search_result:
            await interaction.followup.send("❌ No results found for your search!")
            return
            
        # Download the song
        download_path = await bot.provider_manager.download(
            search_result, 
            quality, 
            interaction.user
        )
        
        if download_path:
            # Send the file to the user
            file = discord.File(download_path, filename=f"{search_result['title']}.mp3")
            embed = bot.ui.create_download_embed(search_result, quality)
            await interaction.followup.send(embed=embed, file=file)
            
            # Clean up the file
            os.remove(download_path)
        else:
            await interaction.followup.send("❌ Download failed!")
        
    except Exception as e:
        logger.error(f"Error in download command: {e}")
        await interaction.followup.send(f"❌ An error occurred: {str(e)}")

@bot.tree.command(name="queue", description="Show the current queue")
async def queue_command(interaction: discord.Interaction):
    """Show the current queue"""
    await interaction.response.defer()
    
    try:
        guild_id = interaction.guild_id
        music_player = bot.get_music_player(guild_id)
        
        queue_info = music_player.get_queue_info()
        embed = bot.ui.create_queue_embed(queue_info)
        await interaction.followup.send(embed=embed)
        
    except Exception as e:
        logger.error(f"Error in queue command: {e}")
        await interaction.followup.send(f"❌ An error occurred: {str(e)}")

@bot.tree.command(name="nowplaying", description="Show currently playing song")
async def nowplaying_command(interaction: discord.Interaction):
    """Show currently playing song"""
    await interaction.response.defer()
    
    try:
        guild_id = interaction.guild_id
        music_player = bot.get_music_player(guild_id)
        
        current_song = music_player.get_current_song()
        if not current_song:
            await interaction.followup.send("❌ Nothing is currently playing!")
            return
            
        embed = bot.ui.create_now_playing_embed(current_song)
        view = bot.ui.create_player_controls(music_player)
        await interaction.followup.send(embed=embed, view=view)
        
    except Exception as e:
        logger.error(f"Error in nowplaying command: {e}")
        await interaction.followup.send(f"❌ An error occurred: {str(e)}")

@bot.tree.command(name="voiceinfo", description="Show voice functionality status")
async def voiceinfo_command(interaction: discord.Interaction):
    """Show voice functionality status"""
    await interaction.response.defer()
    
    try:
        voice_status = bot.voice_fallback.get_voice_warning()
        
        if voice_status:
            embed = discord.Embed(
                title="🔊 Voice Status",
                description=voice_status,
                color=0xffa500
            )
            embed.add_field(
                name="Alternative Solutions",
                value=(
                    "• Use a different Python environment\n"
                    "• Install PyNaCl on a different system\n"
                    "• Use Docker with pre-installed dependencies\n"
                    "• Contact your system administrator"
                ),
                inline=False
            )
            await interaction.followup.send(embed=embed)
        else:
            embed = discord.Embed(
                title="✅ Voice Status",
                description="Voice functionality is fully available!",
                color=0x00ff00
            )
            await interaction.followup.send(embed=embed)
        
    except Exception as e:
        logger.error(f"Error in voiceinfo command: {e}")
        await interaction.followup.send(f"❌ An error occurred: {str(e)}")

if __name__ == "__main__":
    if not DISCORD_TOKEN:
        logger.error("Discord token not found! Please set DISCORD_TOKEN in your environment variables.")
    else:
        bot.run(DISCORD_TOKEN)
