# handlers/check.py
from datetime import datetime
from telegram import Update, InlineKeyboardMarkup, InlineKeyboardButton
from telegram.ext import ContextTypes
from utils.texts import texts
from utils.validate import exif_check_is_today
from utils.states import ACTION, LANGUAGE
from utils.db import log_request
from config import ENABLE_SQLITE, ENABLE_GOOGLE_SHEETS

async def receive_check(update: Update, context: ContextTypes.DEFAULT_TYPE):
    lang = context.user_data.get("lang", "Русский")

    if not update.message.photo:
        await update.message.reply_text(texts[lang]["only_photo"])
        return ACTION

    # Скачиваем bytes для EXIF
    photo = update.message.photo[-1]
    f = await photo.get_file()
    file_bytes = await f.download_as_bytearray()
    is_today, exif_missing = exif_check_is_today(bytes(file_bytes))

    if not is_today:
        # Авто-отклонение + возврат к выбору языка
        await update.message.reply_text(texts[lang]["auto_reject_user"])
        await update.message.reply_text(
            texts["Русский"]["start_greet"]  # текст с выбором языка
        )
        return LANGUAGE

    # Счётчик повторных чеков
    context.user_data["attempt"] = context.user_data.get("attempt", 0) + 1
    retry_note = texts[lang]["retry_label"] if context.user_data["attempt"] > 1 else ""

    u = context.user_data
    flow = u.get("flow")
    asset = u.get("asset")
    asset_amount = u.get("asset_amount", 0.0)
    base = u.get("calc", {}).get("base", 0.0)
    fee = u.get("calc", {}).get("fee", 0.0)
    total = u.get("calc", {}).get("total", 0.0)
    username = update.effective_user.username or update.effective_user.first_name
    wallet = u.get("wallet")

    exif_line = "⚠️ EXIF отсутствует — проверь внимательно" if exif_missing else "EXIF OK"

    kb = InlineKeyboardMarkup([
        [InlineKeyboardButton("✅ Подтвердить", callback_data="approve"),
         InlineKeyboardButton("❌ Отклонить", callback_data="reject")]
    ])

    cap_key = "channel_caption_buy" if flow == "buy" else "channel_caption_sell"
    caption = texts[lang][cap_key].format(
        asset=asset, username=username, asset_amount=asset_amount,
        base=base, fee=fee, total=total, wallet=wallet, exif=exif_line
    )
    if retry_note:
        caption = retry_note + caption

    # Отправка фото в канал
    sent = await context.bot.send_photo(
        chat_id=context.bot_data["CHANNEL_USERNAME"],
        photo=photo.file_id,
        caption=caption,
        reply_markup=kb
    )

    # Лог в БД/Sheets
    log_request({
        "ts": datetime.utcnow().isoformat(),
        "flow": flow, "asset": asset, "asset_amount": asset_amount,
        "base_usdt": base, "fee_usdt": fee, "total_usdt": total,
        "username": username, "user_id": update.effective_user.id,
        "wallet": wallet, "status": "pending"
    }, enable_sqlite=ENABLE_SQLITE, enable_gs=ENABLE_GOOGLE_SHEETS)

    # Сохранить в pending
    pending = context.bot_data.setdefault("pending", {})
    pending[sent.message_id] = {
        "lang": lang, "user_chat_id": update.effective_chat.id,
        "asset": asset, "asset_amount": asset_amount, "usdt_total": total,
        "wallet": wallet, "flow": flow
    }

    await update.message.reply_text(texts[lang]["after_check_wait"])
    return ACTION
