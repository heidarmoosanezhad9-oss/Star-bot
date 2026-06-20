"""
Bot configuration — edit these values before running.
"""

# ── Required ───────────────────────────────────────────────────────────────────
BOT_TOKEN = "8901051611:AAGfhJQ_hET3UFCnhvH-Q4qSRdeHl_tG9Yg"
ADMIN_IDS = [7959284252]

# ── Star economy ───────────────────────────────────────────────────────────────
DAILY_STARS          = 5       # Free stars per day
INVITE_STARS         = 10      # Stars per invited friend who joins
JOIN_STARS           = 3       # Stars for joining each required channel

# ── Order pricing (stars per member) ──────────────────────────────────────────
STARS_PER_MEMBER     = 5       # Cost in stars for each member ordered

# ── Referral ───────────────────────────────────────────────────────────────────
BOT_USERNAME         = "user_info_bot"     # Without @

# ── Private results channel ────────────────────────────────────────────────────
# After an order is approved the user gets an invite link to this channel
RESULTS_CHANNEL_ID   = -1003965394113      # Your private channel ID

# ── Database ───────────────────────────────────────────────────────────────────
DATABASE_PATH        = "bot_database.db"
