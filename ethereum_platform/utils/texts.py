# utils/texts.py
language_map = {
    "🇷🇺 Русский": "Русский",
    "🇦🇲 Հայերեն": "Հայերեն",
    "🇬🇧 English": "English"
}

texts = {
    "Русский": {
        "brand": "💎 Ethereum Платформа®",
        "start_greet": (
            "👋 Добро пожаловать!\n"
            "Вы используете 💎 Ethereum Платформа® — безопасный и удобный сервис для обмена USDT, BTC и ETH.\n\n"
            "Выберите язык / Խնդրում ենք ընտրել լեզուն / Please select a language:"
        ),
        "rates_once": (
            "📊 Текущие курсы:\n"
            "₿ BTC: {btc:.4f} USDT | Ξ ETH: {eth:.4f} USDT\n"
            "💵 Оплата и выплаты: только USDT-ERC20\n"
            "⚠️ Комиссия 3% (покупка +, продажа −)"
        ),
        "menu_info": "Выберите действие:",
        "buttons": [["💰 Купить BTC/ETH", "💸 Продать BTC/ETH"], ["⬅️ Назад"]],
        "pick_asset": "Выберите актив: BTC или ETH.",
        "enter_amount_buy": "Введите количество {asset}, которое хотите купить (например 0.01):",
        "enter_amount_sell": "Введите количество {asset}, которое хотите продать (например 0.01):",
        "merchant_addr_title": "💳 Адрес для оплаты (USDT-ERC20):\n`{addr}`\n(нажмите, чтобы скопировать)",
        "enter_wallet": "Отправьте ваш 💵 USDT-ERC20 адрес для выплаты (начинается с 0x…):",
        "bad_wallet": "Неверный адрес. Должен начинаться с 0x, быть длиной 42 и соответствовать формату EIP-55.",
        "send_check": "Теперь пришлите **только фото/скриншот** чека. Текст/файлы не принимаются.",
        "only_photo": "Принимается **только фото/скриншот** чека. Пришлите изображение.",
        "after_check_wait": "✅ Чек получен. Ваша заявка ждёт подтверждения оператора.",
        "calc_buy": "Курс {asset}: {price:.4f} USDT\nСумма: {base:.2f} USDT\nКомиссия (3%): {fee:.2f} USDT\n**Итого к оплате:** {total:.2f} USDT",
        "calc_sell": "Курс {asset}: {price:.4f} USDT\nСумма: {base:.2f} USDT\nКомиссия (3%): {fee:.2f} USDT\n**К получению:** {total:.2f} USDT",
        "approved_user": "✅ Ваша заявка одобрена.\nАктив: {asset}\nКоличество: {asset_amount:.8f} {asset}\nUSDT-ERC20: {usdt_total:.2f}\nОператор отправил то, что вы запрашивали.",
        "auto_reject_user": "❌ Ваша заявка отклонена.\nПричина: чек не видно / дата и время не сегодняшние / чек неверный.\nПожалуйста, отправьте корректный чек (чёткое фото с актуальными датой/временем).",
        "retry_label": "⚠️ Повторная отправка чека\n",
        "channel_caption_buy": (
            "🟢 Покупка {asset}\n"
            "Пользователь: @{username}\n"
            "Количество: {asset_amount:.8f} {asset}\n\n"
            "Сумма: {base:.2f} USDT\nКомиссия (3%): {fee:.2f} USDT\n"
            "Итого к оплате: {total:.2f} USDT\n\n"
            "USDT-ERC20 адрес: {wallet}\n"
            "{exif}\nСтатус: Ожидает подтверждения"
        ),
        "channel_caption_sell": (
            "🔴 Продажа {asset}\n"
            "Пользователь: @{username}\n"
            "Количество: {asset_amount:.8f} {asset}\n\n"
            "Сумма: {base:.2f} USDT\nКомиссия (3%): {fee:.2f} USDT\n"
            "К выплате: {total:.2f} USDT\n\n"
            "USDT-ERC20 адрес (клиента): {wallet}\n"
            "{exif}\nСтатус: Ожидает подтверждения"
        ),
        "lang_keyboard": [["🇷🇺 Русский"], ["🇦🇲 Հայերեն"], ["🇬🇧 English"]]
    },
    "Հայերեն": {
        "brand": "💎 Ethereum Հարթակ®",
        "start_greet": (
            "👋 Բարի գալուստ։\n"
            "Դուք օգտագործում եք 💎 Ethereum Հարթակ® — անվտանգ և հարմար ծառայություն USDT, BTC և ETH փոխանակման համար։\n\n"
            "Խնդրում ենք ընտրել լեզուն / Выберите язык / Please select a language:"
        ),
        "rates_once": (
            "📊 Ընթացիկ փոխարժեքներ:\n"
            "₿ BTC: {btc:.4f} USDT | Ξ ETH: {eth:.4f} USDT\n"
            "💵 Վճարումները՝ միայն USDT-ERC20\n"
            "⚠️ Միջնորդավճար 3% (գնման՝ +, վաճառքի՝ −)"
        ),
        "menu_info": "Ընտրեք գործողությունը՝",
        "buttons": [["💰 Գնել BTC/ETH", "💸 Վաճառել BTC/ETH"], ["⬅️ Վերադառնալ"]],
        "pick_asset": "Ընտրեք ակտիվ՝ BTC կամ ETH։",
        "enter_amount_buy": "Մուտքագրեք {asset}-ի քանակը, որը ցանկանում եք գնել (օր. 0.01)։",
        "enter_amount_sell": "Մուտքագրեք {asset}-ի քանակը, որը ցանկանում եք վաճառել (օր. 0.01)։",
        "merchant_addr_title": "💳 Վճարման հասցե (USDT-ERC20):\n`{addr}`\n(սեղմեք՝ պատճենելու համար)",
        "enter_wallet": "Ուղարկեք ձեր 💵 USDT-ERC20 հասցեն (սկսվում է 0x…)՝ վճարման համար:",
        "bad_wallet": "Սխալ հասցե․ պետք է սկսվի 0x-ով, լինի 42 նիշ և համապատասխանի EIP-55 ֆորմատին։",
        "send_check": "Այժմ ուղարկեք **միայն լուսանկար/սքրինշոթ**՝ որպես չեկ։",
        "only_photo": "Ընդունվում է **միայն լուսանկար/սքրինշոթ**։",
        "after_check_wait": "✅ Ստուգումը ստացվեց։ Ձեր հայտը սպասում է հաստատման։",
        "calc_buy": "Գին {asset}: {price:.4f} USDT\nԳումար: {base:.2f} USDT\nՄիջնորդավճար (3%): {fee:.2f} USDT\n**Վճարում:** {total:.2f} USDT",
        "calc_sell": "Գին {asset}: {price:.4f} USDT\nԳումար: {base:.2f} USDT\nՄիջնորդավճար (3%): {fee:.2f} USDT\n**Կստանաք:** {total:.2f} USDT",
        "approved_user": "✅ Ձեր հայտը հաստատվել է։\nԱկտիվ՝ {asset}\nՔանակ՝ {asset_amount:.8f} {asset}\nUSDT-ERC20՝ {usdt_total:.2f}։",
        "auto_reject_user": "❌ Ձեր հայտը մերժվել է։\nՊատասխան՝ չեկը չի երևում / ամսաթիվը և ժամը այսօրը չեն / չեկը սխալ է։",
        "retry_label": "⚠️ Կրկնակի ստուգում\n",
        "channel_caption_buy": (
            "🟢 Գնում {asset}\n"
            "Օգտատեր՝ @{username}\n"
            "Քանակ՝ {asset_amount:.8f} {asset}\n\n"
            "Գումար՝ {base:.2f} USDT\nՄիջնորդավճար (3%)՝ {fee:.2f} USDT\n"
            "Վճարում՝ {total:.2f} USDT\n\n"
            "USDT-ERC20 հասցե՝ {wallet}\n"
            "{exif}\nԿարգավիճակ՝ Սպասում է հաստատման"
        ),
        "channel_caption_sell": (
            "🔴 Վաճառք {asset}\n"
            "Օգտատեր՝ @{username}\n"
            "Քանակ՝ {asset_amount:.8f} {asset}\n\n"
            "Գումար՝ {base:.2f} USDT\nՄիջնորդավճար (3%)՝ {fee:.2f} USDT\n"
            "Ստանալու եք՝ {total:.2f} USDT\n\n"
            "USDT-ERC20 (հաճախորդի)՝ {wallet}\n"
            "{exif}\nԿարգավիճակ՝ Սպասում է հաստատման"
        ),
        "lang_keyboard": [["🇷🇺 Русский"], ["🇦🇲 Հայերեն"], ["🇬🇧 English"]]
    },
    "English": {
        "brand": "💎 Ethereum Platform®",
        "start_greet": (
            "👋 Welcome!\n"
            "You are using 💎 Ethereum Platform® — a safe and convenient service for exchanging USDT, BTC and ETH.\n\n"
            "Please select a language / Խնդրում ենք ընտրել լեզուն / Выберите язык:"
        ),
        "rates_once": (
            "📊 Current rates:\n"
            "₿ BTC: {btc:.4f} USDT | Ξ ETH: {eth:.4f} USDT\n"
            "💵 Settlement: USDT-ERC20 only\n"
            "⚠️ Fee 3% (buy +, sell −)"
        ),
        "menu_info": "Choose an action:",
        "buttons": [["💰 Buy BTC/ETH", "💸 Sell BTC/ETH"], ["⬅️ Back"]],
        "pick_asset": "Choose asset: BTC or ETH.",
        "enter_amount_buy": "Enter how much {asset} you want to buy (e.g., 0.01):",
        "enter_amount_sell": "Enter how much {asset} you want to sell (e.g., 0.01):",
        "merchant_addr_title": "💳 Payment address (USDT-ERC20):\n`{addr}`\n(tap to copy)",
        "enter_wallet": "Send your 💵 USDT-ERC20 payout address (starts with 0x…):",
        "bad_wallet": "Invalid address. Must start with 0x, be 42 chars, and follow EIP-55 format.",
        "send_check": "Now send **photo/screenshot only** of the receipt. Text/files are not accepted.",
        "only_photo": "Only **photo/screenshot** is accepted at this step.",
        "after_check_wait": "✅ Receipt received. Your request is pending operator approval.",
        "calc_buy": "{asset} price: {price:.4f} USDT\nSubtotal: {base:.2f} USDT\nFee (3%): {fee:.2f} USDT\n**To pay:** {total:.2f} USDT",
        "calc_sell": "{asset} price: {price:.4f} USDT\nSubtotal: {base:.2f} USDT\nFee (3%): {fee:.2f} USDT\n**You will receive:** {total:.2f} USDT",
        "approved_user": "✅ Your request has been approved.\nAsset: {asset}\nAmount: {asset_amount:.8f} {asset}\nUSDT-ERC20: {usdt_total:.2f}.",
        "auto_reject_user": "❌ Your request was rejected.\nReason: receipt not visible / not today’s date/time / invalid receipt.",
        "retry_label": "⚠️ Retry receipt\n",
        "channel_caption_buy": (
            "🟢 Buy {asset}\n"
            "User: @{username}\n"
            "Amount: {asset_amount:.8f} {asset}\n\n"
            "Subtotal: {base:.2f} USDT\nFee (3%): {fee:.2f} USDT\n"
            "Total to pay: {total:.2f} USDT\n\n"
            "USDT-ERC20 address: {wallet}\n"
            "{exif}\nStatus: Waiting for approval"
        ),
        "channel_caption_sell": (
            "🔴 Sell {asset}\n"
            "User: @{username}\n"
            "Amount: {asset_amount:.8f} {asset}\n\n"
            "Subtotal: {base:.2f} USDT\nFee (3%): {fee:.2f} USDT\n"
            "To receive: {total:.2f} USDT\n\n"
            "Client USDT-ERC20 address: {wallet}\n"
            "{exif}\nStatus: Waiting for approval"
        ),
        "lang_keyboard": [["🇷🇺 Русский"], ["🇦🇲 Հայերեն"], ["🇬🇧 English"]]
    }
}
