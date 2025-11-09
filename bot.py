import asyncio
from datetime import datetime
import logging
import sqlite3
import aiohttp

from telegram import (
    Update, ReplyKeyboardMarkup, ReplyKeyboardRemove,
    InlineKeyboardMarkup, InlineKeyboardButton
)
from telegram.ext import (
    Application, CommandHandler, MessageHandler, ConversationHandler,
    ContextTypes, filters, CallbackQueryHandler
)

# ===================== CONFIG (заполни 3 строки) =====================
TOKEN = "PASTE_YOUR_BOT_TOKEN"
CHANNEL_USERNAME = "@ethereumamoperator"      # username канала/чата (с @) или числовой ID
MERCHANT_USDT_ADDRESS = "0xYourUSDT_ERC20_Address_Here"  # Твой USDT-ERC20 адрес
# ====================================================================

FEE_RATE = 0.03
ALLOWED_ASSETS = ("BTC", "ETH")

# ---- логирование
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("ethereum_platform")

# ---- состояния
LANGUAGE, ACTION, PICK_ASSET, ENTER_AMOUNT, ENTER_WALLET, AWAITING_CHECK = range(6)

# ---- стартовые бэкап-цены (если сеть не ответит)
FALLBACK = {"BTC": 56000.0, "ETH": 3500.0, "USDAMD": 400.0}

# ---- языки и тексты
language_map = {"🇷🇺 Русский": "Русский", "🇦🇲 Հայերեն": "Հայերեն", "🇬🇧 English": "English"}

