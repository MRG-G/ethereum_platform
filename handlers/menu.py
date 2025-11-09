# handlers/menu.py
from telegram import Update, ReplyKeyboardRemove
from telegram.ext import ContextTypes
from utils.texts import texts
from utils.states import ACTION, PICK_ASSET, ENTER_AMOUNT, ENTER_WALLET
from utils.pricing import fetch_prices
from utils.validate import basic_eth_format, strong_checksum
from config import (
    FEE_RATE, ALLOWED_ASSETS, MERCHANT_USDT_ADDRESS,
    MERCHANT_BTC_ADDRESS, MERCHANT_ETH_ADDRESS
)

def get_lang(context) -> str:
    return context.user_data.get("lang", "Русский")

def parse_float(s: str):
    try:
        return float((s or "").replace(",", "."))
    except Exception:
        return None

async def action(update: Update, context: ContextTypes.DEFAULT_TYPE):
    lang = get_lang(context)
    txt = (update.message.text or "").strip()

    if ("Купить" in txt) or ("Buy" in txt) or ("Գնել" in txt):
        context.user_data["flow"] = "buy"
        await update.message.reply_text(texts[lang]["pick_asset"], reply_markup=ReplyKeyboardRemove())
        return PICK_ASSET

    if ("Продать" in txt) or ("Sell" in txt) or ("Վաճառել" in txt):
        context.user_data["flow"] = "sell"
        await update.message.reply_text(texts[lang]["pick_asset"], reply_markup=ReplyKeyboardRemove())
        return PICK_ASSET

    if ("⬅️" in txt) or ("Back" in txt) or ("Վերադառնալ" in txt):
        from handlers.start import start
        return await start(update, context)

    await update.message.reply_text(texts[lang]["menu_info"])
    return ACTION

async def pick_asset(update: Update, context: ContextTypes.DEFAULT_TYPE):
    lang = get_lang(context)
    asset = (update.message.text or "").upper().strip()
    if asset not in ALLOWED_ASSETS:
        await update.message.reply_text(texts[lang]["pick_asset"])
        return PICK_ASSET

    context.user_data["asset"] = asset
    flow = context.user_data.get("flow")

    if flow == "buy":
        await update.message.reply_text(texts[lang]["enter_amount_buy"].format(asset=asset))
    else:
        await update.message.reply_text(texts[lang]["enter_amount_sell"].format(asset=asset))
    return ENTER_AMOUNT

async def enter_amount(update: Update, context: ContextTypes.DEFAULT_TYPE):
    lang = get_lang(context)
    amount = parse_float(update.message.text)
    if not amount or amount <= 0:
        asset = context.user_data.get("asset", "BTC")
        flow = context.user_data.get("flow")
        if flow == "buy":
            await update.message.reply_text(texts[lang]["enter_amount_buy"].format(asset=asset))
        else:
            await update.message.reply_text(texts[lang]["enter_amount_sell"].format(asset=asset))
        return ENTER_AMOUNT

    context.user_data["asset_amount"] = amount
    asset = context.user_data.get("asset", "BTC")

    prices = await fetch_prices()
    price = prices[asset]
    base = amount * price
    fee = base * FEE_RATE

    if context.user_data.get("flow") == "buy":
        total = base + fee
        context.user_data["calc"] = {"base": base, "fee": fee, "total": total, "price": price}
        
        # Запросим адрес получателя перед показом деталей
        await update.message.reply_text(texts[lang]["enter_wallet"])
        return ENTER_WALLET
    else:
        total = base - fee
        context.user_data["calc"] = {"base": base, "fee": fee, "total": total, "price": price}
        
        # Получаем адрес мерчанта для выбранной криптовалюты и сохраняем его
        if asset == "BTC":
            merchant_wallet = MERCHANT_BTC_ADDRESS
        elif asset == "ETH":
            merchant_wallet = MERCHANT_ETH_ADDRESS
        else:
            merchant_wallet = MERCHANT_USDT_ADDRESS

        context.user_data["merchant_wallet"] = merchant_wallet

        # Показываем расчёт в выбранном языке (шаблон включает merchant_wallet)
        await update.message.reply_text(
            texts[lang]["calc_sell"].format(
                asset=asset, price=price, base=base, fee=fee, total=total, merchant_wallet=merchant_wallet
            ),
            parse_mode="Markdown"
        )

        # Запрашиваем адрес пользователя для получения USDT
        await update.message.reply_text(texts[lang]["enter_wallet"])
        return ENTER_WALLET

async def enter_wallet(update: Update, context: ContextTypes.DEFAULT_TYPE):
    lang = get_lang(context)
    wallet = (update.message.text or "").strip()
    if not basic_eth_format(wallet) or not strong_checksum(wallet):
        await update.message.reply_text(texts[lang]["bad_wallet"])
        return ENTER_WALLET

    context.user_data["wallet"] = wallet
    
    # Получаем сохраненные данные расчета
    calc = context.user_data.get("calc", {})
    asset = context.user_data.get("asset")
    flow = context.user_data.get("flow")
    
    if flow == "buy":
        # Показываем расчет с адресом пользователя для получения (используем текстовые шаблоны)
        await update.message.reply_text(
            texts[lang]["calc_buy"].format(
                asset=asset,
                price=calc.get("price", 0),
                base=calc.get("base", 0),
                fee=calc.get("fee", 0),
                total=calc.get("total", 0),
                user_wallet=wallet
            ),
            parse_mode="Markdown"
        )

        # Показываем адрес для оплаты USDT (merchant USDT)
        await update.message.reply_text(
            texts[lang]["merchant_addr_title"].format(addr=MERCHANT_USDT_ADDRESS),
            parse_mode="Markdown"
        )
    else:  # flow == "sell"
        # Для продажи: НЕ повторяем расчёт — он уже был показан после ввода суммы.
        # Берём merchant_wallet, который мы сохранили ранее
        merchant_wallet = context.user_data.get("merchant_wallet")

        # Подтверждение получения адреса клиента и напоминание куда отправить крипту
        await update.message.reply_text(
            texts[lang].get("sell_wallet_received", "Адрес получен." ).format(
                asset=asset, merchant_wallet=merchant_wallet
            ),
            parse_mode="Markdown"
        )
    
    await update.message.reply_text(texts[lang]["send_check"])
    from utils.states import AWAITING_CHECK
    return AWAITING_CHECK
