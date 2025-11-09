# bot.py
import logging
from telegram.ext import (
    Application, CommandHandler, MessageHandler, ConversationHandler, CallbackQueryHandler, ContextTypes, filters
)

from config import TOKEN, CHANNEL_USERNAME, ENABLE_SQLITE, ENABLE_GOOGLE_SHEETS, GOOGLE_SHEETS_JSON_PATH, GOOGLE_SHEET_NAME
from utils.states import LANGUAGE, ACTION, PICK_ASSET, ENTER_AMOUNT, ENTER_WALLET, AWAITING_CHECK
from utils.db import init_sqlite, init_google_sheets
from handlers.start import start, set_language
from handlers.menu import action, pick_asset, enter_amount, enter_wallet
from handlers.check import receive_check
from handlers.admin import button_callback

logging.basicConfig(level=logging.INFO)
log = logging.getLogger("ethereum_platform")

def main():
    # Инициализация хранилищ
    if ENABLE_SQLITE:
        init_sqlite("orders.db")
    if ENABLE_GOOGLE_SHEETS:
        init_google_sheets(GOOGLE_SHEETS_JSON_PATH, GOOGLE_SHEET_NAME)

    app = Application.builder().token(TOKEN).build()

    # Данные доступные всем хендлерам
    app.bot_data["CHANNEL_USERNAME"] = CHANNEL_USERNAME
    app.bot_data["pending"] = {}

    conv = ConversationHandler(
        entry_points=[CommandHandler("start", start)],
        states={
            LANGUAGE: [MessageHandler(filters.TEXT & ~filters.COMMAND, set_language)],
            ACTION: [MessageHandler(filters.TEXT & ~filters.COMMAND, action)],
            PICK_ASSET: [MessageHandler(filters.TEXT & ~filters.COMMAND, pick_asset)],
            ENTER_AMOUNT: [MessageHandler(filters.TEXT & ~filters.COMMAND, enter_amount)],
            ENTER_WALLET: [MessageHandler(filters.TEXT & ~filters.COMMAND, enter_wallet)],
            AWAITING_CHECK: [
                MessageHandler(filters.PHOTO, receive_check),
                MessageHandler(~filters.PHOTO & ~filters.COMMAND, receive_check),
            ],
        },
        fallbacks=[CommandHandler("start", start)],
    )

    app.add_handler(conv)
    app.add_handler(CallbackQueryHandler(button_callback))

    print("✅ Bot is running...")
    app.run_polling()

if __name__ == "__main__":
    main()
