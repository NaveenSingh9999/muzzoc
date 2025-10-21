# Muzzoc - Advanced Discord Music Bot

A modern Discord music bot built with Discord.py 2.3+ featuring slash commands, multi-provider support, and advanced audio streaming capabilities.

## Features

### 🎵 Music Playback
- **Multi-Provider Support**: YouTube, Spotify, SoundCloud
- **Network-Based Extraction**: Direct MP3/MP4 extraction from network traffic
- **Advanced Streaming**: Chunk combining and optimized audio streaming
- **High-Quality Audio**: Best available quality from each provider
- **Smart Provider Selection**: Automatic fallback and provider-specific optimizations

### 🎮 Modern UI/UX
- **Slash Commands**: Modern Discord slash command interface
- **Interactive Buttons**: Play, pause, skip, shuffle, loop controls
- **Rich Embeds**: Beautiful song information displays
- **Real-time Updates**: Dynamic queue and player status

### 📋 Queue Management
- **Smart Queue**: Add songs to specific positions
- **Playlist Support**: Create and manage custom playlists
- **Loop Modes**: Single song, queue, or off
- **Shuffle**: Randomize queue order
- **Queue Persistence**: Maintains queue across bot restarts

### ⬇️ Download Support
- **Multi-Quality Downloads**: High, medium, low quality options
- **Provider-Specific**: Optimized downloads for each source
- **Temporary Files**: Secure file handling with auto-cleanup

## Commands

### Music Commands
- `/play <song> [provider] [position]` - Play a song
- `/pause` - Pause current song
- `/resume` - Resume paused song
- `/skip` - Skip current song
- `/stop` - Stop music and clear queue

### Queue Commands
- `/addtoqueue <song> [provider] [position]` - Add song to queue
- `/clearqueue` - Clear the music queue
- `/queue` - Show current queue
- `/nowplaying` - Show currently playing song

### Playlist Commands
- `/playlist create <name>` - Create a new playlist
- `/playlist add <name> <song>` - Add song to playlist
- `/playlist play <name>` - Play a playlist
- `/playlist list` - List your playlists
- `/playlist delete <name>` - Delete a playlist

### Download Commands
- `/download <song> [provider] [quality]` - Download a song

## Setup

### Prerequisites
- Python 3.8+
- FFmpeg installed on your system
- Discord Bot Token
- No API keys required (uses network-based extraction)

### Installation

1. **Clone the repository**
   ```bash
   git clone <repository-url>
   cd Muzzoc
   ```

2. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

3. **Install FFmpeg**
   - **Windows**: Download from https://ffmpeg.org/download.html
   - **macOS**: `brew install ffmpeg`
   - **Linux**: `sudo apt install ffmpeg`

4. **Set up environment variables**
   Create a `.env` file with:
   ```env
   DISCORD_TOKEN=your_discord_bot_token
   ```

5. **Run the bot**
   ```bash
   python bot.py
   ```

### Network-Based Extraction

#### How It Works
- **YouTube**: Direct network interception to extract MP3/MP4 URLs
- **Spotify**: Web interface scraping with YouTube fallback
- **SoundCloud**: Direct stream URL extraction
- **No API Keys Required**: Uses network traffic analysis

## Configuration

Edit `config.py` to customize:
- Bot prefix
- Maximum queue size
- Maximum playlist size
- Download path
- Logging level

## Advanced Features

### Network-Based Extraction
The bot uses advanced network interception techniques:
- **Direct URL Extraction**: Intercepts network traffic to find MP3/MP4 URLs
- **HTML Parsing**: Extracts metadata from web pages
- **Stream Testing**: Validates audio URLs before use
- **Fallback System**: YouTube fallback for all providers

### Provider Optimization
Each provider is optimized for best performance:
- **YouTube**: Network traffic analysis for direct audio URLs
- **Spotify**: Web scraping with YouTube fallback
- **SoundCloud**: Direct stream URL extraction

### Queue Management
- Position-based insertion
- Smart provider fallback
- Queue persistence
- Playlist integration

## Troubleshooting

### Common Issues

1. **"FFmpeg not found"**
   - Ensure FFmpeg is installed and in your PATH
   - On Windows, add FFmpeg to your system PATH

2. **"No results found"**
   - Check your internet connection
   - Verify provider API keys (if using Spotify/SoundCloud)
   - Try different search terms

3. **"Audio quality issues"**
   - Check your internet connection
   - Try different quality settings
   - Verify FFmpeg installation

### Logs
The bot logs important events to the console. Check logs for:
- Connection issues
- Provider errors
- Audio stream problems

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Test thoroughly
5. Submit a pull request

## License

This project is licensed under the MIT License - see the LICENSE file for details.

## Support

For support, please:
1. Check the troubleshooting section
2. Search existing issues
3. Create a new issue with detailed information

## Credits

- **Discord.py**: Modern Discord API wrapper
- **yt-dlp**: YouTube audio extraction
- **Spotipy**: Spotify API wrapper
- **SoundCloud**: SoundCloud API
- **FFmpeg**: Audio processing

---

**Muzzoc** - Bringing the world's music to Discord with style! 🎵
