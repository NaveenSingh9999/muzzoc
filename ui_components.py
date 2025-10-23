import discord
from discord import app_commands
from typing import Optional, List, Dict, Any
import asyncio
from datetime import datetime, timedelta

class MusicUI:
    def __init__(self):
        self.provider_emojis = {
            'youtube': '🔴',
            'spotify': '🟢',
            'soundcloud': '🟠'
        }
    
    def create_now_playing_embed(self, song: Dict, queue_position: int = None) -> discord.Embed:
        """Create a now playing embed"""
        embed = discord.Embed(
            title="🎵 Now Playing",
            color=0x1db954 if song.get('provider') == 'spotify' else 0xff0000
        )
        
        # Song title and artist
        title = song.get('title', 'Unknown')
        artist = song.get('artist', song.get('uploader', 'Unknown'))
        
        if artist and artist != 'Unknown':
            embed.add_field(
                name="Track",
                value=f"**{title}**\nby {artist}",
                inline=False
            )
        else:
            embed.add_field(
                name="Track",
                value=f"**{title}**",
                inline=False
            )
        
        # Duration
        duration = song.get('duration', 0)
        if duration > 0:
            duration_str = self._format_duration(duration)
            embed.add_field(name="Duration", value=duration_str, inline=True)
        
        # Provider
        provider = song.get('provider', 'youtube')
        provider_emoji = self.provider_emojis.get(provider, '🎵')
        embed.add_field(name="Source", value=f"{provider_emoji} {provider.title()}", inline=True)
        
        # Queue position
        if queue_position:
            embed.add_field(name="Position", value=f"#{queue_position}", inline=True)
        
        # Thumbnail
        thumbnail = song.get('thumbnail', '')
        if thumbnail:
            embed.set_thumbnail(url=thumbnail)
        
        # Additional info
        if song.get('album'):
            embed.add_field(name="Album", value=song['album'], inline=True)
        
        if song.get('view_count'):
            embed.add_field(name="Views", value=f"{song['view_count']:,}", inline=True)
        
        # Determine requester name safely whether 'added_by' is a Member/User or a dict
        added_by = song.get('added_by')
        requester_name = 'Unknown'
        if isinstance(added_by, (discord.Member, discord.User)):
            # Prefer display_name for Member, fallback to name
            requester_name = getattr(added_by, 'display_name', None) or getattr(added_by, 'name', 'Unknown')
        elif isinstance(added_by, dict):
            requester_name = added_by.get('display_name') or added_by.get('name', 'Unknown')

        embed.set_footer(text=f"Requested by {requester_name}")
        embed.timestamp = datetime.now()
        
        return embed
    
    def create_queue_embed(self, queue_info: Dict) -> discord.Embed:
        """Create a queue embed"""
        embed = discord.Embed(
            title="📋 Music Queue",
            color=0x7289da
        )
        
        current_song = queue_info.get('current_song')
        queue = queue_info.get('queue', [])
        
        # Current song
        if current_song:
            embed.add_field(
                name="🎵 Now Playing",
                value=f"**{current_song.get('title', 'Unknown')}**\n"
                      f"by {current_song.get('artist', current_song.get('uploader', 'Unknown'))}",
                inline=False
            )
        
        # Queue
        if queue:
            queue_text = ""
            for i, song in enumerate(queue[:10], 1):  # Show first 10 songs
                duration = self._format_duration(song.get('duration', 0))
                queue_text += f"**{i}.** {song.get('title', 'Unknown')} `{duration}`\n"
            
            if len(queue) > 10:
                queue_text += f"\n*... and {len(queue) - 10} more songs*"
            
            embed.add_field(name="📝 Up Next", value=queue_text, inline=False)
        else:
            embed.add_field(name="📝 Up Next", value="Queue is empty", inline=False)
        
        # Queue info
        embed.add_field(
            name="📊 Queue Info",
            value=f"**Total Songs:** {len(queue)}\n"
                  f"**Loop Mode:** {queue_info.get('loop_mode', 'off').title()}\n"
                  f"**Shuffle:** {'On' if queue_info.get('shuffle') else 'Off'}\n"
                  f"**Volume:** {int(queue_info.get('volume', 0.5) * 100)}%",
            inline=True
        )
        
        embed.set_footer(text=f"Use /addtoqueue to add more songs")
        embed.timestamp = datetime.now()
        
        return embed
    
    def create_queue_added_embed(self, song: Dict, position: int) -> discord.Embed:
        """Create an embed for when a song is added to queue"""
        embed = discord.Embed(
            title="✅ Added to Queue",
            color=0x00ff00
        )
        
        embed.add_field(
            name="Track",
            value=f"**{song.get('title', 'Unknown')}**\n"
                  f"by {song.get('artist', song.get('uploader', 'Unknown'))}",
            inline=False
        )
        
        embed.add_field(name="Position", value=f"#{position}", inline=True)
        
        duration = song.get('duration', 0)
        if duration > 0:
            embed.add_field(name="Duration", value=self._format_duration(duration), inline=True)
        
        provider = song.get('provider', 'youtube')
        provider_emoji = self.provider_emojis.get(provider, '🎵')
        embed.add_field(name="Source", value=f"{provider_emoji} {provider.title()}", inline=True)
        
        embed.set_footer(text="Song will play automatically when it's turn comes")
        embed.timestamp = datetime.now()
        
        return embed
    
    def create_playlist_list_embed(self, playlists: List[str]) -> discord.Embed:
        """Create an embed showing user's playlists"""
        embed = discord.Embed(
            title="📚 Your Playlists",
            color=0x9932cc
        )
        
        if playlists:
            playlist_text = ""
            for i, playlist in enumerate(playlists, 1):
                playlist_text += f"**{i}.** {playlist}\n"
            
            embed.add_field(name="Playlists", value=playlist_text, inline=False)
        else:
            embed.add_field(name="Playlists", value="No playlists found", inline=False)
        
        embed.add_field(
            name="Commands",
            value="`/playlist play <name>` - Play a playlist\n"
                  "`/playlist add <name> <song>` - Add song to playlist\n"
                  "`/playlist delete <name>` - Delete a playlist",
            inline=False
        )
        
        embed.set_footer(text="Use /playlist create <name> to create a new playlist")
        embed.timestamp = datetime.now()
        
        return embed
    
    def create_download_embed(self, song: Dict, quality: str) -> discord.Embed:
        """Create an embed for downloaded song"""
        embed = discord.Embed(
            title="⬇️ Download Complete",
            color=0x00ff00
        )
        
        embed.add_field(
            name="Track",
            value=f"**{song.get('title', 'Unknown')}**\n"
                  f"by {song.get('artist', song.get('uploader', 'Unknown'))}",
            inline=False
        )
        
        embed.add_field(name="Quality", value=quality.title(), inline=True)
        
        duration = song.get('duration', 0)
        if duration > 0:
            embed.add_field(name="Duration", value=self._format_duration(duration), inline=True)
        
        provider = song.get('provider', 'youtube')
        provider_emoji = self.provider_emojis.get(provider, '🎵')
        embed.add_field(name="Source", value=f"{provider_emoji} {provider.title()}", inline=True)
        
        embed.set_footer(text="File will be deleted after download")
        embed.timestamp = datetime.now()
        
        return embed
    
    def create_error_embed(self, error_message: str) -> discord.Embed:
        """Create an error embed"""
        embed = discord.Embed(
            title="❌ Error",
            description=error_message,
            color=0xff0000
        )
        
        embed.set_footer(text="Please try again or contact support if the issue persists")
        embed.timestamp = datetime.now()
        
        return embed
    
    def create_player_controls(self, music_player) -> 'PlayerControlsView':
        """Create player control buttons"""
        return PlayerControlsView(music_player)
    
    def _format_duration(self, seconds: int) -> str:
        """Format duration in seconds to MM:SS or HH:MM:SS"""
        if seconds < 3600:
            return f"{seconds // 60}:{seconds % 60:02d}"
        else:
            hours = seconds // 3600
            minutes = (seconds % 3600) // 60
            secs = seconds % 60
            return f"{hours}:{minutes:02d}:{secs:02d}"

