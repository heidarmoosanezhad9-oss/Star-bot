"""
User-facing handlers — fully localised, settings from DB.
"""

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
from telegram.error import BadRequest

import database as db
from config import ADMIN_IDS
from helpers import t
from languages import TEXTS, LANG_NAMES, DEFAULT_LANG


# ── Keyboards ──────────────────────────────────────────────────────────────────

def main_menu_keyboard(uid: int):
    return InlineKeyboardMarkup([
        [InlineKeyboardButton(t(uid, "btn_daily"),    callback_data="daily_stars"),
         InlineKeyboardButton(t(uid, "btn_profile"),  callback_data="profile")],
        [InlineKeyboardButton(t(uid, "btn_earn"),     callback_data="earn_stars"),
         InlineKeyboardButton(t(uid, "btn_invite"),   callback_data="invite_friends")],
        [InlineKeyboardButton(t(uid, "btn_buy"),      callback_data="buy_stars"),
         InlineKeyboardButton(t(uid, "btn_code"),     callback_data="star_code")],
        [InlineKeyboardButton(t(uid, "btn_orders"),   callback_data="member_orders")],
        [InlineKeyboardButton(t(uid, "btn_new_order"),callback_data="new_order")],
        [InlineKeyboardButton(t(uid, "btn_language"), callback_data="choose_language")],
    ])


def back_btn(uid: int, cb="main_menu"):
    return InlineKeyboardMarkup([[InlineKeyboardButton(t(uid, "btn_back"), callback_data=cb)]])


# ── Required channel gate ──────────────────────────────────────────────────────

async def _check_required_channels(bot, user_id: int) -> list:
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
    uid = update.effective_user.id
    buttons = [
        [InlineKeyboardButton(f"📢 {ch['channel_name']}", url=ch["invite_link"])]
        for ch in not_joined
    ]
    buttons.append([InlineKeyboardButton(t(uid, "join_gate_btn"), callback_data="main_menu")])
    kb   = InlineKeyboardMarkup(buttons)
    text = t(uid, "join_gate")
    if update.callback_query:
        await update.callback_query.edit_message_text(text, reply_markup=kb, parse_mode="Markdown")
    else:
        await update.message.reply_text(text, reply_markup=kb, parse_mode="Markdown")


# ── /start ─────────────────────────────────────────────────────────────────────

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    args = context.args

    invited_by = None
    if args:
        try:
            invited_by = int(args[0])
            if invited_by == user.id:
                invited_by = None
        except ValueError:
            pass

    db.upsert_user(user.id, user.username or "", user.full_name, invited_by)

    if invited_by:
        invite_stars = db.get_int_setting("invite_stars", 10)
        rewarded = db.record_invite_reward(invited_by, user.id)
        if rewarded:
            try:
                await context.bot.send_message(
                    invited_by,
                    t(invited_by, "invite_reward_msg", name=user.full_name, stars=invite_stars),
                    parse_mode="Markdown"
                )
            except Exception:
                pass

    not_joined = await _check_required_channels(context.bot, user.id)
    if not_joined:
        await _send_join_gate(update, context, not_joined)
        return

    u = db.get_user(uid)
    text = t(uid, "main_menu_title", stars=u["stars"])
    kb   = main_menu_keyboard(uid)
    try:
        await query.edit_message_text(text, reply_markup=kb, parse_mode="Markdown")
    except Exception:
        await context.bot.send_message(uid, text, reply_markup=kb, parse_mode="Markdown")


# ── Main menu ──────────────────────────────────────────────────────────────────

async def main_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    uid   = update.effective_user.id

    not_joined = await _check_required_channels(context.bot, uid)
    if not_joined:
        await _send_join_gate(update, context, not_joined)
        return

    u = db.get_user(uid)
    await query.edit_message_text(
        t(uid, "main_menu_title", stars=u["stars"]),
        reply_markup=main_menu_keyboard(uid),
        parse_mode="Markdown"
    )


# ── Language picker ────────────────────────────────────────────────────────────

