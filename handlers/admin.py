# handlers/admin.py
from datetime import datetime
from telegram.ext import ContextTypes
from utils.texts import texts
from utils.db import log_request
from config import ENABLE_SQLITE, ENABLE_GOOGLE_SHEETS

async def button_callback(update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()

    pending = context.bot_data.setdefault("pending", {})
    msg_id = q.message.message_id
    if msg_id not in pending:
        await q.answer("Заявка не найдена", show_alert=True)
        return

    pdata = pending.pop(msg_id)
    lang = pdata["lang"]
    user_id = pdata["user_chat_id"]

    # Лог статуса
    log_request({
        "ts": datetime.utcnow().isoformat(),
        "flow": pdata["flow"],
        "asset": pdata["asset"],
        "asset_amount": pdata["asset_amount"],
        "base_usdt": None,
        "fee_usdt": None,
        "total_usdt": pdata["usdt_total"],
        "username": None,
        "user_id": user_id,
        "wallet": pdata["wallet"],
        "status": "approved" if q.data == "approve" else "rejected"
    }, enable_sqlite=ENABLE_SQLITE, enable_gs=ENABLE_GOOGLE_SHEETS)

    if q.data == "approve":
        await context.bot.send_message(
            chat_id=user_id,
            text=texts[lang]["approved_user"].format(
                asset=pdata["asset"], asset_amount=pdata["asset_amount"], usdt_total=pdata["usdt_total"]
            )
        )
        new_caption = (q.message.caption or "") + "\n✅ Заявка подтверждена"
        await q.edit_message_caption(caption=new_caption, reply_markup=None)

    elif q.data == "reject":
        from telegram import ReplyKeyboardMarkup
        
        # Отправляем сообщение об отказе
        await context.bot.send_message(chat_id=user_id, text=texts[lang]["auto_reject_user"])
        
        # Показываем меню выбора языка с клавиатурой
        keyboard = ReplyKeyboardMarkup(
            texts["Русский"]["lang_keyboard"],
            resize_keyboard=True,
            one_time_keyboard=True
        )
        await context.bot.send_message(
            chat_id=user_id,
            text=texts["Русский"]["start_greet"],
            reply_markup=keyboard
        )
        
        # Обновляем статус заявки в канале
        new_caption = (q.message.caption or "") + "\n❌ Отклонено"
        await q.edit_message_caption(caption=new_caption, reply_markup=None)