texts = {
    "Русский": {
        "brand": "💎 Ethereum Платформа",
        # на /start — без курса, только выбор языка
        "start": "🌐 {brand}\n\nВыберите язык / Խնդրում ենք ընտրել լեզուն / Please select a language:",
        # после выбора языка — покажем курс
        "rates": "📊 Курс: BTC {btc_usdt:.2f} USDT ({btc_amd:,} AMD) | ETH {eth_usdt:.2f} USDT ({eth_amd:,} AMD)\n"
                 "💵 Расчёты: только USDT-ERC20\n"
                 "⚠️ Комиссия: 3% — при покупке добавляется, при продаже удерживается.",
        "menu": "Выберите действие:",
        "buttons": [["💰 Купить BTC/ETH", "💸 Продать BTC/ETH"], ["⬅️ Назад"]],
        "pick_asset": "Выберите актив: BTC или ETH.",
        "enter_amount_buy": "Введите количество {asset}, которое хотите купить (например 0.01):",
        "enter_amount_sell": "Введите количество {asset}, которое хотите продать (например 0.01):",
        "merchant_addr_title": "💳 Адрес для оплаты (USDT-ERC20):\n`{addr}`",
        "enter_wallet": "Укажите ваш 💵 USDT-ERC20 адрес для выплаты (начинается с 0x…):",
        "bad_wallet": "Неверный адрес. Должен начинаться с 0x, длина 42 символа. (EIP-55 чек не обязателен)",
        "send_check": "Теперь отправьте только фото/скриншот чека. Текст не принимается.",
        "only_photo": "На этом шаге принимается только фото/скриншот чека.",
        "after_check_wait": "✅ Чек получен. Ваша заявка ждёт подтверждения оператора.",
        "calc_buy": ("Курс {asset}: {price:.2f} USDT ({price_amd:,} AMD)\n"
                     "Сумма: {base:.2f} USDT ({base_amd:,} AMD)\n"
                     "Комиссия (3%): {fee:.2f} USDT ({fee_amd:,} AMD)\n"
                     "К оплате: {total:.2f} USDT ({total_amd:,} AMD)\n\n"
                     "➡️ Отправьте на адрес выше: {total:.2f} USDT-ERC20"),
        "calc_sell": ("Курс {asset}: {price:.2f} USDT ({price_amd:,} AMD)\n"
                      "Сумма: {base:.2f} USDT ({base_amd:,} AMD)\n"
                      "Комиссия (3%): {fee:.2f} USDT ({fee_amd:,} AMD)\n"
                      "К получению: {total:.2f} USDT ({total_amd:,} AMD)\n\n"
                      "➡️ Вы получите: {total:.2f} USDT-ERC20"),
        "approved_user": ("✅ Ваша заявка одобрена.\n"
                          "Актив: {asset}\nКоличество: {asset_amount:.8f} {asset}\n"
                          "Итог: {usdt_total:.2f} USDT ({amd_total:,} AMD)\n"
                          "Оператор отправил запрошенное."),
        "auto_reject_user": ("❌ Ваша заявка отклонена.\n"
                             "Причина: чек не видно / дата и время не сегодняшние / чек неверный.\n"
                             "Пожалуйста, отправьте корректный чек (чёткое фото с актуальными датой/временем)."),
        "channel_caption_buy": ("🟢 Покупка {asset}\nПользователь: @{username}\nКоличество: {asset_amount:.8f} {asset}\n\n"
                                "Сумма: {base:.2f} USDT ({base_amd:,} AMD)\n"
                                "Комиссия: {fee:.2f} USDT ({fee_amd:,} AMD)\n"
                                "Итого к оплате: {total:.2f} USDT ({total_amd:,} AMD)\n\n"
                                "Адрес USDT-ERC20: {wallet}\n{retry}Статус: Ожидает подтверждения"),
        "channel_caption_sell": ("🔴 Продажа {asset}\nПользователь: @{username}\nКоличество: {asset_amount:.8f} {asset}\n\n"
                                 "Сумма: {base:.2f} USDT ({base_amd:,} AMD)\n"
                                 "Комиссия: {fee:.2f} USDT ({fee_amd:,} AMD)\n"
                                 "К выплате: {total:.2f} USDT ({total_amd:,} AMD)\n\n"
                                 "USDT-ERC20 (клиента): {wallet}\n{retry}Статус: Ожидает подтверждения"),
        "retry_label": "⚠️ Повторная отправка чека\n",
        "lang_prompt": "Выберите язык / Խնդրում ենք ընտրել լեզուն / Please select a language:",
    },
    "Հայերեն": {
        "brand": "💎 Ethereum Պլատֆորմ",
        "start": "🌐 {brand}\n\nԽնդրում ենք ընտրել լեզուն / Выберите язык / Please select a language:",
        "rates": "📊 Փոխարժեք՝ BTC {btc_usdt:.2f} USDT ({btc_amd:,} AMD) | ETH {eth_usdt:.2f} USDT ({eth_amd:,} AMD)\n"
                 "💵 Վճարումներ՝ միայն USDT-ERC20\n"
                 "⚠️ Միջնորդավճար՝ 3% (գնման դեպքում ավելացվում է, վաճառքի դեպքում՝ պահվում է)։",
        "menu": "Ընտրեք գործողությունը՝",
        "buttons": [["💰 Գնել BTC/ETH", "💸 Վաճառել BTC/ETH"], ["⬅️ Վերադառնալ"]],
        "pick_asset": "Ընտրեք ակտիվ՝ BTC կամ ETH։",
        "enter_amount_buy": "Մուտքագրեք {asset}-ի քանակը, որը ցանկանում եք գնել (օր. 0.01)։",
        "enter_amount_sell": "Մուտքագրեք {asset}-ի քանակը, որը ցանկանում եք վաճառել (օր. 0.01)։",
        "merchant_addr_title": "💳 Վճարման հասցե (USDT-ERC20):\n`{addr}`",
        "enter_wallet": "Գրեք ձեր 💵 USDT-ERC20 հասցեն (սկսվում է 0x…)՝ վճարման համար:",
        "bad_wallet": "Սխալ հասցե․ պետք է սկսվի 0x-ով և լինի 42 նիշ։",
        "send_check": "Հիմա ուղարկեք միայն վճարման լուսանկար/սքրինշոթ։",
        "only_photo": "Այս փուլում ընդունվում է միայն լուսանկար/սքրինշոթ։",
        "after_check_wait": "✅ Ստուգումը ստացվեց։ Ձեր հայտը սպասում է օպերատորի հաստատմանը։",
        "calc_buy": ("Գին {asset}-ի՝ {price:.2f} USDT ({price_amd:,} AMD)\n"
                     "Գումար՝ {base:.2f} USDT ({base_amd:,} AMD)\n"
                     "Միջնորդավճար՝ {fee:.2f} USDT ({fee_amd:,} AMD)\n"
                     "Վճարում՝ {total:.2f} USDT ({total_amd:,} AMD)\n\n"
                     "➡️ Ուղարկեք վերեւում նշված հասցեին՝ {total:.2f} USDT-ERC20"),
        "calc_sell": ("Գին {asset}-ի՝ {price:.2f} USDT ({price_amd:,} AMD)\n"
                      "Գումար՝ {base:.2f} USDT ({base_amd:,} AMD)\n"
                      "Միջնորդավճար՝ {fee:.2f} USDT ({fee_amd:,} AMD)\n"
                      "Կստանաք՝ {total:.2f} USDT ({total_amd:,} AMD)\n\n"
                      "➡️ Կստանաք՝ {total:.2f} USDT-ERC20"),
        "approved_user": ("✅ Ձեր հայտը հաստատվել է։\nԱկտիվ՝ {asset}\nՔանակ՝ {asset_amount:.8f} {asset}\n"
                          "USDT-ERC20՝ {usdt_total:.2f} ({amd_total:,} AMD)\nՕպերատորը ուղարկել է Ձեր պահանջածը։"),
        "auto_reject_user": ("❌ Ձեր հայտը մերժվել է։\nՊատճառ՝ չեկը չի երևում / ամսաթիվը և ժամը այսօրը չեն / չեկը սխալ է։\n"
                             "Խնդրում ենք ուղարկել հստակ լուսանկար՝ արդի ամսաթվով/ժամով։"),
        "channel_caption_buy": ("🟢 Գնում {asset}\nՕգտատեր՝ @{username}\nՔանակ՝ {asset_amount:.8f} {asset}\n\n"
                                "Գումար՝ {base:.2f} USDT ({base_amd:,} AMD)\n"
                                "Միջնորդավճար՝ {fee:.2f} USDT ({fee_amd:,} AMD)\n"
                                "Վճարում՝ {total:.2f} USDT ({total_amd:,} AMD)\n\n"
                                "USDT-ERC20 հասցե՝ {wallet}\n{retry}Կարգավիճակ՝ Սպասում է հաստատման"),
        "channel_caption_sell": ("🔴 Վաճառք {asset}\nՕգտատեր՝ @{username}\nՔանակ՝ {asset_amount:.8f} {asset}\n\n"
                                 "Գումար՝ {base:.2f} USDT ({base_amd:,} AMD)\n"
                                 "Միջնորդավճար՝ {fee:.2f} USDT ({fee_amd:,} AMD)\n"
                                 "Ստանալու եք՝ {total:.2f} USDT ({total_amd:,} AMD)\n\n"
                                 "Հաճախորդի USDT-ERC20՝ {wallet}\n{retry}Կարգավիճակ՝ Սպասում է հաստատման"),
        "retry_label": "⚠️ Կրկնակի ստուգում\n",
        "lang_prompt": "Խնդրում ենք ընտրել լեզուն / Выберите язык / Please select a language:",
    },
    "English": {
        "brand": "💎 Ethereum Platform",
        "start": "🌐 {brand}\n\nPlease select a language / Խնդրում ենք ընտրել լեզուն / Выберите язык:",
        "rates": "📊 Rates: BTC {btc_usdt:.2f} USDT ({btc_amd:,} AMD) | ETH {eth_usdt:.2f} USDT ({eth_amd:,} AMD)\n"
                 "💵 Settlement: USDT-ERC20 only\n"
                 "⚠️ Fee: 3% — added on buy, withheld on sell.",
        "menu": "Choose an action:",
        "buttons": [["💰 Buy BTC/ETH", "💸 Sell BTC/ETH"], ["⬅️ Back"]],
        "pick_asset": "Choose asset: BTC or ETH.",
        "enter_amount_buy": "Enter how much {asset} you want to buy (e.g., 0.01):",
        "enter_amount_sell": "Enter how much {asset} you want to sell (e.g., 0.01):",
        "merchant_addr_title": "💳 Payment address (USDT-ERC20):\n`{addr}`",
        "enter_wallet": "Provide your 💵 USDT-ERC20 payout address (starts with 0x…):",
        "bad_wallet": "Invalid address. Must start with 0x and be 42 chars.",
        "send_check": "Now send the receipt photo/screenshot only. Text is not accepted.",
        "only_photo": "Only a photo/screenshot is accepted at this step.",
        "after_check_wait": "✅ Receipt received. Awaiting operator approval.",
        "calc_buy": ("{asset} price: {price:.2f} USDT ({price_amd:,} AMD)\n"
                     "Subtotal: {base:.2f} USDT ({base_amd:,} AMD)\n"
                     "Fee (3%): {fee:.2f} USDT ({fee_amd:,} AMD)\n"
                     "To pay: {total:.2f} USDT ({total_amd:,} AMD)\n\n"
                     "➡️ Send to the address above: {total:.2f} USDT-ERC20"),
        "calc_sell": ("{asset} price: {price:.2f} USDT ({price_amd:,} AMD)\n"
                      "Subtotal: {base:.2f} USDT ({base_amd:,} AMD)\n"
                      "Fee (3%): {fee:.2f} USDT ({fee_amd:,} AMD)\n"
                      "You will receive: {total:.2f} USDT ({total_amd:,} AMD)\n\n"
                      "➡️ You will receive: {total:.2f} USDT-ERC20"),
        "approved_user": ("✅ Approved.\nAsset: {asset}\nAmount: {asset_amount:.8f} {asset}\n"
                          "Total: {usdt_total:.2f} USDT ({amd_total:,} AMD)\nThe operator has sent it."),
        "auto_reject_user": ("❌ Rejected.\nReason: receipt not visible / not today's date/time / invalid receipt.\n"
                             "Please send a clear receipt with current date/time."),
        "channel_caption_buy": ("🟢 Buy {asset}\nUser: @{username}\nAmount: {asset_amount:.8f} {asset}\n\n"
                                "Subtotal: {base:.2f} USDT ({base_amd:,} AMD)\n"
                                "Fee: {fee:.2f} USDT ({fee_amd:,} AMD)\n"
                                "Total to pay: {total:.2f} USDT ({total_amd:,} AMD)\n\n"
                                "USDT-ERC20 address: {wallet}\n{retry}Status: Waiting for approval"),
        "channel_caption_sell": ("🔴 Sell {asset}\nUser: @{username}\nAmount: {asset_amount:.8f} {asset}\n\n"
                                 "Subtotal: {base:.2f} USDT ({base_amd:,} AMD)\n"
                                 "Fee: {fee:.2f} USDT ({fee_amd:,} AMD)\n"
                                 "To receive: {total:.2f} USDT ({total_amd:,} AMD)\n\n"
                                 "Client USDT-ERC20: {wallet}\n{retry}Status: Waiting for approval"),
        "retry_label": "⚠️ Retry receipt\n",
        "lang_prompt": "Please select a language / Խնդրում ենք ընտրել լեզուն / Выберите язык:",
    }
}

