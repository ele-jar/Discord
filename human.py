# human.py

# This file contains all the "human-like" settings for your bot.
# By changing these values, you can control how cautious and human-like the bot behaves.
# Slower, more random timings are safer.

# --- DM Reply Timings ---

# When you receive a DM, the bot will wait for a random duration within this range
# before it sends a reply. This simulates you reading the message and thinking.
MIN_DM_REPLY_DELAY_SECONDS = 2.0  # e.g., wait at least 2 seconds
MAX_DM_REPLY_DELAY_SECONDS = 5.0  # e.g., wait at most 5 seconds

# --- Typing Simulation ---

# Before sending a message (both in DMs and in the market channel), the bot will
# show the "typing..." indicator for a random duration in this range.
# This is a very strong visual cue of human activity.
MIN_TYPING_SECONDS = 1.5
MAX_TYPING_SECONDS = 4.0

# --- Market Board Update Cycle ---

# This is the most important setting for safety.
# The bot will NOT update the market board instantly. Instead, it runs on a cycle.
# Every X minutes, it will gather all new listings and update the board in one single edit.
# A longer interval is safer and less spammy.
# Recommended: 10-15 minutes to be safe. 5 minutes for faster updates.
MARKET_UPDATE_INTERVAL_MINUTES = 10
