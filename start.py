#!/usr/bin/env python3
"""
Muzzoc Discord Music Bot Startup Script
"""

import os
import sys
import subprocess
import logging
from pathlib import Path

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def check_requirements():
    """Check if all requirements are installed"""
    try:
        import discord
        import yt_dlp
        import aiohttp
        import spotipy
        import soundcloud
        logger.info("✅ All required packages are installed")
        return True
    except ImportError as e:
        logger.error(f"❌ Missing required package: {e}")
        logger.error("Please run: pip install -r requirements.txt")
        return False

def check_ffmpeg():
    """Check if FFmpeg is installed"""
    try:
        result = subprocess.run(['ffmpeg', '-version'], 
                              capture_output=True, text=True, timeout=5)
        if result.returncode == 0:
            logger.info("✅ FFmpeg is installed")
            return True
        else:
            logger.error("❌ FFmpeg not found")
            return False
    except (subprocess.TimeoutExpired, FileNotFoundError):
        logger.error("❌ FFmpeg not found in PATH")
        logger.error("Please install FFmpeg:")
        logger.error("  Windows: Download from https://ffmpeg.org/download.html")
        logger.error("  macOS: brew install ffmpeg")
        logger.error("  Linux: sudo apt install ffmpeg")
        return False

def check_env_file():
    """Check if .env file exists"""
    env_path = Path(".env")
    if env_path.exists():
        logger.info("✅ .env file found")
        return True
    else:
        logger.warning("⚠️  .env file not found")
        logger.warning("Please create a .env file with your Discord token:")
        logger.warning("DISCORD_TOKEN=your_discord_bot_token")
        return False

def create_directories():
    """Create necessary directories"""
    directories = ['downloads', 'logs']
    for directory in directories:
        Path(directory).mkdir(exist_ok=True)
        logger.info(f"✅ Created directory: {directory}")

def main():
    """Main startup function"""
    logger.info("🚀 Starting Muzzoc Discord Music Bot...")
    
    # Check requirements
    if not check_requirements():
        sys.exit(1)
    
    # Check FFmpeg
    if not check_ffmpeg():
        sys.exit(1)
    
    # Check .env file
    check_env_file()
    
    # Create directories
    create_directories()
    
    # Start the bot
    logger.info("🎵 Starting Muzzoc Bot...")
    try:
        from bot import bot
        bot.run()
    except KeyboardInterrupt:
        logger.info("👋 Bot stopped by user")
    except Exception as e:
        logger.error(f"❌ Bot error: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
