import asyncio
from datetime import datetime, timezone
import json
import os
import sqlite3
import aiohttp
import logging
from typing import Dict, Any, Optional

from telegram import (
    Update, ReplyKeyboardMarkup, ReplyKeyboardRemove,
    InlineKeyboardMarkup, InlineKeyboardButton
)
from telegram.ext import (
    Application, CommandHandler, MessageHandler, ConversationHandler,
    ContextTypes, filters, CallbackQueryHandler
)

# ====== CONFIG ======
try:
    from config import (
        TOKEN as BOT_TOKEN,
        CHANNEL_USERNAME,
        ENABLE_SQLITE,
        ENABLE_GOOGLE_SHEETS,
        GOOGLE_SHEETS_JSON_PATH,
        GOOGLE_SHEET_NAME,
        # опционально:
        # FEE_RATE, ALLOWED_ASSETS
    )
except Exception:
    # если нет config.py — читаем из ENV
    BOT_TOKEN = os.getenv("BOT_TOKEN", "")
    CHANNEL_USERNAME = os.getenv("CHANNEL_USERNAME", "@ethereumamoperator")
    ENABLE_SQLITE = os.getenv("ENABLE_SQLITE", "false").lower() == "true"
    ENABLE_GOOGLE_SHEETS = os.getenv("ENABLE_GOOGLE_SHEETS", "false").lower() == "true"
    GOOGLE_SHEETS_JSON_PATH = os.getenv("GOOGLE_SHEETS_JSON_PATH", "./service_account.json")
    GOOGLE_SHEET_NAME = os.getenv("GOOGLE_SHEET_NAME", "Transactions")

MERCHANT_USDT_ADDRESS = os.getenv("MERCHANT_USDT_ADDRESS", "0xYourUSDT_ERC20_Address_Here")

FEE_RATE = float(os.getenv("FEE_RATE", "0.03"))
ALLOWED_ASSETS = ("BTC", "ETH")  # по требованию — работаем только с BTC/ETH

# ====== LOGGING ======
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("ethereum_platform")

# ====== STATES ======
LANGUAGE, ACTION, PICK_ASSET, ENTER_AMOUNT, ENTER_WALLET, AWAITING_CHECK = range(6)

# ====== GLOBAL RATES CACHE ======
# Обновляется фоново каждые 60 сек
_rates_cache = {
    "updated_ts": None,      # datetime in UTC
    "btc_usdt": None,
    "eth_usdt": None,
    "usdt_amd": None,        # средний P2P (fallback fx)
}

# ====== LANG ======
language_map = {
    "🇷🇺 Русский": "Русский",
    "🇦🇲 Հայերեն": "Հայերեն",
    "🇬🇧 English": "English"
}

