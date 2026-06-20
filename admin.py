"""
Admin panel — full control over every bot feature:
  • Required channels (add/remove)
  • Earn channels (add/remove/edit reward)
  • Star codes (create/delete)
  • Settings (daily stars, invite stars, per-member cost, buy contact, limits…)
  • Text editor (edit any bot message in FA or EN, restore defaults)
  • User management (search, view, add/deduct stars, ban check)
  • Orders (approve/reject with note)
  • Broadcast
  • Stats
"""

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    ContextTypes, ConversationHandler,
    CommandHandler, CallbackQueryHandler, MessageHandler, filters
)

import database as db
from config import ADMIN_IDS, RESULTS_CHANNEL_ID
from languages import TEXTS, LANG_NAMES, DEFAULT_LANG

# ── Conversation states ────────────────────────────────────────────────────────
(
    # Channels
    AW_CH_ID, AW_CH_NAME, AW_CH_LINK,
    AW_EARN_ID, AW_EARN_NAME, AW_EARN_LINK, AW_EARN_STARS,
    # Codes
    AW_CODE, AW_CODE_STARS, AW_CODE_USES,
    # Broadcast
    AW_BROADCAST,
    # Order reject
    AW_REJECT_NOTE,
    # Settings
    AW_SETTING_VALUE,
    # Text edit
    AW_TEXT_LANG, AW_TEXT_KEY, AW_TEXT_VALUE,
    # User management
    AW_USER_SEARCH, AW_USER_STARS,
) = range(18)


def is_admin(uid: int) -> bool:
    return uid in ADMIN_IDS


# ── Admin main panel ───────────────────────────────────────────────────────────

def admin_keyboard():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("📢 کانال‌های اجباری",    callback_data="admin_channels"),
         InlineKeyboardButton("💎 کانال‌های کسب",       callback_data="admin_earn_channels")],
        [InlineKeyboardButton("📋 سفارشات در انتظار",   callback_data="admin_orders")],
        [InlineKeyboardButton("🎟 کدهای ستاره",          callback_data="admin_codes")],
        [InlineKeyboardButton("⚙️ تنظیمات",              callback_data="admin_settings")],
        [InlineKeyboardButton("✏️ ویرایش متن‌ها",        callback_data="admin_texts")],
        [InlineKeyboardButton("👤 مدیریت کاربران",       callback_data="admin_users")],
        [InlineKeyboardButton("📣 ارسال همگانی",         callback_data="admin_broadcast"),
         InlineKeyboardButton("📊 آمار",                 callback_data="admin_stats")],
    ])


async def admin_panel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    if not is_admin(uid):
        if update.callback_query:
            await update.callback_query.answer("⛔ Access denied.", show_alert=True)
        else:
            await update.message.reply_text("⛔ Access denied.")
        return

    text = "🛠 *پنل مدیریت*\n\nیک بخش را انتخاب کن:"
    if update.callback_query:
        await update.callback_query.answer()
        await update.callback_query.edit_message_text(text, reply_markup=admin_keyboard(), parse_mode="Markdown")
    else:
        await update.message.reply_text(text, reply_markup=admin_keyboard(), parse_mode="Markdown")


def back_admin():
    return InlineKeyboardMarkup([[InlineKeyboardButton("⬅️ پنل ادمین", callback_data="admin_panel")]])


# ── Required channels ──────────────────────────────────────────────────────────

async def manage_channels(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    if not is_admin(update.effective_user.id):
        return

    channels = db.get_required_channels()
    text     = "📢 *کانال‌های اجباری*\n\n"
    buttons  = []

    if channels:
        for ch in channels:
            text += f"• {ch['channel_name']} (`{ch['channel_id']}`)\n"
            buttons.append([InlineKeyboardButton(
                f"🗑 حذف {ch['channel_name']}",
                callback_data=f"admin_remove_channel_{ch['channel_id']}"
            )])
    else:
        text += "_هیچ کانالی اضافه نشده._"

    buttons.append([InlineKeyboardButton("➕ افزودن کانال اجباری", callback_data="admin_add_channel")])
    buttons.append([InlineKeyboardButton("⬅️ بازگشت", callback_data="admin_panel")])
    await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(buttons), parse_mode="Markdown")


