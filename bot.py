# bot.py
import discord
from discord.ext import tasks
import json
import random
import asyncio
from datetime import datetime
import os
import logging
from dotenv import load_dotenv

# --- 1. SETUP LOGGING ---
# Create a logger that prints timestamped messages to your terminal
logging.basicConfig(
    level=logging.INFO,
    format='[%(asctime)s] [%(levelname)s] %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
log = logging.getLogger(__name__)

# --- 2. LOAD CONFIGURATION FROM .env FILE ---
log.info("Loading configuration from .env file...")
load_dotenv()
TOKEN = os.getenv('DISCORD_TOKEN')
try:
    MARKET_CHANNEL_ID = int(os.getenv('MARKET_CHANNEL_ID'))
except (ValueError, TypeError):
    MARKET_CHANNEL_ID = None # Handle case where it's missing or invalid

# --- 3. GLOBAL VARIABLES ---
DATA_FILE = 'market_data.json'
client = discord.Client()
market_data = {"market_message_id": None, "listings": []}

# Import our custom settings and messages (no changes needed in those files)
import human
import msg

# --- DATA HANDLING ---
def load_data():
    """Loads market data from the JSON file into memory."""
    global market_data
    if os.path.exists(DATA_FILE):
        with open(DATA_FILE, 'r') as f:
            try:
                market_data = json.load(f)
                log.info(f"Successfully loaded data from {DATA_FILE}.")
            except json.JSONDecodeError:
                log.warning(f"{DATA_FILE} is corrupted or empty. Starting with a fresh data set.")
                market_data = {"market_message_id": None, "listings": []}
    else:
        log.info(f"{DATA_FILE} not found. A new one will be created on the first save.")

def save_data():
    """Saves the current market data from memory to the JSON file."""
    with open(DATA_FILE, 'w') as f:
        json.dump(market_data, f, indent=4)
    log.info(f"Market data saved to {DATA_FILE}.")

# --- CORE EVENTS ---
@client.event
async def on_ready():
    """Called when the bot successfully connects to Discord."""
    log.info(f"Logged in as {client.user.name} ({client.user.id})")
    log.info("Bot is ready and listening for DMs.")
    load_data()
    update_market_board.start() # Start the periodic update loop
    log.info(f"Market update loop scheduled to run every {human.MARKET_UPDATE_INTERVAL_MINUTES} minutes.")

@client.event
async def on_message(message):
    """Called for every message the user account can see."""
    # We only care about DMs sent to us, and not from ourself
    if not isinstance(message.channel, discord.DMChannel) or message.author == client.user:
        return

    log.info(f"Received DM from {message.author.name}: '{message.content}'")
    content = message.content.lower().strip()

    if not content.startswith('sell'):
        log.info("DM did not start with 'sell', ignoring.")
        return

    log.info("Attempting to parse listing from DM...")
    parts = content.split()
    try:
        # Expected format: sell [amount] [item] for [price_amount] [price_item]
        if len(parts) != 6 or parts[0] != 'sell' or parts[3] != 'for':
            raise ValueError("Incorrect command structure.")

        quantity = int(parts[1])
        item_name = parts[2]
        price_amount = int(parts[4])
        price_item = parts[5]
        log.info(f"Successfully parsed listing: {quantity} {item_name} for {price_amount} {price_item}")

        new_listing = {
            "seller_id": str(message.author.id),
            "seller_name": message.author.name,
            "item_name": item_name,
            "quantity": quantity,
            "price_item": price_item,
            "price_amount": price_amount,
            "timestamp": datetime.utcnow().isoformat()
        }
        market_data['listings'].append(new_listing)
        save_data()

        # --- Human Touch: Delayed & Varied DM Reply ---
        delay = random.uniform(human.MIN_DM_REPLY_DELAY_SECONDS, human.MAX_DM_REPLY_DELAY_SECONDS)
        log.info(f"Waiting for {delay:.2f} seconds before replying...")
        await asyncio.sleep(delay)
        
        async with message.channel.typing():
            typing_duration = random.uniform(human.MIN_TYPING_SECONDS, human.MAX_TYPING_SECONDS)
            log.info(f"Simulating typing for {typing_duration:.2f} seconds...")
            await asyncio.sleep(typing_duration)
            reply_text = msg.get_random_dm_reply(item_name, quantity, price_item, price_amount)
            await message.channel.send(reply_text)
            log.info(f"Sent DM reply to {message.author.name}.")

    except (ValueError, IndexError) as e:
        log.warning(f"Failed to parse DM. Error: {e}. Sending help message.")
        await message.channel.send(msg.HELP_MESSAGE)

# --- BACKGROUND TASK ---
@tasks.loop(minutes=human.MARKET_UPDATE_INTERVAL_MINUTES)
async def update_market_board():
    """The main background loop that periodically updates the market board."""
    log.info("--- Starting scheduled market update task ---")
    
    channel = client.get_channel(MARKET_CHANNEL_ID)
    if not channel:
        log.error(f"FATAL: Cannot find channel with ID {MARKET_CHANNEL_ID}. Please check your .env file.")
        return

    # 1. Build the formatted text for the board
    log.info("Grouping and calculating cheapest listings...")
    grouped_items = {}
    for listing in market_data['listings']:
        item = listing['item_name']
        if item not in grouped_items: grouped_items[item] = []
        grouped_items[item].append(listing)

    market_body_parts = []
    if not grouped_items:
        market_body_parts.append("The market is currently empty! DM me to list your items.")
    else:
        for item_name in sorted(grouped_items.keys()):
            listings = grouped_items[item_name]
            cheapest = min(listings, key=lambda x: x['price_amount'] / x['quantity'])
            ppu = cheapest['price_amount'] / cheapest['quantity']
            price_per_unit_str = f"{ppu:.2f}".rstrip('0').rstrip('.')
            market_body_parts.append(
                f"**<:arrow:1185568475253891152> {item_name.replace('_', ' ').title()}**\n"
                f"  • **Cheapest:** `{price_per_unit_str} {cheapest['price_item']}` per unit (Sold by `{cheapest['seller_name']}`)\n"
                f"  • **Total Listings:** `{len(listings)}`"
            )
    log.info(f"Generated market body with {len(grouped_items)} item groups.")
    market_body = "\n\n".join(market_body_parts)
    
    now_time = datetime.now().strftime("%I:%M %p UTC")
    full_message_content = msg.MARKET_BOARD_TEMPLATE.format(market_body=market_body, last_updated=now_time)

    # 2. **[FIXED LOGIC]** Safely fetch, edit, or create the message
    message_to_edit = None
    if market_data.get('market_message_id'):
        try:
            log.info(f"Attempting to fetch existing market message with ID: {market_data['market_message_id']}")
            message_to_edit = await channel.fetch_message(market_data['market_message_id'])
            log.info("Successfully fetched existing message.")
        except discord.NotFound:
            log.warning("Market message not found (it was likely deleted). Will post a new one.")
            market_data['market_message_id'] = None # Clear the invalid ID
        except discord.Forbidden:
            log.error(f"I don't have permission to read message history in channel {MARKET_CHANNEL_ID}. Cannot update.")
            return # Can't proceed
        except Exception as e:
            log.error(f"An unexpected error occurred while fetching the message: {e}")
            return

    # --- Human Touch: Typing Simulation ---
    async with channel.typing():
        typing_duration = random.uniform(human.MIN_TYPING_SECONDS, human.MAX_TYPING_SECONDS)
        log.info(f"Simulating typing in market channel for {typing_duration:.2f} seconds...")
        await asyncio.sleep(typing_duration)
    
        try:
            if message_to_edit:
                await message_to_edit.edit(content=full_message_content)
                log.info("Market board message successfully EDITED.")
            else:
                log.info("No existing message found, POSTING a new market board.")
                new_message = await channel.send(full_message_content)
                market_data['market_message_id'] = new_message.id
                log.info(f"New market board posted. Message ID: {new_message.id}")
            save_data() # Save the new message ID if created
        except discord.Forbidden:
            log.error(f"I don't have permission to send/edit messages in channel {MARKET_CHANNEL_ID}. Please check permissions.")
        except Exception as e:
            log.error(f"An unexpected error occurred during message update: {e}")

    log.info("--- Market update task finished ---")

@update_market_board.before_loop
async def before_update_loop():
    await client.wait_until_ready()

# --- RUN THE BOT ---
if __name__ == "__main__":
    if not TOKEN or not MARKET_CHANNEL_ID:
        log.error("FATAL: DISCORD_TOKEN or MARKET_CHANNEL_ID is missing from your .env file.")
        log.error("Please create a .env file and fill it with your credentials.")
    else:
        client.run(TOKEN)
