"""
Star-bot — main entry point (flat structure, no handlers folder)
"""

from telegram.ext import (
    Application, CommandHandler, CallbackQueryHandler,
    MessageHandler, filters
)

from config import BOT_TOKEN
import database as db

from user import (
    start, main_menu, daily_stars, profile,
    earn_stars, verify_join, invite_friends,
    buy_stars, star_code, member_orders,
    check_order_status, cancel_order, new_order,
    handle_text, choose_language, set_language,
)
from orders import order_conv_handler
from admin import (
    admin_panel, admin_conv_handler,
    manage_channels, remove_channel,
    manage_earn_channels, remove_earn_channel,
    manage_orders, approve_order,
    manage_star_codes, delete_star_code,
    manage_settings, manage_texts,
    text_list_for_lang, text_reset,
    view_user, stats,
)


def main():
    db.init_db()

    app = Application.builder().token(BOT_TOKEN).build()

    # ── Conversation handlers (must be first) ──────────────────────────────────
    app.add_handler(admin_conv_handler())
    app.add_handler(order_conv_handler())

    # ── Commands ───────────────────────────────────────────────────────────────
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("admin", admin_panel))

    # ── Admin panel ────────────────────────────────────────────────────────────
    app.add_handler(CallbackQueryHandler(admin_panel,           pattern="^admin_panel$"))
    app.add_handler(CallbackQueryHandler(manage_channels,       pattern="^admin_channels$"))
    app.add_handler(CallbackQueryHandler(remove_channel,        pattern="^admin_remove_channel_"))
    app.add_handler(CallbackQueryHandler(manage_earn_channels,  pattern="^admin_earn_channels$"))
    app.add_handler(CallbackQueryHandler(remove_earn_channel,   pattern="^admin_remove_earn_"))
    app.add_handler(CallbackQueryHandler(manage_orders,         pattern="^admin_orders$"))
    app.add_handler(CallbackQueryHandler(approve_order,         pattern=r"^admin_approve_(\d+)$"))
    app.add_handler(CallbackQueryHandler(manage_star_codes,     pattern="^admin_codes$"))
    app.add_handler(CallbackQueryHandler(delete_star_code,      pattern="^admin_delete_code_"))
    app.add_handler(CallbackQueryHandler(manage_settings,       pattern="^admin_settings$"))
    app.add_handler(CallbackQueryHandler(manage_texts,          pattern="^admin_texts$"))
    app.add_handler(CallbackQueryHandler(text_list_for_lang,    pattern="^admin_text_lang_"))
    app.add_handler(CallbackQueryHandler(text_reset,            pattern="^admin_text_reset_"))
    app.add_handler(CallbackQueryHandler(view_user,             pattern="^admin_view_user_"))
    app.add_handler(CallbackQueryHandler(stats,                 pattern="^admin_stats$"))

    # ── User navigation ────────────────────────────────────────────────────────
    app.add_handler(CallbackQueryHandler(main_menu,             pattern="^main_menu$"))
    app.add_handler(CallbackQueryHandler(daily_stars,           pattern="^daily_stars$"))
    app.add_handler(CallbackQueryHandler(profile,               pattern="^profile$"))
    app.add_handler(CallbackQueryHandler(earn_stars,            pattern="^earn_stars$"))
    app.add_handler(CallbackQueryHandler(verify_join,           pattern="^verify_join_"))
    app.add_handler(CallbackQueryHandler(invite_friends,        pattern="^invite_friends$"))
    app.add_handler(CallbackQueryHandler(buy_stars,             pattern="^buy_stars$"))
    app.add_handler(CallbackQueryHandler(star_code,             pattern="^star_code$"))
    app.add_handler(CallbackQueryHandler(member_orders,         pattern="^member_orders$"))
    app.add_handler(CallbackQueryHandler(check_order_status,    pattern="^order_status_"))
    app.add_handler(CallbackQueryHandler(cancel_order,          pattern="^cancel_order_"))
    app.add_handler(CallbackQueryHandler(new_order,             pattern="^new_order$"))
    app.add_handler(CallbackQueryHandler(choose_language,       pattern="^choose_language$"))
    app.add_handler(CallbackQueryHandler(set_language,          pattern="^set_lang_"))

    # ── Text fallback ──────────────────────────────────────────────────────────
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text))

    print("🤖 Bot is running...")
    app.run_polling()


if __name__ == "__main__":
    main()
