"""
User-facing handlers
"""

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
from telegram.error import BadRequest

import database as db
from config import (
    BOT_USERNAME, DAILY_STARS, INVITE_STARS, JOIN_STARS,
    STARS_PER_MEMBER, ADMIN_IDS
)


# ── Helpers ────────────────────────────────────────────────────────────────────

def main_menu_keyboard():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("⭐ Daily Stars",      callback_data="daily_stars"),
         InlineKeyboardButton("👤 Profile",           callback_data="profile")],
        [InlineKeyboardButton("💎 Earn Stars",        callback_data="earn_stars"),
         InlineKeyboardButton("👥 Invite Friends",    callback_data="invite_friends")],
        [InlineKeyboardButton("🛒 Buy Stars",         callback_data="buy_stars"),
         InlineKeyboardButton("🎟 Star Code",         callback_data="star_code")],
        [InlineKeyboardButton("📋 My Orders",         callback_data="member_orders")],
        [InlineKeyboardButton("➕ New Member Order",  callback_data="new_order")],
    ])


async def _check_required_channels(bot, user_id: int) -> list:
    """Returns list of channels the user has NOT joined yet."""
    required = db.get_required_channels()
    not_joined = []
    for ch in required:
        try:
            member = await bot.get_chat_member(ch["channel_id"], user_id)
            if member.status in ("left", "kicked", "banned"):
                not_joined.append(ch)
        except Exception:
            not_joined.append(ch)
    return not_joined


async def _send_join_gate(update: Update, context: ContextTypes.DEFAULT_TYPE, not_joined: list):
    """Show join buttons for required channels."""
    buttons = [
        [InlineKeyboardButton(f"📢 {ch['channel_name']}", url=ch["invite_link"])]
        for ch in not_joined
    ]
    buttons.append([InlineKeyboardButton("✅ I Joined — Check Again", callback_data="main_menu")])
    kb = InlineKeyboardMarkup(buttons)
    text = (
        "👋 Welcome!\n\n"
        "To use this bot you must first join the channels below.\n"
        "After joining, press *I Joined — Check Again*."
    )
    if update.callback_query:
        await update.callback_query.edit_message_text(text, reply_markup=kb, parse_mode="Markdown")
    else:
        await update.message.reply_text(text, reply_markup=kb, parse_mode="Markdown")


# ── /start ─────────────────────────────────────────────────────────────────────

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user   = update.effective_user
    args   = context.args

    invited_by = None
    if args:
        try:
            invited_by = int(args[0])
            if invited_by == user.id:
                invited_by = None
        except ValueError:
            pass

    db.upsert_user(user.id, user.username or "", user.full_name, invited_by)

    # Award invite reward to referrer
    if invited_by:
        rewarded = db.record_invite_reward(invited_by, user.id)
        if rewarded:
            try:
                await context.bot.send_message(
                    invited_by,
                    f"🎉 Your friend *{user.full_name}* joined via your link!\n"
                    f"You received *{INVITE_STARS} stars* ⭐",
                    parse_mode="Markdown"
                )
            except Exception:
                pass

    not_joined = await _check_required_channels(context.bot, user.id)
    if not_joined:
        await _send_join_gate(update, context, not_joined)
        return

    u = db.get_user(user.id)
    await update.message.reply_text(
        f"🌟 Welcome back, *{user.full_name}*!\n\n"
        f"⭐ Stars: *{u['stars']}*\n\n"
        "Choose an option from the menu below:",
        reply_markup=main_menu_keyboard(),
        parse_mode="Markdown"
    )


# ── Main menu (callback) ───────────────────────────────────────────────────────

async def main_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user  = update.effective_user

    not_joined = await _check_required_channels(context.bot, user.id)
    if not_joined:
        await _send_join_gate(update, context, not_joined)
        return

    u = db.get_user(user.id)
    await query.edit_message_text(
        f"🌟 *Main Menu*\n\n⭐ Stars: *{u['stars']}*\n\nChoose an option:",
        reply_markup=main_menu_keyboard(),
        parse_mode="Markdown"
    )


# ── Daily stars ────────────────────────────────────────────────────────────────