# Короткие фразы для баннера/меню
TEXTS = {
    "Русский": {
        "brand": "💎 Ethereum Платформа",
        "choose_lang": "Выберите язык / Խնդրում ենք ընտրել լեզուն / Please select a language:",
        "menu": "Выберите действие:",
        "buttons": [["💰 Купить BTC/ETH", "💸 Продать BTC/ETH"], ["⬅️ Назад"]],
        "pick_asset": "Выберите актив: BTC или ETH.",
        "enter_amount_buy": "Введите количество {asset}, которое хотите купить (например 0.01):",
        "enter_amount_sell": "Введите количество {asset}, которое хотите продать (например 0.01):",
        "merchant_addr_title": "💳 Адрес для оплаты (USDT-ERC20):\n`{addr}`",
        "send_check": "Теперь отправьте только фото/скриншот чека. Текст не принимается.",
        "only_photo": "На этом шаге принимается только фото/скрин. Пожалуйста, пришлите изображение.",
        "after_check_wait": "✅ Чек получен. Ваша заявка ждёт подтверждения оператора.",
        "bad_wallet": "Неверный адрес. Должен начинаться с 0x, длина 42, корректный checksum (EIP-55).",
        "enter_wallet": "Укажите адрес вашего 💵 USDT-ERC20 (начинается с 0x…):",
        "rates_title": "Курсы криптовалют (обновлено: {ago})",
        "buy_header": "🟢 Покупка {asset}",
        "sell_header": "🔴 Продажа {asset}",
        "calc_line_rate": "Курс {asset}: {usdt:.2f} USDT (~{amd} AMD)",
        "calc_line_base": "Сумма: {usdt:.2f} USDT (~{amd} AMD)",
        "calc_line_fee": "Комиссия 3%: {usdt:.2f} USDT (~{amd} AMD)",
        "calc_line_total_buy": "К оплате: {usdt:.2f} USDT (~{amd} AMD)",
        "calc_line_total_sell": "К получению: {usdt:.2f} USDT (~{amd} AMD)",
        "copied_reply": "Адрес для оплаты: {addr}",
        "auto_reject_user": (
            "❌ Ваша заявка отклонена.\n"
            "Причина: чек не видно / не сегодняшняя дата/время / чек неверный.\n"
            "Отправьте, пожалуйста, корректный чек."
        ),
        "approved_user": (
            "✅ Ваша заявка одобрена.\n"
            "Актив: {asset}\n"
            "Количество: {asset_amount:.8f} {asset}\n"
            "Итого: {total_usdt:.2f} USDT (~{total_amd} AMD)\n"
            "Оператор отправил то, что вы запрашивали."
        ),
        "channel_caption_buy": (
            "🟢 Покупка {asset}\n"
            "Пользователь: @{username}\n"
            "Количество: {asset_amount:.8f} {asset}\n\n"
            "Сумма: {base_usdt:.2f} USDT (~{base_amd} AMD)\n"
            "Комиссия (3%): {fee_usdt:.2f} USDT (~{fee_amd} AMD)\n"
            "Итого к оплате: {total_usdt:.2f} USDT (~{total_amd} AMD)\n\n"
            "Адрес USDT-ERC20: {wallet}\n"
            "Статус: Ожидает подтверждения"
        ),
        "channel_caption_sell": (
            "🔴 Продажа {asset}\n"
            "Пользователь: @{username}\n"
            "Количество: {asset_amount:.8f} {asset}\n\n"
            "Сумма: {base_usdt:.2f} USDT (~{base_amd} AMD)\n"
            "Комиссия (3%): {fee_usdt:.2f} USDT (~{fee_amd} AMD)\n"
            "К выплате: {total_usdt:.2f} USDT (~{total_amd} AMD)\n\n"
            "USDT-ERC20 адрес клиента: {wallet}\n"
            "Статус: Ожидает подтверждения"
        ),
    },
    "Հայերեն": {
        "brand": "💎 Ethereum հարթակ",
        "choose_lang": "Խնդրում ենք ընտրել լեզուն / Выберите язык / Please select a language:",
        "menu": "Ընտրեք գործողությունը՝",
        "buttons": [["💰 Գնել BTC/ETH", "💸 Վաճառել BTC/ETH"], ["⬅️ Վերադառնալ"]],
        "pick_asset": "Ընտրեք ակտիվ՝ BTC կամ ETH։",
        "enter_amount_buy": "Մուտքագրեք {asset}-ի քանակը, որը ցանկանում եք գնել (օր. 0.01)։",
        "enter_amount_sell": "Մուտքագրեք {asset}-ի քանակը, որը ցանկանում եք վաճառել (օր. 0.01)։",
        "merchant_addr_title": "💳 Վճարման հասցե (USDT-ERC20):\n`{addr}`",
        "send_check": "Այժմ ուղարկեք միայն վճարման լուսանկար/սքրինշոթ։ Տեքստը չի ընդունվում։",
        "only_photo": "Այս փուլում ընդունվում է միայն լուսանկար/սքրինշոթ։",
        "after_check_wait": "✅ Ստուգումը ստացվեց։ Հայտը սպասում է օպերատորի հաստատմանը։",
        "bad_wallet": "Սխալ հասցե․ պետք է սկսվի 0x-ով, լինի 42 նիշ, ունենալ ճիշտ EIP-55 checksum։",
        "enter_wallet": "Նշեք ձեր 💵 USDT-ERC20 հասցեն (սկսվում է 0x…):",
        "rates_title": "Փոխարժեքներ (թարմացվեց՝ {ago})",
        "buy_header": "🟢 Գնում {asset}",
        "sell_header": "🔴 Վաճառք {asset}",
        "calc_line_rate": "Փոխարժեք {asset}: {usdt:.2f} USDT (~{amd} AMD)",
        "calc_line_base": "Գումար՝ {usdt:.2f} USDT (~{amd} AMD)",
        "calc_line_fee": "Միջնորդավճար 3%՝ {usdt:.2f} USDT (~{amd} AMD)",
        "calc_line_total_buy": "Վճարում՝ {usdt:.2f} USDT (~{amd} AMD)",
        "calc_line_total_sell": "Կստանաք՝ {usdt:.2f} USDT (~{amd} AMD)",
        "copied_reply": "Վճարման հասցե՝ {addr}",
        "auto_reject_user": (
            "❌ Ձեր հայտը մերժվեց.\n"
            "Պատճառ՝ չեկը չի երևում/այսօրվա ամսաթիվ/ժամ չկա/չեկը սխալ է։\n"
            "Ուղարկեք, խնդրում ենք, ճիշտ չեկ։"
        ),
        "approved_user": (
            "✅ Ձեր հայտը հաստատվել է.\n"
            "Ակտիվ՝ {asset}\n"
            "Քանակ՝ {asset_amount:.8f} {asset}\n"
            "Ընդհանուր՝ {total_usdt:.2f} USDT (~{total_amd} AMD)\n"
            "Օպերատորը ուղարկել է Ձեր պահանջածը։"
        ),
        "channel_caption_buy": (
            "🟢 Գնում {asset}\n"
            "Օգտատեր՝ @{username}\n"
            "Քանակ՝ {asset_amount:.8f} {asset}\n\n"
            "Գումար՝ {base_usdt:.2f} USDT (~{base_amd} AMD)\n"
            "Միջնորդավճար (3%)՝ {fee_usdt:.2f} USDT (~{fee_amd} AMD)\n"
            "Վճարում՝ {total_usdt:.2f} USDT (~{total_amd} AMD)\n\n"
            "USDT-ERC20 հասցե՝ {wallet}\n"
            "Կարգավիճակ՝ Սպասում է հաստատման"
        ),
        "channel_caption_sell": (
            "🔴 Վաճառք {asset}\n"
            "Օգտատեր՝ @{username}\n"
            "Քանակ՝ {asset_amount:.8f} {asset}\n\n"
            "Գումար՝ {base_usdt:.2f} USDT (~{base_amd} AMD)\n"
            "Միջնորդավճար (3%)՝ {fee_usdt:.2f} USDT (~{fee_amd} AMD)\n"
            "Ստանալու եք՝ {total_usdt:.2f} USDT (~{total_amd} AMD)\n\n"
            "Հաճախորդի USDT-ERC20 հասցե՝ {wallet}\n"
            "Կարգավիճակ՝ Սպասում է հաստատման"
        ),
    },
    "English": {
        "brand": "💎 Ethereum Platform",
        "choose_lang": "Please select a language / Խնդրում ենք ընտրել լեզուն / Выберите язык:",
        "menu": "Choose an action:",
        "buttons": [["💰 Buy BTC/ETH", "💸 Sell BTC/ETH"], ["⬅️ Back"]],
        "pick_asset": "Choose asset: BTC or ETH.",
        "enter_amount_buy": "Enter the amount of {asset} you want to buy (e.g., 0.01):",
        "enter_amount_sell": "Enter the amount of {asset} you want to sell (e.g., 0.01):",
        "merchant_addr_title": "💳 Payment address (USDT-ERC20):\n`{addr}`",
        "send_check": "Now send a photo/screenshot of the receipt only. Text is not accepted.",
        "only_photo": "At this step, only a photo/screenshot is accepted.",
        "after_check_wait": "✅ Receipt received. Your request is pending operator approval.",
        "bad_wallet": "Invalid address. Must start with 0x, 42 chars, correct EIP-55 checksum.",
        "enter_wallet": "Provide your 💵 USDT-ERC20 address (starts with 0x…):",
        "rates_title": "Crypto rates (updated: {ago})",
        "buy_header": "🟢 Buy {asset}",
        "sell_header": "🔴 Sell {asset}",
        "calc_line_rate": "{asset} price: {usdt:.2f} USDT (~{amd} AMD)",
        "calc_line_base": "Subtotal: {usdt:.2f} USDT (~{amd} AMD)",
        "calc_line_fee": "Fee 3%: {usdt:.2f} USDT (~{amd} AMD)",
        "calc_line_total_buy": "To pay: {usdt:.2f} USDT (~{amd} AMD)",
        "calc_line_total_sell": "You will receive: {usdt:.2f} USDT (~{amd} AMD)",
        "copied_reply": "Payment address: {addr}",
        "auto_reject_user": (
            "❌ Your request was rejected.\n"
            "Reason: receipt not visible / not today's date & time / invalid receipt.\n"
            "Please send a correct receipt."
        ),
        "approved_user": (
            "✅ Your request has been approved.\n"
            "Asset: {asset}\n"
            "Amount: {asset_amount:.8f} {asset}\n"
            "Total: {total_usdt:.2f} USDT (~{total_amd} AMD)\n"
            "The operator has sent what you requested."
        ),
        "channel_caption_buy": (
            "🟢 Buy {asset}\n"
            "User: @{username}\n"
            "Amount: {asset_amount:.8f} {asset}\n\n"
            "Subtotal: {base_usdt:.2f} USDT (~{base_amd} AMD)\n"
            "Fee (3%): {fee_usdt:.2f} USDT (~{fee_amd} AMD)\n"
            "Total to pay: {total_usdt:.2f} USDT (~{total_amd} AMD)\n\n"
            "USDT-ERC20 address: {wallet}\n"
            "Status: Waiting for approval"
        ),
        "channel_caption_sell": (
            "🔴 Sell {asset}\n"
            "User: @{username}\n"
            "Amount: {asset_amount:.8f} {asset}\n\n"
            "Subtotal: {base_usdt:.2f} USDT (~{base_amd} AMD)\n"
            "Fee (3%): {fee_usdt:.2f} USDT (~{fee_amd} AMD)\n"
            "To receive: {total_usdt:.2f} USDT (~{total_amd} AMD)\n\n"
            "Client USDT-ERC20 address: {wallet}\n"
            "Status: Waiting for approval"
        ),
    }
}

