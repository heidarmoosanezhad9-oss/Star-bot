"""
Order placement conversation (type selection via callback, then text steps)
"""

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    ContextTypes, ConversationHandler,
    CallbackQueryHandler, MessageHandler, CommandHandler, filters
)

import database as db

ORDER_TYPE, ORDER_TARGET, ORDER_COUNT = range(3)


async def choose_type(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    order_type = query.data.split("order_type_")[1]   # 'channel' or 'group'
    context.user_data["order_type"] = order_type
    db.set_state(update.effective_user.id, "awaiting_order_target")

    emoji = "📢" if order_type == "channel" else "👥"
    await query.edit_message_text(
        f"{emoji} *{order_type.title()} Order*\n\n"
        "Send the channel/group username or invite link:\n"
        "_(e.g. @mychannel or https://t.me/mychannel)_\n\n"
        "/cancel to abort.",
        parse_mode="Markdown"
    )
    return ORDER_TARGET


async def recv_target(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["order_target"] = update.message.text.strip()
    db.set_state(update.effective_user.id, "awaiting_order_count")
    await update.message.reply_text(
        "👥 How many members do you want?\n_(minimum 10, maximum 10 000)_",
        parse_mode="Markdown"
    )
    return ORDER_COUNT


async def recv_count(update: Update, context: ContextTypes.DEFAULT_TYPE):
    from config import STARS_PER_MEMBER, ADMIN_IDS
    try:
        count = int(update.message.text.strip())
        if count < 10 or count > 10_000:
            raise ValueError
    except ValueError:
        await update.message.reply_text("❌ Please enter a number between 10 and 10 000.")
        return ORDER_COUNT

    uid        = update.effective_user.id
    target     = context.user_data.pop("order_target", "")
    order_type = context.user_data.pop("order_type", "channel")
    cost       = count * STARS_PER_MEMBER
    u          = db.get_user(uid)

    db.set_state(uid, "")

    if u["stars"] < cost:
        kb = InlineKeyboardMarkup([
            [InlineKeyboardButton("💎 Earn Stars", callback_data="earn_stars")],
            [InlineKeyboardButton("🛒 Buy Stars",  callback_data="buy_stars")],
            [InlineKeyboardButton("⬅️ Main Menu",  callback_data="main_menu")],
        ])
        await update.message.reply_text(
            f"❌ You need *{cost}⭐* but only have *{u['stars']}⭐*.",
            reply_markup=kb, parse_mode="Markdown"
        )
        return ConversationHandler.END

    # Deduct stars and create order
    db.update_stars(uid, -cost)
    order_id = db.create_order(uid, target, order_type, count, cost)

    # Notify admins
    for admin_id in ADMIN_IDS:
        try:
            kb_admin = InlineKeyboardMarkup([[
                InlineKeyboardButton("✅ Approve", callback_data=f"admin_approve_{order_id}"),
                InlineKeyboardButton("❌ Reject",  callback_data=f"admin_reject_{order_id}"),
            ]])
            await update.get_bot().send_message(
                admin_id,
                f"📋 *New Order #{order_id}*\n\n"
                f"👤 User ID: `{uid}`\n"
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
        "⏳ An admin will review your order shortly.",
        reply_markup=kb, parse_mode="Markdown"
    )
    return ConversationHandler.END


async def cancel_order_conv(update: Update, context: ContextTypes.DEFAULT_TYPE):
    db.set_state(update.effective_user.id, "")
    context.user_data.pop("order_target", None)
    context.user_data.pop("order_type", None)
    kb = InlineKeyboardMarkup([[InlineKeyboardButton("⬅️ Main Menu", callback_data="main_menu")]])
    await update.message.reply_text("❌ Order cancelled.", reply_markup=kb)
    return ConversationHandler.END


def order_conv_handler():
    return ConversationHandler(
        entry_points=[
            CallbackQueryHandler(choose_type, pattern="^order_type_(channel|group)$")
        ],
        states={
            ORDER_TARGET: [MessageHandler(filters.TEXT & ~filters.COMMAND, recv_target)],
            ORDER_COUNT:  [MessageHandler(filters.TEXT & ~filters.COMMAND, recv_count)],
        },
        fallbacks=[CommandHandler("cancel", cancel_order_conv)],
        per_message=False,
    )
