"""
Admin-facing handlers
"""

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    ContextTypes, ConversationHandler,
    CommandHandler, CallbackQueryHandler, MessageHandler, filters
)

import database as db
from config import ADMIN_IDS, RESULTS_CHANNEL_ID

# Conversation states
(
    ADMIN_WAITING_CHANNEL_ID, ADMIN_WAITING_CHANNEL_NAME, ADMIN_WAITING_CHANNEL_LINK,
    ADMIN_WAITING_EARN_ID, ADMIN_WAITING_EARN_NAME, ADMIN_WAITING_EARN_LINK, ADMIN_WAITING_EARN_STARS,
    ADMIN_WAITING_CODE, ADMIN_WAITING_CODE_STARS, ADMIN_WAITING_CODE_USES,
    ADMIN_BROADCAST_MSG,
    ADMIN_REJECT_NOTE,
) = range(12)


def is_admin(user_id: int) -> bool:
    return user_id in ADMIN_IDS


def admin_keyboard():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("📢 Required Channels", callback_data="admin_channels"),
         InlineKeyboardButton("💎 Earn Channels",     callback_data="admin_earn_channels")],
        [InlineKeyboardButton("📋 Pending Orders",    callback_data="admin_orders")],
        [InlineKeyboardButton("🎟 Star Codes",        callback_data="admin_codes")],
        [InlineKeyboardButton("📣 Broadcast",         callback_data="admin_broadcast"),
         InlineKeyboardButton("📊 Stats",             callback_data="admin_stats")],
    ])


# ── /admin ─────────────────────────────────────────────────────────────────────

async def admin_panel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    if not is_admin(uid):
        if update.callback_query:
            await update.callback_query.answer("⛔ Access denied.", show_alert=True)
        else:
            await update.message.reply_text("⛔ Access denied.")
        return

    text = "🛠 *Admin Panel*\n\nSelect an option:"
    if update.callback_query:
        await update.callback_query.answer()
        await update.callback_query.edit_message_text(text, reply_markup=admin_keyboard(), parse_mode="Markdown")
    else:
        await update.message.reply_text(text, reply_markup=admin_keyboard(), parse_mode="Markdown")


# ── Required channels ──────────────────────────────────────────────────────────

async def manage_channels(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    if not is_admin(update.effective_user.id):
        return

    channels = db.get_required_channels()
    text = "📢 *Required Channels*\n\n"
    buttons = []

    if channels:
        for ch in channels:
            text += f"• {ch['channel_name']} (`{ch['channel_id']}`)\n"
            buttons.append([InlineKeyboardButton(
                f"🗑 Remove {ch['channel_name']}",
                callback_data=f"admin_remove_channel_{ch['channel_id']}"
            )])
    else:
        text += "_No channels added yet._"

    buttons.append([InlineKeyboardButton("➕ Add Required Channel", callback_data="admin_add_channel")])
    buttons.append([InlineKeyboardButton("⬅️ Back", callback_data="admin_panel")])
    await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(buttons), parse_mode="Markdown")


