#!/bin/bash

# Muzzoc Discord Music Bot Runner
echo "🎵 Starting Muzzoc Discord Music Bot..."

# Check if Python is available
if ! command -v python3 &> /dev/null; then
    echo "❌ Python 3 is not installed or not in PATH"
    exit 1
fi

# Check if virtual environment exists
if [ ! -d "venv" ]; then
    echo "📦 Creating virtual environment..."
    python3 -m venv venv
fi

# Activate virtual environment
echo "🔧 Activating virtual environment..."
source venv/bin/activate

# Install requirements
echo "📥 Installing requirements..."
pip install -r requirements.txt

# Check if .env file exists
if [ ! -f ".env" ]; then
    echo "⚠️  .env file not found!"
    echo "Please create a .env file with your Discord token:"
    echo "DISCORD_TOKEN=your_discord_bot_token"
    echo ""
    echo "You can copy .env.example to .env and edit it:"
    echo "cp .env.example .env"
    exit 1
fi

# Run the bot
echo "🚀 Starting Muzzoc Bot..."
python3 start.py