# ====== DB (опционально) ======
def init_sqlite():
    if not ENABLE_SQLITE:
        return
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

def log_to_sqlite(row: dict):
    if not ENABLE_SQLITE:
        return
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

# ====== Google Sheets (если нужно) ======
_gs_worksheet = None
def init_google_sheets():
    global _gs_worksheet
    if not ENABLE_GOOGLE_SHEETS:
        return
    try:
        import gspread
        from oauth2client.service_account import ServiceAccountCredentials
        scope = ["https://spreadsheets.google.com/feeds",
                 "https://www.googleapis.com/auth/drive"]
        creds = ServiceAccountCredentials.from_json_keyfile_name(GOOGLE_SHEETS_JSON_PATH, scope)
        gc = gspread.authorize(creds)
        try:
            sh = gc.open(GOOGLE_SHEET_NAME)
        except Exception:
            sh = gc.create(GOOGLE_SHEET_NAME)
        try:
            _gs_worksheet = sh.worksheet("Orders")
        except Exception:
            _gs_worksheet = sh.add_worksheet(title="Orders", rows="1000", cols="20")
            _gs_worksheet.append_row(
                ["ts", "flow", "asset", "asset_amount", "base_usdt", "fee_usdt",
                 "total_usdt", "username", "user_id", "wallet", "status"]
            )
    except Exception as e:
        logger.error(f"Google Sheets init failed: {e}")