async def choose_language(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    uid   = update.effective_user.id

    buttons = [
        [InlineKeyboardButton(name, callback_data=f"set_lang_{code}")]
        for code, name in LANG_NAMES.items()
    ]
    buttons.append([InlineKeyboardButton(t(uid, "btn_back"), callback_data="main_menu")])
    await query.edit_message_text(
        t(uid, "choose_lang"),
        reply_markup=InlineKeyboardMarkup(buttons),
        parse_mode="Markdown"
    )


async def set_language(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    uid  = update.effective_user.id
    lang = query.data.split("set_lang_")[1]

    if lang not in TEXTS:
        lang = DEFAULT_LANG

    db.set_user_lang(uid, lang)
    u = db.get_user(uid)
    await query.edit_message_text(
        t(uid, "lang_set", lang=LANG_NAMES.get(lang, lang)) + "\n\n" +
        t(uid, "main_menu_title", stars=u["stars"]),
        reply_markup=main_menu_keyboard(uid),
        parse_mode="Markdown"
    )


# ── Daily stars ────────────────────────────────────────────────────────────────

async def daily_stars(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    uid   = update.effective_user.id

    claimed = db.claim_daily(uid)
    u       = db.get_user(uid)
    daily   = db.get_int_setting("daily_stars", 5)

    if claimed:
        text = t(uid, "daily_claimed", amount=daily, total=u["stars"])
    else:
        text = t(uid, "daily_already", total=u["stars"])

    await query.edit_message_text(text, reply_markup=back_btn(uid), parse_mode="Markdown")


# ── Profile ────────────────────────────────────────────────────────────────────

async def profile(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    uid   = update.effective_user.id
    u     = db.get_user(uid)
    inv   = db.get_invite_count(uid)
    ords  = db.get_user_orders(uid)

    text = t(uid, "profile_title",
             uid=uid,
             name=u["full_name"],
             stars=u["stars"],
             invites=inv,
             orders=len(ords),
             joined=u["joined_at"][:10] if u["joined_at"] else "—")

    await query.edit_message_text(text, reply_markup=back_btn(uid), parse_mode="Markdown")


# ── Earn stars ─────────────────────────────────────────────────────────────────

async def earn_stars(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    uid   = update.effective_user.id

    channels = db.get_earn_channels()
    if not channels:
        await query.edit_message_text(
            t(uid, "earn_empty"),
            reply_markup=back_btn(uid),
            parse_mode="Markdown"
        )
        return

    buttons = []
    for ch in channels:
        already = db.has_claimed_earn(uid, ch["channel_id"])
        label = f"✅ {ch['channel_name']}" if already else f"📢 {ch['channel_name']} (+{ch['stars_reward']}⭐)"
        buttons.append([InlineKeyboardButton(label, url=ch["invite_link"])])
        if not already:
            verify_label = t(uid, "btn_verify", name=ch["channel_name"])
            buttons.append([InlineKeyboardButton(verify_label, callback_data=f"verify_join_{ch['channel_id']}")])

    buttons.append([InlineKeyboardButton(t(uid, "btn_back"), callback_data="main_menu")])
    await query.edit_message_text(
        t(uid, "earn_title"),
        reply_markup=InlineKeyboardMarkup(buttons),
        parse_mode="Markdown"
    )


async def verify_join(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    uid      = update.effective_user.id
    ch_id    = query.data.split("verify_join_")[1]

    if db.has_claimed_earn(uid, ch_id):
        await query.answer(t(uid, "earn_already"), show_alert=True)
        return

    try:
        member = await context.bot.get_chat_member(ch_id, uid)
        joined = member.status not in ("left", "kicked", "banned")
    except Exception:
        joined = False

    if not joined:
        await query.answer(t(uid, "earn_not_joined"), show_alert=True)
        return

    conn_rows = db.get_earn_channels()
    ch = next((c for c in conn_rows if c["channel_id"] == ch_id), None)
    if not ch:
        return

    db.record_earn_claim(uid, ch_id)
    db.update_stars(uid, ch["stars_reward"])
    u = db.get_user(uid)
    await query.answer(
        t(uid, "earn_success", stars=ch["stars_reward"], total=u["stars"]),
        show_alert=True
    )
    await earn_stars(update, context)


# ── Invite friends ─────────────────────────────────────────────────────────────

async def invite_friends(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    uid   = update.effective_user.id

    bot_username  = db.get_setting("bot_username", "bot")
    invite_stars  = db.get_int_setting("invite_stars", 10)
    link          = f"https://t.me/{bot_username}?start={uid}"
    count         = db.get_invite_count(uid)

    await query.edit_message_text(
        t(uid, "invite_title", link=link, reward=invite_stars, count=count),
        reply_markup=back_btn(uid),
        parse_mode="Markdown"
    )


# ── Buy stars ──────────────────────────────────────────────────────────────────

async def buy_stars(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    uid   = update.effective_user.id

    contact = db.get_setting("buy_contact", "@admin")
    buttons = [
        [InlineKeyboardButton(f"💬 {contact}", url=f"https://t.me/{contact.lstrip('@')}")],
        [InlineKeyboardButton(t(uid, "btn_back"), callback_data="main_menu")],
    ]
    await query.edit_message_text(
        t(uid, "buy_title"),
        reply_markup=InlineKeyboardMarkup(buttons),
        parse_mode="Markdown"
    )


# ── Star code ──────────────────────────────────────────────────────────────────

async def star_code(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    uid   = update.effective_user.id

    db.set_state(uid, "awaiting_star_code")
    kb = InlineKeyboardMarkup([[InlineKeyboardButton("❌ Cancel", callback_data="main_menu")]])
    await query.edit_message_text(t(uid, "code_prompt"), reply_markup=kb, parse_mode="Markdown")


# ── My orders ─────────────────────────────────────────────────────────────────

async def member_orders(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    uid   = update.effective_user.id
    ords  = db.get_user_orders(uid)

    status_emoji = {"pending": "⏳", "approved": "✅", "rejected": "❌", "done": "🏁"}

    if not ords:
        buttons = [
            [InlineKeyboardButton(t(uid, "btn_new_order_small"), callback_data="new_order")],
            [InlineKeyboardButton(t(uid, "btn_back"), callback_data="main_menu")],
        ]
        await query.edit_message_text(
            t(uid, "orders_empty"),
            reply_markup=InlineKeyboardMarkup(buttons),
            parse_mode="Markdown"
        )
        return

    text    = t(uid, "orders_title")
    buttons = []
    for o in ords:
        emoji = status_emoji.get(o["status"], "❓")
        text += f"{emoji} #{o['id']} — {o['target_type']} — {o['members_count']} members — {o['status']}\n"
        buttons.append([InlineKeyboardButton(
            f"{emoji} #{o['id']} details",
            callback_data=f"order_status_{o['id']}"
        )])

    buttons.append([InlineKeyboardButton(t(uid, "btn_new_order_small"), callback_data="new_order")])
    buttons.append([InlineKeyboardButton(t(uid, "btn_back"), callback_data="main_menu")])
    await query.edit_message_text(
        text, reply_markup=InlineKeyboardMarkup(buttons), parse_mode="Markdown"
    )


async def check_order_status(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query    = update.callback_query
    await query.answer()
    uid      = update.effective_user.id
    order_id = int(query.data.split("order_status_")[1])
    o        = db.get_order(order_id)

    if not o or o["user_id"] != uid:
        await query.answer("Order not found.", show_alert=True)
        return

    status_emoji = {"pending": "⏳", "approved": "✅", "rejected": "❌", "done": "🏁"}
    emoji = status_emoji.get(o["status"], "❓")

    text = t(uid, "order_detail",
             id=o["id"], target=o["target"], type=o["target_type"],
             count=o["members_count"], cost=o["stars_cost"],
             emoji=emoji, status=o["status"],
             date=o["created_at"][:10])

    if o["note"]:
        text += t(uid, "order_note", note=o["note"])

    buttons = [[InlineKeyboardButton(t(uid, "btn_my_orders"), callback_data="member_orders")]]
    if o["status"] == "pending":
        buttons.insert(0, [InlineKeyboardButton(
            t(uid, "btn_cancel_order"), callback_data=f"cancel_order_{o['id']}"
        )])

    await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(buttons), parse_mode="Markdown")


async def cancel_order(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query    = update.callback_query
    await query.answer()
    uid      = update.effective_user.id
    order_id = int(query.data.split("cancel_order_")[1])
    o        = db.get_order(order_id)

    if not o or o["user_id"] != uid or o["status"] != "pending":
        await query.answer("Cannot cancel.", show_alert=True)
        return

    db.update_order_status(order_id, "rejected", "Cancelled by user")
    db.update_stars(uid, o["stars_cost"])
    await query.answer(t(uid, "order_cancelled"), show_alert=True)
    await member_orders(update, context)


# ── New order ──────────────────────────────────────────────────────────────────

async def new_order(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    uid   = update.effective_user.id
    u     = db.get_user(uid)
    price = db.get_int_setting("stars_per_member", 5)

    kb = InlineKeyboardMarkup([
        [InlineKeyboardButton(t(uid, "btn_channel"), callback_data="order_type_channel"),
         InlineKeyboardButton(t(uid, "btn_group"),   callback_data="order_type_group")],
        [InlineKeyboardButton(t(uid, "btn_back"),    callback_data="main_menu")],
    ])
    await query.edit_message_text(
        t(uid, "order_ask_type", stars=u["stars"], price=price),
        reply_markup=kb,
        parse_mode="Markdown"
    )


# ── Text message handler ───────────────────────────────────────────────────────

async def handle_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid   = update.effective_user.id
    state = db.get_state(uid)
    text  = update.message.text.strip()

    if state == "awaiting_star_code":
        stars = db.redeem_star_code(uid, text)
        db.set_state(uid, "")
        u = db.get_user(uid)
        if stars == -1:
            msg = t(uid, "code_invalid")
        else:
            msg = t(uid, "code_success", stars=stars, total=u["stars"])
        kb = InlineKeyboardMarkup([[InlineKeyboardButton(t(uid, "btn_main_menu"), callback_data="main_menu")]])
        await update.message.reply_text(msg, reply_markup=kb, parse_mode="Markdown")