async def add_channel_prompt(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    if not is_admin(update.effective_user.id):
        return
    context.user_data["admin_adding"] = "required"
    await query.edit_message_text(
        "📢 *افزودن کانال اجباری*\n\nآیدی کانال را ارسال کن (مثال: `-1001234567890`).\n"
        "ربات باید ادمین کانال باشد.\n\n/cancel برای لغو",
        parse_mode="Markdown"
    )
    return AW_CH_ID


async def recv_channel_id(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["new_ch_id"] = update.message.text.strip()
    await update.message.reply_text("📝 نام نمایشی کانال را ارسال کن:")
    return AW_CH_NAME


async def recv_channel_name(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["new_ch_name"] = update.message.text.strip()
    await update.message.reply_text("🔗 لینک دعوت کانال را ارسال کن:")
    return AW_CH_LINK


async def recv_channel_link(update: Update, context: ContextTypes.DEFAULT_TYPE):
    link    = update.message.text.strip()
    ch_id   = context.user_data.pop("new_ch_id", "")
    ch_name = context.user_data.pop("new_ch_name", "")
    adding  = context.user_data.pop("admin_adding", "required")

    if adding == "earn":
        context.user_data["earn_ch_id"]   = ch_id
        context.user_data["earn_ch_name"] = ch_name
        context.user_data["earn_link"]    = link
        await update.message.reply_text("⭐ چند ستاره برای عضویت در این کانال؟")
        return AW_EARN_STARS
    else:
        db.add_required_channel(ch_id, ch_name, link)
        await update.message.reply_text(
            f"✅ کانال *{ch_name}* اضافه شد!",
            parse_mode="Markdown",
            reply_markup=back_admin()
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
    text     = "💎 *کانال‌های کسب ستاره*\n\n"
    buttons  = []

    if channels:
        for ch in channels:
            text += f"• {ch['channel_name']} (+{ch['stars_reward']}⭐)\n"
            buttons.append([InlineKeyboardButton(
                f"🗑 حذف {ch['channel_name']}",
                callback_data=f"admin_remove_earn_{ch['channel_id']}"
            )])
    else:
        text += "_هیچ کانالی اضافه نشده._"

    buttons.append([InlineKeyboardButton("➕ افزودن کانال کسب", callback_data="admin_add_earn_channel")])
    buttons.append([InlineKeyboardButton("⬅️ بازگشت", callback_data="admin_panel")])
    await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(buttons), parse_mode="Markdown")


async def add_earn_channel_prompt(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    context.user_data["admin_adding"] = "earn"
    await query.edit_message_text(
        "💎 *افزودن کانال کسب ستاره*\n\nآیدی کانال را ارسال کن.\n\n/cancel برای لغو",
        parse_mode="Markdown"
    )
    return AW_EARN_ID


async def recv_earn_id(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["earn_ch_id"] = update.message.text.strip()
    await update.message.reply_text("📝 نام نمایشی کانال:")
    return AW_EARN_NAME


async def recv_earn_name(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["earn_ch_name"] = update.message.text.strip()
    await update.message.reply_text("🔗 لینک دعوت:")
    return AW_EARN_LINK


async def recv_earn_link(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["earn_link"] = update.message.text.strip()
    await update.message.reply_text("⭐ چند ستاره برای عضویت؟")
    return AW_EARN_STARS


async def recv_earn_stars(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        stars = int(update.message.text.strip())
    except ValueError:
        await update.message.reply_text("❌ عدد معتبر وارد کن.")
        return AW_EARN_STARS

    db.add_earn_channel(
        context.user_data.pop("earn_ch_id", ""),
        context.user_data.pop("earn_ch_name", ""),
        context.user_data.pop("earn_link", ""),
        stars
    )
    await update.message.reply_text("✅ کانال کسب ستاره اضافه شد!", reply_markup=back_admin())
    return ConversationHandler.END


async def remove_earn_channel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    if not is_admin(update.effective_user.id):
        return
    ch_id = query.data.split("admin_remove_earn_", 1)[1]
    db.remove_earn_channel(ch_id)
    await manage_earn_channels(update, context)


# ── Settings ───────────────────────────────────────────────────────────────────

SETTING_LABELS = {
    "daily_stars":      "⭐ ستاره روزانه رایگان",
    "invite_stars":     "👥 ستاره برای دعوت هر دوست",
    "join_stars":       "📢 ستاره برای عضویت در کانال",
    "stars_per_member": "💵 هزینه هر ممبر (ستاره)",
    "buy_contact":      "🛒 آیدی پشتیبانی خرید",
    "bot_username":     "🤖 یوزرنیم ربات (بدون @)",
    "results_channel":  "📡 آیدی کانال نتایج",
    "min_order":        "📉 حداقل تعداد ممبر در سفارش",
    "max_order":        "📈 حداکثر تعداد ممبر در سفارش",
}


async def manage_settings(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    if not is_admin(update.effective_user.id):
        return

    settings = db.get_all_settings()
    text     = "⚙️ *تنظیمات ربات*\n\n"
    buttons  = []

    for key, label in SETTING_LABELS.items():
        val = settings.get(key, "—")
        text += f"{label}: `{val}`\n"
        buttons.append([InlineKeyboardButton(
            f"✏️ {label}",
            callback_data=f"admin_edit_setting_{key}"
        )])

    buttons.append([InlineKeyboardButton("⬅️ بازگشت", callback_data="admin_panel")])
    await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(buttons), parse_mode="Markdown")


async def edit_setting_prompt(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    if not is_admin(update.effective_user.id):
        return
    key     = query.data.split("admin_edit_setting_")[1]
    current = db.get_setting(key, "")
    label   = SETTING_LABELS.get(key, key)
    context.user_data["editing_setting"] = key
    await query.edit_message_text(
        f"✏️ *ویرایش: {label}*\n\nمقدار فعلی: `{current}`\n\nمقدار جدید را ارسال کن:\n\n/cancel برای لغو",
        parse_mode="Markdown"
    )
    return AW_SETTING_VALUE


async def recv_setting_value(update: Update, context: ContextTypes.DEFAULT_TYPE):
    key   = context.user_data.pop("editing_setting", None)
    value = update.message.text.strip()
    if key:
        db.set_setting(key, value)
        label = SETTING_LABELS.get(key, key)
        await update.message.reply_text(
            f"✅ *{label}* به `{value}` تغییر یافت!",
            parse_mode="Markdown",
            reply_markup=back_admin()
        )
    return ConversationHandler.END


# ── Text editor ────────────────────────────────────────────────────────────────

async def manage_texts(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    if not is_admin(update.effective_user.id):
        return

    buttons = [
        [InlineKeyboardButton(name, callback_data=f"admin_text_lang_{code}")]
        for code, name in LANG_NAMES.items()
    ]
    buttons.append([InlineKeyboardButton("⬅️ بازگشت", callback_data="admin_panel")])
    await query.edit_message_text(
        "✏️ *ویرایش متن‌های ربات*\n\nابتدا زبان را انتخاب کن:",
        reply_markup=InlineKeyboardMarkup(buttons),
        parse_mode="Markdown"
    )


async def text_list_for_lang(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    if not is_admin(update.effective_user.id):
        return
    lang = query.data.split("admin_text_lang_")[1]
    context.user_data["text_edit_lang"] = lang

    overrides = db.get_text_overrides(lang)
    keys      = list(TEXTS.get(lang, TEXTS[DEFAULT_LANG]).keys())

    text    = f"✏️ *متن‌های {LANG_NAMES.get(lang, lang)}*\n\n"
    text   += f"تعداد کل: {len(keys)} | ویرایش شده: {len(overrides)}\n\n"
    text   += "یک کلید را برای ویرایش انتخاب کن:"
    buttons = []

    for key in keys:
        has_override = "✏️ " if key in overrides else ""
        buttons.append([InlineKeyboardButton(
            f"{has_override}{key}",
            callback_data=f"admin_text_edit_{key}"
        )])

    buttons.append([InlineKeyboardButton("⬅️ بازگشت", callback_data="admin_texts")])
    # Split into pages of 20 if needed
    await query.edit_message_text(
        text,
        reply_markup=InlineKeyboardMarkup(buttons[:30]),
        parse_mode="Markdown"
    )


async def text_edit_prompt(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    if not is_admin(update.effective_user.id):
        return
    key  = query.data.split("admin_text_edit_")[1]
    lang = context.user_data.get("text_edit_lang", DEFAULT_LANG)
    context.user_data["text_edit_key"] = key

    overrides = db.get_text_overrides(lang)
    default   = TEXTS.get(lang, {}).get(key, "—")
    current   = overrides.get(key, default)

    buttons = []
    if key in overrides:
        buttons.append([InlineKeyboardButton("🔄 بازگشت به پیش‌فرض", callback_data=f"admin_text_reset_{key}")])
    buttons.append([InlineKeyboardButton("⬅️ بازگشت", callback_data=f"admin_text_lang_{lang}")])

    await query.edit_message_text(
        f"✏️ *ویرایش متن: `{key}`* ({LANG_NAMES.get(lang, lang)})\n\n"
        f"متن فعلی:\n`{current}`\n\n"
        f"متن جدید را ارسال کن (از `{{name}}` `{{stars}}` و غیره استفاده کن):\n\n/cancel برای لغو",
        reply_markup=InlineKeyboardMarkup(buttons),
        parse_mode="Markdown"
    )
    return AW_TEXT_VALUE


async def recv_text_value(update: Update, context: ContextTypes.DEFAULT_TYPE):
    key   = context.user_data.pop("text_edit_key", None)
    lang  = context.user_data.get("text_edit_lang", DEFAULT_LANG)
    value = update.message.text

    if key:
        db.set_text_override(lang, key, value)
        await update.message.reply_text(
            f"✅ متن `{key}` برای زبان {LANG_NAMES.get(lang, lang)} ذخیره شد!",
            parse_mode="Markdown",
            reply_markup=back_admin()
        )
    return ConversationHandler.END


async def text_reset(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    if not is_admin(update.effective_user.id):
        return
    key  = query.data.split("admin_text_reset_")[1]
    lang = context.user_data.get("text_edit_lang", DEFAULT_LANG)
    db.delete_text_override(lang, key)

    # Re-show the text list for this language
    overrides = db.get_text_overrides(lang)
    keys      = list(TEXTS.get(lang, TEXTS[DEFAULT_LANG]).keys())
    text      = f"✏️ *متن‌های {LANG_NAMES.get(lang, lang)}*\n\n✅ متن `{key}` به پیش‌فرض بازگشت.\n\nیک کلید را برای ویرایش انتخاب کن:"
    buttons   = []
    for k in keys:
        has_override = "✏️ " if k in overrides else ""
        buttons.append([InlineKeyboardButton(f"{has_override}{k}", callback_data=f"admin_text_edit_{k}")])
    buttons.append([InlineKeyboardButton("⬅️ بازگشت", callback_data="admin_texts")])
    await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(buttons[:30]), parse_mode="Markdown")


# ── User management ────────────────────────────────────────────────────────────

async def manage_users(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    if not is_admin(update.effective_user.id):
        return

    stats = db.get_stats()
    text  = (
        f"👤 *مدیریت کاربران*\n\n"
        f"👥 کل کاربران: *{stats['users']}*\n\n"
        "جستجو: آیدی، یوزرنیم یا اسم کاربر را ارسال کن."
    )
    buttons = [[InlineKeyboardButton("⬅️ بازگشت", callback_data="admin_panel")]]
    context.user_data["admin_action"] = "user_search"
    await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(buttons), parse_mode="Markdown")
    return AW_USER_SEARCH


async def recv_user_search(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query_text = update.message.text.strip()
    users      = db.search_users(query_text)

    if not users:
        await update.message.reply_text("❌ کاربری یافت نشد.", reply_markup=back_admin())
        return ConversationHandler.END

    if len(users) == 1:
        return await _show_user(update, context, users[0])

    buttons = [
        [InlineKeyboardButton(
            f"👤 {u['full_name']} ({u['user_id']})",
            callback_data=f"admin_view_user_{u['user_id']}"
        )]
        for u in users
    ]
    buttons.append([InlineKeyboardButton("⬅️ بازگشت", callback_data="admin_panel")])
    await update.message.reply_text(
        f"✅ *{len(users)} کاربر یافت شد:*",
        reply_markup=InlineKeyboardMarkup(buttons),
        parse_mode="Markdown"
    )
    return ConversationHandler.END


async def view_user(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    if not is_admin(update.effective_user.id):
        return
    uid = int(query.data.split("admin_view_user_")[1])
    u   = db.get_user(uid)
    if not u:
        await query.answer("کاربر یافت نشد.", show_alert=True)
        return
    await _show_user_query(query, context, u)


async def _show_user(update, context, u):
    inv  = db.get_invite_count(u["user_id"])
    ords = db.get_user_orders(u["user_id"])
    text = (
        f"👤 *اطلاعات کاربر*\n\n"
        f"🆔 آیدی: `{u['user_id']}`\n"
        f"📛 نام: {u['full_name']}\n"
        f"👤 یوزرنیم: @{u['username'] or '—'}\n"
        f"⭐ ستاره: *{u['stars']}*\n"
        f"👥 دعوت‌ها: *{inv}*\n"
        f"📋 سفارشات: *{len(ords)}*\n"
        f"🌐 زبان: {u['lang'] or 'fa'}\n"
        f"📅 عضویت: {u['joined_at'][:10] if u['joined_at'] else '—'}"
    )
    buttons = [
        [InlineKeyboardButton("➕ افزودن ستاره", callback_data=f"admin_add_stars_{u['user_id']}"),
         InlineKeyboardButton("➖ کسر ستاره",    callback_data=f"admin_sub_stars_{u['user_id']}")],
        [InlineKeyboardButton("⬅️ بازگشت",       callback_data="admin_panel")],
    ]
    if hasattr(update, "message") and update.message:
        await update.message.reply_text(text, reply_markup=InlineKeyboardMarkup(buttons), parse_mode="Markdown")
    return ConversationHandler.END


async def _show_user_query(query, context, u):
    inv  = db.get_invite_count(u["user_id"])
    ords = db.get_user_orders(u["user_id"])
    text = (
        f"👤 *اطلاعات کاربر*\n\n"
        f"🆔 آیدی: `{u['user_id']}`\n"
        f"📛 نام: {u['full_name']}\n"
        f"👤 یوزرنیم: @{u['username'] or '—'}\n"
        f"⭐ ستاره: *{u['stars']}*\n"
        f"👥 دعوت‌ها: *{inv}*\n"
        f"📋 سفارشات: *{len(ords)}*\n"
        f"🌐 زبان: {u['lang'] or 'fa'}\n"
        f"📅 عضویت: {u['joined_at'][:10] if u['joined_at'] else '—'}"
    )
    buttons = [
        [InlineKeyboardButton("➕ افزودن ستاره", callback_data=f"admin_add_stars_{u['user_id']}"),
         InlineKeyboardButton("➖ کسر ستاره",    callback_data=f"admin_sub_stars_{u['user_id']}")],
        [InlineKeyboardButton("⬅️ بازگشت",       callback_data="admin_panel")],
    ]
    await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(buttons), parse_mode="Markdown")


async def add_stars_prompt(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    uid   = int(query.data.split("admin_add_stars_")[1])
    context.user_data["stars_action"]  = "add"
    context.user_data["stars_user_id"] = uid
    await query.edit_message_text(
        f"➕ *افزودن ستاره به کاربر `{uid}`*\n\nتعداد ستاره را وارد کن:\n\n/cancel برای لغو",
        parse_mode="Markdown"
    )
    return AW_USER_STARS


async def sub_stars_prompt(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    uid   = int(query.data.split("admin_sub_stars_")[1])
    context.user_data["stars_action"]  = "sub"
    context.user_data["stars_user_id"] = uid
    await query.edit_message_text(
        f"➖ *کسر ستاره از کاربر `{uid}`*\n\nتعداد ستاره را وارد کن:\n\n/cancel برای لغو",
        parse_mode="Markdown"
    )
    return AW_USER_STARS


async def recv_user_stars(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        amount = int(update.message.text.strip())
    except ValueError:
        await update.message.reply_text("❌ عدد معتبر وارد کن.")
        return AW_USER_STARS

    action  = context.user_data.pop("stars_action", "add")
    user_id = context.user_data.pop("stars_user_id", None)
    if not user_id:
        return ConversationHandler.END

    delta = amount if action == "add" else -amount
    db.update_stars(user_id, delta)
    u = db.get_user(user_id)

    sign = "+" if action == "add" else "-"
    await update.message.reply_text(
        f"✅ {sign}{amount} ستاره برای کاربر `{user_id}`.\n"
        f"⭐ موجودی جدید: *{u['stars']}*",
        parse_mode="Markdown",
        reply_markup=back_admin()
    )

    # Notify user
    try:
        await context.bot.send_message(
            user_id,
            f"{'➕' if action == 'add' else '➖'} ادمین *{amount} ستاره* {'به حساب شما اضافه کرد' if action == 'add' else 'از حساب شما کسر کرد'}.\n⭐ موجودی: *{u['stars']}*",
            parse_mode="Markdown"
        )
    except Exception:
        pass

    return ConversationHandler.END


# ── Orders ─────────────────────────────────────────────────────────────────────

async def manage_orders(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    if not is_admin(update.effective_user.id):
        return

    orders = db.get_pending_orders()
    if not orders:
        await query.edit_message_text(
            "📋 هیچ سفارش در انتظاری وجود ندارد.",
            reply_markup=back_admin()
        )
        return

    text    = f"📋 *سفارشات در انتظار* ({len(orders)})\n\n"
    buttons = []
    for o in orders:
        text += f"#{o['id']} — {o['target_type']} — {o['members_count']} ممبر — `{o['target']}`\n"
        buttons.append([
            InlineKeyboardButton(f"✅ تأیید #{o['id']}", callback_data=f"admin_approve_{o['id']}"),
            InlineKeyboardButton(f"❌ رد #{o['id']}",    callback_data=f"admin_reject_{o['id']}"),
        ])
    buttons.append([InlineKeyboardButton("⬅️ بازگشت", callback_data="admin_panel")])
    await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(buttons), parse_mode="Markdown")


async def approve_order(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query    = update.callback_query
    await query.answer()
    if not is_admin(update.effective_user.id):
        return
    order_id = int(query.data.split("admin_approve_")[1])
    o        = db.get_order(order_id)
    if not o:
        await query.answer("سفارش یافت نشد.", show_alert=True)
        return

    db.update_order_status(order_id, "approved")

    try:
        link_obj = await context.bot.create_chat_invite_link(RESULTS_CHANNEL_ID, member_limit=1)
        invite   = link_obj.invite_link
    except Exception:
        invite = None

    from helpers import t
    msg = t(o["user_id"], "order_approved_msg",
            id=order_id, target=o["target"], count=o["members_count"])
    if invite:
        msg += f"\n\n🔗 {invite}"

    kb = InlineKeyboardMarkup([[InlineKeyboardButton(
        t(o["user_id"], "btn_my_orders"), callback_data="member_orders"
    )]])
    try:
        await context.bot.send_message(o["user_id"], msg, reply_markup=kb, parse_mode="Markdown")
    except Exception:
        pass

    await query.answer("✅ سفارش تأیید و کاربر مطلع شد!", show_alert=True)
    await manage_orders(update, context)


async def reject_order(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query    = update.callback_query
    await query.answer()
    if not is_admin(update.effective_user.id):
        return
    order_id = int(query.data.split("admin_reject_")[1])
    context.user_data["rejecting_order"] = order_id
    await query.edit_message_text(
        f"❌ *رد سفارش #{order_id}*\n\nدلیل رد را ارسال کن (برای کاربر ارسال می‌شود):\n\n/skip برای رد بدون دلیل | /cancel برای لغو",
        parse_mode="Markdown"
    )
    return AW_REJECT_NOTE


async def recv_reject_note(update: Update, context: ContextTypes.DEFAULT_TYPE):
    order_id = context.user_data.pop("rejecting_order", None)
    note     = update.message.text.strip() if update.message.text != "/skip" else "سفارش توسط ادمین رد شد."
    if not order_id:
        return ConversationHandler.END

    o = db.get_order(order_id)
    if o:
        db.update_order_status(order_id, "rejected", note)
        db.update_stars(o["user_id"], o["stars_cost"])
        from helpers import t
        try:
            await context.bot.send_message(
                o["user_id"],
                t(o["user_id"], "order_rejected_msg",
                  id=order_id, reason=note, cost=o["stars_cost"]),
                parse_mode="Markdown"
            )
        except Exception:
            pass

    await update.message.reply_text("✅ سفارش رد شد و کاربر مطلع شد.", reply_markup=back_admin())
    return ConversationHandler.END


# ── Star codes ─────────────────────────────────────────────────────────────────

async def manage_star_codes(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    if not is_admin(update.effective_user.id):
        return

    codes   = db.get_all_star_codes()
    text    = "🎟 *کدهای ستاره*\n\n"
    buttons = []

    if codes:
        for c in codes:
            text += f"• `{c['code']}` — {c['stars']}⭐ — {c['uses']}/{c['max_uses']} بار استفاده\n"
            buttons.append([InlineKeyboardButton(
                f"🗑 حذف {c['code']}", callback_data=f"admin_delete_code_{c['code']}"
            )])
    else:
        text += "_هیچ کدی وجود ندارد._"

    buttons.append([InlineKeyboardButton("➕ ساخت کد", callback_data="admin_create_code")])
    buttons.append([InlineKeyboardButton("⬅️ بازگشت", callback_data="admin_panel")])
    await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(buttons), parse_mode="Markdown")


async def create_star_code_prompt(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    await query.edit_message_text(
        "🎟 متن کد را ارسال کن (مثال: `LAUNCH50`):\n\n/cancel برای لغو",
        parse_mode="Markdown"
    )
    return AW_CODE


async def recv_code_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["new_code"] = update.message.text.strip().upper()
    await update.message.reply_text("⭐ چند ستاره؟")
    return AW_CODE_STARS


async def recv_code_stars(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        stars = int(update.message.text.strip())
    except ValueError:
        await update.message.reply_text("❌ عدد معتبر وارد کن.")
        return AW_CODE_STARS
    context.user_data["new_code_stars"] = stars
    await update.message.reply_text("🔢 حداکثر تعداد استفاده؟")
    return AW_CODE_USES


async def recv_code_uses(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        uses = int(update.message.text.strip())
    except ValueError:
        await update.message.reply_text("❌ عدد معتبر وارد کن.")
        return AW_CODE_USES

    code  = context.user_data.pop("new_code", "")
    stars = context.user_data.pop("new_code_stars", 0)
    db.create_star_code(code, stars, uses)
    await update.message.reply_text(
        f"✅ کد `{code}` ساخته شد! ({stars}⭐، {uses} بار استفاده)",
        parse_mode="Markdown",
        reply_markup=back_admin()
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
    await query.edit_message_text("📣 پیام همگانی را ارسال کن:\n\n/cancel برای لغو")
    return AW_BROADCAST


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
        f"📣 ارسال همگانی انجام شد!\n✅ موفق: {sent}\n❌ ناموفق: {fail}",
        reply_markup=back_admin()
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
        f"📊 *آمار ربات*\n\n"
        f"👤 کل کاربران: *{s['users']}*\n"
        f"📋 کل سفارشات: *{s['orders']}*\n"
        f"⏳ در انتظار: *{s['pending']}*\n"
        f"✅ تأیید شده: *{s['approved']}*\n"
        f"❌ رد شده: *{s['rejected']}*\n"
        f"⭐ کل ستاره‌های کاربران: *{s['stars_total']}*"
    )
    await query.edit_message_text(text, reply_markup=back_admin(), parse_mode="Markdown")


# ── Cancel ─────────────────────────────────────────────────────────────────────

async def cancel_conv(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("❌ لغو شد.", reply_markup=back_admin())
    return ConversationHandler.END


# ── Conversation handler ───────────────────────────────────────────────────────

def admin_conv_handler():
    return ConversationHandler(
        entry_points=[
            # Channels
            CallbackQueryHandler(add_channel_prompt,       pattern="^admin_add_channel$"),
            CallbackQueryHandler(add_earn_channel_prompt,  pattern="^admin_add_earn_channel$"),
            # Codes
            CallbackQueryHandler(create_star_code_prompt,  pattern="^admin_create_code$"),
            # Broadcast
            CallbackQueryHandler(broadcast_prompt,         pattern="^admin_broadcast$"),
            # Order reject
            CallbackQueryHandler(reject_order,             pattern=r"^admin_reject_(\d+)$"),
            # Settings
            CallbackQueryHandler(edit_setting_prompt,      pattern="^admin_edit_setting_"),
            # Text edit
            CallbackQueryHandler(text_edit_prompt,         pattern="^admin_text_edit_"),
            # User management (search)
            CallbackQueryHandler(manage_users,             pattern="^admin_users$"),
            # User stars
            CallbackQueryHandler(add_stars_prompt,         pattern="^admin_add_stars_"),
            CallbackQueryHandler(sub_stars_prompt,         pattern="^admin_sub_stars_"),
        ],
        states={
            AW_CH_ID:         [MessageHandler(filters.TEXT & ~filters.COMMAND, recv_channel_id)],
            AW_CH_NAME:       [MessageHandler(filters.TEXT & ~filters.COMMAND, recv_channel_name)],
            AW_CH_LINK:       [MessageHandler(filters.TEXT & ~filters.COMMAND, recv_channel_link)],
            AW_EARN_ID:       [MessageHandler(filters.TEXT & ~filters.COMMAND, recv_earn_id)],
            AW_EARN_NAME:     [MessageHandler(filters.TEXT & ~filters.COMMAND, recv_earn_name)],
            AW_EARN_LINK:     [MessageHandler(filters.TEXT & ~filters.COMMAND, recv_earn_link)],
            AW_EARN_STARS:    [MessageHandler(filters.TEXT & ~filters.COMMAND, recv_earn_stars)],
            AW_CODE:          [MessageHandler(filters.TEXT & ~filters.COMMAND, recv_code_text)],
            AW_CODE_STARS:    [MessageHandler(filters.TEXT & ~filters.COMMAND, recv_code_stars)],
            AW_CODE_USES:     [MessageHandler(filters.TEXT & ~filters.COMMAND, recv_code_uses)],
            AW_BROADCAST:     [MessageHandler(filters.TEXT & ~filters.COMMAND, recv_broadcast)],
            AW_REJECT_NOTE:   [
                MessageHandler(filters.TEXT & ~filters.COMMAND, recv_reject_note),
                CommandHandler("skip", recv_reject_note),
            ],
            AW_SETTING_VALUE: [MessageHandler(filters.TEXT & ~filters.COMMAND, recv_setting_value)],
            AW_TEXT_VALUE:    [MessageHandler(filters.TEXT & ~filters.COMMAND, recv_text_value)],
            AW_USER_SEARCH:   [MessageHandler(filters.TEXT & ~filters.COMMAND, recv_user_search)],
            AW_USER_STARS:    [MessageHandler(filters.TEXT & ~filters.COMMAND, recv_user_stars)],
        },
        fallbacks=[CommandHandler("cancel", cancel_conv)],
        per_message=False,
    )