async def add_channel_prompt(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    if not is_admin(update.effective_user.id):
        return
    context.user_data["admin_adding"] = "required"
    await query.edit_message_text(
        "📢 *Add Required Channel*\n\nSend the channel ID (e.g. `-1001234567890`).\n"
        "The bot must be an admin in the channel.\n\n/cancel to abort.",
        parse_mode="Markdown"
    )
    return ADMIN_WAITING_CHANNEL_ID


async def recv_channel_id(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["new_ch_id"] = update.message.text.strip()
    await update.message.reply_text("📝 Send the channel *display name*:", parse_mode="Markdown")
    return ADMIN_WAITING_CHANNEL_NAME


async def recv_channel_name(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["new_ch_name"] = update.message.text.strip()
    await update.message.reply_text("🔗 Send the channel *invite link*:", parse_mode="Markdown")
    return ADMIN_WAITING_CHANNEL_LINK


async def recv_channel_link(update: Update, context: ContextTypes.DEFAULT_TYPE):
    link = update.message.text.strip()
    ch_id   = context.user_data.pop("new_ch_id", "")
    ch_name = context.user_data.pop("new_ch_name", "")
    adding  = context.user_data.pop("admin_adding", "required")

    if adding == "earn":
        context.user_data["earn_link"] = link
        await update.message.reply_text("⭐ How many stars for joining this channel?")
        return ADMIN_WAITING_EARN_STARS
    else:
        db.add_required_channel(ch_id, ch_name, link)
        await update.message.reply_text(
            f"✅ Required channel *{ch_name}* added!",
            parse_mode="Markdown",
            reply_markup=InlineKeyboardMarkup([[
                InlineKeyboardButton("⬅️ Back to Admin", callback_data="admin_panel")
            ]])
        )
        return ConversationHandler.END


async def remove_channel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    if not is_admin(update.effective_user.id):
        return
    ch_id = query.data.split("admin_remove_channel_", 1)[1]
    db.remove_required_channel(ch_id)
    await manage_channels(update, context)


# ── Earn channels ──────────────────────────────────────────────────────────────

async def manage_earn_channels(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    if not is_admin(update.effective_user.id):
        return

    channels = db.get_earn_channels()
    text = "💎 *Earn Channels*\n\n"
    buttons = []

    if channels:
        for ch in channels:
            text += f"• {ch['channel_name']} (+{ch['stars_reward']}⭐)\n"
            buttons.append([InlineKeyboardButton(
                f"🗑 Remove {ch['channel_name']}",
                callback_data=f"admin_remove_earn_{ch['channel_id']}"
            )])
    else:
        text += "_No earn channels added yet._"

    buttons.append([InlineKeyboardButton("➕ Add Earn Channel", callback_data="admin_add_earn_channel")])
    buttons.append([InlineKeyboardButton("⬅️ Back", callback_data="admin_panel")])
    await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(buttons), parse_mode="Markdown")


async def add_earn_channel_prompt(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    context.user_data["admin_adding"] = "earn"
    await query.edit_message_text(
        "💎 *Add Earn Channel*\n\nSend the channel ID.\n\n/cancel to abort.",
        parse_mode="Markdown"
    )
    return ADMIN_WAITING_EARN_ID


async def recv_earn_id(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["earn_id"] = update.message.text.strip()
    await update.message.reply_text("📝 Send the channel display name:")
    return ADMIN_WAITING_EARN_NAME


async def recv_earn_name(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["earn_name"] = update.message.text.strip()
    await update.message.reply_text("🔗 Send the invite link:")
    return ADMIN_WAITING_EARN_LINK


async def recv_earn_link(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["earn_link"] = update.message.text.strip()
    await update.message.reply_text("⭐ How many stars for joining?")
    return ADMIN_WAITING_EARN_STARS


async def recv_earn_stars(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        stars = int(update.message.text.strip())
    except ValueError:
        await update.message.reply_text("❌ Enter a valid number.")
        return ADMIN_WAITING_EARN_STARS

    db.add_earn_channel(
        context.user_data.pop("earn_id", ""),
        context.user_data.pop("earn_name", ""),
        context.user_data.pop("earn_link", ""),
        stars
    )
    await update.message.reply_text(
        "✅ Earn channel added!",
        reply_markup=InlineKeyboardMarkup([[
            InlineKeyboardButton("⬅️ Admin Panel", callback_data="admin_panel")
        ]])
    )
    return ConversationHandler.END


async def remove_earn_channel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    if not is_admin(update.effective_user.id):
        return
    ch_id = query.data.split("admin_remove_earn_", 1)[1]
    db.remove_earn_channel(ch_id)
    await manage_earn_channels(update, context)


# ── Orders ─────────────────────────────────────────────────────────────────────

async def manage_orders(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    if not is_admin(update.effective_user.id):
        return

    orders = db.get_pending_orders()
    if not orders:
        text = "📋 No pending orders."
        kb   = InlineKeyboardMarkup([[InlineKeyboardButton("⬅️ Back", callback_data="admin_panel")]])
        await query.edit_message_text(text, reply_markup=kb)
        return

    text = f"📋 *Pending Orders* ({len(orders)})\n\n"
    buttons = []
    for o in orders:
        text += f"#{o['id']} — {o['target_type']} — {o['members_count']} members\n"
        buttons.append([
            InlineKeyboardButton(f"✅ Approve #{o['id']}", callback_data=f"admin_approve_{o['id']}"),
            InlineKeyboardButton(f"❌ Reject #{o['id']}",  callback_data=f"admin_reject_{o['id']}"),
        ])
    buttons.append([InlineKeyboardButton("⬅️ Back", callback_data="admin_panel")])
    await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(buttons), parse_mode="Markdown")


async def approve_order(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query    = update.callback_query
    await query.answer()
    if not is_admin(update.effective_user.id):
        return
    order_id = int(query.data.split("admin_approve_")[1])
    o        = db.get_order(order_id)
    if not o:
        await query.answer("Order not found.", show_alert=True)
        return

    db.update_order_status(order_id, "approved")

    # Create invite link to results channel
    try:
        link_obj = await context.bot.create_chat_invite_link(
            RESULTS_CHANNEL_ID, member_limit=1
        )
        invite = link_obj.invite_link
    except Exception:
        invite = None

    msg = (
        f"✅ *Order #{order_id} Approved!*\n\n"
        f"📌 Target: `{o['target']}`\n"
        f"👥 Members: {o['members_count']}\n\n"
        "📣 *What to do next:*\n"
        "1️⃣ Make sure your channel/group is public or add our bot as admin.\n"
        "2️⃣ Members will start joining within 24 hours.\n"
        "3️⃣ Track progress in your orders list.\n\n"
    )
    if invite:
        msg += f"🔗 Join our results channel for updates:\n{invite}"

    kb = InlineKeyboardMarkup([[InlineKeyboardButton("📋 My Orders", callback_data="member_orders")]])
    try:
        await context.bot.send_message(o["user_id"], msg, reply_markup=kb, parse_mode="Markdown")
    except Exception:
        pass

    await query.answer("✅ Order approved and user notified!", show_alert=True)
    await manage_orders(update, context)


async def reject_order(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query    = update.callback_query
    await query.answer()
    if not is_admin(update.effective_user.id):
        return
    order_id = int(query.data.split("admin_reject_")[1])
    context.user_data["rejecting_order"] = order_id
    await query.edit_message_text(
        f"❌ *Reject Order #{order_id}*\n\nSend a rejection reason (sent to user):\n\n/skip to reject without note.",
        parse_mode="Markdown"
    )
    return ADMIN_REJECT_NOTE


async def recv_reject_note(update: Update, context: ContextTypes.DEFAULT_TYPE):
    order_id = context.user_data.pop("rejecting_order", None)
    note     = update.message.text.strip() if update.message.text != "/skip" else "Order rejected by admin."
    if not order_id:
        return ConversationHandler.END

    o = db.get_order(order_id)
    if o:
        db.update_order_status(order_id, "rejected", note)
        db.update_stars(o["user_id"], o["stars_cost"])   # refund
        try:
            await context.bot.send_message(
                o["user_id"],
                f"❌ *Order #{order_id} was rejected.*\n\n"
                f"📝 Reason: {note}\n\n"
                f"💫 Your *{o['stars_cost']} stars* have been refunded.",
                parse_mode="Markdown"
            )
        except Exception:
            pass

    await update.message.reply_text(
        "✅ Order rejected and user notified.",
        reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("⬅️ Admin Panel", callback_data="admin_panel")]])
    )
    return ConversationHandler.END


# ── Star codes ─────────────────────────────────────────────────────────────────

async def manage_star_codes(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    if not is_admin(update.effective_user.id):
        return

    codes = db.get_all_star_codes()
    text  = "🎟 *Star Codes*\n\n"
    buttons = []

    if codes:
        for c in codes:
            text += f"• `{c['code']}` — {c['stars']}⭐ — {c['uses']}/{c['max_uses']} uses\n"
            buttons.append([InlineKeyboardButton(
                f"🗑 Delete {c['code']}", callback_data=f"admin_delete_code_{c['code']}"
            )])
    else:
        text += "_No codes._"

    buttons.append([InlineKeyboardButton("➕ Create Code", callback_data="admin_create_code")])
    buttons.append([InlineKeyboardButton("⬅️ Back", callback_data="admin_panel")])
    await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(buttons), parse_mode="Markdown")


async def create_star_code(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    await query.edit_message_text("🎟 Send the code text (e.g. `LAUNCH50`):\n\n/cancel to abort.", parse_mode="Markdown")
    return ADMIN_WAITING_CODE


async def recv_code_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["new_code"] = update.message.text.strip().upper()
    await update.message.reply_text("⭐ How many stars does this code give?")
    return ADMIN_WAITING_CODE_STARS


async def recv_code_stars(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        stars = int(update.message.text.strip())
    except ValueError:
        await update.message.reply_text("❌ Enter a valid number.")
        return ADMIN_WAITING_CODE_STARS
    context.user_data["new_code_stars"] = stars
    await update.message.reply_text("🔢 Max number of uses? (Enter a number)")
    return ADMIN_WAITING_CODE_USES


async def recv_code_uses(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        uses = int(update.message.text.strip())
    except ValueError:
        await update.message.reply_text("❌ Enter a valid number.")
        return ADMIN_WAITING_CODE_USES

    code  = context.user_data.pop("new_code", "")
    stars = context.user_data.pop("new_code_stars", 0)
    db.create_star_code(code, stars, uses)
    await update.message.reply_text(
        f"✅ Code `{code}` created! ({stars}⭐, {uses} uses)",
        parse_mode="Markdown",
        reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("⬅️ Admin Panel", callback_data="admin_panel")]])
    )
    return ConversationHandler.END


async def delete_star_code(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    if not is_admin(update.effective_user.id):
        return
    code = query.data.split("admin_delete_code_", 1)[1]
    db.delete_star_code(code)
    await manage_star_codes(update, context)


# ── Broadcast ──────────────────────────────────────────────────────────────────

async def broadcast_prompt(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    if not is_admin(update.effective_user.id):
        return
    await query.edit_message_text("📣 Send the broadcast message:\n\n/cancel to abort.")
    return ADMIN_BROADCAST_MSG


async def recv_broadcast(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg  = update.message.text
    uids = db.get_all_users()
    sent = fail = 0
    for uid in uids:
        try:
            await context.bot.send_message(uid, msg)
            sent += 1
        except Exception:
            fail += 1

    await update.message.reply_text(
        f"📣 Broadcast done!\n✅ Sent: {sent}\n❌ Failed: {fail}",
        reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("⬅️ Admin Panel", callback_data="admin_panel")]])
    )
    return ConversationHandler.END


# ── Stats ──────────────────────────────────────────────────────────────────────

async def stats(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    if not is_admin(update.effective_user.id):
        return

    s = db.get_stats()
    text = (
        f"📊 *Bot Statistics*\n\n"
        f"👤 Total Users: *{s['users']}*\n"
        f"📋 Total Orders: *{s['orders']}*\n"
        f"⏳ Pending Orders: *{s['pending']}*\n"
        f"✅ Approved Orders: *{s['approved']}*"
    )
    kb = InlineKeyboardMarkup([[InlineKeyboardButton("⬅️ Back", callback_data="admin_panel")]])
    await query.edit_message_text(text, reply_markup=kb, parse_mode="Markdown")


# ── Cancel helper ──────────────────────────────────────────────────────────────

async def cancel_conv(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "❌ Cancelled.",
        reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("⬅️ Admin Panel", callback_data="admin_panel")]])
    )
    return ConversationHandler.END


# ── Conversation handler ───────────────────────────────────────────────────────

def admin_conv_handler():
    return ConversationHandler(
        entry_points=[
            CallbackQueryHandler(add_channel_prompt,     pattern="^admin_add_channel$"),
            CallbackQueryHandler(add_earn_channel_prompt, pattern="^admin_add_earn_channel$"),
            CallbackQueryHandler(create_star_code,       pattern="^admin_create_code$"),
            CallbackQueryHandler(broadcast_prompt,       pattern="^admin_broadcast$"),
            CallbackQueryHandler(reject_order,           pattern=r"^admin_reject_(\d+)$"),
        ] 
        states={
            ADMIN_WAITING_CHANNEL_ID:   [MessageHandler(filters.TEXT & ~filters.COMMAND, recv_channel_id)],
            ADMIN_WAITING_CHANNEL_NAME: [MessageHandler(filters.TEXT & ~filters.COMMAND, recv_channel_name)],
            ADMIN_WAITING_CHANNEL_LINK: [MessageHandler(filters.TEXT & ~filters.COMMAND, recv_channel_link)],
            ADMIN_WAITING_EARN_ID:      [MessageHandler(filters.TEXT & ~filters.COMMAND, recv_earn_id)],
            ADMIN_WAITING_EARN_NAME:    [MessageHandler(filters.TEXT & ~filters.COMMAND, recv_earn_name)],
            ADMIN_WAITING_EARN_LINK:    [MessageHandler(filters.TEXT & ~filters.COMMAND, recv_earn_link)],
            ADMIN_WAITING_EARN_STARS:   [MessageHandler(filters.TEXT & ~filters.COMMAND, recv_earn_stars)],
            ADMIN_WAITING_CODE:         [MessageHandler(filters.TEXT & ~filters.COMMAND, recv_code_text)],
            ADMIN_WAITING_CODE_STARS:   [MessageHandler(filters.TEXT & ~filters.COMMAND, recv_code_stars)],
            ADMIN_WAITING_CODE_USES:    [MessageHandler(filters.TEXT & ~filters.COMMAND, recv_code_uses)],
            ADMIN_BROADCAST_MSG:        [MessageHandler(filters.TEXT & ~filters.COMMAND, recv_broadcast)],
            ADMIN_REJECT_NOTE:          [
                MessageHandler(filters.TEXT & ~filters.COMMAND, recv_reject_note),
                CommandHandler("skip", recv_reject_note),
            ],
        },
        fallbacks=[CommandHandler("cancel", cancel_conv)],
        per_message=False,
    )
