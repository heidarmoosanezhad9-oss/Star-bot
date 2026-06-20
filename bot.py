"""
Telegram Star Exchange Bot
Main entry point
"""

import logging
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, MessageHandler, filters
from config import BOT_TOKEN
from user import *
from admin import *
from orders import *
from database import init_db

logging.basicConfig(format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO)
logger = logging.getLogger(__name__)

def main():
    init_db()
    app = Application.builder().token(BOT_TOKEN).build()
    
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CallbackQueryHandler(main_menu, pattern="^main_menu$"))
    app.add_handler(CallbackQueryHandler(daily_stars, pattern="^daily_stars$"))
    app.add_handler(CallbackQueryHandler(profile, pattern="^profile$"))
    app.add_handler(CallbackQueryHandler(earn_stars, pattern="^earn_stars$"))
    app.add_handler(CallbackQueryHandler(invite_friends, pattern="^invite_friends$"))
    app.add_handler(CallbackQueryHandler(buy_stars, pattern="^buy_stars$"))
    app.add_handler(CallbackQueryHandler(star_code, pattern="^star_code$"))
    app.add_handler(CallbackQueryHandler(member_orders, pattern="^member_orders$"))
    app.add_handler(CallbackQueryHandler(new_order, pattern="^new_order$"))
    app.add_handler(CallbackQueryHandler(verify_join, pattern=r"^verify_join_(.+)$"))
    app.add_handler(CallbackQueryHandler(check_order_status, pattern=r"^order_status_(\d+)$"))
    app.add_handler(CallbackQueryHandler(cancel_order, pattern=r"^cancel_order_(\d+)$"))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text))
    app.add_handler(order_conv_handler())
    
    app.add_handler(CommandHandler("admin", admin_panel))
    app.add_handler(CallbackQueryHandler(admin_panel, pattern="^admin_panel$"))
    app.add_handler(CallbackQueryHandler(manage_channels, pattern="^admin_channels$"))
    app.add_handler(CallbackQueryHandler(add_channel_prompt, pattern="^admin_add_channel$"))
    app.add_handler(CallbackQueryHandler(remove_channel, pattern=r"^admin_remove_channel_(.+)$"))
    app.add_handler(CallbackQueryHandler(manage_orders, pattern="^admin_orders$"))
    app.add_handler(CallbackQueryHandler(approve_order, pattern=r"^admin_approve_(\d+)$"))
    app.add_handler(CallbackQueryHandler(reject_order, pattern=r"^admin_reject_(\d+)$"))
    app.add_handler(CallbackQueryHandler(manage_star_codes, pattern="^admin_codes$"))
    app.add_handler(CallbackQueryHandler(create_star_code, pattern="^admin_create_code$"))
    app.add_handler(CallbackQueryHandler(delete_star_code, pattern=r"^admin_delete_code_(.+)$"))
    app.add_handler(CallbackQueryHandler(broadcast_prompt, pattern="^admin_broadcast$"))
    app.add_handler(CallbackQueryHandler(stats, pattern="^admin_stats$"))
    app.add_handler(admin_conv_handler())
    
    logger.info("Bot is running...")
    app.run_polling()

if __name__ == "__main__":
    main()
