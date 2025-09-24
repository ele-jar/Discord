import discord
from discord.ext import tasks
import yaml
import random
import asyncio
import logging
import json # [NEW] Added for state management
import os   # [NEW] Added for file checking
from datetime import datetime, timezone, timedelta

# --- 1. SETUP & CONFIGURATION ---
logging.basicConfig(level=logging.INFO, format='[%(asctime)s] [%(levelname)s] %(message)s', datefmt='%Y-%m-%d %H:%M:%S')
log = logging.getLogger(__name__)

def load_config():
    try:
        with open('config.yaml', 'r') as f:
            log.info("Loading configuration from config.yaml...")
            return yaml.safe_load(f)
    except FileNotFoundError:
        log.error("FATAL: config.yaml not found! Please create it and fill it out.")
        return None
config = load_config()
if not config: exit()

# --- 2. STATE MANAGEMENT (THE FIX) ---
STATE_FILE = 'state.json'
bot_state = {
    "is_on_break": False,
    "phase_end_time_iso": None
}

def load_state():
    """Loads the bot's state from a file."""
    global bot_state
    if os.path.exists(STATE_FILE):
        with open(STATE_FILE, 'r') as f:
            bot_state = json.load(f)
            log.info(f"Loaded previous state from {STATE_FILE}.")
    else:
        log.info(f"{STATE_FILE} not found. Starting with a fresh state.")

def save_state():
    """Saves the bot's current state to a file."""
    with open(STATE_FILE, 'w') as f:
        json.dump(bot_state, f, indent=4)
    log.info(f"Bot state saved to {STATE_FILE}.")

# --- 3. GLOBAL VARIABLES ---
client = discord.Client()
# This timestamp is critical. We only process joins that happen AFTER this time.
PROCESS_JOINS_AFTER = datetime.now(timezone.utc)

# (The schedule_wave function from the previous code is perfect and needs no changes)
async def schedule_wave(message: discord.Message):
    user = message.author
    delay = random.uniform(config['human_touch']['min_wave_delay_seconds'], config['human_touch']['max_wave_delay_seconds'])
    log.info(f"SCHEDULING WAVE for user '{user.name}'. Action will be performed in {delay / 60:.2f} minutes.")
    await asyncio.sleep(delay)
    try:
        log.info(f"WAVE TIME for '{user.name}'. Fetching latest message state.")
        message = await message.channel.fetch_message(message.id)
    except discord.NotFound:
        log.warning(f"Message for user '{user.name}' was deleted. Skipping.")
        return
    wave_button = discord.utils.find(lambda c: isinstance(c, discord.Button) and c.label == "Wave to say hi!", message.components[0].children)
    if wave_button:
        log.info(f"Button found for '{user.name}'. Attempting to click...")
        try:
            await wave_button.click()
            log.info(f"SUCCESS: Successfully waved to '{user.name}'.")
        except Exception as e:
            log.error(f"FAILED to click wave button for '{user.name}'. Error: {e}")
    else:
        log.warning(f"Could not find 'Wave to say hi!' button for '{user.name}'.")

# --- 4. DISCORD EVENT HANDLERS ---
@client.event
async def on_ready():
    global PROCESS_JOINS_AFTER
    log.info(f"Logged in as {client.user.name} ({client.user.id})")
    log.info(f"Monitoring welcome channel ID: {config['discord_settings']['welcome_channel_id']}")
    load_state() # [FIX] Load the persistent state on startup
    PROCESS_JOINS_AFTER = datetime.now(timezone.utc)
    log.info(f"Initialization complete. Will process joins after {PROCESS_JOINS_AFTER.strftime('%Y-%m-%d %H:%M:%S')}")
    manage_breaks.start()

@client.event
async def on_message(message: discord.Message):
    if bot_state["is_on_break"]: return
    if message.channel.id != config['discord_settings']['welcome_channel_id']: return
    if message.type != discord.MessageType.new_member: return
    if message.created_at < PROCESS_JOINS_AFTER:
        log.info(f"Ignoring old join message for '{message.author.name}'.")
        return
    log.info(f"DETECTED new member join: '{message.author.name}'. Handing off to wave scheduler.")
    asyncio.create_task(schedule_wave(message))

# --- 5. REWRITTEN BREAK MANAGEMENT TASK (THE FIX) ---
@tasks.loop(minutes=1) # Check every minute to see if we need to change state
async def manage_breaks():
    global bot_state, PROCESS_JOINS_AFTER
    now = datetime.now(timezone.utc)
    
    # Check if a phase end time exists and if we have passed it
    phase_end_time = datetime.fromisoformat(bot_state["phase_end_time_iso"]) if bot_state["phase_end_time_iso"] else None

    if phase_end_time and now < phase_end_time:
        # We are in the middle of a saved phase. Do nothing and wait.
        remaining_time = phase_end_time - now
        log.info(f"Continuing current phase. {'Break' if bot_state['is_on_break'] else 'Active'} phase ends in {remaining_time.total_seconds() / 60:.2f} minutes.")
        return
        
    # If we are here, it means the previous phase ended or it's the first run. Time to start a new phase.
    if bot_state["is_on_break"]:
        # --- End Break, Start Active Phase ---
        duration_hours = random.uniform(config['break_schedule']['min_active_hours'], config['break_schedule']['max_active_hours'])
        end_time = now + timedelta(hours=duration_hours)
        bot_state["is_on_break"] = False
        bot_state["phase_end_time_iso"] = end_time.isoformat()
        PROCESS_JOINS_AFTER = now # Update the timestamp to ignore joins during the break
        log.info(f"BREAK IS OVER. Bot is now ACTIVE. Next break in {duration_hours:.2f} hours.")
        save_state()
    else:
        # --- End Active, Start Break Phase ---
        duration_minutes = random.uniform(config['break_schedule']['min_break_minutes'], config['break_schedule']['max_break_minutes'])
        end_time = now + timedelta(minutes=duration_minutes)
        bot_state["is_on_break"] = True
        bot_state["phase_end_time_iso"] = end_time.isoformat()
        log.info(f"STARTING BREAK. Bot will be offline for {duration_minutes:.2f} minutes.")
        save_state()

@manage_breaks.before_loop
async def before_manage_breaks():
    await client.wait_until_ready()

# --- 6. RUN THE BOT ---
if __name__ == "__main__":
    TOKEN = config.get('discord_settings', {}).get('token')
    if not TOKEN or TOKEN == "YOUR_TOKEN_HERE":
        log.error("FATAL: Token is missing or not set in config.yaml! Please update the file.")
    else:
        client.run(TOKEN)