# ===================== STORAGE =====================
pending = {}  # channel_msg_id -> request dict

# ===================== DB (SQLite) =================
def init_sqlite():
    conn = sqlite3.connect("orders.db")
    cur = conn.cursor()
    cur.execute("""
        CREATE TABLE IF NOT EXISTS orders (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            ts TEXT,
            flow TEXT,
            asset TEXT,
            asset_amount REAL,
            base_usdt REAL,
            fee_usdt REAL,
            total_usdt REAL,
            username TEXT,
            user_id INTEGER,
            wallet TEXT,
            status TEXT
        );
    """)
    conn.commit()
    conn.close()

def log_request(row: dict):
    conn = sqlite3.connect("orders.db")
    cur = conn.cursor()
    cur.execute("""
        INSERT INTO orders (ts, flow, asset, asset_amount, base_usdt, fee_usdt, total_usdt,
                            username, user_id, wallet, status)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?);
    """, (
        row.get("ts"), row.get("flow"), row.get("asset"), row.get("asset_amount"),
        row.get("base_usdt"), row.get("fee_usdt"), row.get("total_usdt"),
        row.get("username"), row.get("user_id"), row.get("wallet"), row.get("status")
    ))
    conn.commit()
    conn.close()

# ===================== PRICES ======================
async def fetch_binance(symbol: str) -> float:
    url = f"https://api.binance.com/api/v3/ticker/price?symbol={symbol}"
    timeout = aiohttp.ClientTimeout(total=6)
    async with aiohttp.ClientSession(timeout=timeout) as s:
        async with s.get(url) as r:
            j = await r.json()
            return float(j["price"])

