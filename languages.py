"""
Multi-language text strings — FA / EN
All user-visible text lives here so the admin can edit from the panel.
Dynamic overrides are stored in the DB table `text_overrides`.
"""

TEXTS = {
    "fa": {
        # ── Welcome / Gate ─────────────────────────────────────────────
        "welcome_back":        "🌟 خوش برگشتی، *{name}*!\n\n⭐ ستاره‌ها: *{stars}*\n\nیک گزینه را انتخاب کن:",
        "join_gate":           "👋 خوش آمدی!\n\nبرای استفاده از ربات ابتدا باید در کانال‌های زیر عضو شوی.\nبعد از عضویت، دکمه *بررسی عضویت* را بزن.",
        "join_gate_btn":       "✅ عضو شدم — بررسی کن",

        # ── Main menu ──────────────────────────────────────────────────
        "main_menu_title":     "🌟 *منوی اصلی*\n\n⭐ ستاره‌ها: *{stars}*\n\nیک گزینه انتخاب کن:",
        "btn_daily":           "⭐ ستاره روزانه",
        "btn_profile":         "👤 پروفایل",
        "btn_earn":            "💎 کسب ستاره",
        "btn_invite":          "👥 دعوت دوستان",
        "btn_buy":             "🛒 خرید ستاره",
        "btn_code":            "🎟 کد ستاره",
        "btn_orders":          "📋 سفارشات من",
        "btn_new_order":       "➕ سفارش ممبر جدید",
        "btn_language":        "🌐 تغییر زبان",
        "btn_back":            "⬅️ بازگشت",

        # ── Daily stars ────────────────────────────────────────────────
        "daily_claimed":       "✅ *{amount} ستاره روزانه* دریافت کردی!\n\n⭐ مجموع: *{total}*\n\nفردا برگرد!",
        "daily_already":       "⏳ امروز ستاره روزانه‌ات را گرفته‌ای.\n\n⭐ مجموع: *{total}*\n\nفردا بیا!",

        # ── Profile ────────────────────────────────────────────────────
        "profile_title":       "👤 *پروفایل شما*\n\n🆔 آیدی: `{uid}`\n📛 نام: {name}\n⭐ ستاره: *{stars}*\n👥 دوستان دعوت شده: *{invites}*\n📋 سفارشات: *{orders}*\n📅 تاریخ عضویت: {joined}",

        # ── Earn stars ─────────────────────────────────────────────────
        "earn_title":          "💎 *کسب ستاره*\n\nدر کانال‌های زیر عضو شو و ستاره بگیر!",
        "earn_empty":          "😔 هیچ کانال فعالی وجود ندارد. بعداً بررسی کن!",
        "earn_already":        "✅ قبلاً برای این کانال ستاره گرفته‌ای.",
        "earn_not_joined":     "❌ هنوز عضو این کانال نشده‌ای! ابتدا عضو شو.",
        "earn_success":        "🎉 *{stars} ستاره* دریافت کردی!\n\n⭐ مجموع: *{total}*",

        # ── Invite ─────────────────────────────────────────────────────
        "invite_title":        "👥 *دعوت دوستان*\n\n🔗 لینک دعوت شما:\n`{link}`\n\n💡 به ازای هر دوستی که با لینک شما عضو شود، *{reward} ستاره* دریافت می‌کنید!\n\n👥 دوستان دعوت شده: *{count}*",
        "invite_reward_msg":   "🎉 دوستت *{name}* از لینک شما ثبت‌نام کرد!\n*{stars} ستاره* دریافت کردی ⭐",

        # ── Buy stars ──────────────────────────────────────────────────
        "buy_title":           "🛒 *خرید ستاره*\n\nبرای خرید ستاره با ادمین در تماس باشید:",

        # ── Star code ──────────────────────────────────────────────────
        "code_prompt":         "🎟 *بازخرید کد ستاره*\n\nکد خود را تایپ کرده و ارسال کن:",
        "code_success":        "🎉 کد با موفقیت فعال شد! *{stars} ستاره* دریافت کردی.\n\n⭐ مجموع: *{total}*",
        "code_invalid":        "❌ کد نامعتبر یا قبلاً استفاده شده. دوباره امتحان کن.",

        # ── Orders ─────────────────────────────────────────────────────
        "orders_empty":        "📋 هیچ سفارشی ندارید.\n\nاولین سفارش خود را ثبت کن!",
        "orders_title":        "📋 *سفارشات شما*\n\n",
        "order_detail":        "📋 *سفارش #{id}*\n\n📌 هدف: `{target}`\n📂 نوع: {type}\n👥 ممبر: {count}\n⭐ هزینه: {cost}\n{emoji} وضعیت: *{status}*\n📅 تاریخ: {date}",
        "order_note":          "\n📝 توضیح: {note}",
        "order_placed":        "✅ *سفارش #{id} ثبت شد!*\n\n📌 هدف: `{target}`\n👥 ممبر: {count}\n⭐ کسر شد: {cost}\n\n⏳ ادمین بررسی می‌کند. اطلاع داده خواهد شد.",
        "order_approved_msg":  "✅ *سفارش #{id} تأیید شد!*\n\n📌 هدف: `{target}`\n👥 ممبر: {count}\n\n📣 *مراحل بعدی:*\n۱️⃣ کانال/گروه خود را عمومی کن یا ربات را ادمین کن.\n۲️⃣ ممبرها ظرف ۲۴ ساعت اضافه می‌شوند.\n۳️⃣ پیشرفت را در لیست سفارشات دنبال کن.",
        "order_rejected_msg":  "❌ *سفارش #{id} رد شد.*\n\n📝 دلیل: {reason}\n\n💫 *{cost} ستاره* بازگشت داده شد.",
        "order_cancelled":     "✅ سفارش لغو شد و ستاره‌ها بازگشت داده شد.",
        "order_not_enough":    "❌ به *{cost}⭐* نیاز داری ولی فقط *{have}⭐* داری.",
        "order_ask_type":      "➕ *سفارش ممبر جدید*\n\n⭐ ستاره‌های شما: *{stars}*\n💵 هزینه: *{price} ستاره به ازای هر ممبر*\n\nچه نوع هدفی می‌خواهی رشد دهی؟",
        "order_ask_target":    "📌 یوزرنیم یا لینک دعوت کانال/گروه را ارسال کن:\n_(مثال: @mychannel یا https://t.me/mychannel)_\n\n/cancel برای لغو",
        "order_ask_count":     "👥 چند ممبر می‌خواهی؟ (حداقل ۱۰، حداکثر ۱۰۰۰۰)",
        "order_count_invalid": "❌ عدد معتبر بین ۱۰ و ۱۰۰۰۰ وارد کن.",
        "btn_channel":         "📢 کانال",
        "btn_group":           "👥 گروه",
        "btn_new_order_small": "➕ سفارش جدید",
        "btn_cancel_order":    "❌ لغو سفارش",
        "btn_my_orders":       "📋 سفارشات من",
        "btn_earn_stars":      "💎 کسب ستاره",
        "btn_buy_stars":       "🛒 خرید ستاره",
        "btn_main_menu":       "⬅️ منوی اصلی",
        "btn_verify":          "✅ تأیید عضویت: {name}",
        "cancelled":           "❌ لغو شد.",

        # ── Language picker ────────────────────────────────────────────
        "choose_lang":         "🌐 زبان مورد نظر خود را انتخاب کن:",
        "lang_set":            "✅ زبان به *{lang}* تغییر یافت!",
    },

    "en": {
        # ── Welcome / Gate ─────────────────────────────────────────────
        "welcome_back":        "🌟 Welcome back, *{name}*!\n\n⭐ Stars: *{stars}*\n\nChoose an option:",
        "join_gate":           "👋 Welcome!\n\nTo use this bot you must first join the channels below.\nAfter joining, press *I Joined — Check Again*.",
        "join_gate_btn":       "✅ I Joined — Check Again",

        # ── Main menu ──────────────────────────────────────────────────
        "main_menu_title":     "🌟 *Main Menu*\n\n⭐ Stars: *{stars}*\n\nChoose an option:",
        "btn_daily":           "⭐ Daily Stars",
        "btn_profile":         "👤 Profile",
        "btn_earn":            "💎 Earn Stars",
        "btn_invite":          "👥 Invite Friends",
        "btn_buy":             "🛒 Buy Stars",
        "btn_code":            "🎟 Star Code",
        "btn_orders":          "📋 My Orders",
        "btn_new_order":       "➕ New Member Order",
        "btn_language":        "🌐 Change Language",
        "btn_back":            "⬅️ Back",

        # ── Daily stars ────────────────────────────────────────────────
        "daily_claimed":       "✅ You claimed *{amount} daily stars*!\n\n⭐ Total: *{total}*\n\nCome back tomorrow!",
        "daily_already":       "⏳ You already claimed your daily stars today.\n\n⭐ Total: *{total}*\n\nCome back tomorrow!",

        # ── Profile ────────────────────────────────────────────────────
        "profile_title":       "👤 *Your Profile*\n\n🆔 ID: `{uid}`\n📛 Name: {name}\n⭐ Stars: *{stars}*\n👥 Friends Invited: *{invites}*\n📋 Orders: *{orders}*\n📅 Joined: {joined}",

        # ── Earn stars ─────────────────────────────────────────────────
        "earn_title":          "💎 *Earn Stars*\n\nJoin a channel below and claim your stars!",
        "earn_empty":          "😔 No earning channels available right now. Check back later!",
        "earn_already":        "✅ You already claimed stars for this channel.",
        "earn_not_joined":     "❌ You haven't joined this channel yet! Join first.",
        "earn_success":        "🎉 You received *{stars} stars*!\n\n⭐ Total: *{total}*",

        # ── Invite ─────────────────────────────────────────────────────
        "invite_title":        "👥 *Invite Friends*\n\n🔗 Your invite link:\n`{link}`\n\n💡 You receive *{reward} stars* for every friend who joins!\n\n👥 Friends invited: *{count}*",
        "invite_reward_msg":   "🎉 Your friend *{name}* joined via your link!\nYou received *{stars} stars* ⭐",

        # ── Buy stars ──────────────────────────────────────────────────
        "buy_title":           "🛒 *Buy Stars*\n\nContact admin to purchase stars:",

        # ── Star code ──────────────────────────────────────────────────
        "code_prompt":         "🎟 *Redeem Star Code*\n\nType your code and send it:",
        "code_success":        "🎉 Code redeemed! You received *{stars} stars*.\n\n⭐ Total: *{total}*",
        "code_invalid":        "❌ Invalid or already used code. Please try again.",

        # ── Orders ─────────────────────────────────────────────────────
        "orders_empty":        "📋 You have no orders yet.\n\nPlace your first order below!",
        "orders_title":        "📋 *Your Orders*\n\n",
        "order_detail":        "📋 *Order #{id}*\n\n📌 Target: `{target}`\n📂 Type: {type}\n👥 Members: {count}\n⭐ Cost: {cost}\n{emoji} Status: *{status}*\n📅 Date: {date}",
        "order_note":          "\n📝 Note: {note}",
        "order_placed":        "✅ *Order #{id} placed!*\n\n📌 Target: `{target}`\n👥 Members: {count}\n⭐ Deducted: {cost}\n\n⏳ An admin will review your order shortly.",
        "order_approved_msg":  "✅ *Order #{id} Approved!*\n\n📌 Target: `{target}`\n👥 Members: {count}\n\n📣 *What to do next:*\n1️⃣ Make sure your channel/group is public or add our bot as admin.\n2️⃣ Members will start joining within 24 hours.\n3️⃣ Track progress in your orders list.",
        "order_rejected_msg":  "❌ *Order #{id} was rejected.*\n\n📝 Reason: {reason}\n\n💫 *{cost} stars* have been refunded.",
        "order_cancelled":     "✅ Order cancelled and stars refunded.",
        "order_not_enough":    "❌ You need *{cost}⭐* but only have *{have}⭐*.",
        "order_ask_type":      "➕ *New Member Order*\n\n⭐ Your stars: *{stars}*\n💵 Cost: *{price} stars per member*\n\nWhat type of target do you want to grow?",
        "order_ask_target":    "📌 Send the username or invite link:\n_(e.g. @mychannel or https://t.me/mychannel)_\n\n/cancel to abort",
        "order_ask_count":     "👥 How many members? (min 10, max 10 000)",
        "order_count_invalid": "❌ Enter a number between 10 and 10 000.",
        "btn_channel":         "📢 Channel",
        "btn_group":           "👥 Group",
        "btn_new_order_small": "➕ New Order",
        "btn_cancel_order":    "❌ Cancel Order",
        "btn_my_orders":       "📋 My Orders",
        "btn_earn_stars":      "💎 Earn Stars",
        "btn_buy_stars":       "🛒 Buy Stars",
        "btn_main_menu":       "⬅️ Main Menu",
        "btn_verify":          "✅ Verify: {name}",
        "cancelled":           "❌ Cancelled.",

        # ── Language picker ────────────────────────────────────────────
        "choose_lang":         "🌐 Choose your language:",
        "lang_set":            "✅ Language set to *{lang}*!",
    },
}

LANG_NAMES = {"fa": "🇮🇷 فارسی", "en": "🇬🇧 English"}
DEFAULT_LANG = "fa"