def log_to_google_sheets(row: dict):
    if not ENABLE_GOOGLE_SHEETS or _gs_worksheet is None:
        return
    try:
        _gs_worksheet.append_row([
            row.get("ts"), row.get("flow"), row.get("asset"), row.get("asset_amount"),
            row.get("base_usdt"), row.get("fee_usdt"), row.get("total_usdt"),
            row.get("username"), row.get("user_id"), row.get("wallet"), row.get("status")
        ])
    except Exception as e:
        logger.error(f"Google Sheets append failed: {e}")

def log_request(row: dict):
    log_to_sqlite(row)
    log_to_google_sheets(row)

# ====== PRICE FETCH (Binance spot + P2P AMD) ======
BINANCE_TICKER = "https://api.binance.com/api/v3/ticker/price?symbol={symbol}"

async def fetch_binance_spot(session: aiohttp.ClientSession) -> Dict[str, float]:
    """Возвращает spot-цену BTCUSDT и ETHUSDT с Binance."""
    out = {}
    for sym in ("BTCUSDT", "ETHUSDT"):
        async with session.get(BINANCE_TICKER.format(symbol=sym)) as r:
            data = await r.json()
            out[sym] = float(data["price"])
    return {"BTC": out["BTCUSDT"], "ETH": out["ETHUSDT"]}

