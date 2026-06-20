# ⭐ Telegram Star Exchange Bot

A fully-featured member-growth exchange bot for Telegram. Users earn stars by joining channels, inviting friends, or redeeming codes — then spend those stars to grow their own channel or group.

---

## 📁 File Structure

```
telegram_star_bot/
├── bot.py              # Entry point — registers all handlers
├── config.py           # All settings (edit this first)
├── database.py         # SQLite database layer
├── requirements.txt
├── handlers/
│   ├── __init__.py
│   ├── user.py         # All user-facing menus & logic
│   ├── admin.py        # Admin panel
│   └── orders.py       # Order placement conversation
```

---

## ⚙️ Setup

### 1. Install dependencies

```bash
pip install -r requirements.txt
```

### 2. Create your bot

1. Open [@BotFather](https://t.me/BotFather) on Telegram
2. Send `/newbot` and follow the steps
3. Copy your **Bot Token**

### 3. Edit `config.py`

```python
BOT_TOKEN        = "YOUR_BOT_TOKEN"        # From BotFather
ADMIN_IDS        = [123456789]             # Your Telegram user ID(s)
BOT_USERNAME     = "YourBotUsername"       # Without @
RESULTS_CHANNEL_ID = -100xxxxxxxxxx        # Private channel ID for order updates
```

**To find your Telegram user ID:** message [@userinfobot](https://t.me/userinfobot)

**To find a channel ID:** forward a message from it to [@userinfobot](https://t.me/userinfobot)

### 4. Add the bot as admin

- In every **required channel** (join gate): add bot as admin with "Add Members" permission
- In every **earn channel**: add bot as admin with at least "Read Messages" permission
- In the **results channel**: add bot as admin with "Invite Users via Link" permission

### 5. Run the bot

```bash
python bot.py
```

---

## 🛠 Admin Commands

| Command / Button | Action |
|---|---|
| `/admin` | Open the admin panel |
| 📢 Required Channels | Channels users MUST join before using the bot |
| 💎 Earn Channels | Channels users can join to earn stars |
| 📋 Pending Orders | Review, approve, or reject member orders |
| 🎟 Star Codes | Create/delete gift codes |
| 📣 Broadcast | Send a message to all users |
| 📊 Stats | View user & order counts |

---

## 👤 User Menu

| Button | Action |
|---|---|
| ⭐ Daily Stars | Claim free stars once per day |
| 👤 Profile | View stats, star balance, invite count |
| 💎 Earn Stars | Join channels to earn stars |
| 👥 Invite Friends | Get a referral link (+stars per friend) |
| 🛒 Buy Stars | Contact admin to purchase stars |
| 🎟 Star Code | Redeem a gift code for stars |
| 📋 My Orders | View all past and pending orders |
| ➕ New Member Order | Place a new channel/group growth order |

---

## 💡 Star Economy (defaults in `config.py`)

| Action | Stars |
|---|---|
| Daily claim | +5 ⭐ |
| Friend joins via your link | +10 ⭐ |
| Joining an earn channel | +3 ⭐ (configurable per channel) |
| Each member ordered | −5 ⭐ per member |

---

## 🔄 Order Flow

1. User selects **New Order** → picks channel or group
2. Enters target username/link and desired member count
3. Stars are deducted immediately
4. Admins receive a notification with **Approve / Reject** buttons
5. On approval → user gets instructions + a one-time invite link to the results channel
6. On rejection → stars are fully refunded + reason sent to user

---

## 🚀 Running in Production (Linux server)

Create a systemd service at `/etc/systemd/system/starbot.service`:

```ini
[Unit]
Description=Telegram Star Bot
After=network.target

[Service]
WorkingDirectory=/path/to/telegram_star_bot
ExecStart=/usr/bin/python3 bot.py
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
```

Then:

```bash
sudo systemctl daemon-reload
sudo systemctl enable starbot
sudo systemctl start starbot
sudo systemctl status starbot
```

---

## 📝 Notes

- The bot uses **SQLite** — no external database needed
- All data is stored in `bot_database.db` (auto-created on first run)
- Star codes are case-insensitive and each user can only redeem each code once
- Cancelled orders refund stars automatically
- The bot detects if a user hasn't joined required channels and shows the join gate again
