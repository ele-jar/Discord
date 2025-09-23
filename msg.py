# msg.py
import random

# --- DM Replies ---
# A list of varied, friendly replies the bot will send after receiving a valid listing DM.
# The bot will randomly choose one of these. {item_info} will be replaced with the listing details.
# Adding more variety makes the bot feel less robotic.
DM_REPLIES = [
    "Got it! I've added your listing for {item_info} to the board. I'll update it soon.",
    "Thanks! Your offer for {item_info} has been noted. It'll show up on the next market refresh.",
    "Perfect, listing for {item_info} is now in the queue. The market board will be updated in a bit.",
    "Alright, received your listing for {item_info}. I'll get it posted with the next batch.",
    "Listing accepted: {item_info}. Thanks for contributing to the market!",
    "Cheers! Your {item_info} sale is registered. It will be public on the next update cycle.",
    "Noted. {item_info} is on the list. Good luck with the sale!",
    "Excellent. I've recorded your listing for {item_info}.",
    "All set! Your listing for {item_info} will be on the board after the next scheduled update.",
    "You got it. {item_info} is now pending for the market update.",
    "I've jotted that down. {item_info} will be up shortly.",
    "Great, the market ledger now includes your sale of {item_info}.",
    "Consider it done. Your listing for {item_info} is in.",
    "Copy that. Adding {item_info} to the market listings.",
    "Received and processing your listing for {item_info}. It will appear on the board soon.",
]

def get_random_dm_reply(item_name, quantity, price_item, price_amount):
    """Formats and returns a random DM reply."""
    item_info = f"{quantity} {item_name} for {price_amount} {price_item}"
    message_template = random.choice(DM_REPLIES)
    return message_template.format(item_info=item_info)


# --- Help & Error Messages ---
HELP_MESSAGE = (
    "Sorry, I didn't understand that. Please use the format:\n"
    "`sell [amount] [item_name] for [price_amount] [price_item]`\n\n"
    "**Examples:**\n"
    "- `sell 64 diamond for 128 iron_ingot`\n"
    "- `sell 1 netherite_sword for 5 diamond_block`\n\n"
    "*Note: Item names must be one word (e.g., `diamond_block` not `diamond block`).*"
)

# --- Market Board Template ---
# This is the main template for the market board message.
# It uses Discord markdown for pretty formatting.
# {last_updated} and {market_body} will be filled in by the bot.
MARKET_BOARD_TEMPLATE = """
<:emerald:1185568471587373146> **Minecraft Market Board** <:emerald:1185568471587373146>
*To list an item, send me a DM! Format: `sell [amount] [item] for [price] [currency]`*
`------------------------------------------------`
{market_body}
`------------------------------------------------`
*Last Updated: {last_updated}*
"""