# P2P AMD: официальный публичный endpoint под AMD отсутствует часто,
# поэтому делаем попытку (если вернёт), иначе fallback на FX (exchangerate.host)
P2P_ENDPOINT = "https://p2p.binance.com/bapi/c2c/v2/friendly/c2c/adv/search"

async def _fetch_p2p_side_avg(session: aiohttp.ClientSession, trade_type: str) -> Optional[float]:
    """
    Возвращает среднюю цену по 10 объявлениям по USDT/AMD для trade_type in {"BUY","SELL"}.
    Если AMD недоступен — вернёт None.
    """
    payload = {
        "page": 1,
        "rows": 10,
        "asset": "USDT",
        "fiat": "AMD",
        "tradeType": trade_type,  # "BUY" or "SELL"
        "publisherType": None
    }
    headers = {"Content-Type": "application/json"}
    try:
        async with session.post(P2P_ENDPOINT, json=payload, headers=headers) as r:
            data = await r.json()
            ads = data.get("data", [])
            prices = []
            for adv in ads:
                try:
                    p = float(adv["adv"]["price"])
                    prices.append(p)
                except Exception:
                    continue
            if prices:
                return sum(prices)/len(prices)
    except Exception as e:
        logger.warning(f"P2P AMD fetch failed ({trade_type}): {e}")
    return None

async def fetch_usdt_amd(session: aiohttp.ClientSession) -> float:
    """P2P средний (если доступен), иначе fallback на FX (exchangerate.host)."""
    buy = await _fetch_p2p_side_avg(session, "BUY")
    sell = await _fetch_p2p_side_avg(session, "SELL")
    if buy and sell:
        return (buy + sell) / 2.0
    # fallback (официальный FX)
    try:
        async with session.get("https://api.exchangerate.host/latest?base=USD&symbols=AMD") as r:
            fx = await r.json()
            rate = float(fx["rates"]["AMD"])
            return rate
    except Exception as e:
        logger.warning(f"FX fallback USD->AMD failed: {e}")
        # последняя надежда — вернуть 0, чтобы не сломать формат
        return 0.0

def fmt_amd(i: float) -> str:
    # Округление до целого, формат с запятыми: 1,234,567 AMD
    return f"{int(round(i)):,.0f} AMD".replace(",", ",")

def human_ago(ts: datetime) -> str:
    if not ts:
        return "now"
    sec = int((datetime.now(timezone.utc) - ts).total_seconds())
    if sec < 60:
        return f"{sec} sec ago"
    m = sec // 60
    return f"{m} min ago"

async def update_rates_periodically(app: Application):
    """Фоновая задача: обновлять кэш цен каждые 60 сек."""
    await asyncio.sleep(1)
    timeout = aiohttp.ClientTimeout(total=8)
    while True:
        try:
            async with aiohttp.ClientSession(timeout=timeout) as session:
                spot = await fetch_binance_spot(session)
                usdt_amd = await fetch_usdt_amd(session)
                _rates_cache["btc_usdt"] = spot["BTC"]
                _rates_cache["eth_usdt"] = spot["ETH"]
                _rates_cache["usdt_amd"] = usdt_amd
                _rates_cache["updated_ts"] = datetime.now(timezone.utc)
                logger.info(f"Rates updated: BTC {spot['BTC']:.2f}, ETH {spot['ETH']:.2f}, USDT/AMD {usdt_amd:.4f}")
        except Exception as e:
            logger.warning(f"Rates update failed: {e}")
        await asyncio.sleep(60)

def rate_header(lang: str) -> str:
    t = TEXTS[lang]
    ago = human_ago(_rates_cache["updated_ts"])
    btc = _rates_cache["btc_usdt"] or 0.0
    eth = _rates_cache["eth_usdt"] or 0.0
    u2a = _rates_cache["usdt_amd"] or 0.0
    btc_amd = fmt_amd(btc * u2a) if u2a else "— AMD"
    eth_amd = fmt_amd(eth * u2a) if u2a else "— AMD"

    lines = [
        f"{t['brand']}",
        f"📊 {t['rates_title'].format(ago=ago)}",
        f"₿ BTC: {btc:,.2f} USDT (~{btc_amd})",
        f"✨ ETH: {eth:,.2f} USDT (~{eth_amd})",
        "💵 USDT-ERC20 only"
    ]
    return "\n".join(lines)