async def fetch_usd_to_amd() -> float:
    # свободный курс USD→AMD
    url = "https://api.exchangerate.host/latest?base=USD&symbols=AMD"
    timeout = aiohttp.ClientTimeout(total=6)
    async with aiohttp.ClientSession(timeout=timeout) as s:
        async with s.get(url) as r:
            j = await r.json()
            return float(j["rates"]["AMD"])

async def update_rates(bot_app: Application):
    """Обновляет курсы и кладёт их в bot_data."""
    try:
        btc = await fetch_binance("BTCUSDT")
        eth = await fetch_binance("ETHUSDT")
        usd_amd = await fetch_usd_to_amd()
        bot_app.bot_data["rates"] = {"BTC": btc, "ETH": eth, "USDAMD": usd_amd}
    except Exception as e:
        logger.warning(f"Price update failed: {e}")
        bot_app.bot_data["rates"] = FALLBACK.copy()

def get_rates(context: ContextTypes.DEFAULT_TYPE):
    rates = context.application.bot_data.get("rates")
    if not rates:
        rates = FALLBACK
    return rates

def fmt_amd(x: float) -> str:
    # красиво: разделитель тысяч пробелом, без десятых
    return f"{int(round(x)):,}".replace(",", " ")

def parse_float(s: str):
    try:
        return float(s.replace(",", "."))
    except Exception:
        return None

