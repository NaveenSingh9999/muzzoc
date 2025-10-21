"""
Voice functionality fallback for systems where PyNaCl cannot be installed
"""

import discord
import logging
from typing import Optional

logger = logging.getLogger(__name__)

class VoiceFallback:
    """Fallback voice functionality when PyNaCl is not available"""
    
    def __init__(self):
        self.pynacl_available = self._check_pynacl()
        
    def _check_pynacl(self) -> bool:
        """Check if PyNaCl is available"""
        try:
            import nacl
            return True
        except ImportError:
            logger.warning("PyNaCl not available - voice features will be limited")
            return False
    
    async def connect_to_voice(self, channel: discord.VoiceChannel) -> Optional[discord.VoiceClient]:
        """Connect to voice channel with fallback"""
        if not self.pynacl_available:
            logger.error("Cannot connect to voice - PyNaCl is required for voice functionality")
            return None
        
        try:
            return await channel.connect()
        except Exception as e:
            logger.error(f"Failed to connect to voice channel: {e}")
            return None
    
    def create_audio_source(self, url: str, **kwargs) -> Optional[discord.FFmpegPCMAudio]:
        """Create audio source with fallback"""
        if not self.pynacl_available:
            logger.error("Cannot create audio source - PyNaCl is required")
            return None
        
        try:
            return discord.FFmpegPCMAudio(url, **kwargs)
        except Exception as e:
            logger.error(f"Failed to create audio source: {e}")
            return None
    
    def get_voice_warning(self) -> str:
        """Get warning message about voice limitations"""
        if not self.pynacl_available:
            return (
                "⚠️ **Voice Features Limited**\n"
                "PyNaCl is not installed, so voice features are disabled.\n"
                "To enable voice features, install PyNaCl:\n"
                "```bash\npip install PyNaCl\n```"
            )
        return ""