def build_kb(lang: str) -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(TEXTS[lang]["buttons"], resize_keyboard=True)

def get_lang(context: ContextTypes.DEFAULT_TYPE) -> str:
    return context.user_data.get("lang", "Русский")

def parse_float(s: str):
    try:
        return float((s or "").replace(",", "."))
    except Exception:
        return None

async def send_language_prompt_only(chat_id, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [["🇷🇺 Русский"], ["🇦🇲 Հայերեն"], ["🇬🇧 English"]]
    await context.bot.send_message(
        chat_id=chat_id,
        text=TEXTS["Русский"]["choose_lang"],
        reply_markup=ReplyKeyboardMarkup(keyboard, resize_keyboard=True, one_time_keyboard=True)
    )

# ====== HANDLERS ======
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # Приветствие БЕЗ курса (по требованию)
    keyboard = [["🇷🇺 Русский"], ["🇦🇲 Հայերեն"], ["🇬🇧 English"]]
    msg = await update.message.reply_text(
        TEXTS["Русский"]["choose_lang"],
        reply_markup=ReplyKeyboardMarkup(keyboard, resize_keyboard=True, one_time_keyboard=True)
    )
    context.user_data["start_msg_id"] = msg.message_id
    return LANGUAGE

async def set_language(update: Update, context: ContextTypes.DEFAULT_TYPE):
    lang = language_map.get(update.message.text)
    if not lang:
        await update.message.reply_text(TEXTS["Русский"]["choose_lang"])
        return LANGUAGE
    context.user_data["lang"] = lang

    # удаляем стартовое (если есть)
    try:
        sm = context.user_data.get("start_msg_id")
        if sm:
            await context.bot.delete_message(chat_id=update.effective_chat.id, message_id=sm)
    except Exception:
        pass

    # показываем КУРС (после выбора языка) + меню
    await update.message.reply_text(rate_header(lang))
    await update.message.reply_text(TEXTS[lang]["menu"], reply_markup=build_kb(lang))
    return ACTION

async def action(update: Update, context: ContextTypes.DEFAULT_TYPE):
    lang = get_lang(context)
    txt = (update.message.text or "").strip()

    if ("Купить" in txt) or ("Buy" in txt) or ("Գնել" in txt):
        context.user_data["flow"] = "buy"
        # показать шапку курса
        await update.message.reply_text(rate_header(lang), reply_markup=ReplyKeyboardRemove())
        await update.message.reply_text(TEXTS[lang]["pick_asset"])
        return PICK_ASSET

    if ("Продать" in txt) or ("Sell" in txt) or ("Վաճառել" in txt):
        context.user_data["flow"] = "sell"
        await update.message.reply_text(rate_header(lang), reply_markup=ReplyKeyboardRemove())
        await update.message.reply_text(TEXTS[lang]["pick_asset"])
        return PICK_ASSET

    if ("⬅️" in txt) or ("Back" in txt) or ("Վերադառնալ" in txt):
        return await start(update, context)

    await update.message.reply_text(TEXTS[lang]["menu"], reply_markup=build_kb(lang))
    return ACTION

async def pick_asset(update: Update, context: ContextTypes.DEFAULT_TYPE):
    lang = get_lang(context)
    asset = (update.message.text or "").upper().strip()
    if asset not in ALLOWED_ASSETS:
        await update.message.reply_text(TEXTS[lang]["pick_asset"])
        return PICK_ASSET

    context.user_data["asset"] = asset
    if context.user_data.get("flow") == "buy":
        await update.message.reply_text(TEXTS[lang]["enter_amount_buy"].format(asset=asset))
    else:
        await update.message.reply_text(TEXTS[lang]["enter_amount_sell"].format(asset=asset))
    return ENTER_AMOUNT

async def enter_amount(update: Update, context: ContextTypes.DEFAULT_TYPE):
    lang = get_lang(context)
    amount = parse_float(update.message.text)
    if not amount or amount <= 0:
        asset = context.user_data.get("asset", "BTC")
        if context.user_data.get("flow") == "buy":
            await update.message.reply_text(TEXTS[lang]["enter_amount_buy"].format(asset=asset))
        else:
            await update.message.reply_text(TEXTS[lang]["enter_amount_sell"].format(asset=asset))
        return ENTER_AMOUNT

    context.user_data["asset_amount"] = amount
    asset = context.user_data["asset"]

    # Текущие курсы из кэша
    price_usdt = _rates_cache["btc_usdt"] if asset == "BTC" else _rates_cache["eth_usdt"]
    u2a = _rates_cache["usdt_amd"] or 0.0

    base_usdt = amount * (price_usdt or 0.0)
    fee_usdt = base_usdt * FEE_RATE
    if context.user_data.get("flow") == "buy":
        total_usdt = base_usdt + fee_usdt
        header = TEXTS[lang]["buy_header"].format(asset=asset)
        total_line = TEXTS[lang]["calc_line_total_buy"]
        # Показываем адрес мерчанта сразу
        await update.message.reply_text(
            f"{header}\n\n"
            f"{TEXTS[lang]['calc_line_rate'].format(asset=asset, usdt=price_usdt or 0.0, amd=fmt_amd((price_usdt or 0.0)*u2a))}\n"
            f"{TEXTS[lang]['calc_line_base'].format(usdt=base_usdt, amd=fmt_amd(base_usdt*u2a))}\n"
            f"{TEXTS[lang]['calc_line_fee'].format(usdt=fee_usdt, amd=fmt_amd(fee_usdt*u2a))}\n"
            f"{total_line.format(usdt=total_usdt, amd=fmt_amd(total_usdt*u2a))}"
        )
        await update.message.reply_text(
            TEXTS[lang]["merchant_addr_title"].format(addr=MERCHANT_USDT_ADDRESS),
            parse_mode="Markdown"
        )
        await update.message.reply_text(TEXTS[lang]["send_check"])
        context.user_data["wallet"] = MERCHANT_USDT_ADDRESS
        context.user_data["calc"] = {
            "base_usdt": base_usdt,
            "fee_usdt": fee_usdt,
            "total_usdt": total_usdt,
            "price_usdt": price_usdt or 0.0
        }
        return AWAITING_CHECK
    else:
        total_usdt = base_usdt - fee_usdt
        header = TEXTS[lang]["sell_header"].format(asset=asset)
        total_line = TEXTS[lang]["calc_line_total_sell"]
        await update.message.reply_text(
            f"{header}\n\n"
            f"{TEXTS[lang]['calc_line_rate'].format(asset=asset, usdt=price_usdt or 0.0, amd=fmt_amd((price_usdt or 0.0)*u2a))}\n"
            f"{TEXTS[lang]['calc_line_base'].format(usdt=base_usdt, amd=fmt_amd(base_usdt*u2a))}\n"
            f"{TEXTS[lang]['calc_line_fee'].format(usdt=fee_usdt, amd=fmt_amd(fee_usdt*u2a))}\n"
            f"{total_line.format(usdt=total_usdt, amd=fmt_amd(total_usdt*u2a))}"
        )
        await update.message.reply_text(TEXTS[lang]["enter_wallet"])
        context.user_data["calc"] = {
            "base_usdt": base_usdt,
            "fee_usdt": fee_usdt,
            "total_usdt": total_usdt,
            "price_usdt": price_usdt or 0.0
        }
        return ENTER_WALLET

def _basic_eth_format(addr: str) -> bool:
    return isinstance(addr, str) and addr.startswith("0x") and len(addr) == 42

def _strong_checksum(addr: str) -> bool:
    try:
        from eth_utils import is_checksum_address
        return is_checksum_address(addr)
    except Exception:
        return True

async def enter_wallet(update: Update, context: ContextTypes.DEFAULT_TYPE):
    lang = get_lang(context)
    wallet = (update.message.text or "").strip()
    if not _basic_eth_format(wallet) or not _strong_checksum(wallet):
        await update.message.reply_text(TEXTS[lang]["bad_wallet"])
        await update.message.reply_text("ℹ️ Для точной проверки установите пакет: eth-utils")
        return ENTER_WALLET
    context.user_data["wallet"] = wallet
    await update.message.reply_text(TEXTS[lang]["send_check"])
    return AWAITING_CHECK

async def receive_check(update: Update, context: ContextTypes.DEFAULT_TYPE):
    lang = get_lang(context)
    if not update.message.photo:
        await update.message.reply_text(TEXTS[lang]["only_photo"])
        return AWAITING_CHECK

    photo_id = update.message.photo[-1].file_id
    u = context.user_data
    flow = u.get("flow")
    asset = u.get("asset")
    amount = u.get("asset_amount", 0.0)
    calc = u.get("calc", {})
    price_usdt = calc.get("price_usdt", 0.0)
    base_usdt = calc.get("base_usdt", 0.0)
    fee_usdt = calc.get("fee_usdt", 0.0)
    total_usdt = calc.get("total_usdt", 0.0)
    u2a = _rates_cache["usdt_amd"] or 0.0

    username = update.effective_user.username or update.effective_user.first_name
    wallet = u.get("wallet")

    kb = InlineKeyboardMarkup([
        [InlineKeyboardButton("✅ Подтвердить", callback_data="approve"),
         InlineKeyboardButton("❌ Отклонить", callback_data="reject")]
    ])

    caption_tpl = TEXTS[lang]["channel_caption_buy"] if flow == "buy" else TEXTS[lang]["channel_caption_sell"]
    caption = caption_tpl.format(
        asset=asset,
        username=username,
        asset_amount=amount,
        base_usdt=base_usdt, base_amd=fmt_amd(base_usdt*u2a),
        fee_usdt=fee_usdt,   fee_amd=fmt_amd(fee_usdt*u2a),
        total_usdt=total_usdt, total_amd=fmt_amd(total_usdt*u2a),
        wallet=wallet
    )

    sent = await context.bot.send_photo(
        chat_id=CHANNEL_USERNAME,
        photo=photo_id,
        caption=caption,
        reply_markup=kb
    )

    # Логи
    log_request({
        "ts": datetime.utcnow().isoformat(),
        "flow": flow, "asset": asset, "asset_amount": amount,
        "base_usdt": base_usdt, "fee_usdt": fee_usdt, "total_usdt": total_usdt,
        "username": username, "user_id": update.effective_user.id,
        "wallet": wallet, "status": "pending"
    })

    # для коллбэка
    context.user_data["pending_msg_id"] = sent.message_id
    context.application.chat_data.setdefault("pending", {})
    context.application.chat_data["pending"][sent.message_id] = {
        "lang": lang,
        "user_chat_id": update.effective_chat.id,
        "asset": asset,
        "asset_amount": amount,
        "usdt_total": total_usdt,
        "usdt_amd": u2a,
        "wallet": wallet,
        "flow": flow,
    }

    await update.message.reply_text(TEXTS[lang]["after_check_wait"])
    return ACTION

async def button_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    msg_id = query.message.message_id

    pend = context.application.chat_data.get("pending", {})
    if msg_id not in pend:
        await query.answer("Заявка не найдена", show_alert=True)
        return

    pdata = pend.pop(msg_id)
    lang = pdata["lang"]
    user_id = pdata["user_chat_id"]

    total_usdt = pdata["usdt_total"]
    total_amd = fmt_amd(total_usdt * (pdata.get("usdt_amd") or 0.0))

    if query.data == "approve":
        await context.bot.send_message(
            chat_id=user_id,
            text=TEXTS[lang]["approved_user"].format(
                asset=pdata["asset"],
                asset_amount=pdata["asset_amount"],
                total_usdt=total_usdt,
                total_amd=total_amd
            )
        )
        await query.edit_message_caption(caption=(query.message.caption or "") + "\n✅ Заявка подтверждена", reply_markup=None)

    elif query.data == "reject":
        # авто-сообщение и возвращаем на выбор языка (БЕЗ приветствия)
        await context.bot.send_message(chat_id=user_id, text=TEXTS[lang]["auto_reject_user"])
        await send_language_prompt_only(user_id, context)
        await query.edit_message_caption(caption=(query.message.caption or "") + "\n❌ Отклонено", reply_markup=None)

# ====== MAIN ======
def main():
    init_sqlite()
    if ENABLE_GOOGLE_SHEETS:
        init_google_sheets()

    app = Application.builder().token(BOT_TOKEN).build()

    # Фоновое обновление курсов
    app.create_task(update_rates_periodically(app))

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
