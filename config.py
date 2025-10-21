import os
from dotenv import load_dotenv

load_dotenv()

# Discord Bot Configuration
DISCORD_TOKEN = os.getenv('DISCORD_TOKEN')

# Bot Configuration
BOT_PREFIX = '/'
MAX_QUEUE_SIZE = 100
MAX_PLAYLIST_SIZE = 50
DOWNLOAD_PATH = './downloads'

# Network-based extraction settings
NETWORK_TIMEOUT = 10
MAX_RETRIES = 3
USER_AGENT_ROTATION = True
