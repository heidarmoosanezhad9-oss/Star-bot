"""
Order placement conversation handler.
"""

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    ContextTypes, ConversationHandler,
    CallbackQueryHandler, MessageHandler, CommandHandler, filters
)

import database as db
from config import ADMIN_IDS
from helpers import t

ORDER_TARGET, ORDER_COUNT = range(2)


async def choose_type(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    uid        = update.effective_user.id
    order_type = query.data.split("order_type_")[1]
    context.user_data["order_type"] = order_type
    db.set_state(uid, "awaiting_order_target")

    await query.edit_message_text(
        t(uid, "order_ask_target"),
        parse_mode="Markdown"
    )
    return ORDER_TARGET


async def recv_target(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    context.user_data["order_target"] = update.message.text.strip()
    db.set_state(uid, "awaiting_order_count")
    await update.message.reply_text(t(uid, "order_ask_count"), parse_mode="Markdown")
    return ORDER_COUNT


async def recv_count(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid     = update.effective_user.id
    min_ord = db.get_int_setting("min_order", 10)
    max_ord = db.get_int_setting("max_order", 10000)

    try:
        count = int(update.message.text.strip())
        if count < min_ord or count > max_ord:
            raise ValueError
    except ValueError:
        await update.message.reply_text(t(uid, "order_count_invalid"), parse_mode="Markdown")
        return ORDER_COUNT

    target     = context.user_data.pop("order_target", "")
    order_type = context.user_data.pop("order_type", "channel")
    price      = db.get_int_setting("stars_per_member", 5)
    cost       = count * price
    u          = db.get_user(uid)

    db.set_state(uid, "")

    if u["stars"] < cost:
        kb = InlineKeyboardMarkup([
            [InlineKeyboardButton(t(uid, "btn_earn_stars"), callback_data="earn_stars")],
            [InlineKeyboardButton(t(uid, "btn_buy_stars"),  callback_data="buy_stars")],
            [InlineKeyboardButton(t(uid, "btn_main_menu"),  callback_data="main_menu")],
        ])
        await update.message.reply_text(
            t(uid, "order_not_enough", cost=cost, have=u["stars"]),
            reply_markup=kb, parse_mode="Markdown"
        )
        return ConversationHandler.END

    db.update_stars(uid, -cost)
    order_id = db.create_order(uid, target, order_type, count, cost)

    for admin_id in ADMIN_IDS:
        try:
            kb_admin = InlineKeyboardMarkup([[
                InlineKeyboardButton("✅ Approve", callback_data=f"admin_approve_{order_id}"),
                InlineKeyboardButton("❌ Reject",  callback_data=f"admin_reject_{order_id}"),
            ]])
            await update.get_bot().send_message(
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
        [InlineKeyboardButton(t(uid, "btn_my_orders"), callback_data="member_orders")],
        [InlineKeyboardButton(t(uid, "btn_main_menu"), callback_data="main_menu")],
    ])
    await update.message.reply_text(
        t(uid, "order_placed", id=order_id, target=target, count=count, cost=cost),
        reply_markup=kb, parse_mode="Markdown"
    )
    return ConversationHandler.END


async def cancel_order_conv(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    db.set_state(uid, "")
    context.user_data.pop("order_target", None)
    context.user_data.pop("order_type", None)
    kb = InlineKeyboardMarkup([[InlineKeyboardButton(t(uid, "btn_main_menu"), callback_data="main_menu")]])
    await update.message.reply_text(t(uid, "cancelled"), reply_markup=kb)
    return ConversationHandler.END


def order_conv_handler():
    return ConversationHandler(
        entry_points=[CallbackQueryHandler(choose_type, pattern="^order_type_(channel|group)$")],
        states={
            ORDER_TARGET: [MessageHandler(filters.TEXT & ~filters.COMMAND, recv_target)],
            ORDER_COUNT:  [MessageHandler(filters.TEXT & ~filters.COMMAND, recv_count)],
        },
        fallbacks=[CommandHandler("cancel", cancel_order_conv)],
        per_message=False,
    )