def build_kb(lang: str) -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(texts[lang]["buttons"], resize_keyboard=True)

def get_lang(context: ContextTypes.DEFAULT_TYPE) -> str:
    return context.user_data.get("lang", "Русский")

def valid_eth_addr(addr: str) -> bool:
    return isinstance(addr, str) and addr.startswith("0x") and len(addr) == 42

# ===================== UI HELPERS ==================
async def send_lang_prompt(update_or_chat, context: ContextTypes.DEFAULT_TYPE):
    kb = [["🇷🇺 Русский"], ["🇦🇲 Հայերեն"], ["🇬🇧 English"]]
    msg = texts["Русский"]["lang_prompt"]
    if isinstance(update_or_chat, Update):
        await update_or_chat.effective_chat.send_message(
            msg, reply_markup=ReplyKeyboardMarkup(kb, resize_keyboard=True, one_time_keyboard=True)
        )
    else:
        await context.bot.send_message(update_or_chat, msg,
            reply_markup=ReplyKeyboardMarkup(kb, resize_keyboard=True, one_time_keyboard=True))

# ===================== HANDLERS ====================
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # Приветствие БЕЗ курса
    kb = [["🇷🇺 Русский"], ["🇦🇲 Հայերեն"], ["🇬🇧 English"]]
    banner = texts["Русский"]["start"].format(brand=texts["Русский"]["brand"])
    m = await update.message.reply_text(
        banner, reply_markup=ReplyKeyboardMarkup(kb, resize_keyboard=True, one_time_keyboard=True)
    )
    context.user_data["start_msg_id"] = m.message_id
    return LANGUAGE

