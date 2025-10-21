# Installing PyNaCl for Muzzoc Bot

PyNaCl is required for voice functionality in Discord bots. Here are several methods to install it:

## Method 1: Standard Installation (Recommended)

```bash
pip install PyNaCl
```

## Method 2: Using Conda (Alternative)

```bash
conda install pynacl
```

## Method 3: System Package Manager

### Ubuntu/Debian:
```bash
sudo apt-get install python3-nacl
```

### CentOS/RHEL:
```bash
sudo yum install python3-nacl
```

### Arch Linux:
```bash
sudo pacman -S python-pynacl
```

## Method 4: Docker (If compilation fails)

Create a `Dockerfile`:

```dockerfile
FROM python:3.11-slim

# Install system dependencies
RUN apt-get update && apt-get install -y \
    libsodium-dev \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies
COPY requirements.txt .
RUN pip install -r requirements.txt

# Copy bot files
COPY . .

# Run the bot
CMD ["python", "bot.py"]
```

Then build and run:
```bash
docker build -t muzzoc-bot .
docker run -e DISCORD_TOKEN=your_token muzzoc-bot
```

## Method 5: Pre-compiled Wheels

If compilation fails, try installing from pre-compiled wheels:

```bash
pip install --only-binary=all PyNaCl
```

## Method 6: Alternative Python Environment

Use a different Python environment that has PyNaCl pre-installed:

```bash
# Using pyenv
pyenv install 3.11.0
pyenv virtualenv 3.11.0 muzzoc-env
pyenv activate muzzoc-env
pip install PyNaCl
```

## Troubleshooting

### Common Issues:

1. **Compilation Error**: PyNaCl requires libsodium to be installed
   ```bash
   # Ubuntu/Debian
   sudo apt-get install libsodium-dev
   
   # macOS
   brew install libsodium
   ```

2. **Permission Error**: Use virtual environment
   ```bash
   python -m venv venv
   source venv/bin/activate  # Linux/macOS
   # or
   venv\Scripts\activate  # Windows
   pip install PyNaCl
   ```

3. **Architecture Issues**: Try different Python version
   ```bash
   pip install PyNaCl==1.4.0  # Older version
   ```

## Verification

Test if PyNaCl is working:

```python
try:
    import nacl
    print("✅ PyNaCl is installed and working!")
except ImportError:
    print("❌ PyNaCl is not installed")
```

## Alternative: Text-Only Mode

If PyNaCl cannot be installed, the bot will still work for:
- Queue management
- Download functionality  
- Text-based commands
- Metadata display

Voice features will be disabled until PyNaCl is installed.

## Support

If you continue to have issues:
1. Check your Python version (3.8+ required)
2. Ensure you have build tools installed
3. Try using a virtual environment
4. Consider using Docker for a clean environment
