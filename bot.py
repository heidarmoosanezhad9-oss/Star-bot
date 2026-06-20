import logging
from telegram.ext import (
    Application, CommandHandler, CallbackQueryHandler,
    MessageHandler, filters
)
from config import BOT_TOKEN
import user, admin, orders
from database import init_db

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO
)

def main():
    init_db()
    app = Application.builder().token(BOT_TOKEN).build()

    app.add_handler(CommandHandler("start", user.start))
    app.add_handler(CallbackQueryHandler(user.main_menu, pattern="^main_menu$"))
    app.add_handler(CallbackQueryHandler(user.daily_stars, pattern="^daily_stars$"))
    app.add_handler(CallbackQueryHandler(user.profile, pattern="^profile$"))
    app.add_handler(CallbackQueryHandler(user.earn_stars, pattern="^earn_stars$"))
    app.add_handler(CallbackQueryHandler(user.invite_friends, pattern="^invite_friends$"))
    app.add_handler(CallbackQueryHandler(user.buy_stars, pattern="^buy_stars$"))
    app.add_handler(CallbackQueryHandler(user.star_code, pattern="^star_code$"))
    app.add_handler(CallbackQueryHandler(user.member_orders, pattern="^member_orders$"))
    app.add_handler(CallbackQueryHandler(user.new_order, pattern="^new_order$"))
    app.add_handler(CallbackQueryHandler(user.verify_join, pattern=r"^verify_join_(.+)$"))
    app.add_handler(CallbackQueryHandler(user.check_order_status, pattern=r"^order_status_(\d+)$"))
    app.add_handler(CallbackQueryHandler(user.cancel_order, pattern=r"^cancel_order_(\d+)$"))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, user.handle_text))
    app.add_handler(orders.order_conv_handler())
    app.add_handler(CommandHandler("admin", admin.admin_panel))
    app.add_handler(CallbackQueryHandler(admin.admin_panel, pattern="^admin_panel$"))
    app.add_handler(CallbackQueryHandler(admin.manage_channels, pattern="^admin_channels$"))
    app.add_handler(CallbackQueryHandler(admin.add_channel_prompt, pattern="^admin_add_channel$"))
    app.add_handler(CallbackQueryHandler(admin.remove_channel, pattern=r"^admin_remove_channel_(.+)$"))
    app.add_handler(CallbackQueryHandler(admin.manage_orders, pattern="^admin_orders$"))
    app.add_handler(CallbackQueryHandler(admin.approve_order, pattern=r"^admin_approve_(\d+)$"))
    app.add_handler(CallbackQueryHandler(admin.reject_order, pattern=r"^admin_reject_(\d+)$"))
    app.add_handler(CallbackQueryHandler(admin.manage_star_codes, pattern="^admin_codes$"))
    app.add_handler(CallbackQueryHandler(admin.create_star_code, pattern="^admin_create_code$"))
    app.add_handler(CallbackQueryHandler(admin.delete_star_code, pattern=r"^admin_delete_code_(.+)$"))
    app.add_handler(CallbackQueryHandler(admin.broadcast_prompt, pattern="^admin_broadcast$"))
    app.add_handler(CallbackQueryHandler(admin.stats, pattern="^admin_stats$"))
    app.add_handler(admin.admin_conv_handler())

    app.run_polling()

if __name__ == "__main__":
    main()