async def set_language(update: Update, context: ContextTypes.DEFAULT_TYPE):
    lang = language_map.get(update.message.text)
    if not lang:
        await update.message.reply_text(texts["Русский"]["lang_prompt"])
        return LANGUAGE
    context.user_data["lang"] = lang
    context.user_data["attempt"] = 0

    # удаляем приветствие
    try:
        mid = context.user_data.get("start_msg_id")
        if mid:
            await context.bot.delete_message(update.effective_chat.id, mid)
    except Exception:
        pass

    # показываем КУРС
    rates = get_rates(context)
    usd_amd = rates["USDAMD"]
    btc_usdt, eth_usdt = rates["BTC"], rates["ETH"]
    btc_amd = fmt_amd(btc_usdt * usd_amd)
    eth_amd = fmt_amd(eth_usdt * usd_amd)

    await update.message.reply_text(
        texts[lang]["rates"].format(
            btc_usdt=btc_usdt, eth_usdt=eth_usdt,
            btc_amd=btc_amd, eth_amd=eth_amd
        )
    )
    await update.message.reply_text(texts[lang]["menu"], reply_markup=build_kb(lang))
    return ACTION

async def action(update: Update, context: ContextTypes.DEFAULT_TYPE):
    lang = get_lang(context)
    txt = (update.message.text or "").strip()

    if ("Купить" in txt) or ("Buy" in txt) or ("Գնել" in txt):
        context.user_data["flow"] = "buy"
        # при входе в покупку — ещё раз показываем курс
        await set_language_like_rates_echo(update, context)
        await update.message.reply_text(texts[lang]["pick_asset"], reply_markup=ReplyKeyboardRemove())
        return PICK_ASSET

    if ("Продать" in txt) or ("Sell" in txt) or ("Վաճառել" in txt):
        context.user_data["flow"] = "sell"
        await set_language_like_rates_echo(update, context)
        await update.message.reply_text(texts[lang]["pick_asset"], reply_markup=ReplyKeyboardRemove())
        return PICK_ASSET

    if ("⬅️" in txt) or ("Back" in txt) or ("Վերադառնալ" in txt):
        return await start(update, context)

    await update.message.reply_text(texts[lang]["menu"], reply_markup=build_kb(lang))
    return ACTION

async def set_language_like_rates_echo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    lang = get_lang(context)
    rates = get_rates(context)
    usd_amd = rates["USDAMD"]
    btc_usdt, eth_usdt = rates["BTC"], rates["ETH"]
    btc_amd = fmt_amd(btc_usdt * usd_amd)
    eth_amd = fmt_amd(eth_usdt * usd_amd)
    await update.message.reply_text(
        texts[lang]["rates"].format(
            btc_usdt=btc_usdt, eth_usdt=eth_usdt,
            btc_amd=btc_amd, eth_amd=eth_amd
        )
    )

async def pick_asset(update: Update, context: ContextTypes.DEFAULT_TYPE):
    lang = get_lang(context)
    asset = (update.message.text or "").upper().strip()
    if asset not in ALLOWED_ASSETS:
        await update.message.reply_text(texts[lang]["pick_asset"])
        return PICK_ASSET
    context.user_data["asset"] = asset
    if context.user_data.get("flow") == "buy":
        await update.message.reply_text(texts[lang]["enter_amount_buy"].format(asset=asset))
    else:
        await update.message.reply_text(texts[lang]["enter_amount_sell"].format(asset=asset))
    return ENTER_AMOUNT

