import discord
import asyncio
import os
from threading import Thread
from flask import Flask
from rustplus import RustSocket, EntityEvent

# ==========================================
# CONFIGURATION (Loaded from Cloud Settings)
# ==========================================
# We use os.getenv to safely pull your secrets from the cloud settings
RUST_IP = os.getenv("RUST_IP")
RUST_PORT = os.getenv("RUST_PORT")
STEAM_ID = os.getenv("STEAM_ID") 
PLAYER_TOKEN = os.getenv("PLAYER_TOKEN")
DISCORD_TOKEN = os.getenv("DISCORD_TOKEN")
ALERT_CHANNEL_ID = os.getenv("ALERT_CHANNEL_ID")

# Convert numbers to integers (safely)
try:
    if STEAM_ID: STEAM_ID = int(STEAM_ID)
    if PLAYER_TOKEN: PLAYER_TOKEN = int(PLAYER_TOKEN)
    if ALERT_CHANNEL_ID: ALERT_CHANNEL_ID = int(ALERT_CHANNEL_ID)
    if RUST_PORT: RUST_PORT = int(RUST_PORT)
except ValueError:
    print("Error: SteamID, Token, or Channel ID is not a number!")

# ==========================================
# 1. WEB SERVER (Keeps Bot Awake)
# ==========================================
app = Flask('')

@app.route('/')
def home():
    return "Rust Bot is Alive and Listening!"

def run_web():
    # Use port 8080 or the environment's assigned port
    port = int(os.environ.get('PORT', 8080))
    app.run(host='0.0.0.0', port=port)

def keep_alive():
    t = Thread(target=run_web)
    t.start()

# ==========================================
# 2. RUST & DISCORD CONNECTION
# ==========================================
intents = discord.Intents.default()
intents.message_content = True
bot = discord.Client(intents=intents)

# Initialize Rust Socket
rust_socket = None
if RUST_IP and PLAYER_TOKEN:
    rust_socket = RustSocket(RUST_IP, RUST_PORT, STEAM_ID, PLAYER_TOKEN)
else:
    print("WARNING: Rust config missing! Bot will not connect to game.")

# ==========================================
# 3. RUST EVENTS (Raid Alarm)
# ==========================================
if rust_socket:
    @rust_socket.event
    async def entity_event(event: EntityEvent):
        # This runs when a Smart Alarm or Switch changes state
        # event.value is True (On) or False (Off)
        if event.value: 
            print(f"Smart Device triggered! ID: {event.entity_id}")
            channel = bot.get_channel(ALERT_CHANNEL_ID)
            if channel:
                # You can customize this message!
                await channel.send(f"@everyone 🚨 **RAID ALARM TRIGGERED!** 🚨\nDevice ID: {event.entity_id} is ACTIVE.")

# ==========================================
# 4. DISCORD EVENTS
# ==========================================
@bot.event
async def on_ready():
    print(f'Logged in as {bot.user}')
    
    if rust_socket:
        try:
            await rust_socket.connect()
            print("✅ Connected to Rust Server!")
        except Exception as e:
            print(f"❌ Failed to connect to Rust: {e}")
    else:
        print("❌ Rust Socket not initialized (Check env vars)")

@bot.event
async def on_message(message):
    if message.author == bot.user:
        return

    # Command: !status
    if message.content == '!status':
        if rust_socket:
            try:
                info = await rust_socket.get_info()
                await message.channel.send(f"**Server:** {info.name}\n**Players:** {info.players}/{info.max_players}\n**Queued:** {info.queued_players}")
            except:
                await message.channel.send("❌ Could not get server info (Game might be down or bot disconnected).")
        else:
            await message.channel.send("❌ Bot is not configured for Rust.")

# ==========================================
# 5. START
# ==========================================
if __name__ == "__main__":
    keep_alive()
    if DISCORD_TOKEN:
        bot.run(DISCORD_TOKEN)
    else:
        print("Error: DISCORD_TOKEN is missing!")