async def daily_stars(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    claimed = db.claim_daily(update.effective_user.id)
    u       = db.get_user(update.effective_user.id)

    if claimed:
        text = (
            f"✅ You claimed your *{DAILY_STARS} daily stars*!\n\n"
            f"⭐ Total stars: *{u['stars']}*\n\n"
            "Come back tomorrow for more!"
        )
    else:
        text = (
            f"⏳ You already claimed your daily stars today.\n\n"
            f"⭐ Total stars: *{u['stars']}*\n\n"
            "Come back tomorrow!"
        )

    kb = InlineKeyboardMarkup([[InlineKeyboardButton("⬅️ Back", callback_data="main_menu")]])
    await query.edit_message_text(text, reply_markup=kb, parse_mode="Markdown")


# ── Profile ────────────────────────────────────────────────────────────────────

async def profile(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    uid  = update.effective_user.id
    u    = db.get_user(uid)
    inv  = db.get_invite_count(uid)
    ords = db.get_user_orders(uid)

    text = (
        f"👤 *Your Profile*\n\n"
        f"🆔 ID: `{uid}`\n"
        f"📛 Name: {u['full_name']}\n"
        f"⭐ Stars: *{u['stars']}*\n"
        f"👥 Friends Invited: *{inv}*\n"
        f"📋 Total Orders: *{len(ords)}*\n"
        f"📅 Joined: {u['joined_at'][:10] if u['joined_at'] else '—'}"
    )

    kb = InlineKeyboardMarkup([[InlineKeyboardButton("⬅️ Back", callback_data="main_menu")]])
    await query.edit_message_text(text, reply_markup=kb, parse_mode="Markdown")


# ── Earn stars (join channels) ─────────────────────────────────────────────────

async def earn_stars(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    channels = db.get_earn_channels()
    if not channels:
        text = "😔 No earning channels are available right now. Check back later!"
        kb   = InlineKeyboardMarkup([[InlineKeyboardButton("⬅️ Back", callback_data="main_menu")]])
        await query.edit_message_text(text, reply_markup=kb)
        return

    buttons = []
    for ch in channels:
        buttons.append([
            InlineKeyboardButton(
                f"📢 {ch['channel_name']} (+{ch['stars_reward']}⭐)",
                url=ch["invite_link"]
            )
        ])
        buttons.append([
            InlineKeyboardButton(
                f"✅ Verify join: {ch['channel_name']}",
                callback_data=f"verify_join_{ch['channel_id']}"
            )
        ])

    buttons.append([InlineKeyboardButton("⬅️ Back", callback_data="main_menu")])
    kb = InlineKeyboardMarkup(buttons)
    await query.edit_message_text(
        "💎 *Earn Stars*\n\nJoin a channel below, then press Verify to claim your stars!",
        reply_markup=kb,
        parse_mode="Markdown"
    )


async def verify_join(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query      = update.callback_query
    await query.answer()
    channel_id = query.data.split("verify_join_", 1)[1]
    uid        = update.effective_user.id

    # Look up channel
    channels = db.get_earn_channels()
    ch = next((c for c in channels if c["channel_id"] == channel_id), None)
    if not ch:
        await query.answer("Channel not found.", show_alert=True)
        return

    try:
        member = await context.bot.get_chat_member(channel_id, uid)
        if member.status in ("left", "kicked", "banned"):
            await query.answer("❌ You haven't joined yet!", show_alert=True)
            return
    except BadRequest:
        await query.answer("⚠️ Bot is not an admin in that channel.", show_alert=True)
        return

    # Check if already rewarded (use code_redemptions table reused for simplicity)
    import sqlite3
    conn = db.get_conn()
    already = conn.execute(
        "SELECT 1 FROM code_redemptions WHERE user_id=? AND code=?",
        (uid, f"earn_{channel_id}")
    ).fetchone()
    if already:
        conn.close()
        await query.answer("✅ You already claimed stars for this channel.", show_alert=True)
        return
    conn.execute(
        "INSERT INTO code_redemptions (user_id,code) VALUES (?,?)",
        (uid, f"earn_{channel_id}")
    )
    conn.execute("UPDATE users SET stars=stars+? WHERE user_id=?", (ch["stars_reward"], uid))
    conn.commit()
    conn.close()

    u = db.get_user(uid)
    await query.answer(f"🎉 +{ch['stars_reward']} stars awarded!", show_alert=True)
    await earn_stars(update, context)


# ── Invite friends ─────────────────────────────────────────────────────────────

async def invite_friends(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    uid  = update.effective_user.id
    link = f"https://t.me/{BOT_USERNAME}?start={uid}"
    inv  = db.get_invite_count(uid)

    text = (
        f"👥 *Invite Friends*\n\n"
        f"Share your link and earn *{INVITE_STARS}⭐* for each friend who joins!\n\n"
        f"🔗 Your link:\n`{link}`\n\n"
        f"👫 Friends invited so far: *{inv}*"
    )
    kb = InlineKeyboardMarkup([[InlineKeyboardButton("⬅️ Back", callback_data="main_menu")]])
    await query.edit_message_text(text, reply_markup=kb, parse_mode="Markdown")


# ── Buy stars ──────────────────────────────────────────────────────────────────

async def buy_stars(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    text = (
        "🛒 *Buy Stars*\n\n"
        "Contact an admin to purchase stars:\n\n"
        "💳 Prices:\n"
        "• 50 ⭐ = $1\n"
        "• 150 ⭐ = $2.50\n"
        "• 500 ⭐ = $7\n"
        "• 1000 ⭐ = $12\n\n"
        "📩 Contact: @AdminUsername"
    )
    kb = InlineKeyboardMarkup([[InlineKeyboardButton("⬅️ Back", callback_data="main_menu")]])
    await query.edit_message_text(text, reply_markup=kb, parse_mode="Markdown")


# ── Star code ──────────────────────────────────────────────────────────────────

async def star_code(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    db.set_state(update.effective_user.id, "awaiting_star_code")
    kb = InlineKeyboardMarkup([[InlineKeyboardButton("❌ Cancel", callback_data="main_menu")]])
    await query.edit_message_text(
        "🎟 *Redeem Star Code*\n\nType your code below and send it:",
        reply_markup=kb,
        parse_mode="Markdown"
    )


# ── Member orders list ─────────────────────────────────────────────────────────

async def member_orders(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    uid  = update.effective_user.id
    ords = db.get_user_orders(uid)

    if not ords:
        text = "📋 You have no orders yet.\n\nPlace your first order below!"
        buttons = [
            [InlineKeyboardButton("➕ New Order", callback_data="new_order")],
            [InlineKeyboardButton("⬅️ Back",     callback_data="main_menu")],
        ]
    else:
        status_emoji = {"pending": "⏳", "approved": "✅", "rejected": "❌", "done": "🏁"}
        text = "📋 *Your Orders*\n\n"
        buttons = []
        for o in ords:
            emoji = status_emoji.get(o["status"], "❓")
            text += f"{emoji} #{o['id']} — {o['target_type']} — {o['members_count']} members — {o['status']}\n"
            buttons.append([
                InlineKeyboardButton(
                    f"{emoji} Order #{o['id']} details",
                    callback_data=f"order_status_{o['id']}"
                )
            ])
        buttons.append([InlineKeyboardButton("➕ New Order", callback_data="new_order")])
        buttons.append([InlineKeyboardButton("⬅️ Back",     callback_data="main_menu")])

    kb = InlineKeyboardMarkup(buttons)
    await query.edit_message_text(text, reply_markup=kb, parse_mode="Markdown")


async def check_order_status(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query    = update.callback_query
    await query.answer()
    order_id = int(query.data.split("order_status_")[1])
    o        = db.get_order(order_id)

    if not o or o["user_id"] != update.effective_user.id:
        await query.answer("Order not found.", show_alert=True)
        return

    status_emoji = {"pending": "⏳", "approved": "✅", "rejected": "❌", "done": "🏁"}
    emoji = status_emoji.get(o["status"], "❓")

    text = (
        f"📋 *Order #{o['id']}*\n\n"
        f"📌 Target: `{o['target']}`\n"
        f"📂 Type: {o['target_type']}\n"
        f"👥 Members: {o['members_count']}\n"
        f"⭐ Cost: {o['stars_cost']} stars\n"
        f"{emoji} Status: *{o['status']}*\n"
        f"📅 Created: {o['created_at'][:10]}\n"
    )
    if o["note"]:
        text += f"\n📝 Note: {o['note']}"

    buttons = [[InlineKeyboardButton("⬅️ My Orders", callback_data="member_orders")]]
    if o["status"] == "pending":
        buttons.insert(0, [InlineKeyboardButton("❌ Cancel Order", callback_data=f"cancel_order_{o['id']}")])

    await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(buttons), parse_mode="Markdown")


async def cancel_order(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query    = update.callback_query
    await query.answer()
    order_id = int(query.data.split("cancel_order_")[1])
    o        = db.get_order(order_id)

    if not o or o["user_id"] != update.effective_user.id or o["status"] != "pending":
        await query.answer("Cannot cancel this order.", show_alert=True)
        return

    db.update_order_status(order_id, "rejected", "Cancelled by user")
    db.update_stars(update.effective_user.id, o["stars_cost"])   # refund

    await query.answer("✅ Order cancelled and stars refunded.", show_alert=True)
    await member_orders(update, context)


# ── New order (redirects to conversation) ─────────────────────────────────────

async def new_order(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    uid = update.effective_user.id
    u   = db.get_user(uid)

    kb = InlineKeyboardMarkup([
        [InlineKeyboardButton("📢 Channel", callback_data="order_type_channel"),
         InlineKeyboardButton("👥 Group",   callback_data="order_type_group")],
        [InlineKeyboardButton("⬅️ Back",    callback_data="main_menu")],
    ])
    await query.edit_message_text(
        f"➕ *New Member Order*\n\n"
        f"⭐ Your stars: *{u['stars']}*\n"
        f"💵 Cost: *{STARS_PER_MEMBER} stars per member*\n\n"
        "What type of target do you want to grow?",
        reply_markup=kb,
        parse_mode="Markdown"
    )


# ── Text message handler (star codes + order steps) ───────────────────────────

async def handle_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid   = update.effective_user.id
    state = db.get_state(uid)
    text  = update.message.text.strip()

    if state == "awaiting_star_code":
        stars = db.redeem_star_code(uid, text)
        db.set_state(uid, "")
        u = db.get_user(uid)
        if stars == -1:
            msg = "❌ Invalid or already used code. Please try again."
        else:
            msg = f"🎉 Code redeemed! You received *{stars} stars*.\n\n⭐ Total: *{u['stars']}*"
        kb = InlineKeyboardMarkup([[InlineKeyboardButton("⬅️ Main Menu", callback_data="main_menu")]])
        await update.message.reply_text(msg, reply_markup=kb, parse_mode="Markdown")

    elif state == "awaiting_order_target":
        context.user_data["order_target"] = text
        db.set_state(uid, "awaiting_order_count")
        await update.message.reply_text(
            "👥 How many members do you want? (Enter a number, e.g. 100)"
        )

    elif state == "awaiting_order_count":
        try:
            count = int(text)
            if count < 1:
                raise ValueError
        except ValueError:
            await update.message.reply_text("❌ Please enter a valid number.")
            return

        target      = context.user_data.get("order_target", "")
        order_type  = context.user_data.get("order_type", "channel")
        cost        = count * STARS_PER_MEMBER
        u           = db.get_user(uid)

        if u["stars"] < cost:
            db.set_state(uid, "")
            kb = InlineKeyboardMarkup([
                [InlineKeyboardButton("💎 Earn Stars",  callback_data="earn_stars")],
                [InlineKeyboardButton("🛒 Buy Stars",   callback_data="buy_stars")],
                [InlineKeyboardButton("⬅️ Main Menu",   callback_data="main_menu")],
            ])
            await update.message.reply_text(
                f"❌ You need *{cost}⭐* but only have *{u['stars']}⭐*.\n\nEarn or buy more stars:",
                reply_markup=kb, parse_mode="Markdown"
            )
            return

        # Deduct and create order
        db.update_stars(uid, -cost)
        order_id = db.create_order(uid, target, order_type, count, cost)
        db.set_state(uid, "")

        # Notify admins
        for admin_id in ADMIN_IDS:
            try:
                kb_admin = InlineKeyboardMarkup([
                    [InlineKeyboardButton("✅ Approve", callback_data=f"admin_approve_{order_id}"),
                     InlineKeyboardButton("❌ Reject",  callback_data=f"admin_reject_{order_id}")],
                ])
                await context.bot.send_message(
                    admin_id,
                    f"📋 *New Order #{order_id}*\n\n"
                    f"👤 User: [{u['full_name']}](tg://user?id={uid}) (`{uid}`)\n"
                    f"📌 Target: `{target}`\n"
                    f"📂 Type: {order_type}\n"
                    f"👥 Members: {count}\n"
                    f"⭐ Cost: {cost}",
                    reply_markup=kb_admin,
                    parse_mode="Markdown"
                )
            except Exception:
                pass

        kb = InlineKeyboardMarkup([
            [InlineKeyboardButton("📋 My Orders", callback_data="member_orders")],
            [InlineKeyboardButton("⬅️ Main Menu", callback_data="main_menu")],
        ])
        await update.message.reply_text(
            f"✅ *Order #{order_id} placed!*\n\n"
            f"📌 Target: `{target}`\n"
            f"👥 Members: {count}\n"
            f"⭐ Deducted: {cost} stars\n\n"
            "⏳ An admin will review your order shortly. You'll be notified when it's approved.",
            reply_markup=kb,
            parse_mode="Markdown"
        )

    elif state == "awaiting_order_type":
        # handled by callback
        pass