async def enter_amount(update: Update, context: ContextTypes.DEFAULT_TYPE):
    lang = get_lang(context)
    amount = parse_float(update.message.text or "")
    if not amount or amount <= 0:
        asset = context.user_data.get("asset", "BTC")
        if context.user_data.get("flow") == "buy":
            await update.message.reply_text(texts[lang]["enter_amount_buy"].format(asset=asset))
        else:
            await update.message.reply_text(texts[lang]["enter_amount_sell"].format(asset=asset))
        return ENTER_AMOUNT

    context.user_data["asset_amount"] = amount
    asset = context.user_data.get("asset", "BTC")

    # текущие курсы
    rates = get_rates(context)
    price_usdt = rates[asset]
    usd_amd = rates["USDAMD"]

    base = amount * price_usdt
    fee = base * FEE_RATE
    base_amd = base * usd_amd
    fee_amd = fee * usd_amd

    if context.user_data.get("flow") == "buy":
        total = base + fee
        total_amd = base_amd + fee_amd
        context.user_data["calc"] = {"base": base, "fee": fee, "total": total, "price": price_usdt}
        await update.message.reply_text(
            texts[lang]["merchant_addr_title"].format(addr=MERCHANT_USDT_ADDRESS),
            parse_mode="Markdown"
        )
        await update.message.reply_text(
            texts[lang]["calc_buy"].format(
                asset=asset, price=price_usdt, price_amd=fmt_amd(price_usdt*usd_amd),
                base=base, base_amd=fmt_amd(base_amd),
                fee=fee, fee_amd=fmt_amd(fee_amd),
                total=total, total_amd=fmt_amd(total_amd)
            )
        )
        await update.message.reply_text(texts[lang]["send_check"])
        context.user_data["wallet"] = MERCHANT_USDT_ADDRESS
        return AWAITING_CHECK
    else:
        total = base - fee
        total_amd = base_amd - fee_amd
        context.user_data["calc"] = {"base": base, "fee": fee, "total": total, "price": price_usdt}
        await update.message.reply_text(
            texts[lang]["calc_sell"].format(
                asset=asset, price=price_usdt, price_amd=fmt_amd(price_usdt*usd_amd),
                base=base, base_amd=fmt_amd(base_amd),
                fee=fee, fee_amd=fmt_amd(fee_amd),
                total=total, total_amd=fmt_amd(total_amd)
            )
        )
        await update.message.reply_text(texts[lang]["enter_wallet"])
        return ENTER_WALLET

async def enter_wallet(update: Update, context: ContextTypes.DEFAULT_TYPE):
    lang = get_lang(context)
    wallet = (update.message.text or "").strip()
    if not valid_eth_addr(wallet):
        await update.message.reply_text(texts[lang]["bad_wallet"])
        return ENTER_WALLET
    context.user_data["wallet"] = wallet
    await update.message.reply_text(texts[lang]["send_check"])
    return AWAITING_CHECK