class PlayerControlsView(discord.ui.View):
    """Interactive player controls"""
    
    def __init__(self, music_player):
        super().__init__(timeout=300)  # 5 minutes timeout
        self.music_player = music_player
    
    @discord.ui.button(label="⏸️ Pause", style=discord.ButtonStyle.secondary, custom_id="pause")
    async def pause_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Pause button"""
        if self.music_player.is_playing_now():
            await self.music_player.pause()
            await interaction.response.send_message("⏸️ Music paused!", ephemeral=True)
        else:
            await interaction.response.send_message("❌ Nothing is playing!", ephemeral=True)
    
    @discord.ui.button(label="▶️ Resume", style=discord.ButtonStyle.secondary, custom_id="resume")
    async def resume_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Resume button"""
        if self.music_player.is_paused_now():
            await self.music_player.resume()
            await interaction.response.send_message("▶️ Music resumed!", ephemeral=True)
        else:
            await interaction.response.send_message("❌ Music is not paused!", ephemeral=True)
    
    @discord.ui.button(label="⏭️ Skip", style=discord.ButtonStyle.secondary, custom_id="skip")
    async def skip_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Skip button"""
        if self.music_player.is_playing_now():
            await self.music_player.skip()
            await interaction.response.send_message("⏭️ Song skipped!", ephemeral=True)
        else:
            await interaction.response.send_message("❌ Nothing is playing!", ephemeral=True)
    
    @discord.ui.button(label="🔀 Shuffle", style=discord.ButtonStyle.secondary, custom_id="shuffle")
    async def shuffle_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Shuffle button"""
        self.music_player.toggle_shuffle()
        shuffle_status = "On" if self.music_player.shuffle else "Off"
        await interaction.response.send_message(f"🔀 Shuffle {shuffle_status}!", ephemeral=True)
    
    @discord.ui.button(label="🔁 Loop", style=discord.ButtonStyle.secondary, custom_id="loop")
    async def loop_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Loop button"""
        current_mode = self.music_player.loop_mode
        if current_mode == "off":
            self.music_player.set_loop_mode("single")
            await interaction.response.send_message("🔁 Loop: Single song!", ephemeral=True)
        elif current_mode == "single":
            self.music_player.set_loop_mode("queue")
            await interaction.response.send_message("🔁 Loop: Queue!", ephemeral=True)
        else:
            self.music_player.set_loop_mode("off")
            await interaction.response.send_message("🔁 Loop: Off!", ephemeral=True)
    
    @discord.ui.button(label="📋 Queue", style=discord.ButtonStyle.primary, custom_id="queue")
    async def queue_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Queue button"""
        queue_info = self.music_player.get_queue_info()
        embed = MusicUI().create_queue_embed(queue_info)
        await interaction.response.send_message(embed=embed, ephemeral=True)
    
    @discord.ui.button(label="⏹️ Stop", style=discord.ButtonStyle.danger, custom_id="stop")
    async def stop_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Stop button"""
        await self.music_player.stop()
        await interaction.response.send_message("⏹️ Music stopped!", ephemeral=True)
    
    async def on_timeout(self):
        """Called when the view times out"""
        # Disable all buttons
        for item in self.children:
            item.disabled = True
        
        # Update the message if possible
        try:
            await self.message.edit(view=self)
        except:
            pass

class ProviderSelectView(discord.ui.View):
    """Provider selection view"""
    
    def __init__(self, query: str, music_player):
        super().__init__(timeout=60)
        self.query = query
        self.music_player = music_player
    
    @discord.ui.select(
        placeholder="Choose a music provider...",
        options=[
            discord.SelectOption(label="YouTube", value="yt", emoji="🔴", description="Search YouTube for music"),
            discord.SelectOption(label="Spotify", value="spotify", emoji="🟢", description="Search Spotify for music"),
            discord.SelectOption(label="SoundCloud", value="soundcloud", emoji="🟠", description="Search SoundCloud for music")
        ]
    )
    async def provider_select(self, interaction: discord.Interaction, select: discord.ui.Select):
        """Handle provider selection"""
        await interaction.response.defer()
        
        provider = select.values[0]
        
        # Search for the song
        search_result = await self.music_player.provider_manager.search(self.query, provider)
        
        if search_result:
            # Add to queue
            queue_position = await self.music_player.add_to_queue(
                search_result, 
                interaction.user
            )
            
            # Create and send UI
            embed = MusicUI().create_now_playing_embed(search_result, queue_position)
            view = MusicUI().create_player_controls(self.music_player)
            
            await interaction.followup.send(embed=embed, view=view)
            
            # Start playing if not already playing
            if not self.music_player.is_playing_now():
                await self.music_player.play_next()
        else:
            await interaction.followup.send("❌ No results found for your search!")

class VolumeControlView(discord.ui.View):
    """Volume control view"""
    
    def __init__(self, music_player):
        super().__init__(timeout=60)
        self.music_player = music_player
    
    @discord.ui.button(label="🔉", style=discord.ButtonStyle.secondary, custom_id="vol_up")
    async def volume_up(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Increase volume"""
        current_volume = self.music_player.volume
        new_volume = min(1.0, current_volume + 0.1)
        self.music_player.set_volume(new_volume)
        await interaction.response.send_message(f"🔉 Volume: {int(new_volume * 100)}%", ephemeral=True)
    
    @discord.ui.button(label="🔊", style=discord.ButtonStyle.secondary, custom_id="vol_down")
    async def volume_down(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Decrease volume"""
        current_volume = self.music_player.volume
        new_volume = max(0.0, current_volume - 0.1)
        self.music_player.set_volume(new_volume)
        await interaction.response.send_message(f"🔊 Volume: {int(new_volume * 100)}%", ephemeral=True)
    
    @discord.ui.button(label="🔇", style=discord.ButtonStyle.danger, custom_id="vol_mute")
    async def volume_mute(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Mute volume"""
        self.music_player.set_volume(0.0)
        await interaction.response.send_message("🔇 Volume muted!", ephemeral=True)
