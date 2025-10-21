#!/usr/bin/env python3
"""
OAuth2 Permission Calculator for Muzzoc Discord Bot
"""

# Discord Permission Flags
PERMISSIONS = {
    # Text Permissions
    'SEND_MESSAGES': 0x0000000000000800,
    'SEND_TTS_MESSAGES': 0x0000000000001000,
    'EMBED_LINKS': 0x0000000000004000,
    'ATTACH_FILES': 0x0000000000008000,
    'READ_MESSAGE_HISTORY': 0x0000000000010000,
    'MENTION_EVERYONE': 0x0000000000020000,
    'USE_EXTERNAL_EMOJIS': 0x0000000000040000,
    'ADD_REACTIONS': 0x0000000000040000,
    
    # Voice Permissions
    'CONNECT': 0x0000000000100000,
    'SPEAK': 0x0000000000200000,
    'MUTE_MEMBERS': 0x0000000000400000,
    'DEAFEN_MEMBERS': 0x0000000000800000,
    'MOVE_MEMBERS': 0x0000000001000000,
    'USE_VAD': 0x0000000002000000,
    
    # General Permissions
    'VIEW_CHANNEL': 0x0000000000000400,
    'MANAGE_CHANNELS': 0x0000000000000010,
    'MANAGE_ROLES': 0x0000000000001000,
    'MANAGE_GUILD': 0x0000000000000020,
    'KICK_MEMBERS': 0x0000000000000002,
    'BAN_MEMBERS': 0x0000000000000004,
    'ADMINISTRATOR': 0x0000000000000008,
    
    # Slash Commands
    'USE_SLASH_COMMANDS': 0x0000000000000000,  # No specific permission needed
    
    # Application Commands
    'USE_APPLICATION_COMMANDS': 0x0000000000000000,  # No specific permission needed
}

def calculate_permissions():
    """Calculate required permissions for Muzzoc bot"""
    
    # Essential permissions for music bot
    required_permissions = [
        'VIEW_CHANNEL',           # View channels
        'SEND_MESSAGES',          # Send messages
        'EMBED_LINKS',            # Send embeds
        'ATTACH_FILES',           # Send files (for downloads)
        'READ_MESSAGE_HISTORY',   # Read message history
        'USE_EXTERNAL_EMOJIS',    # Use external emojis
        'ADD_REACTIONS',          # Add reactions
        'CONNECT',                # Connect to voice channels
        'SPEAK',                  # Speak in voice channels
        'USE_VAD',                # Use voice activity detection
    ]
    
    # Calculate permission integer
    permission_int = 0
    for permission in required_permissions:
        if permission in PERMISSIONS:
            permission_int |= PERMISSIONS[permission]
    
    return permission_int, required_permissions

def main():
    """Main function to display OAuth2 permissions"""
    permission_int, permissions = calculate_permissions()
    
    print("🎵 Muzzoc Discord Bot - OAuth2 Permissions")
    print("=" * 50)
    print(f"Permission Integer: {permission_int}")
    print(f"Permission Integer (Hex): 0x{permission_int:08x}")
    print()
    print("Required Permissions:")
    for permission in permissions:
        print(f"  ✓ {permission}")
    print()
    print("OAuth2 URL:")
    print(f"https://discord.com/api/oauth2/authorize?client_id=1187776965604819114&permissions={permission_int}&scope=bot%20applications.commands")
    print()
    print("Note: Replace YOUR_BOT_CLIENT_ID with your actual bot's client ID")
    print()
    print("Additional Information:")
    print("- These permissions allow the bot to:")
    print("  • Connect to voice channels")
    print("  • Play music and audio")
    print("  • Send rich embeds and messages")
    print("  • Download and send files")
    print("  • Use slash commands")
    print("  • React to messages")

if __name__ == "__main__":
    main()