async def receive_check(update: Update, context: ContextTypes.DEFAULT_TYPE):
    lang = get_lang(context)
    if not update.message.photo:
        await update.message.reply_text(texts[lang]["only_photo"])
        return AWAITING_CHECK

    context.user_data["attempt"] = context.user_data.get("attempt", 0) + 1
    is_retry = context.user_data["attempt"] > 1

    photo_id = update.message.photo[-1].file_id
    u = context.user_data
    flow = u.get("flow")
    asset = u.get("asset")
    asset_amount = u.get("asset_amount", 0.0)
    base = u.get("calc", {}).get("base", 0.0)
    fee = u.get("calc", {}).get("fee", 0.0)
    total = u.get("calc", {}).get("total", 0.0)
    username = update.effective_user.username or update.effective_user.first_name
    wallet = u.get("wallet")

    rates = get_rates(context)
    usd_amd = rates["USDAMD"]
    base_amd = fmt_amd(base * usd_amd)
    fee_amd = fmt_amd(fee * usd_amd)
    total_amd = fmt_amd(total * usd_amd)

    retry_note = texts[lang]["retry_label"] if is_retry else ""
    keyboard = InlineKeyboardMarkup([[InlineKeyboardButton("✅ Подтвердить", callback_data="approve"),
                                      InlineKeyboardButton("❌ Отклонить", callback_data="reject")]])

    if flow == "buy":
        caption = texts[lang]["channel_caption_buy"].format(
            asset=asset, username=username, asset_amount=asset_amount,
            base=base, base_amd=base_amd, fee=fee, fee_amd=fee_amd,
            total=total, total_amd=total_amd, wallet=wallet, retry=retry_note
        )
    else:
        caption = texts[lang]["channel_caption_sell"].format(
            asset=asset, username=username, asset_amount=asset_amount,
            base=base, base_amd=base_amd, fee=fee, fee_amd=fee_amd,
            total=total, total_amd=total_amd, wallet=wallet, retry=retry_note
        )

    sent = await context.bot.send_photo(chat_id=CHANNEL_USERNAME, photo=photo_id,
                                        caption=caption, reply_markup=keyboard)

    # лог
    log_request({
        "ts": datetime.utcnow().isoformat(),
        "flow": flow, "asset": asset, "asset_amount": asset_amount,
        "base_usdt": base, "fee_usdt": fee, "total_usdt": total,
        "username": username, "user_id": update.effective_user.id,
        "wallet": wallet, "status": "pending"
    })

    pending[sent.message_id] = {
        "lang": lang, "user_chat_id": update.effective_chat.id,
        "asset": asset, "asset_amount": asset_amount,
        "usdt_total": total, "usd_amd": usd_amd,
        "wallet": wallet, "flow": flow, "photo_id": photo_id
    }

    await update.message.reply_text(texts[lang]["after_check_wait"])
    return ACTION

async def button_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    msg_id = query.message.message_id
    if msg_id not in pending:
        await query.answer("Заявка не найдена", show_alert=True)
        return

    pdata = pending.pop(msg_id)
    lang = pdata["lang"]
    user_id = pdata["user_chat_id"]

    # обновим лог
    log_request({
        "ts": datetime.utcnow().isoformat(),
        "flow": pdata["flow"], "asset": pdata["asset"], "asset_amount": pdata["asset_amount"],
        "base_usdt": None, "fee_usdt": None, "total_usdt": pdata["usdt_total"],
        "username": None, "user_id": user_id, "wallet": pdata["wallet"],
        "status": "approved" if query.data == "approve" else "rejected"
    })

    if query.data == "approve":
        amd_total = fmt_amd(pdata["usdt_total"] * pdata["usd_amd"])
        await context.bot.send_message(
            chat_id=user_id,
            text=texts[lang]["approved_user"].format(
                asset=pdata["asset"], asset_amount=pdata["asset_amount"],
                usdt_total=pdata["usdt_total"], amd_total=amd_total
            )
        )
        await query.edit_message_caption(caption=(query.message.caption or "") + "\n✅ Подтверждено", reply_markup=None)

    elif query.data == "reject":
        await context.bot.send_message(chat_id=user_id, text=texts[lang]["auto_reject_user"])
        # сразу вернуть на выбор языка (без приветствия)
        await send_lang_prompt(user_id, context)
        await query.edit_message_caption(caption=(query.message.caption or "") + "\n❌ Отклонено", reply_markup=None)

# ===================== APP / JOBS ==================
async def post_init(app: Application):
    # первый апдейт
    await update_rates(app)
    # периодическое обновление через JobQueue (каждые 60 сек)
    app.job_queue.run_repeating(lambda c: update_rates(app), interval=60, first=60)

def main():
    init_sqlite()
    app = Application.builder().token(TOKEN).post_init(post_init).build()

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
