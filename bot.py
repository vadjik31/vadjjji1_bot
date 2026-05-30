# -*- coding: utf-8 -*-
"""
Amazon-воронка: Telegram-бот.  Боевая сборка для @vadjik.

╔══════════════════════════════════════════════════════════════════════╗
║  BOT_TOKEN — в Railway Variables (или локально в .env).             ║
║  ADMIN_ID, BOT_LINK, CHANNEL — зашиты в CONFIG ниже.                ║
╚══════════════════════════════════════════════════════════════════════╝
"""

import asyncio
import hashlib
import re
import hmac
import json
import logging
import os
import threading
import time
from collections import defaultdict
from datetime import datetime, timedelta, time as dt_time
from zoneinfo import ZoneInfo

from urllib.parse import quote, urlencode
import urllib.request
from telegram import (
    Update, InlineKeyboardButton, InlineKeyboardMarkup, InputMediaPhoto,
    KeyboardButton, ReplyKeyboardMarkup, WebAppInfo,
)
from telegram.constants import ChatAction, ChatMemberStatus
from telegram.error import BadRequest, TimedOut
from telegram.ext import (
    Application, CommandHandler, CallbackQueryHandler,
    MessageHandler, ContextTypes, filters,
)

# ╔══════════════════════════════════════════════════════════════════════╗
# ║                          C   O   N   F   I   G                       ║
# ╚══════════════════════════════════════════════════════════════════════╝


# ──────────────────────────────────────────────────────────────────────
# 1) СЕКРЕТЫ И ССЫЛКИ
#    BOT_TOKEN — только Railway / .env (не в коде).
#    Ниже три строки — зашиты по твоему запросу (без Variables).
# ──────────────────────────────────────────────────────────────────────

BOT_TOKEN = os.getenv("BOT_TOKEN", "").strip()

ADMIN_ID = 630926654
BOT_LINK = "https://t.me/vadjjik1_bot"

CALL_LINK = os.getenv("CALL_LINK", "").strip() or "https://t.me/vadjik"
SITE_LINK = os.getenv("SITE_LINK", "").strip() or "https://vadjik.com/"
RESULTS_LINK = os.getenv("RESULTS_URL", "").strip() or "https://vadjik.com/results"
ABOUT_LINK = os.getenv("ABOUT_LINK", "").strip() or "https://telegra.ph/Kto-ya-05-06-7"

HOWMANY_URL = (
    os.getenv("Howmany", "").strip()
    or os.getenv("HOWMANY", "").strip()
    or os.getenv("HOWMANY_URL", "").strip()
    or "https://vadjik31.github.io/apppp/amazon-calc.html"
)

MENU_FORMATS = "💎 Форматы сотрудничества и обучения"
MENU_RESULTS = "📈 Результаты учеников"
MENU_GUIDE = "📘 Забрать гайд, 3 фатальных ошибки"
MENU_ABOUT = "👤 Обо мне"
MENU_EARN = "💸 Посчитать мой доход"
MENU_QUESTIONS = "💬 У меня есть вопросы"

QUESTIONS_HINT = (
    "\n\n💬 Есть вопросы — нажмите «У меня есть вопросы» в меню внизу."
)
QUESTIONS_STEPS = frozenset({
    "fork", "offer", "lead", "qualified", "qualified_cold",
})
PROOFS_BEFORE_CAPTION_SEC = float(os.getenv("PROOFS_BEFORE_CAPTION_PAUSE", "2") or "2")
PROOFS_V1_INTRO_PAUSE_SEC = float(os.getenv("PROOFS_V1_INTRO_PAUSE", "1.5") or "1.5")
PROOFS_V1_BEFORE_MAIN_SEC = float(os.getenv("PROOFS_V1_BEFORE_MAIN_PAUSE", "1.5") or "1.5")

SITE_PAY_ORIGIN = "https://vadjik.com"
WEBAPP_ENGAGE_SEC = 30
BONUS_REMIND_HOURS = float(os.getenv("BONUS_REMIND_HOURS", "3") or "3")
BONUS_REMIND_SEC = max(3600, int(BONUS_REMIND_HOURS * 3600))
BONUS_REMIND_MAX = int(os.getenv("BONUS_REMIND_MAX", "3") or "3")
BONUS_REMIND_KEYS = ("bonus_remind_1", "bonus_remind_2", "bonus_remind_3")
OFFER_STEPS = frozenset({"fork", "offer", "lead", "qualified", "qualified_cold"})
PAY_TARIFFS = (
    ("💳 Сам — оплатить", "myself"),
    ("💳 Поток — оплатить", "potok"),
    ("💳 Продвинутый", "advanced"),
    ("💳 Под ключ", "vip"),
)

WEBAPP_URL = (
    os.getenv("WEBAPP_URL", "").strip()
    or "https://vadjik31.github.io/apppp/index.html"
)
WEBAPP_BUILD = "20260530l"

APP_DATA_API = (
    os.getenv("APP_DATA_API", "").strip()
    or "https://vadjik.com/api/public/app-data"
)
APP_DATA_API_KEY = (
    os.getenv("APP_DATA_API_KEY", "").strip()
    or "vadjik_api_2cQ5gPnlBXo7iMAC7UofpurS4fa8uBVM"
)
_FLOW_MONTHS = (
    "янв", "фев", "мар", "апр", "мая", "июн",
    "июл", "авг", "сен", "окт", "ноя", "дек",
)
_FLOW_CACHE = {"flow_date": None, "flow_time": "19:00", "fetched_at": 0.0}


# ──────────────────────────────────────────────────────────────────────
# ПРОМО-СКИДКА (PROMO_SECRET — в Railway, общий с сайтом)
# ──────────────────────────────────────────────────────────────────────

PROMO_SECRET = os.getenv("PROMO_SECRET", "").strip()
DISCOUNT_URL = os.getenv("DISCOUNT_URL", "").strip() or "https://vadjik.com/faster_discount"
PROMO_HOURS = int(os.getenv("PROMO_HOURS", "24") or "24")
PROMO_DISCOUNT = int(os.getenv("PROMO_DISCOUNT", "20") or "20")


# ──────────────────────────────────────────────────────────────────────
# 2) ЛИД-МАГНИТ — канал для проверки подписки (бот = админ канала)
# ──────────────────────────────────────────────────────────────────────

CHANNEL_USERNAME = "@vadjikamazon"

# Автоотчёты админу (время — Europe/Moscow)
REPORT_TZ = ZoneInfo("Europe/Moscow")
REPORT_AUTO_ENABLED = True

GUIDE_FILE_ID = (
    os.getenv("GUIDE_FILE_ID", "").strip()
    or "BQACAgIAAxkBAAIBMGoYngYvtSejdbzTGF6F_FKBc-LqAALYmwAClIrJSDEbEaQrNI_jOwQ"
)
GUIDE_FILENAME = "guide.pdf"


# ──────────────────────────────────────────────────────────────────────
# 3) ВИДЕО И КРУЖКИ.
#
#    ⚠️ file_id привязан к КОНКРЕТНОМУ боту (BOT_TOKEN). Если сменил токен
#    или залил id от другого бота — будет Wrong file identifier.
#    Как обновить: напиши ЭТОМУ боту каждое видео/кружок → /id → вставь
#    сюда → redeploy. Проверка: /checkmedia (только админ).
#
#    Видео — только «прикрепить → Видео» (BAAC…), не «Файл» (BQAC…).
# ──────────────────────────────────────────────────────────────────────

MEDIA = {

    # КРУЖОК «КТО Я» (47 сек) — после /start.
    "circle_intro":  {
        "file_id": "DQACAgIAAxkBAAMhahhQfhCycqexkKysYDi_MMFQ4WwAAlmZAAJBpaBIUqucIOryZbc7BA",
        "sec": 58,
    },

    # ВИДЕО 1 — история Игоря (217 сек, ~3:37). Отправлено как «Видео» → стрим.
    "video_1":       {
        "file_id": "BAACAgIAAxkBAAIBBGoYmu4vEl1Xny0mrxfYdEhwOMNpAAK6mwAClIrJSNzoF_JMaoecOwQ",
        "kind": "video",
        "sec": 217,
    },

    # ВИДЕО 2 — схема по шагам (360 сек, 6:00).
    "video_2":       {
        "file_id": "BAACAgIAAxkBAAIBBmoYmv_yc3sme3xtmxQfQ9rs7xpPAAK7mwAClIrJSNH1lbWK9gsKOwQ",
        "kind": "video",
        "sec": 360,
    },

    # ВИДЕО 3 — страхи и отговорки (440 сек, ~7:20).
    "video_3":       {
        "file_id": "BAACAgIAAxkBAAIBCGoYmxLiiAR8ngom2FhminNqVIWVAAK9mwAClIrJSDdBry1NzUHrOwQ",
        "kind": "video",
        "sec": 440,
    },

    # КРУЖОК-РАЗВИЛКА (58 сек) — после видео 3, мост к офферу.
    "circle_fork":   {
        "file_id": "DQACAgIAAxkBAAMfahhQbWjfCilhcGCa5i6O7rDJJTcAAlqaAAJBpahI4aN9dQb-NTs7BA",
        "sec": 47,
    },
}


# ──────────────────────────────────────────────────────────────────────
# 4) СКРИНЫ-ПРУФЫ. Берутся с postimg.cc — Telegram сам качает по URL.
#    Захочешь зашить как file_id: включи /id, перешли скрин боту,
#    замени "url" на "file_id".
# ──────────────────────────────────────────────────────────────────────

# Блок A — после видео 1.
PROOFS_AFTER_V1 = [
    {"url": "https://i.postimg.cc/N0gpZWrD/photo-2026-05-26-17-43-03.jpg"},
    {"url": "https://i.postimg.cc/5txnDZFp/photo-2026-05-26-17-43-22.jpg"},
]

# Блок B — после видео 2 (file_id от боевого бота, /id).
PROOFS_AFTER_V2 = [
    {
        "file_id": "AgACAgIAAxkBAAIBKGoYnT-aaDoOmZ2vltHe2iXgAaPGAAL6HGsblIrJSC-VmGZXt0xFAQADAgADeAADOwQ",
        "caption": "Александр, США",
    },
    {
        "file_id": "AgACAgIAAxkBAAIBKmoYnXtjm52qX2Okfk_Qdj2YtVl3AAL8HGsblIrJSEQbRGUJod0-AQADAgADeAADOwQ",
        "caption": "Алексей, США",
    },
    {
        "file_id": "AgACAgIAAxkBAAIBLGoYnYpnHzwCL80yrCxGkFzIIBgXAAL9HGsblIrJSNCKbfggnqqmAQADAgADeQADOwQ",
        "caption": "Анатолий, Германия",
    },
    {
        "file_id": "AgACAgIAAxkBAAIBLmoYnZ03RLEbndt7gooGFYNwMXa0AAL-HGsblIrJSIWN74fE8EnCAQADAgADeAADOwQ",
        "caption": "Дмитрий, Италия",
    },
]

# Блок C — стек учеников по странам (по кнопке «Результаты учеников»).
PROOFS_STUDENTS = [
    {"url": "https://i.postimg.cc/bvN41GLJ/Aleksej-SSA.png"},
    {"url": "https://i.postimg.cc/hGy6sS3Z/Andrej-Francia.jpg"},
    {"url": "https://i.postimg.cc/5txnDZFp/photo-2026-05-26-17-43-22.jpg"},
    {"url": "https://i.postimg.cc/J0JFRj7y/Valeria-Germania.jpg"},
    {"url": "https://i.postimg.cc/MZM2sQwp/photo-2024-05-09-21-42-26.jpg"},
    {"url": "https://i.postimg.cc/RV58XpGd/Igori-Italia.png"},
    {"url": "https://i.postimg.cc/bNx5M0BJ/Kiril-Germania.jpg"},
    {"url": "https://i.postimg.cc/VN6HdxLt/Marina-Kanada.png"},
]

# Скрин страницы с результатами с сайта.
SITE_SCREEN = {"url": "https://i.postimg.cc/Twnjw0m1/Screenshot-138.png"}

# Скрины второй Mini App «Сколько можно заработать» (file_id от этого бота).
HOWMANY_SCREENS = [
    {"file_id": "AgACAgIAAxkBAAICMWoZYJaN72HvmOpxzk56UTclkPB8AAIYHGsblIrRSJ5Sqk8akXZkAQADAgADeQADOwQ"},
    {"file_id": "AgACAgIAAxkBAAICM2oZYKNN27GZ7Cz-YTEn7UfT8JIjAAIZHGsblIrRSNgnEytjZuUdAQADAgADeQADOwQ"},
    {"file_id": "AgACAgIAAxkBAAICNWoZYKtNeD9n40dWVg0Dxe5nams2AAIaHGsblIrRSGz3zk84tdonAQADAgADeQADOwQ"},
    {"file_id": "AgACAgIAAxkBAAICN2oZYLZORkUUb7Q7vIgtC9JgFCbQAAIbHGsblIrRSL8Psdezzt8PAQADAgADeQADOwQ"},
]
# Публичные URL картинок для Mini App (заполняется при старте бота из file_id).
HOWMANY_IMG_URLS = []


# ──────────────────────────────────────────────────────────────────────
# 5) ДОГОНЯЮЩИЕ: 2 на step, часы от входа на step (Д2 = +3 ч к Д1, offer +24 ч).
# ──────────────────────────────────────────────────────────────────────

# Исключения из защиты funnel_claims: только проверка подписки на канал.
# Воронка (go_intro, видео и т.д.) — один раз; «Я подписался» — сколько нужно,
# пока подписка не подтверждена и гайд не выдан.
FUNNEL_REPEAT_ACTIONS = frozenset({"lm_check"})

STEP_DRIP_SCHEDULE = {
    "start":     [(2, "drip_start_1"), (5, "drip_start_2")],
    "intro":     [(2, "drip_intro_1"), (5, "drip_intro_2")],
    "v1":        [(2, "drip_v1_1"), (5, "drip_v1_2")],
    "v2":        [(2, "drip_v2_1"), (5, "drip_v2_2")],
    "v3":        [(2, "drip_v3_1"), (5, "drip_v3_2")],
    "offer":     [(24, "drip_offer_1"), (48, "drip_offer_2")],
    "qualified": [(12, "drip_lead_1"), (24, "drip_lead_2")],
}


# ──────────────────────────────────────────────────────────────────────
# 6) ТЕКСТЫ. Меняй формулировки свободно.
# ──────────────────────────────────────────────────────────────────────

TXT = {
    "start": (
        "Привет 👋 На связи Вадим.\n\n"
        "Покажу, как выйти на первые $750 чистыми на Amazon — с нуля, "
        "без опыта и без «волшебных схем».\n\n"
        "Проведу вас тем же путём, что прошёл Игорь: как он разобрался, "
        "нашёл товар, сделал первую закупку и забрал прибыль. По дороге — "
        "реальные скрины кабинета людей, которые сейчас делают "
        "$5 000–7 000 в месяц.\n\n"
        "Сразу честно: миллиона за месяц не обещаю. Обещаю показать, "
        "как это устроено на самом деле.\n\n"
        "🎁 В конце — PDF «3 фатальные ошибки новичка»: из-за них за 6 лет "
        "я видел, как люди теряли деньги и уходили с Amazon. Чтобы вы "
        "так не делали.\n\n"
        "Поехали? 👇"
    ),
    "after_circle_intro": (
        "Рад познакомиться 🙂\n\n"
        "Сейчас покажу, как Amazon работает на самом деле — без хаоса, "
        "догадок и красивых обещаний.\n\n"
        "Начнём с короткой истории Игоря, минуты на 4. Он начинал ровно "
        "с того же: не понимал, какие товары брать, где искать поставщиков "
        "и как вообще подойти к первой закупке.\n\n"
        "В видео разберём, почему первые товары не зашли, что он поменял "
        "в подходе — и как в итоге вышел на первые чистые деньги. Без воды "
        "и мотивации, просто реальный путь от «я не понимаю, что делать» "
        "до первого результата.\n\n"
        "Включайте 👇"
    ),
    "after_v1_video": (
        "Досмотрели? 🙂\n\n"
        "Теперь самое важное: почему первый список товаров оказался "
        "слабым, что именно в нём не сходилось — и что изменилось "
        "после правок."
    ),
    "proofs_v1_intro": (
        "📈 А вот, кстати, реальные результаты учеников. Такого можно "
        "дойти, если идти по шагам — а не угадывать товар наугад."
    ),
    "proofs_v1_caption": (
        "💡 Смотрите, почему этот пример важен.\n\n"
        "Игорь тоже не нашёл хороший товар с первого раза. Где-то не "
        "сходились цифры. Где-то товар выглядел нормально, а на деле не "
        "подходил. Где-то закупка просто не имела смысла.\n\n"
        "Но он не бросил — взял правки, переделал, и уже со второй "
        "попытки нашёл рабочие варианты.\n\n"
        "Дальше всё пошло по цепочке:\n\n"
        "📦 закупка → 🏷 подготовка → 🚚 отправка на Amazon → "
        "💵 продажи → ✅ чистая прибыль.\n\n"
        "Вот так и выглядит настоящий путь: не «угадал товар», а "
        "проверил, исправил, дошёл до результата.\n\n"
        "Дальше покажу простыми словами, откуда вообще берётся "
        "прибыль 👇"
    ),
    "after_v1": (
        "💡 Смысл не в том, что Игорь сразу всё понял.\n\n"
        "⚠️ Сначала он ошибся — и именно поэтому пример нормальный.\n\n"
        "📋 Теперь разберём саму схему: откуда берётся прибыль на Amazon "
        "и что делает продавец 👇"
    ),
    "after_v2_video": (
        "Досмотрели? 🙂\n\n"
        "Покажу теперь, как эта же модель выглядит на разных рынках — "
        "чтобы вы видели, что она не «только для одной страны»."
    ),
    "bridge_v2": (
        "⚙️ Суть проще, чем кажется.\n\n"
        "На Amazon уже есть покупатели. Люди каждый день заходят и "
        "покупают. Вам не нужно создавать товар, строить бренд и кого-то "
        "уговаривать.\n\n"
        "Задача другая:\n\n"
        "1️⃣ найти товар, который уже покупают\n"
        "2️⃣ найти, где его взять дешевле\n"
        "3️⃣ посчитать расходы\n"
        "4️⃣ отправить на склад Amazon\n"
        "5️⃣ забрать разницу после продажи\n\n"
        "В следующем видео разберу всю схему по шагам 👇"
    ),
    "proofs_v2_caption": (
        "💡 Вот в этом и весь смысл.\n\n"
        "Вы не создаёте спрос с нуля. Спрос уже есть, покупатели уже "
        "есть, товары уже продаются.\n\n"
        "Ваша задача — найти товар, где сходятся три вещи:\n\n"
        "1️⃣ его можно купить дешевле\n"
        "2️⃣ его уже покупают на Amazon\n"
        "3️⃣ после всех расходов остаётся прибыль\n\n"
        "Нашли такой — дальше понятный цикл:\n\n"
        "купили → подготовили → отправили → продали → часть вернули "
        "в товар.\n\n"
        "И работает это хоть из СНГ, хоть из Европы, хоть из США. "
        "Неважно, кем вы были раньше — наёмным сотрудником, в декрете "
        "или вообще из другой сферы. Amazon про это не спрашивает.\n\n"
        "Готовы дальше? 👇"
    ),
    "after_v2": (
        "Теперь вы понимаете, как это работает 🙂\n\n"
        "Но есть момент: даже когда схема понятна, человек часто всё "
        "равно не начинает. И мешает обычно одно и то же:\n\n"
        "💸 «нет денег»\n"
        "⏰ «нет времени»\n"
        "🗣 «я не знаю язык»\n"
        "🔒 «а вдруг заблокируют»\n"
        "⌛ «уже поздно заходить»\n"
        "📦 «там одни конкуренты»\n\n"
        "Дальше — честный разбор каждой причины. Не мотивация в стиле "
        "«ты сможешь, если поверишь», а по пунктам, как с этим на самом "
        "деле (~7 мин) 👇"
    ),
    "v3_loading": (
        "▶️ Загружаю видео «Почему не начинают» (~7 мин).\n\n"
        "Подождите несколько секунд — ролик появится следующим сообщением."
    ),
    "after_v3_video": (
        "✅ Если вы дошли до этого момента — вы уже сделали больше, "
        "чем большинство.\n\n"
        "Разобрали путь Игоря, увидели рабочую схему и поняли, какие "
        "страхи чаще всего мешают начать.\n\n"
        "💸 А в конце вы узнаете, сколько можете заработать на Amazon "
        "именно на своём примере — мы сделали калькулятор под ваш "
        "бюджет. Осталось последнее — как пройти этот путь самому."
    ),
    "after_v3": (
        "Как получить первые продажи без хаоса и типичных ошибок? "
        "Если интересно — жмите 👇"
    ),
    "calc_pitch": (
        "Прежде чем показать форматы — кое-что интереснее 👇\n\n"
        "Мы сделали калькулятор, который считает на вашем примере: "
        "вводите, сколько готовы вложить сейчас, сколько можете "
        "добавлять каждый месяц и примерные расходы — а он показывает, "
        "где вы можете оказаться через год, если начнёте Amazon "
        "сегодня.\n\n"
        "Это не «средние по больнице», а ваши цифры. Откройте — "
        "займёт минуту 👇"
    ),
    "calc_pitch_nourl": (
        "Прежде чем показать форматы — пара слов про деньги 🙂\n\n"
        "Сколько реально заработать на Amazon, зависит от того, "
        "сколько вы вкладываете и как часто докупаете товар. На "
        "разборе мы считаем это под вашу ситуацию.\n\n"
        "Идём дальше к форматам 👇"
    ),
    "bonus_offer_after_app": (
        "Но вы могли бы активировать бонус и получить уникальные цены "
        "для вас, которые значительно комфортнее, а также супер-предложение!\n\n"
        "Активировать?"
    ),
    "bonus_remind_1": (
        "В «Форматах» можно один раз посмотреть цены со скидкой "
        "{discount}%.\n\n"
        "Откройте мини-приложение и нажмите кнопку внутри — меньше "
        "минуты. Просто посмотреть цифры, без оплаты."
    ),
    "bonus_remind_2": (
        "Скидка пока не закреплена — её нужно один раз активировать "
        "в приложении.\n\n"
        "«💎 Форматы» → кнопка со спец. ценами → увидите "
        "«было → стало». Не актуально — пропустите 🙂"
    ),
    "bonus_remind_3": (
        "Последний раз напомню про скидку 🙂\n\n"
        "−{discount}% доступны в «Форматах» — только посмотреть, без "
        "оплаты и регистрации, ничего не списывается. Дальше дёргать "
        "не буду."
    ),
    "after_fork_circle": (
        "Смотрите 🙂\n\n"
        "Дойти самому реально — но в одиночку легко застрять на "
        "мелочах: то поставщик не проходит проверку, то прибыль "
        "посчитана без комиссий. Обидно терять на этом первые "
        "деньги.\n\n"
        "Поэтому я и собрал форматы, где вы идёте не вслепую, а по "
        "шагам — с проверкой каждого решения и поддержкой до первой "
        "реальной продажи. Обычно это занимает около полутора "
        "месяцев.\n\n"
        "Самое сложное вы уже сделали — разобрались, как это "
        "работает. Дальше проще, когда рядом есть кто-то, кто этот "
        "путь уже прошёл.\n\n"
        "👇 Откройте «Форматы» — там цены и что входит. А рядом "
        "калькулятор: прикинуть, сколько реально заработать под ваш "
        "бюджет. Без обязательств — просто посмотреть."
    ),
    "after_fork_menu_hint": (
        "👇 Всё под рукой в меню внизу: «Форматы и цены», "
        "«Калькулятор», результаты учеников и вопросы.\n\n"
        "Можно вернуться в любой момент — ничего не потеряется."
    ),
    "menu_results": (
        "Результаты учеников — на сайте, со скринами и цифрами 👇"
    ),
    "menu_about": (
        "Коротко о том, кто я, чем занимаюсь и почему Amazon — в статье 👇"
    ),
    "menu_earn": (
        "💸 Калькулятор — прикинуть доход на Amazon при разном бюджете.\n\n"
        "Нажмите «💸 Посчитать мой доход» в меню внизу — откроется "
        "мини-приложение 👇"
    ),
    "programs_text": (
        "Вот варианты обучения — от «разберусь сам» до «под ключ» 👇\n\n"
        "1️⃣ Обучаюсь сам — $750\n"
        "Все уроки, программы-помощники, записи прошлых занятий, доступ "
        "навсегда. Свой темп.\n\n"
        "2️⃣ Поток — $1100\n"
        "Всё то же + группа, 2 личных разбора со мной, один поставщик на "
        "старт, поддержка. До первых продаж.\n\n"
        "3️⃣ Продвинутый — $1700 ⭐ (чаще всего)\n"
        "Всё из «Потока» + 4 личных разбора, три поставщика, рынок США "
        "или Европа, поддержка 4 месяца.\n\n"
        "4️⃣ Под ключ — $4200 💎\n"
        "12 личных разборов, 10 поставщиков, помощь с 50 товарами, сайт "
        "и учёт, поддержка полгода. Цель — $15 000+ продаж в месяц.\n\n"
        "🎁 В каждый пакет — инструменты (~$2 000) бесплатно.\n\n"
        "Что вам подойдёт — смотрите в мини-приложении или напишите мне 🙂"
    ),
    "students_caption": (
        "Разные страны и разные старты — одна схема 👇\n\n"
        "Посмотрите, кто уже прошёл путь с поддержкой — и вернитесь к "
        "форматам, если ещё не открывали 👇"
    ),
    "site_caption": (
        "На сайте — ещё больше историй с цифрами и скринами 👇\n\n"
        "Загляните, если хотите увидеть масштаб."
    ),
    "back_to_offer": (
        "Посмотрели? Вернитесь в меню или заберите скидку 👇"
    ),
    "promo_fallback": (
        "Отлично 🙂\n\n"
        "Напишите мне — разберём вашу ситуацию и подберём формат старта 👇"
    ),
    "drip_start_1": (
        "Открыли и закрыли — это нормально, почти все так с первого "
        "раза 🙂\n\n"
        "Если коротко: дальше я на пальцах показываю, как люди с нуля "
        "выходят на первые деньги на Amazon. Без регистраций — просто "
        "посмотреть. Гляньте, когда будет минута 👇"
    ),
    "drip_start_2": (
        "Это, кстати, не только для тех, кто «в теме».\n\n"
        "С нуля начинали и айтишники, и мамы в декрете, и люди с "
        "обычной работой за границей. Amazon не спрашивает, кем вы были "
        "раньше — показать, с чего начать? 👇"
    ),
    "drip_intro_1": (
        "Кружок посмотрели — дальше короткое видео, минуты на 4.\n\n"
        "По-честному: с чего реально начинают, где чаще всего лажают "
        "с первым товаром и как доходят до первых денег. Включайте, "
        "когда удобно 👇"
    ),
    "drip_intro_2": (
        "Понимаю, даже 4 минуты — это «сесть и посмотреть».\n\n"
        "Но это, наверное, единственное место, где быстро становится "
        "ясно: реально оно или очередная сказка про лёгкие деньги. "
        "Решите уже по факту 👇"
    ),
    "drip_v1_1": (
        "Обещал разбор — вот он: на живом примере, что именно не "
        "сходилось в первых товарах и что поменяли.\n\n"
        "Там же скрины результатов — видно, к чему ведёт нормальная "
        "проверка 👇"
    ),
    "drip_v1_2": (
        "2–3 минуты, без воды.\n\n"
        "Это как раз момент, где становится понятно, откуда вообще "
        "берётся прибыль. Дальше — только конкретика 👇"
    ),
    "drip_v2_1": (
        "Схему по шагам разобрали — найти, проверить, отправить на склад.\n\n"
        "Дальше короткие примеры с разных рынков: чтобы было видно, "
        "что это работает не в одной стране 👇"
    ),
    "drip_v2_2": (
        "Особенно в тему, если вы не в СНГ.\n\n"
        "Модель одна и та же — хоть из Берлина, хоть из Алматы, "
        "отличия мелкие. Сейчас покажу на примерах 👇"
    ),
    "drip_v3_1": (
        "Кстати, прежде чем смотреть форматы — у меня есть для вас "
        "калькулятор 💸\n\n"
        "Вводите свой бюджет — он считает, где вы можете быть через "
        "год, если начнёте Amazon сегодня. На вашем примере, не "
        "«средние цифры». Гляньте 👇"
    ),
    "drip_v3_2": (
        "Если Amazon ещё интересен — посчитайте на себя 🙂\n\n"
        "Калькулятор спрашивает, сколько готовы вложить и докупать "
        "каждый месяц, и показывает результат через год. Минута — и "
        "видно, ваше это или нет 👇"
    ),
    "drip_offer_1": (
        "Не торопитесь с решением — это нормально 🙂\n\n"
        "Если просто интересно, во сколько обходится старт — "
        "откройте «Форматы»: там цены и что входит, без "
        "обязательств. Посмотреть и закрыть — тоже нормально 👇"
    ),
    "drip_offer_2": (
        "Многие на этом месте сначала считают цифры под себя 💸\n\n"
        "В меню внизу есть калькулятор: вводите бюджет — покажет, "
        "как может расти прибыль со временем. Иногда именно цифры "
        "помогают понять, ваше это или нет 👇"
    ),
    "drip_lead_1": (
        "Скидку закрепил 👌 Если удобнее обсудить голосом или в "
        "личке — пишите напрямую.\n\n"
        "Разберём вашу ситуацию без шаблонных ответов 👇"
    ),
    "drip_lead_2": (
        "Таймер по скидке идёт.\n\n"
        "Если остались вопросы по формату или старту — лучше задать "
        "сейчас, пока −20% в силе 👇"
    ),
    "lm_offer": (
        "Перед стартом дам полезный материал 🎁\n\n"
        "📘 Это гайд по ошибкам, из-за которых новички чаще всего теряют "
        "деньги на Amazon.\n\n"
        "Внутри не просто «что не делать», а разбор:\n\n"
        "— ❌ как обычно ошибаются;\n"
        "— 💸 к чему это приводит;\n"
        "— ✅ как действовать правильно;\n"
        "— 🔍 что проверить до первой закупки.\n\n"
        "Заберите бесплатно 👇"
    ),
    "lm_subscribe": (
        "Отлично 🙌\n\n"
        "Подпишитесь на канал и нажмите «Я подписался» — гайд сразу "
        "придёт сюда.\n\n"
        "В канале также публикую разборы, примеры товаров и полезные "
        "заметки по Amazon."
    ),
    "lm_not_subscribed": (
        "Пока не вижу подписку 🤔\n\n"
        "Перейдите в канал, подпишитесь и нажмите «Я подписался» ещё раз."
    ),
    "lm_delivered": (
        "Готово, держите гайд 🎁\n\n"
        "Прочитайте перед первой закупкой — он может сэкономить вам "
        "деньги и нервы.\n\n"
        "Если захотите разобрать вашу ситуацию — нажмите кнопку ниже "
        "или «У меня есть вопросы» в меню 👇"
    ),
    "lm_skip": (
        "Без проблем 🙂\n\n"
        "Если позже захотите забрать гайд или задать вопрос — напишите мне."
    ),
    "lm_error": (
        "Не получилось проверить подписку. Возможно, канал ещё "
        "настраивается или бот не видит статус.\n\n"
        "Напишите мне лично — пришлю гайд вручную 👇"
    ),
    "promo_hot": (
        "Отлично 🙂\n\n"
        "Закрепляю для вас бонус на {hours} часов: скидка {discount}% "
        "на обучение.\n\n"
        "Нажмите кнопку — откроется страница со скидкой. В "
        "мини-приложении цены тоже обновятся на время бонуса.\n\n"
        "Кнопка ниже 👇"
    ),
    "promo_warm": (
        "Отлично 🙂\n\n"
        "Закрепляю для вас бонус на {hours} часов: скидка {discount}% "
        "на обучение.\n\n"
        "Нажмите кнопку — откроется страница со скидкой. В "
        "мини-приложении цены тоже обновятся на время бонуса.\n\n"
        "Кнопка ниже 👇"
    ),
    "promo_pinned": (
        "⏳ Ваш бонус активен: скидка {discount}% на обучение.\n"
        "Осталось: {left}\n\n"
        "Забрать можно в сообщении выше 👆"
    ),
    "promo_expired": (
        "⌛ Бонус по таймеру закончился.\n\n"
        "Но вы всё равно можете написать мне — посмотрим вашу ситуацию "
        "и подумаем, какой старт будет адекватным 👇"
    ),
    "promo_drip": (
        "⏳ Бонус ещё активен.\n\n"
        "Если хотите забрать скидку — кнопка выше 👆"
    ),
    "media_fail": (
        "Видео сейчас не открылось — техническая ошибка на стороне бота.\n\n"
        "Напишите мне лично — пришлю ролик или ссылку вручную 👇"
    ),
    "return_locked": (
        "Вы уже смотрели все материалы 🙂\n\n"
        "⏳ Персональная скидка была доступна 24 часа — сейчас действуют "
        "только стандартные цены.\n\n"
        "📋 Меню внизу — результаты, форматы, гайд и контакты."
    ),
    "resume_hi": (
        "С возвращением! Восстанавливаю переписку — продолжаем с того "
        "места, где остановились 👇"
    ),
}

# Напоминания о PDF-гайде в воронке (ротация, до GUIDE_TEASER_MAX раз).
GUIDE_TEASER_MAX = 5
GUIDE_TEASERS = [
    (
        "⚠️ Некоторые ошибки на Amazon стоят очень дорого. В конце вы получите "
        "бесплатный гайд с 3 ошибками, которые лучше узнать до первой закупки."
    ),
    (
        "💸 3 ошибки амазонщика — для кого-то это десятки тысяч долларов. "
        "🎁 Для вас в конце пути — бесплатно."
    ),
    (
        "🎁 Напоминаю: в конце — бесплатный PDF «3 ошибки новичка». "
        "Что проверить до первой закупки, чтобы не слить бюджет на старте."
    ),
]


# ──────────────────────────────────────────────────────────────────────
# 7) НАДПИСИ НА КНОПКАХ.
# ──────────────────────────────────────────────────────────────────────

BTN = {
    "start":      "Показать, с чего начать",
    "v1_watch":   "▶️ Включить видео (4 мин)",
    "v1_proofs":  "📸 Показать, что пошло не так",
    "to_v2":      "Откуда берётся прибыль",
    "v2_watch":   "▶️ Смотреть схему по шагам (6 мин)",
    "v2_proofs":  "🌍 Показать примеры по странам",
    "v3_yes":     "✅ Да, дальше",
    "v3_watch":   "▶️ Почему люди не начинают (7 мин)",
    "to_v3":      "▶️ Почему не начинают (~7 мин)",
    "to_v3_next": "➡️ Показать как",
    "show_formats": "➡️ Показать форматы",
    "to_fork":    "➡️ Дальше",
    "to_fork_how": "Хочу узнать как",
    "calc_open":  "💸 Узнать мою цифру за год",
    "calc_skip":  "Пропустить, к форматам →",
    "calc_to_fork": "➡️ Показать форматы",
    "students":   "Результаты учеников",
    "programs":   "💎 Открыть форматы и цены",
    "site":       "Открыть сайт с результатами",
    "results_open": "Открыть результаты на сайте",
    "about_open":   "Читать «Кто я»",
    "to_lead":    "🎁 Скидка −20% (24 ч)",
    "lm_get":     "📘 Забрать PDF-гайд",
    "lm_get_first": "📘 Сначала забрать PDF-гайд",
    "contact":    "Написать Вадиму",
    # лид-магнит
    "lm_grab":    "Забрать топ-3 ошибки (бесплатно)",
    "lm_want":    "Хочу забрать",
    "lm_skip":    "Пропустить",
    "lm_goto":    "Перейти в канал",
    "lm_check":   "Я подписался ✅",
    # промо
    "promo_get":  "🔥 Забрать скидку −20%",
    "promo_app":  "💎 Открыть программы со скидкой",
    "activate_bonus": "✅ Активировать",
}


# ╔══════════════════════════════════════════════════════════════════════╗
# ║                       К О Н Е Ц    C O N F I G                       ║
# ╚══════════════════════════════════════════════════════════════════════╝


logging.basicConfig(
    format="%(asctime)s %(levelname)s %(message)s", level=logging.INFO
)
log = logging.getLogger("amazon_bot")
# Убираем спам HTTP-запросов в логах (в их URL виден токен бота).
logging.getLogger("httpx").setLevel(logging.WARNING)
logging.getLogger("telegram").setLevel(logging.WARNING)
logging.getLogger("apscheduler").setLevel(logging.WARNING)

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.getenv("DATA_DIR", BASE_DIR)
os.makedirs(DATA_DIR, exist_ok=True)
STATE_FILE = os.path.join(DATA_DIR, "users.json")
STATE_BACKUP = STATE_FILE + ".bak"
GUIDE_PATH = os.path.join(BASE_DIR, GUIDE_FILENAME)

CHANNEL_LINK = "https://t.me/" + CHANNEL_USERNAME.lstrip("@")

_state_io_lock = threading.Lock()
_state_data_lock = threading.RLock()
_state_dirty = False
_user_locks = defaultdict(asyncio.Lock)
_user_funnel_locks = defaultdict(asyncio.Lock)
_media_send_sem = asyncio.Semaphore(int(os.getenv("MEDIA_SEND_PARALLEL", "8") or "8"))


def normalize_uid(uid):
    """Единый int id — ключи STATE и job_queue всегда через uid_str()."""
    if isinstance(uid, int):
        return uid
    s = str(uid).strip()
    if s.isdigit() or (s.startswith("-") and s[1:].isdigit()):
        return int(s)
    raise ValueError(f"invalid telegram uid: {uid!r}")


def uid_str(uid):
    return str(normalize_uid(uid))


def user_id_from(update):
    if update and update.effective_user:
        return normalize_uid(update.effective_user.id)
    raise ValueError("update without effective_user")


def load_state():
    for path in (STATE_FILE, STATE_BACKUP):
        if not os.path.exists(path):
            continue
        try:
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)
            if path != STATE_FILE:
                log.warning("users.json повреждён — восстановлен из .bak")
            return data
        except Exception as e:
            log.error("load_state %s failed: %s", path, e)
    return {}


def _flush_state_to_disk():
    """Атомарная запись на диск (снимок STATE под lock — без гонок)."""
    snapshot = None
    with _state_data_lock:
        keys = list(STATE.keys())
        snapshot = {}
        for k in keys:
            for _ in range(4):
                try:
                    snapshot[k] = json.loads(
                        json.dumps(STATE.get(k, {}), ensure_ascii=False),
                    )
                    break
                except (RuntimeError, ValueError, TypeError):
                    time.sleep(0.002)
            else:
                snapshot[k] = dict(STATE.get(k, {}) or {})
    with _state_io_lock:
        try:
            tmp = STATE_FILE + ".tmp"
            with open(tmp, "w", encoding="utf-8") as f:
                json.dump(snapshot, f, ensure_ascii=False, indent=2)
            os.replace(tmp, STATE_FILE)
            try:
                with open(STATE_BACKUP, "w", encoding="utf-8") as f:
                    json.dump(snapshot, f, ensure_ascii=False, indent=2)
            except Exception:
                pass
        except Exception as e:
            log.error("save_state failed: %s", e)
            raise


def save_state(state):
    """Пометить state «грязным» — запись на диск в фоне, без блокировки бота."""
    global _state_dirty
    _state_dirty = True


async def _state_flush_loop():
    """Периодически сливает STATE на диск в отдельном потоке."""
    global _state_dirty
    while True:
        await asyncio.sleep(0.08)
        if not _state_dirty:
            continue
        while _state_dirty:
            _state_dirty = False
            try:
                await asyncio.to_thread(_flush_state_to_disk)
            except Exception:
                _state_dirty = True
                await asyncio.sleep(0.5)


async def flush_state_now():
    """Немедленно сохранить (перед выключением)."""
    global _state_dirty
    if not _state_dirty:
        return
    _state_dirty = False
    await asyncio.to_thread(_flush_state_to_disk)


STATE = load_state()


def _now():
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def u(uid):
    key = uid_str(uid)
    with _state_data_lock:
        if key not in STATE:
            STATE[key] = {"step": "start", "answers": {}, "joined": _now()}
        return STATE[key]


def set_step(uid, step):
    with _state_data_lock:
        rec = u(uid)
        rec["step"] = step
        rec["step_at"] = _now()
    save_state(STATE)


# ── Воронка: UTM, этапы, возврат, один проход ─────────────────────────
ADMIN_USERNAME = "vadjik"
_replaying_users = set()

UTM_NAMES = {
    "tg": "Telegram", "you": "YouTube", "inst": "Instagram",
    "tik": "TikTok", "fb": "Facebook",
}

RU_MONTHS = (
    "", "Январь", "Февраль", "Март", "Апрель", "Май", "Июнь",
    "Июль", "Август", "Сентябрь", "Октябрь", "Ноябрь", "Декабрь",
)

REPORT_HEADERS = (
    "telegram_id", "username", "имя", "utm", "откуда",
    "остановился_на", "дата_остановки", "шаг_код",
    "мини_апп", "мини_апп_когда",
    "забрал_гайд", "бонус_забрал", "бонус_активен", "заблокирован",
    "вошёл", "температура", "статус",
)

MILESTONE_LABELS = {
    "start": "Старт — приветствие",
    "circle_intro": "1-й кружок «Кто я»",
    "after_circle_intro": "Сообщение после 1-го кружка",
    "before_v1": "Перед видео 1 (Игорь)",
    "video_1": "Видео 1 — история Игоря",
    "after_v1_video": "1-е сообщение после видео 1",
    "proofs_v1": "Скрины после видео 1",
    "proofs_v1_caption": "Подпись к скринам после видео 1",
    "after_v1_proofs": "2-е сообщение после видео 1",
    "bridge_v2": "Перед видео 2 — схема",
    "video_2": "Видео 2 — схема по шагам",
    "after_v2_video": "1-е сообщение после видео 2",
    "proofs_v2": "Скрины после видео 2",
    "proofs_v2_caption": "2-е сообщение после видео 2",
    "after_v2": "3-е сообщение после видео 2 — почему не начинают",
    "v3_loading": "Загрузка видео 3",
    "video_3": "Видео 3 — почему не начинают",
    "after_v3_video": "1-е сообщение после видео 3",
    "after_v3": "2-е сообщение после видео 3",
    "circle_fork": "2-й кружок — развилка",
    "after_fork": "Меню внизу — оффер",
    "lm_offer": "Предложение PDF-гайда",
    "qualified": "Забрал бонус −20%",
    "return_locked": "Вернулся — бонус уже закончился",
}

MEDIA_MILESTONE = {
    "circle_intro": "circle_intro",
    "video_1": "video_1",
    "video_2": "video_2",
    "video_3": "video_3",
    "circle_fork": "circle_fork",
}


def parse_utm(args):
    if not args:
        return ""
    raw = (args[0] or "").strip().lower()
    if raw.startswith("utm_"):
        raw = raw[4:]
    return re.sub(r"[^a-z0-9_]", "", raw)[:32]


def utm_display(code):
    if not code:
        return "прямой / без метки"
    return UTM_NAMES.get(code, code)


def webapp_report_label(rec):
    """Открыл ли Mini App (любое время — не путать с 30 с для оплаты)."""
    return "да" if rec.get("webapp_opened") else "нет"


def webapp_report_when(rec):
    return rec.get("webapp_opened_at") or ""


def parse_joined_dt(rec):
    s = (rec.get("joined") or "").strip()
    if not s:
        return None
    for fmt in ("%Y-%m-%d %H:%M:%S", "%Y-%m-%d"):
        try:
            return datetime.strptime(s, fmt)
        except ValueError:
            continue
    return None


def lead_report_row(uid, rec, now=None):
    if now is None:
        now = time.time()
    promo = rec.get("promo") or {}
    dl = promo.get("deadline", 0)
    bonus_active = bool(dl and dl > now)
    return [
        uid,
        rec.get("username", ""),
        rec.get("full_name", ""),
        rec.get("utm", ""),
        utm_display(rec.get("utm", "")),
        rec.get("milestone_label", rec.get("step", "")),
        rec.get("milestone_at", rec.get("step_at", "")),
        rec.get("milestone", rec.get("step", "")),
        webapp_report_label(rec),
        webapp_report_when(rec),
        "да" if rec.get("got_guide") else "",
        "да" if rec.get("bonus_claimed") else "",
        "да" if bonus_active else "",
        "да" if is_funnel_locked(rec) else "",
        rec.get("joined", ""),
        rec.get("temperature", ""),
        rec.get("outcome", ""),
    ]


def collect_leads(since=None, until=None):
    """Лиды по дате первого входа (поле joined). since/until — naive local."""
    items = []
    for uid, rec in STATE.items():
        j = parse_joined_dt(rec)
        if since and (not j or j < since):
            continue
        if until and (not j or j >= until):
            continue
        items.append((uid, rec))
    items.sort(
        key=lambda pair: parse_joined_dt(pair[1]) or datetime.min,
        reverse=True,
    )
    return items


def _safe_sheet_title(name):
    for ch in (":", "\\", "/", "?", "*", "[", "]"):
        name = name.replace(ch, " ")
    return (name or "Лист")[:31]


def build_report_sections(leads, include_all_sheet=True):
    """Листы Excel: «Все лиды» + по месяцам входа."""
    now = time.time()
    all_rows = []
    by_month = defaultdict(list)
    undated = []

    for uid, rec in leads:
        row = lead_report_row(uid, rec, now)
        all_rows.append(row)
        j = parse_joined_dt(rec)
        if j:
            by_month[(j.year, j.month)].append(row)
        else:
            undated.append(row)

    sections = []
    if include_all_sheet:
        sections.append(("Все лиды", all_rows))
    for ym in sorted(by_month.keys()):
        y, m = ym
        sections.append((f"{RU_MONTHS[m]} {y}", by_month[ym]))
    if undated:
        sections.append(("Без даты", undated))
    return sections


def build_report_xlsx(sections):
    from openpyxl import Workbook

    wb = Workbook()
    first = True
    for title, rows in sections:
        st = _safe_sheet_title(title)
        if first:
            ws = wb.active
            ws.title = st
            first = False
        else:
            ws = wb.create_sheet(st)
        ws.append(list(REPORT_HEADERS))
        for row in rows:
            ws.append(row)
    import io
    bio = io.BytesIO()
    wb.save(bio)
    bio.seek(0)
    return bio


def build_report_csv(rows):
    import csv
    import io
    buf = io.StringIO()
    w = csv.writer(buf)
    w.writerow(list(REPORT_HEADERS))
    for row in rows:
        w.writerow(row)
    data = buf.getvalue().encode("utf-8-sig")
    import io as _io
    bio = _io.BytesIO(data)
    bio.seek(0)
    return bio


async def send_report_file(bot, sections, filename, caption):
    try:
        bio = build_report_xlsx(sections)
        ext = "xlsx"
    except ImportError:
        log.warning("openpyxl не установлен — отчёт в CSV")
        rows = sections[0][1] if sections else []
        bio = build_report_csv(rows)
        ext = "csv"
    bio.name = f"{filename}.{ext}"
    await bot.send_document(ADMIN_ID, bio, caption=caption)


async def deliver_period_report(bot, title, since=None, until=None):
    leads = collect_leads(since=since, until=until)
    period_slug = datetime.now(REPORT_TZ).strftime("%Y%m%d")
    if not leads:
        await bot.send_message(
            ADMIN_ID,
            f"📊 {title}\n\nНовых лидов за период нет.",
        )
        return
    sections = build_report_sections(leads, include_all_sheet=True)
    n = len(leads)
    await send_report_file(
        bot, sections, f"leads_{period_slug}",
        f"📊 {title}\n{n} лид(ов). Листы: все + по месяцам входа.",
    )


async def job_report_daily(context):
    if not REPORT_AUTO_ENABLED or not ADMIN_ID:
        return
    now = datetime.now(REPORT_TZ).replace(tzinfo=None)
    since = now - timedelta(hours=24)
    try:
        await deliver_period_report(
            context.bot, "Автоотчёт за 24 часа", since=since,
        )
    except Exception as e:
        log.error("job_report_daily: %s", e)


async def job_report_weekly(context):
    if not REPORT_AUTO_ENABLED or not ADMIN_ID:
        return
    now = datetime.now(REPORT_TZ).replace(tzinfo=None)
    since = now - timedelta(days=7)
    try:
        await deliver_period_report(
            context.bot, "Автоотчёт за 7 дней", since=since,
        )
    except Exception as e:
        log.error("job_report_weekly: %s", e)


async def job_report_monthly(context):
    if not REPORT_AUTO_ENABLED or not ADMIN_ID:
        return
    now = datetime.now(REPORT_TZ)
    if now.day != 1:
        return
    first_this = now.replace(
        day=1, hour=0, minute=0, second=0, microsecond=0,
    ).replace(tzinfo=None)
    last_prev = first_this - timedelta(days=1)
    since = last_prev.replace(day=1)
    until = first_this
    label = f"Автоотчёт за {RU_MONTHS[last_prev.month]} {last_prev.year}"
    try:
        await deliver_period_report(
            context.bot, label, since=since, until=until,
        )
    except Exception as e:
        log.error("job_report_monthly: %s", e)


def setup_auto_reports(application):
    if not REPORT_AUTO_ENABLED or not ADMIN_ID:
        return
    jq = application.job_queue
    if not jq:
        log.warning("job_queue недоступен — автоотчёты отключены")
        return
    tz = REPORT_TZ
    jq.run_daily(
        job_report_daily,
        time=dt_time(9, 0, tzinfo=tz),
        name="auto_report_24h",
    )
    jq.run_daily(
        job_report_weekly,
        time=dt_time(9, 5, tzinfo=tz),
        days=(0,),
        name="auto_report_7d",
    )
    jq.run_daily(
        job_report_monthly,
        time=dt_time(9, 10, tzinfo=tz),
        name="auto_report_month",
    )
    log.info(
        "Автоотчёты: 09:00 — 24ч, пн 09:05 — 7д, 1-е число 09:10 — прошлый месяц (%s)",
        tz,
    )


def is_bot_admin(user):
    """Системные команды — только @vadjik (и ADMIN_ID)."""
    if not user:
        return False
    if user.id == ADMIN_ID:
        return True
    uname = (user.username or "").lower().lstrip("@")
    return uname == ADMIN_USERNAME.lower()


def is_exempt_user(user):
    return is_bot_admin(user)


def user_fast_mode(uid):
    return bool(u(str(uid)).get("fast_mode"))


def user_pauses_off(uid):
    return bool(u(str(uid)).get("pauses_off"))


def pauses_enabled_for(uid):
    if user_pauses_off(uid):
        return False
    return PAUSES_ON


def normalize_username(name):
    return (name or "").strip().lstrip("@").lower()


def find_uid_by_username(username):
    needle = normalize_username(username)
    if not needle:
        return None
    for uid, rec in STATE.items():
        if normalize_username(rec.get("username")) == needle:
            return int(uid) if str(uid).isdigit() else uid
    return None


def set_user_fast_mode(uid, enabled):
    rec = u(uid)
    rec["fast_mode"] = bool(enabled)
    if enabled:
        rec["pauses_off"] = False
    save_state(STATE)


def is_funnel_locked(rec):
    if rec.get("funnel_locked"):
        return True
    if not rec.get("bonus_claimed"):
        return False
    promo = rec.get("promo") or {}
    dl = promo.get("deadline", 0)
    return dl > 0 and time.time() >= dl


def track_milestone(uid, key):
    if uid in _replaying_users:
        return
    rec = u(uid)
    rec["milestone"] = key
    rec["milestone_label"] = MILESTONE_LABELS.get(key, key)
    rec["milestone_at"] = _now()
    save_state(STATE)


def push_history(uid, entry):
    if uid in _replaying_users:
        return
    rec = u(uid)
    if is_funnel_locked(rec):
        return
    hist = rec.setdefault("history", [])
    entry["_ts"] = _now()
    hist.append(entry)
    if len(hist) > 50:
        del hist[0]
    save_state(STATE)


def _serialize_rows(rows):
    if not rows:
        return None
    out = []
    for row in rows:
        if isinstance(row, list):
            out.append([[t, d, k] for t, d, k in row])
        else:
            t, d, k = row
            out.append([t, d, k])
    return out


def _deserialize_rows(stored):
    if not stored:
        return None
    res = []
    for row in stored:
        if row and isinstance(row[0], list):
            res.append([tuple(x) for x in row])
        else:
            res.append(tuple(row))
    return res


async def _emit_history_item(bot, uid, item, with_buttons=False):
    kind = item.get("t")
    if kind == "text":
        rows = _deserialize_rows(item.get("rows")) if with_buttons else None
        markup = kb(rows) if rows else None
        msg = await bot.send_message(uid, item["body"], reply_markup=markup)
        if with_buttons and rows:
            rec = u(uid)
            rec["last_kb_msg"] = msg.message_id
            set_active_callbacks(uid, rows)
            save_state(STATE)
    elif kind == "circle":
        await send_circle(bot, uid, item["k"], log=False)
    elif kind == "video":
        await send_media_file(bot, uid, item["k"], log=False)
    elif kind == "proofs":
        proofs = PROOFS_AFTER_V1 if item.get("p") == "v1" else PROOFS_AFTER_V2
        cap = TXT.get(item.get("cap", ""), "") or None
        await send_proofs(bot, uid, proofs, cap, log=False)
    elif kind == "menu":
        await bot.send_message(uid, item["body"], reply_markup=main_reply_keyboard())


async def replay_user_history(bot, uid):
    hist = u(uid).get("history") or []
    if not hist:
        return
    _replaying_users.add(uid)
    try:
        for item in hist[:-1]:
            await _emit_history_item(bot, uid, item, with_buttons=False)
            await asyncio.sleep(0.35)
        if hist:
            await _emit_history_item(bot, uid, hist[-1], with_buttons=True)
    finally:
        _replaying_users.discard(uid)


def _mk_btn(text, data, kind):
    """kind: False=callback, True/'url'=ссылка, 'webapp'=Mini App."""
    if kind == "webapp":
        return InlineKeyboardButton(text, web_app=WebAppInfo(url=data))
    if kind is True or kind == "url":
        return InlineKeyboardButton(text, url=data)
    return InlineKeyboardButton(text, callback_data=data)


def kb(rows):
    """Inline-клавиатура. Строка = (text, data, kind) или список таких."""
    buttons = []
    for row in rows:
        if isinstance(row, list):
            buttons.append([_mk_btn(t, d, k) for (t, d, k) in row])
        else:
            t, d, k = row
            buttons.append([_mk_btn(t, d, k)])
    return InlineKeyboardMarkup(buttons)


def append_questions_hint(uid, text):
    if u(uid).get("step") in QUESTIONS_STEPS:
        return text + QUESTIONS_HINT
    return text


def callback_ids_from_rows(rows):
    """Callback_data из inline-кнопок (только callback, не url/webapp)."""
    if not rows:
        return []
    out = []
    for row in rows:
        items = [row] if (
            isinstance(row, (list, tuple))
            and len(row) == 3
            and isinstance(row[0], str)
        ) else row
        for t, d, k in items:
            if k is False:
                out.append(d)
    return out


def invalidate_active_callbacks(uid):
    rec = u(uid)
    rec["active_callbacks"] = []
    save_state(STATE)


def set_active_callbacks(uid, rows):
    rec = u(uid)
    rec["active_callbacks"] = callback_ids_from_rows(rows)
    save_state(STATE)


def append_guide_teaser(uid, text):
    """Добавляет напоминание о PDF-гайде (до 5 раз на пользователя)."""
    rec = u(uid)
    if rec.get("got_guide"):
        return text
    step = rec.get("step", "")
    if step in ("lead", "qualified", "qualified_cold", "fork", "offer"):
        return text
    i = rec.get("guide_teaser_i", 0)
    if i >= GUIDE_TEASER_MAX:
        return text
    rec["guide_teaser_i"] = i + 1
    save_state(STATE)
    return f"{text}\n\n{GUIDE_TEASERS[i % len(GUIDE_TEASERS)]}"


async def send_step(bot, uid, text, rows=None, skip_pause=False,
                    guide_teaser=False, questions_hint=False,
                    skip_questions_hint=False, milestone=None, **kwargs):
    """Отправляет сообщение. Кнопки старых сообщений остаются на экране,
    но работает только последний набор callback-кнопок."""
    if guide_teaser:
        text = append_guide_teaser(uid, text)
    if not skip_questions_hint and (
        questions_hint or u(uid).get("step") in QUESTIONS_STEPS
    ):
        text = append_questions_hint(uid, text)
    if milestone:
        track_milestone(uid, milestone)
    rec = u(uid)
    invalidate_active_callbacks(uid)
    markup = kb(rows) if rows else None
    if not skip_pause:
        await pause_text(bot, uid)
    msg = await bot.send_message(normalize_uid(uid), text, reply_markup=markup, **kwargs)
    if rows:
        rec["last_kb_msg"] = msg.message_id
        set_active_callbacks(uid, rows)
    save_state(STATE)
    if uid not in _replaying_users and not is_funnel_locked(rec):
        push_history(uid, {
            "t": "text",
            "body": text,
            "rows": _serialize_rows(rows),
        })
    return msg


# ---------------- ПАУЗЫ МЕЖДУ СООБЩЕНИЯМИ ----------------
#   кружок/видео → текст: MEDIA_TO_TEXT_PAUSE_SEC (40 с)
#   текст → текст: 5–10 с (по длине)
# Выключить: PAUSES=0  |  /pauses  |  /fast — без пауз на медиа

PAUSES_ON = os.getenv("PAUSES", "1").strip().lower() not in ("0", "false", "no", "")
CIRCLE_PAUSE_SEC = float(os.getenv("CIRCLE_PAUSE", "40") or "40")
MEDIA_TO_TEXT_PAUSE_SEC = float(os.getenv("MEDIA_TO_TEXT_PAUSE", "40") or "40")
TEXT_PAUSE_SEC = float(os.getenv("TEXT_PAUSE", "3") or "3")

READ_WPM = int(os.getenv("READ_WPM", "220") or "220")
MIN_TEXT_PAUSE = float(os.getenv("MIN_TEXT_PAUSE", "2") or "2")
MAX_TEXT_PAUSE = float(os.getenv("MAX_TEXT_PAUSE", "10") or "10")
SHORT_TEXT_WORDS = int(os.getenv("SHORT_TEXT_WORDS", "55") or "55")
SHORT_TEXT_MAX_PAUSE = float(os.getenv("SHORT_TEXT_MAX_PAUSE", "3") or "3")


def read_time(text):
    """Сколько секунд человеку нужно, чтобы прочитать этот текст.
    Короткий текст (2–3 строки) → до SHORT_TEXT_MAX_PAUSE (≈3 с).
    Длинный текст → длинная пауза (но не больше MAX_TEXT_PAUSE)."""
    if not text:
        return TEXT_PAUSE_SEC
    words = max(1, len(text.split()))
    t = words / READ_WPM * 60
    cap = SHORT_TEXT_MAX_PAUSE if words <= SHORT_TEXT_WORDS else MAX_TEXT_PAUSE
    return max(MIN_TEXT_PAUSE, min(t, cap))


async def pause_text(bot, chat_id, text=None):
    """Пауза перед текстом: «печатает» + время на чтение ПРЕДЫДУЩЕГО.
    Если text задан — пауза по его длине (умно). Иначе — фикс TEXT_PAUSE_SEC."""
    if not pauses_enabled_for(chat_id):
        return
    try:
        await bot.send_chat_action(chat_id, ChatAction.TYPING)
    except Exception:
        pass
    await asyncio.sleep(read_time(text) if text else TEXT_PAUSE_SEC)


async def pause_after_circle(bot, chat_id):
    """После кружка — дать досмотреть, затем следующий текст.
    /fast у админа — без паузы только для его chat_id."""
    if not pauses_enabled_for(chat_id) or user_fast_mode(chat_id):
        return
    try:
        await bot.send_chat_action(chat_id, ChatAction.TYPING)
    except Exception:
        pass
    await asyncio.sleep(CIRCLE_PAUSE_SEC)


def media_sec(key):
    return int(MEDIA.get(key, {}).get("sec", 0) or 0)


def video_pause_sec(key=None):
    """Пауза после видео перед текстом — фиксированно 40 с."""
    return MEDIA_TO_TEXT_PAUSE_SEC


async def pause_after_video(bot, chat_id, key=None):
    """После видео — дать досмотреть. /fast — без паузы только у кто включил."""
    if not pauses_enabled_for(chat_id) or user_fast_mode(chat_id):
        return
    try:
        await bot.send_chat_action(chat_id, ChatAction.RECORD_VIDEO)
    except Exception:
        pass
    await asyncio.sleep(video_pause_sec(key))


def funnel_pause_sec(uid, default_sec):
    """Длительность паузы воронки для пользователя (0 ≈ сразу при /fast)."""
    if not pauses_enabled_for(uid) or user_fast_mode(uid):
        return 0.05
    return default_sec


def cancel_funnel_pause_jobs(app, uid):
    """Отменить отложенные шаги воронки (не трогает drip/промо)."""
    if not app or not app.job_queue:
        return
    uid_i = normalize_uid(uid)
    prefix = f"funnel_{uid_i}_pause_"
    for job in app.job_queue.jobs():
        if job.name and job.name.startswith(prefix):
            job.schedule_removal()


def schedule_funnel_pause(app, uid, delay_sec, callback, tag, extra=None):
    """Отложить следующий шаг воронки — обработчик кнопки освобождается сразу."""
    if not app or not app.job_queue:
        log.warning("job_queue недоступен — пауза %ss для uid=%s inline", delay_sec, uid)
        return
    uid_i = normalize_uid(uid)
    cancel_funnel_pause_jobs(app, uid_i)
    app.job_queue.run_once(
        callback,
        when=max(0.05, delay_sec),
        name=f"funnel_{uid_i}_pause_{tag}",
        data={"uid": uid_i, **(extra or {})},
    )


async def safe_answer_callback(q, data=""):
    """Ответ на inline-кнопку — не падаем, если запрос уже протух."""
    try:
        if data == "go_intro":
            await q.answer("Загружаю приветствие…", show_alert=False)
        elif data in ("go_v1_play", "go_v2_video", "go_v3_video", "go_v3_prep"):
            await q.answer("Загружаю видео…", show_alert=False)
        elif data == "lm_check":
            await q.answer("Проверяю подписку…", show_alert=False)
        else:
            await q.answer()
    except BadRequest as e:
        msg = str(e).lower()
        if "too old" in msg or "query id is invalid" in msg:
            log.debug("callback протух (старая кнопка или бот долго не отвечал): %s", data)
        else:
            log.warning("callback answer: %s", e)
    except TimedOut:
        log.debug("callback answer timeout: %s", data)


async def run_funnel_step(handler, update, context):
    """Шаг воронки — один пользователь = одна цепочка, без перемешивания."""
    uid = user_id_from(update)
    q = update.callback_query
    action = (q.data if q else None) or getattr(handler, "__name__", "?")
    uid_s = uid_str(uid)

    async with _user_funnel_locks[uid_s]:
        rec = u(uid)
        claims = rec.setdefault("funnel_claims", [])
        if action in claims and action not in FUNNEL_REPEAT_ACTIONS:
            log.info("повторный клик: uid=%s action=%s", uid, action)
            if q:
                try:
                    await q.answer(
                        "Уже обрабатываю — подождите секунду…",
                        show_alert=False,
                    )
                except Exception:
                    pass
            return
        if action not in claims:
            claims.append(action)
        if len(claims) > 80:
            rec["funnel_claims"] = claims[-40:]
        invalidate_active_callbacks(uid)
        save_state(STATE)
        await clear_nudge(context.bot, uid)
        try:
            await handler(update, context)
        except Exception:
            log.exception("funnel step %s failed uid=%s", action, uid)
            if action in claims:
                claims.remove(action)
            save_state(STATE)


async def run_uid_job(context, fn):
    """Отложенный шаг воронки — uid из job.data, блокировка per-user."""
    uid = normalize_uid(context.job.data["uid"])
    async with _user_funnel_locks[uid_str(uid)]:
        await fn(uid, context)


async def send_text(bot, chat_id, text, **kwargs):
    """Текстовое сообщение с паузой по длине ТЕКСТА — больше текст,
    дольше пауза, чтобы человек успел прочитать предыдущее сообщение."""
    await pause_text(bot, chat_id, text=text)
    return await bot.send_message(chat_id, text, **kwargs)


def bot_username_slug():
    return BOT_LINK.rstrip("/").split("/")[-1]


def howmany_webapp_url():
    """HTTPS-адрес калькулятора + contact и img1…img4 для скринов в аппке."""
    url = (HOWMANY_URL or "").strip()
    if not url:
        return ""
    if not url.startswith("http"):
        url = "https://" + url
    url = url.rstrip("/")
    last = url.rsplit("/", 1)[-1]
    if "." not in last:
        url = url + "/amazon-calc.html"
    extra = [f"contact={quote(CALL_LINK, safe='')}"]
    for i, img in enumerate(HOWMANY_IMG_URLS, 1):
        if img:
            extra.append(f"img{i}={quote(img, safe='')}")
    sep = "&" if "?" in url else "?"
    url += sep + "&".join(extra)
    return url


async def refresh_howmany_img_urls(bot):
    """file_id → HTTPS-URL для <img> в amazon-calc.html (кэш при старте)."""
    global HOWMANY_IMG_URLS
    base = f"https://api.telegram.org/file/bot{BOT_TOKEN}/"
    out = []
    for item in HOWMANY_SCREENS:
        fid = item.get("file_id")
        if not fid:
            out.append("")
            continue
        try:
            f = await bot.get_file(fid)
            out.append(base + f.file_path)
        except Exception as e:
            log.error("howmany img %s: %s", fid[:20], e)
            out.append("")
    HOWMANY_IMG_URLS = out
    ok = sum(1 for u in out if u)
    log.info("HOWMANY скрины в аппке: %s/4 URL готовы", ok)


def _webapp_promo_query(uid):
    """Параметры активной скидки для URL Mini App (один аккаунт — все устройства)."""
    if not PROMO_SECRET:
        return ""
    rec = u(uid)
    promo = rec.get("promo") or {}
    deadline = promo.get("deadline", 0)
    link = promo.get("link") or ""
    if deadline <= time.time() or not link:
        return ""
    sig = promo_sig(uid, deadline)
    return (
        f"&uid={uid}&deadline={deadline}&sig={sig}"
        f"&disc={PROMO_DISCOUNT}"
        f"&discount={quote(link, safe='')}"
    )


def refresh_flow_cache_sync():
    """Кэш даты потока с vadjik.com (для подписи кнопок и URL аппки)."""
    try:
        req = urllib.request.Request(
            APP_DATA_API,
            headers={"X-API-Key": APP_DATA_API_KEY},
        )
        with urllib.request.urlopen(req, timeout=12) as resp:
            data = json.loads(resp.read().decode("utf-8"))
        _FLOW_CACHE["flow_date"] = data.get("flow_date")
        _FLOW_CACHE["flow_time"] = data.get("flow_time") or "19:00"
        _FLOW_CACHE["fetched_at"] = time.time()
        log.info(
            "flow cache: %s %s",
            _FLOW_CACHE["flow_date"], _FLOW_CACHE["flow_time"],
        )
    except Exception as e:
        log.warning("flow cache fetch: %s", e)


def flow_date_short():
    """«26 июл» для подписи кнопки."""
    iso = _FLOW_CACHE.get("flow_date")
    if not iso:
        return None
    try:
        y, m, d = iso.split("-")
        mi = int(m) - 1
        if 0 <= mi < 12:
            return f"{int(d)} {_FLOW_MONTHS[mi]}"
    except (ValueError, TypeError):
        pass
    return iso


def formats_menu_label(uid=None):
    """Подпись кнопки «Форматы» — со скидкой после закрепления бонуса."""
    if uid is not None and user_uses_discount_pay(uid):
        return BTN["promo_app"]
    return MENU_FORMATS


def is_menu_formats_text(text):
    if text == MENU_FORMATS:
        return True
    return bool(text and text.startswith(BTN["promo_app"]))


def webapp_url_full(uid=None, app_reset=False):
    """URL Mini App с подставленными ссылками contact/site."""
    if not WEBAPP_URL:
        return ""
    url = (f"{WEBAPP_URL}?contact={quote(CALL_LINK, safe='')}"
           f"&site={quote(SITE_LINK, safe='')}"
           f"&results={quote(RESULTS_LINK, safe='')}"
           f"&bot={quote(bot_username_slug())}"
           f"&appv={WEBAPP_BUILD}")
    if HOWMANY_URL:
        url += f"&howmany={quote(howmany_webapp_url(), safe='')}"
    fd = _FLOW_CACHE.get("flow_date")
    if fd:
        url += f"&flowdate={quote(fd, safe='')}"
        url += f"&flowtime={quote(_FLOW_CACHE.get('flow_time') or '19:00', safe='')}"
    if app_reset:
        url += "&reset=1"
        url += f"&_={int(time.time())}"
    elif uid is not None:
        uid_s = uid_str(uid)
        if is_funnel_locked(u(uid)):
            url += "&locked=1"
        else:
            url += _webapp_promo_query(uid)
        if f"uid={uid_s}" not in url:
            url += f"&uid={uid_s}"
        url += "&wa=1"
    return url


def programs_btn(uid=None):
    """Кнопка Mini App или fallback на текстовый показ программ."""
    if WEBAPP_URL:
        label = formats_menu_label(uid) if uid is not None else BTN["programs"]
        return (label, webapp_url_full(uid), "webapp")
    return (BTN["programs"], "go_programs", False)


def user_uses_discount_pay(uid):
    """Ссылки /discount/* — если уже закрепил бонус (−20%)."""
    rec = u(uid)
    if rec.get("bonus_claimed"):
        return True
    promo = rec.get("promo") or {}
    return bool(promo.get("deadline", 0) > time.time())


def tariff_pay_url(slug, uid):
    if user_uses_discount_pay(uid):
        return f"{SITE_PAY_ORIGIN}/discount/{slug}"
    return f"{SITE_PAY_ORIGIN}/{slug}"


def should_show_pay_row(uid):
    rec = u(uid)
    return rec.get("step") in OFFER_STEPS


def pay_keyboard_rows(uid):
    """Одна кнопка на сайт — только если человек уже забрал бонус."""
    if not should_show_pay_row(uid):
        return []
    if not user_uses_discount_pay(uid):
        return []
    rec = u(uid)
    link = (rec.get("promo") or {}).get("link") or ""
    if not link:
        return []
    return [[KeyboardButton(
        f"💳 Оформить на сайте (−{PROMO_DISCOUNT}%)",
        api_kwargs={"url": link},
    )]]


async def refresh_main_keyboard(bot, uid, hint=None, app_reset=False):
    """Обновить нижнее меню (например, после 30 с в Mini App)."""
    text = hint or "👇"
    try:
        await bot.send_message(
            uid, text, reply_markup=main_reply_keyboard(uid, app_reset=app_reset),
        )
    except Exception as e:
        log.error("refresh_main_keyboard failed: %s", e)
        try:
            await bot.send_message(
                uid, text,
                reply_markup=main_reply_keyboard_fallback(uid, app_reset=app_reset),
            )
        except Exception as e2:
            log.error("refresh_main_keyboard fallback failed: %s", e2)


def main_reply_keyboard_fallback(uid=None, app_reset=False):
    """Меню без WebApp/url — если клиент не принял полную клавиатуру."""
    fmt = MENU_FORMATS if app_reset else (
        formats_menu_label(uid) if uid is not None else MENU_FORMATS
    )
    rows = [
        [KeyboardButton(MENU_EARN), KeyboardButton(fmt)],
        [KeyboardButton(MENU_RESULTS), KeyboardButton(MENU_GUIDE)],
        [KeyboardButton(MENU_ABOUT), KeyboardButton(MENU_QUESTIONS)],
    ]
    if uid is not None and not app_reset:
        rows.extend(pay_keyboard_rows(uid))
    return ReplyKeyboardMarkup(
        rows, resize_keyboard=True, is_persistent=True,
    )


async def _delete_promo_chat_messages(bot, uid, rec):
    """Удалить промо-сообщения и pin без funnel_locked (для /clean)."""
    promo = rec.get("promo") or {}
    pin_id = promo.get("pin_msg_id")
    for mid in {promo.get("main_msg_id"), promo.get("remind_msg_id"), pin_id}:
        if mid:
            try:
                await bot.delete_message(uid, mid)
            except Exception:
                pass
    if pin_id:
        try:
            await bot.unpin_chat_message(uid, pin_id)
        except Exception:
            pass


async def full_reset_user_for_test(bot, uid, application):
    """Полный сброс: state, таймеры, меню без скидки, reset=1 в URL аппки."""
    uid_s = str(uid)
    rec = STATE.get(uid_s) or {}
    await _delete_promo_chat_messages(bot, uid, rec)
    cancel_drips(application, uid)
    cancel_promo_jobs(application, uid)
    cancel_bonus_reminds(application, uid)
    cancel_funnel_pause_jobs(application, uid)
    if uid_s in STATE:
        del STATE[uid_s]
    save_state(STATE)
    await refresh_main_keyboard(
        bot, uid,
        f"🧹 Сброшено. «{MENU_FORMATS}» — обычные цены.\n"
        f"Откройте кнопку заново — localStorage аппки тоже очистится.",
        app_reset=True,
    )


async def mark_webapp_opened(bot, uid, app=None):
    """Фиксация: человек открыл Mini App (для отчёта по воронке)."""
    rec = u(uid)
    if not rec.get("webapp_opened"):
        rec["webapp_opened"] = True
        rec["webapp_opened_at"] = _now()
        save_state(STATE)
    if app and rec.get("step") in OFFER_STEPS:
        schedule_bonus_remind(app, uid)


async def handle_webapp_ready(bot, uid, app=None):
    """30+ сек в аппке — только тихая фиксация для отчёта, без сообщений."""
    rec = u(uid)
    if rec.get("step") not in OFFER_STEPS:
        return
    await mark_webapp_opened(bot, uid, app)
    if rec.get("webapp_engaged"):
        return
    rec["webapp_engaged"] = True
    rec["webapp_engaged_at"] = _now()
    save_state(STATE)


async def activate_bonus(update, context):
    """Активировать бонус после 30 с в аппке — как claim_promo в Mini App."""
    q = update.callback_query
    asyncio.create_task(safe_answer_callback(q, "activate_bonus"))
    uid = update.effective_user.id
    user = update.effective_user
    rec = u(uid)
    if is_funnel_locked(rec) and not is_exempt_user(user):
        await send_with_main_menu(context.bot, uid, TXT["return_locked"])
        return
    promo = rec.get("promo") or {}
    if promo.get("deadline", 0) > time.time():
        await context.bot.send_message(
            uid,
            "Бонус уже активен 👇 Откройте «Форматы сотрудничества» — "
            "цены уже со скидкой.",
        )
        return
    if not PROMO_SECRET:
        await send_step(
            context.bot, uid,
            "Скидка пока настраивается. Напишите мне 👇",
            [(BTN["contact"], CALL_LINK, True)],
        )
        return
    if not rec.get("temperature"):
        rec["temperature"] = "warm"
    save_state(STATE)
    await show_promo(context, uid, user, rec.get("temperature", "warm"))


def fork_inline_rows(uid):
    """Кнопки под сообщением после форка — видны сразу, даже если меню
    внизу ещё не раскрылось.
    3 ряда: главное действие (Форматы), калькулятор на виду, гайд.
    Результаты и контакт намеренно убраны — они в нижнем меню,
    чтобы в момент решения не было паралича выбора."""
    rows = []
    if WEBAPP_URL:
        rows.append([programs_btn(uid)])
    hm = howmany_webapp_url()
    if hm:
        rows.append([(MENU_EARN, hm, "webapp")])
    rows.append([(BTN["lm_get_first"], "go_guide", False)])
    return rows


def main_menu_filter():
    """Только нажатия кнопок нижнего меню (не WebApp — они открываются сами)."""
    fixed = "|".join(re.escape(x) for x in (
        MENU_FORMATS, MENU_RESULTS, MENU_GUIDE, MENU_ABOUT, MENU_EARN,
        MENU_QUESTIONS,
    ))
    promo = re.escape(BTN["promo_app"])
    return filters.Regex(rf"^(({fixed})|({promo})( · .+)?)$")


def main_reply_keyboard(uid=None, app_reset=False):
    """Нижнее закреплённое меню (как на скрине).
    1-й ряд: калькулятор + форматы — калькулятор на виду."""
    rows = []
    hm = howmany_webapp_url()
    fmt = MENU_FORMATS if app_reset else formats_menu_label(uid)
    app_url = webapp_url_full(uid, app_reset=app_reset)
    # Ряд 1: калькулятор и форматы рядом, оба на самом видном месте
    if WEBAPP_URL and hm:
        rows.append([
            KeyboardButton(MENU_EARN, web_app=WebAppInfo(url=hm)),
            KeyboardButton(
                fmt,
                web_app=WebAppInfo(url=app_url),
            ),
        ])
    elif WEBAPP_URL:
        rows.append([
            KeyboardButton(MENU_EARN),
            KeyboardButton(
                fmt,
                web_app=WebAppInfo(url=app_url),
            ),
        ])
    elif hm:
        rows.append([
            KeyboardButton(MENU_EARN, web_app=WebAppInfo(url=hm)),
            KeyboardButton(MENU_FORMATS),
        ])
    else:
        rows.append([
            KeyboardButton(MENU_EARN),
            KeyboardButton(MENU_FORMATS),
        ])
    # Ряд 2: результаты + гайд
    rows.append([KeyboardButton(MENU_RESULTS), KeyboardButton(MENU_GUIDE)])
    # Ряд 3: обо мне + вопросы
    rows.append([KeyboardButton(MENU_ABOUT), KeyboardButton(MENU_QUESTIONS)])
    if uid is not None and not app_reset:
        rows.extend(pay_keyboard_rows(uid))
    return ReplyKeyboardMarkup(
        rows, resize_keyboard=True, is_persistent=True,
    )


async def send_with_main_menu(bot, chat_id, text, clear_inline=False,
                              skip_questions_hint=False):
    """Текст + нижнее меню. Inline-кнопки прошлых сообщений не снимаем."""
    invalidate_active_callbacks(chat_id)
    if clear_inline:
        rec = u(chat_id)
        prev_id = rec.get("last_kb_msg")
        if prev_id:
            try:
                await bot.edit_message_reply_markup(
                    chat_id, prev_id, reply_markup=None)
            except Exception:
                pass
            rec["last_kb_msg"] = None
    if not skip_questions_hint:
        text = append_questions_hint(chat_id, text)
    await pause_text(bot, chat_id, text=text)
    msg = await bot.send_message(
        chat_id, text, reply_markup=main_reply_keyboard(chat_id),
    )
    if chat_id not in _replaying_users and not is_funnel_locked(u(chat_id)):
        push_history(chat_id, {"t": "menu", "body": text})
    return msg


async def clear_nudge(bot, uid):
    """Удалить последнее догоняющее (чтобы не копилось в чате)."""
    rec = u(uid)
    mid = rec.pop("nudge_msg_id", None)
    if mid:
        try:
            await bot.delete_message(normalize_uid(uid), mid)
        except Exception:
            pass
        save_state(STATE)


async def send_nudge(bot, uid, send_fn):
    """Новое догоняющее вместо предыдущего — одно «живое» напоминание."""
    await clear_nudge(bot, uid)
    msg = await send_fn()
    if msg:
        u(uid)["nudge_msg_id"] = msg.message_id
        save_state(STATE)
    return msg


# ---------------- ПРОМО ----------------

def promo_sig(uid, deadline):
    """HMAC-SHA256 от '{uid}.{deadline}', hex lowercase — как ждёт сайт."""
    msg = f"{uid}.{deadline}".encode("utf-8")
    return hmac.new(PROMO_SECRET.encode("utf-8"), msg,
                    hashlib.sha256).hexdigest()


def promo_is_active(rec):
    promo = rec.get("promo") or {}
    return bool(promo.get("active") and promo.get("deadline", 0) > time.time())


def build_discount_link(uid, deadline):
    """Подписанная ссылка на скидочную страницу сайта."""
    sig = promo_sig(uid, deadline)
    qs = urlencode({"uid": uid, "deadline": deadline, "sig": sig})
    return f"{DISCOUNT_URL}?{qs}"


def webapp_promo_url(uid, deadline, discount_link):
    """URL Mini App с активной скидкой (то же, что меню — для inline-кнопки)."""
    return webapp_url_full(uid)


def lead_temperature(answers):
    """hot / warm — по ответам квиза (cold обрабатывается отдельно)."""
    budget = answers.get("q1", "")
    is_big_budget = budget == "$1000+"
    is_max_time = answers.get("q2", "") == "2+ часа"
    is_now = answers.get("q3", "") == "сейчас"
    if is_big_budget and is_max_time and is_now:
        return "hot"
    return "warm"


def fmt_left(deadline):
    """'Xч Yмин' до дедлайна, либо 'истекло'."""
    left = int(deadline - time.time())
    if left <= 0:
        return "истекло"
    h = left // 3600
    m = (left % 3600) // 60
    if h > 0:
        return f"{h}ч {m}мин"
    return f"{m}мин"


def detect_kind(file_id: str) -> str:
    if not file_id:
        return ""
    return {
        "BAAC": "video",
        "BQAC": "document",
        "DQAC": "video_note",
        "AgAC": "photo",
    }.get(file_id[:4], "")


async def probe_file_id(bot, file_id):
    """Проверка file_id. «Too big» для getFile — норма: send_video по file_id работает."""
    if not file_id:
        return False, "пустой file_id"
    try:
        f = await bot.get_file(file_id)
        mb = (f.file_size or 0) / (1024 * 1024)
        return True, f"ok, ~{mb:.0f} МБ"
    except BadRequest as e:
        err = str(e).lower()
        if "too big" in err or "file is too large" in err:
            return True, "ok (getFile недоступен — отправка по file_id)"
        return False, str(e)
    except Exception as e:
        return False, str(e)


async def notify_media_fail(bot, chat_id, key, err):
    """Сообщение пользователю + алерт админу."""
    log.error("send_media %s failed: %s", key, err)
    try:
        await bot.send_message(
            chat_id, TXT["media_fail"],
            reply_markup=kb([(BTN["contact"], CALL_LINK, True)]),
        )
    except Exception:
        pass
    if ADMIN_ID and str(chat_id) != str(ADMIN_ID):
        try:
            me = await bot.get_me()
            await bot.send_message(
                ADMIN_ID,
                f"⚠️ Не отправилось: {key}\n"
                f"Бот: @{me.username}\n"
                f"Пользователь: {chat_id}\n"
                f"Ошибка: {err}\n\n"
                f"Скорее всего file_id не от этого бота. "
                f"Перешли видео сюда → /id → MEDIA → redeploy.\n"
                f"Проверка: /checkmedia",
            )
        except Exception:
            pass


async def send_media_file(bot, chat_id, key, log=True):
    """Отправка видео/документа. True = ушло, False = ошибка (file_id и т.д.)."""
    chat_id = normalize_uid(chat_id)
    ref = MEDIA.get(key, {})
    file_id = ref.get("file_id")
    if not file_id:
        path = ref.get("path")
        if path and os.path.exists(path):
            async with _media_send_sem:
                with open(path, "rb") as f:
                    await bot.send_video(chat_id, f)
            return True
        return False
    kind = ref.get("kind") or detect_kind(file_id)
    try:
        await bot.send_chat_action(chat_id, ChatAction.UPLOAD_VIDEO)
    except Exception:
        pass
    try:
        async with _media_send_sem:
            if kind == "document":
                await bot.send_document(
                    chat_id, file_id,
                    read_timeout=120,
                    write_timeout=120,
                    connect_timeout=30,
                )
            else:
                await bot.send_video(
                    chat_id, file_id,
                    supports_streaming=True,
                    read_timeout=120,
                    write_timeout=120,
                    connect_timeout=30,
                )
        if log and chat_id not in _replaying_users:
            ms = MEDIA_MILESTONE.get(key)
            if ms:
                track_milestone(chat_id, ms)
            push_history(chat_id, {"t": "video", "k": key})
        return True
    except BadRequest as e:
        await notify_media_fail(bot, chat_id, key, e)
        return False
    except Exception as e:
        await notify_media_fail(bot, chat_id, key, e)
        return False


async def send_circle(bot, chat_id, key, log=True):
    chat_id = normalize_uid(chat_id)
    ref = MEDIA.get(key, {})
    fid = ref.get("file_id")
    if not fid:
        return False
    try:
        await bot.send_chat_action(chat_id, ChatAction.RECORD_VIDEO)
        async with _media_send_sem:
            await bot.send_video_note(chat_id, fid)
        if log and chat_id not in _replaying_users:
            ms = MEDIA_MILESTONE.get(key)
            if ms:
                track_milestone(chat_id, ms)
            push_history(chat_id, {"t": "circle", "k": key})
        return True
    except BadRequest as e:
        await notify_media_fail(bot, chat_id, key, e)
        return False
    except Exception as e:
        await notify_media_fail(bot, chat_id, key, e)
        return False


def _resolve_photo_source(item):
    if item.get("file_id"):
        return item["file_id"]
    if item.get("url"):
        return item["url"]
    if item.get("path") and os.path.exists(item["path"]):
        return item["path"]
    return None


async def send_proofs(bot, chat_id, proofs, caption=None, log=True,
                      proofs_key=None, caption_key=None):
    """Фото по URL/file_id. Если у элемента есть caption — шлём по одному."""
    chat_id = normalize_uid(chat_id)
    if log:
        invalidate_active_callbacks(chat_id)
    items = [p for p in proofs if _resolve_photo_source(p)]
    if not items:
        if caption:
            await bot.send_message(chat_id, caption)
        return
    if any(p.get("caption") for p in items):
        try:
            for p in items:
                src = _resolve_photo_source(p)
                if not src:
                    continue
                cap = p.get("caption")
                if isinstance(src, str) and os.path.exists(src):
                    with open(src, "rb") as f:
                        await bot.send_photo(chat_id, f, caption=cap)
                else:
                    await bot.send_photo(chat_id, src, caption=cap)
            return
        except Exception as e:
            log.error("send_proofs (per photo) failed: %s", e)
    sources = [_resolve_photo_source(p) for p in proofs]
    sources = [s for s in sources if s]
    try:
        if len(sources) == 1:
            src = sources[0]
            if isinstance(src, str) and os.path.exists(src):
                with open(src, "rb") as f:
                    await bot.send_photo(chat_id, f, caption=caption or None)
            else:
                await bot.send_photo(chat_id, src, caption=caption or None)
            return
        media = []
        files = []
        for i, src in enumerate(sources[:10]):
            cap = caption if i == 0 else None
            if isinstance(src, str) and os.path.exists(src):
                fh = open(src, "rb")
                files.append(fh)
                media.append(InputMediaPhoto(fh, caption=cap))
            else:
                media.append(InputMediaPhoto(src, caption=cap))
        await bot.send_media_group(chat_id, media)
        for fh in files:
            fh.close()
    except Exception as e:
        log.error("send_proofs failed: %s", e)
        if caption:
            await bot.send_message(chat_id, caption)
    if log and chat_id not in _replaying_users and proofs_key:
        ms = {"v1": "proofs_v1", "proofs_v2": "proofs_v2"}.get(
            proofs_key, proofs_key)
        track_milestone(chat_id, ms)
        push_history(chat_id, {
            "t": "proofs", "p": proofs_key, "cap": caption_key or "",
        })
        if caption and caption_key:
            track_milestone(chat_id, caption_key)
            push_history(chat_id, {"t": "text", "body": caption, "rows": None})


# ---------------- ЛИД-МАГНИТ ----------------

async def is_subscribed(bot, user_id):
    """Проверяет подписку на CHANNEL_USERNAME. None = не удалось проверить."""
    _ACTIVE = frozenset({
        ChatMemberStatus.OWNER,
        ChatMemberStatus.ADMINISTRATOR,
        ChatMemberStatus.MEMBER,
        "creator", "administrator", "member", "owner",
    })

    def _status_val(status):
        if hasattr(status, "value"):
            return status.value
        return str(status)

    try:
        member = await bot.get_chat_member(CHANNEL_USERNAME, user_id)
        st = _status_val(member.status)
        if st in _ACTIVE or member.status in _ACTIVE:
            return True
        if st == "restricted" or member.status == ChatMemberStatus.RESTRICTED:
            return bool(getattr(member, "is_member", False))
        return False
    except Exception as e:
        log.error("is_subscribed failed (%s): %s", CHANNEL_USERNAME, e)
        return None


async def show_lead_magnet_offer(bot, chat_id, intro=None):
    """Показывает предложение лид-магнита с выбором Хочу/Пропустить."""
    text = (intro + "\n\n" if intro else "") + TXT["lm_offer"]
    await send_step(bot, chat_id, text, [
        (BTN["lm_want"], "lm_want", False),
        (BTN["lm_skip"], "lm_skip", False),
    ], milestone="lm_offer")


async def lm_want(update, context):
    uid = update.effective_user.id
    bot = context.bot
    await send_step(bot, uid, TXT["lm_subscribe"], [
            (BTN["lm_goto"], CHANNEL_LINK, True),
            (BTN["lm_check"], "lm_check", False),
        ])


async def lm_skip(update, context):
    uid = update.effective_user.id
    bot = context.bot
    await send_step(bot, uid, TXT["lm_skip"], [(BTN["contact"], CALL_LINK, True)])


async def lm_check(update, context):
    uid = update.effective_user.id
    bot = context.bot
    rec = u(uid)

    if rec.get("got_guide"):
        await send_guide(bot, uid)
        await send_with_main_menu(
            bot, uid,
            "Гайд уже у вас — отправил ещё раз 👇",
            clear_inline=False, skip_questions_hint=True,
        )
        return

    sub = await is_subscribed(bot, uid)

    if sub is None:
        # не смогли проверить — отдадим контакт, не теряем человека
        await send_step(bot, uid, TXT["lm_error"], [(BTN["contact"], CALL_LINK, True)])
        return

    if not sub:
        await send_step(bot, uid, TXT["lm_not_subscribed"], [
                (BTN["lm_goto"], CHANNEL_LINK, True),
                (BTN["lm_check"], "lm_check", False),
            ])
        return

    # подписан — выдаём гайд
    await send_guide(bot, uid)
    rec["got_guide"] = True
    save_state(STATE)
    rows = [(BTN["contact"], CALL_LINK, True)]
    if not promo_is_active(rec):
        rows.insert(0, (BTN["to_lead"], "go_lead", False))
    await send_step(bot, uid, TXT["lm_delivered"], rows, questions_hint=True)


async def send_guide(bot, chat_id):
    """Отправляет гайд. Если файла нет — мягкая заглушка, не падает."""
    try:
        if GUIDE_FILE_ID:
            await bot.send_document(chat_id, GUIDE_FILE_ID)
            return
        if os.path.exists(GUIDE_PATH):
            with open(GUIDE_PATH, "rb") as f:
                await bot.send_document(chat_id, f, filename=GUIDE_FILENAME)
            return
        # гайда ещё нет — отправляем дружелюбную заглушку, бот не падает
        log.warning("guide not found: GUIDE_FILE_ID пуст и нет %s — тестовая заглушка", GUIDE_PATH)
        await bot.send_message(
            chat_id,
            "📘 Гайд ещё готовится — пришлю вам сразу, как только будет готов.\n\n"
            "А пока, если хотите забрать скидку на обучение — "
            "кнопка ниже 👇",
        )
    except Exception as e:
        log.error("send_guide failed: %s", e)


# ---------------- ПОКАЗ ПРОМО ----------------

def cancel_bonus_reminds(app, uid):
    if not app or not app.job_queue:
        return
    prefix = f"bonusremind_{uid_str(uid)}_"
    for job in app.job_queue.jobs():
        if job.name and job.name.startswith(prefix):
            job.schedule_removal()


def should_bonus_remind(rec):
    if rec.get("step") not in OFFER_STEPS:
        return False
    if is_funnel_locked(rec):
        return False
    if rec.get("bonus_claimed"):
        return False
    if rec.get("bonus_remind_count", 0) >= BONUS_REMIND_MAX:
        return False
    promo = rec.get("promo") or {}
    return not (promo.get("deadline", 0) > time.time())


def schedule_bonus_remind(app, uid, delay_sec=None):
    if not app or not app.job_queue:
        return
    rec = u(uid)
    if not should_bonus_remind(rec):
        cancel_bonus_reminds(app, uid)
        return
    cancel_bonus_reminds(app, uid)
    uid_n = normalize_uid(uid)
    app.job_queue.run_once(
        bonus_remind_fire, when=delay_sec or BONUS_REMIND_SEC,
        name=f"bonusremind_{uid_str(uid_n)}_tick",
        data={"uid": uid_n},
    )


async def bonus_remind_fire(context: ContextTypes.DEFAULT_TYPE):
    uid = context.job.data["uid"]
    rec = u(uid)
    if not should_bonus_remind(rec):
        cancel_bonus_reminds(context.application, uid)
        return
    rec["bonus_remind_count"] = rec.get("bonus_remind_count", 0) + 1
    save_state(STATE)
    idx = min(rec["bonus_remind_count"] - 1, len(BONUS_REMIND_KEYS) - 1)
    text = TXT[BONUS_REMIND_KEYS[idx]].format(discount=PROMO_DISCOUNT)
    try:
        await send_nudge(
            context.bot, uid,
            lambda: send_with_main_menu(
                context.bot, uid, text, skip_questions_hint=True,
            ),
        )
    except Exception as e:
        log.error("bonus_remind_fire failed: %s", e)
    if rec.get("bonus_remind_count", 0) < BONUS_REMIND_MAX:
        schedule_bonus_remind(context.application, uid)


def cancel_promo_jobs(app, uid):
    """Снять таймер, напоминание и задачу удаления промо."""
    if not app or not app.job_queue:
        return
    uid_s = uid_str(uid)
    names = {
        f"promotick_{uid_s}",
        f"promoremind_{uid_s}",
        f"promoexpire_{uid_s}",
    }
    for job in app.job_queue.jobs():
        if job.name and job.name in names:
            job.schedule_removal()


async def expire_promo(bot, uid, rec):
    """Удалить сообщения со скидкой / Mini App и открепить таймер."""
    promo = rec.get("promo") or {}
    pin_id = promo.get("pin_msg_id")
    main_id = promo.get("main_msg_id")
    remind_id = promo.get("remind_msg_id")
    ids = {x for x in (pin_id, main_id, remind_id) if x}

    try:
        await bot.unpin_all_chat_messages(uid)
    except Exception:
        if pin_id:
            try:
                await bot.unpin_chat_message(uid, pin_id)
            except Exception:
                pass

    for mid in ids:
        try:
            await bot.delete_message(chat_id=uid, message_id=mid)
        except Exception as e:
            log.debug("promo delete msg %s: %s", mid, e)

    if rec.get("last_kb_msg") in ids:
        rec["last_kb_msg"] = None
    promo["active"] = False
    promo["pin_msg_id"] = None
    promo["main_msg_id"] = None
    promo["remind_msg_id"] = None
    rec["funnel_locked"] = True
    save_state(STATE)


async def promo_expire(context: ContextTypes.DEFAULT_TYPE):
    """Ровно в deadline: удалить промо-сообщения (таймер к этому моменту уже отработал)."""
    uid = context.job.data["uid"]
    rec = u(uid)
    promo = rec.get("promo") or {}
    if time.time() < promo.get("deadline", 0) - 2:
        return
    cancel_promo_jobs(context.application, uid)
    cancel_bonus_reminds(context.application, uid)
    await expire_promo(context.bot, uid, rec)


async def show_promo(context, uid, user, temperature, from_app=False):
    """Выдаёт персональную скидку: ссылка с подписью, закреп, таймер."""
    bot = context.bot
    rec = u(uid)

    if not PROMO_SECRET:
        await send_step(bot, uid, TXT["promo_fallback"],
                        [(BTN["contact"], CALL_LINK, True)])
        log.warning("PROMO_SECRET не задан — промо не выдано, отдан контакт")
        return

    if promo_is_active(rec):
        left = fmt_left(rec["promo"]["deadline"])
        label = formats_menu_label(uid)
        if from_app:
            await refresh_main_keyboard(
                bot, uid,
                f"👇 «{label}» — цены со скидкой ({left})",
            )
        else:
            await refresh_main_keyboard(
                bot, uid,
                f"Скидка уже закреплена — осталось {left}. "
                f"Откройте «{label}» 👇",
            )
        return

    await clear_nudge(bot, uid)
    deadline = int(time.time()) + PROMO_HOURS * 3600
    link = build_discount_link(uid, deadline)

    rec["promo"] = {
        "issued_at": int(time.time()),
        "deadline": deadline,
        "link": link,
        "temperature": temperature,
        "active": True,
    }
    rec["bonus_claimed"] = True
    rec["bonus_remind_count"] = 0
    save_state(STATE)
    cancel_bonus_reminds(context.application, uid)
    cancel_promo_jobs(context.application, uid)

    if from_app:
        label = formats_menu_label(uid)
        intro = (
            f"✅ Скидка −{PROMO_DISCOUNT}% закреплена на {PROMO_HOURS} ч.\n\n"
            f"Снова откройте «{label}» — в приложении цены "
            f"«было → стало».\n\n"
            f"На сайте выбираете формат сами 👇"
        )
    else:
        intro = TXT["promo_hot"] if temperature == "hot" else TXT["promo_warm"]
        intro = intro.format(hours=PROMO_HOURS, discount=PROMO_DISCOUNT)

    rows = [(BTN["promo_get"], link, True)]
    if WEBAPP_URL:
        rows.append((
            formats_menu_label(uid),
            webapp_promo_url(uid, deadline, link),
            "webapp",
        ))
    rows.append((BTN["contact"], CALL_LINK, True))

    promo_msg = await send_step(bot, uid, intro, rows, questions_hint=True)
    rec["promo"]["main_msg_id"] = promo_msg.message_id
    save_state(STATE)

    # закреплённое сообщение с таймером (обычным send_message, чтобы НЕ
    # снять кнопки с промо-сообщения выше)
    try:
        await pause_text(bot, uid)
        pin = await bot.send_message(
            uid, TXT["promo_pinned"].format(
                left=fmt_left(deadline), discount=PROMO_DISCOUNT))
        await bot.pin_chat_message(uid, pin.message_id,
                                   disable_notification=True)
        rec["promo"]["pin_msg_id"] = pin.message_id
        rec["promo"]["pin_started"] = int(time.time())  # для расчёта частоты обновлений
        save_state(STATE)
        jq = context.application.job_queue
        if jq:
            uid_n = normalize_uid(uid)
            uid_s = uid_str(uid_n)
            jq.run_once(
                promo_tick, when=15,
                name=f"promotick_{uid_s}", data={"uid": uid_n},
            )
    except Exception as e:
        log.error("promo pin failed: %s", e)

    jq = context.application.job_queue
    if jq:
        uid_n = normalize_uid(uid)
        uid_s = uid_str(uid_n)
        expire_in = max(1, deadline - int(time.time()))
        jq.run_once(
            promo_expire, when=expire_in,
            name=f"promoexpire_{uid_s}", data={"uid": uid_n},
        )
        remind_in = max(60, (PROMO_HOURS - 2) * 3600)
        jq.run_once(
            promo_remind, when=remind_in,
            name=f"promoremind_{uid_s}", data={"uid": uid_n},
        )

    await refresh_main_keyboard(
        bot, uid,
        f"👇 «{formats_menu_label(uid)}» — цены со скидкой на {PROMO_HOURS} ч",
    )


async def promo_tick(context: ContextTypes.DEFAULT_TYPE):
    """Обновляет закреплённое сообщение с обратным отсчётом.
    Первые 5 минут обновляется каждые 15 сек (ощущается «живым»),
    дальше — каждые 30 минут, чтобы не упереться в лимиты Telegram."""
    uid = context.job.data["uid"]
    rec = u(uid)
    promo = rec.get("promo") or {}
    pin_id = promo.get("pin_msg_id")
    deadline = promo.get("deadline", 0)
    pin_started = promo.get("pin_started", int(time.time()))
    if not pin_id:
        return
    bot = context.bot
    if time.time() >= deadline:
        cancel_promo_jobs(context.application, uid)
        cancel_bonus_reminds(context.application, uid)
        await expire_promo(bot, uid, rec)
        return
    try:
        await bot.edit_message_text(
            TXT["promo_pinned"].format(
                left=fmt_left(deadline), discount=PROMO_DISCOUNT),
            uid, pin_id)
    except Exception:
        pass  # текст не изменился или сообщение удалено — не страшно
    # перепланируем следующий тик: первые 5 минут — каждые 15 сек, потом 30 мин
    elapsed = time.time() - pin_started
    next_in = 15 if elapsed < 300 else 1800
    jq = context.application.job_queue
    if jq:
        jq.run_once(
            promo_tick, when=next_in,
            name=f"promotick_{uid_str(uid)}", data={"uid": normalize_uid(uid)},
        )


async def promo_remind(context: ContextTypes.DEFAULT_TYPE):
    """Однократное напоминание ближе к концу промо."""
    uid = context.job.data["uid"]
    rec = u(uid)
    promo = rec.get("promo") or {}
    deadline = promo.get("deadline", 0)
    if time.time() >= deadline or not promo.get("active", True):
        return
    try:
        remind_msg = await send_step(
            context.bot, uid, TXT["promo_drip"],
            [(BTN["promo_get"], promo.get("link"), True)],
        )
        rec["promo"]["remind_msg_id"] = remind_msg.message_id
        save_state(STATE)
    except Exception as e:
        log.error("promo_remind failed: %s", e)


# ---------------- ДОГОНЯЮЩИЕ ----------------

def cancel_drips(app, uid):
    if not app or not app.job_queue:
        return
    prefix = f"drip_{uid_str(uid)}_"
    for job in app.job_queue.jobs():
        if job.name and job.name.startswith(prefix):
            job.schedule_removal()


# tag → (step, txt_key, rows|None, menu_only)
DRIP_TAG_CONFIG = {
    "drip_start_1":  ("start", "drip_start_1",  [( "start", "go_intro", False)], False),
    "drip_start_2":  ("start", "drip_start_2",  [( "start", "go_intro", False)], False),
    "drip_intro_1":  ("intro", "drip_intro_1",  [("v1_watch", "go_v1_play", False)], False),
    "drip_intro_2":  ("intro", "drip_intro_2",  [("v1_watch", "go_v1_play", False)], False),
    "drip_v1_1":     ("v1", "drip_v1_1",        [("v1_proofs", "go_v1_proofs", False)], False),
    "drip_v1_2":     ("v1", "drip_v1_2",        [("v1_proofs", "go_v1_proofs", False)], False),
    "drip_v2_1":     ("v2", "drip_v2_1",        [("v2_proofs", "go_v2_proofs", False)], False),
    "drip_v2_2":     ("v2", "drip_v2_2",        [("v2_proofs", "go_v2_proofs", False)], False),
    "drip_v3_1":     ("v3", "drip_v3_1",        [("show_formats", "go_calc", False)], False),
    "drip_v3_2":     ("v3", "drip_v3_2",        [("show_formats", "go_calc", False)], False),
    "drip_offer_1":  ("offer", "drip_offer_1",  None, True),
    "drip_offer_2":  ("offer", "drip_offer_2",  None, True),
    "drip_lead_1":   ("qualified", "drip_lead_1", [("contact", CALL_LINK, True)], False),
    "drip_lead_2":   ("qualified", "drip_lead_2", [("contact", CALL_LINK, True)], False),
}


def _drip_rows(spec):
    if not spec:
        return None
    return [(BTN[b], cb, kind) for b, cb, kind in spec]


def schedule_step_drips(app, uid, step_key, step_at_ts=None):
    """2 догонялки на step — часы от входа на step (см. STEP_DRIP_SCHEDULE)."""
    if not app or not app.job_queue:
        return
    cancel_drips(app, uid)
    uid_n = normalize_uid(uid)
    now = time.time()
    if step_at_ts is None:
        step_at_str = u(uid_n).get("step_at")
        if step_at_str:
            try:
                step_at_ts = datetime.strptime(
                    step_at_str, "%Y-%m-%d %H:%M:%S",
                ).timestamp()
            except ValueError:
                step_at_ts = now
        else:
            step_at_ts = now
    elapsed = max(0, now - step_at_ts)
    catch_up_delay = 90
    for hours, tag in STEP_DRIP_SCHEDULE.get(step_key, ()):
        due_in = hours * 3600 - elapsed
        if due_in < -3600:
            continue
        if due_in > 0:
            when = max(60, int(due_in))
        else:
            when = catch_up_delay
            catch_up_delay += 120
        app.job_queue.run_once(
            drip_fire,
            when=when,
            name=f"drip_{uid_str(uid_n)}_{tag}",
            data={"uid": uid_n, "tag": tag},
        )


def restore_step_drips(application):
    """После рестарта бота — восстановить догонялки по step_at."""
    if not application.job_queue:
        return
    count = 0
    for uid, rec in STATE.items():
        step_key = rec.get("step")
        if step_key not in STEP_DRIP_SCHEDULE:
            continue
        step_at_str = rec.get("step_at")
        if not step_at_str:
            continue
        try:
            step_at_ts = datetime.strptime(
                step_at_str, "%Y-%m-%d %H:%M:%S",
            ).timestamp()
        except ValueError:
            continue
        schedule_step_drips(application, uid, step_key, step_at_ts=step_at_ts)
        count += 1
    if count:
        log.info("step_drip: восстановлено для %s пользователей", count)


async def drip_fire(context: ContextTypes.DEFAULT_TYPE):
    data = context.job.data
    uid = data["uid"]
    tag = data["tag"]
    cfg = DRIP_TAG_CONFIG.get(tag)
    if not cfg:
        return
    expected_step, txt_key, row_spec, menu_only = cfg
    rec = u(uid)
    if rec.get("step") != expected_step:
        return

    bot = context.bot
    text = TXT[txt_key]
    try:
        if menu_only:
            await send_nudge(
                bot, uid,
                lambda: send_with_main_menu(
                    bot, uid, text, skip_questions_hint=True,
                ),
            )
        else:
            rows = _drip_rows(row_spec)
            await send_nudge(
                bot, uid,
                lambda: send_step(
                    bot, uid, text, rows, skip_questions_hint=True,
                ),
            )
    except Exception as e:
        log.error("drip_fire failed tag=%s: %s", tag, e)


# ---------------- ШАГИ ВОРОНКИ ----------------

async def _funnel_start_fresh(bot, uid, app=None):
    """Приветствие /start — одно сохранение, без пауз, сразу «печатает»."""
    rec = u(uid)
    rec["step"] = "start"
    rec["step_at"] = _now()
    rows = [(BTN["start"], "go_intro", False)]
    markup = kb(rows)
    try:
        await bot.send_chat_action(uid, ChatAction.TYPING)
    except Exception:
        pass
    msg = await bot.send_message(uid, TXT["start"], reply_markup=markup)
    rec["last_kb_msg"] = msg.message_id
    rec["active_callbacks"] = callback_ids_from_rows(rows)
    if uid not in _replaying_users:
        rec["milestone"] = "start"
        rec["milestone_label"] = MILESTONE_LABELS.get("start", "start")
        rec["milestone_at"] = _now()
        if not is_funnel_locked(rec):
            hist = rec.setdefault("history", [])
            hist.append({
                "t": "text",
                "body": TXT["start"],
                "rows": _serialize_rows(rows),
                "_ts": _now(),
            })
            if len(hist) > 50:
                del hist[0]
    save_state(STATE)
    if app:
        schedule_step_drips(app, uid, "start")


async def cmd_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    uid = user.id
    async with _user_locks[str(uid)]:
        await _cmd_start_impl(update, context)


async def _cmd_start_impl(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    uid = user.id
    cancel_drips(context.application, uid)
    rec = u(uid)
    rec["username"] = user.username or rec.get("username", "")
    rec["full_name"] = user.full_name or rec.get("full_name", "")

    start_raw = ((context.args or [""])[0] or "").strip().lower()
    if start_raw == "wa_open":
        await mark_webapp_opened(context.bot, uid, context.application)
        return
    if start_raw == "wa_ready":
        await handle_webapp_ready(context.bot, uid, context.application)
        return
    if start_raw == "claim_promo":
        promo = rec.get("promo") or {}
        if is_funnel_locked(rec) and not is_exempt_user(user):
            await send_with_main_menu(context.bot, uid, TXT["return_locked"])
            return
        if promo.get("deadline", 0) > time.time():
            await context.bot.send_message(
                uid,
                "Скидка уже закреплена — смотрите сообщение с таймером выше 👆",
            )
            return
        if not PROMO_SECRET:
            await send_step(
                context.bot, uid,
                "Скидка пока настраивается. Напишите мне 👇",
                [(BTN["contact"], CALL_LINK, True)],
            )
            return
        if not rec.get("temperature"):
            rec["temperature"] = "warm"
        save_state(STATE)
        await mark_webapp_opened(context.bot, uid, context.application)
        await show_promo(context, uid, user, rec.get("temperature", "warm"),
                         from_app=True)
        return

    utm = parse_utm(context.args or [])
    if utm and not rec.get("utm"):
        rec["utm"] = utm

    if is_exempt_user(user):
        rec["last_kb_msg"] = None
        rec["active_callbacks"] = []
        await _funnel_start_fresh(context.bot, uid, context.application)
        return

    if is_funnel_locked(rec):
        rec["last_kb_msg"] = None
        rec["active_callbacks"] = []
        track_milestone(uid, "return_locked")
        save_state(STATE)
        await send_with_main_menu(context.bot, uid, TXT["return_locked"])
        return

    hist = rec.get("history") or []
    if hist and rec.get("milestone") and rec.get("milestone") != "start":
        rec["last_kb_msg"] = None
        rec["active_callbacks"] = []
        save_state(STATE)
        await context.bot.send_message(uid, TXT["resume_hi"])
        await replay_user_history(context.bot, uid)
        return

    rec["last_kb_msg"] = None
    rec["active_callbacks"] = []
    await _funnel_start_fresh(context.bot, uid, context.application)


async def _job_after_circle_intro(context: ContextTypes.DEFAULT_TYPE):
    async def work(uid, ctx):
        bot = ctx.application.bot
        try:
            await bot.send_chat_action(uid, ChatAction.TYPING)
        except Exception:
            pass
        await send_step(bot, uid, TXT["after_circle_intro"],
                        [(BTN["v1_watch"], "go_v1_play", False)],
                        skip_pause=True, guide_teaser=True,
                        milestone="after_circle_intro")
        set_step(uid, "intro")
        schedule_step_drips(ctx.application, uid, "intro")
    await run_uid_job(context, work)


async def _job_after_v1_video(context: ContextTypes.DEFAULT_TYPE):
    async def work(uid, ctx):
        bot = ctx.application.bot
        app = ctx.application
        try:
            await bot.send_chat_action(uid, ChatAction.RECORD_VIDEO)
        except Exception:
            pass
        await send_step(bot, uid, TXT["after_v1_video"],
                        [(BTN["v1_proofs"], "go_v1_proofs", False)],
                        skip_pause=True, milestone="after_v1_video")
        set_step(uid, "v1")
        schedule_step_drips(app, uid, "v1")
    await run_uid_job(context, work)


async def _job_after_v2_video(context: ContextTypes.DEFAULT_TYPE):
    async def work(uid, ctx):
        bot = ctx.application.bot
        app = ctx.application
        try:
            await bot.send_chat_action(uid, ChatAction.RECORD_VIDEO)
        except Exception:
            pass
        await send_step(bot, uid, TXT["after_v2_video"],
                        [(BTN["v2_proofs"], "go_v2_proofs", False)],
                        skip_pause=True, milestone="after_v2_video")
        set_step(uid, "v2")
        schedule_step_drips(app, uid, "v2")
    await run_uid_job(context, work)


async def _job_after_v3_video(context: ContextTypes.DEFAULT_TYPE):
    async def work(uid, ctx):
        bot = ctx.application.bot
        app = ctx.application
        try:
            await bot.send_chat_action(uid, ChatAction.RECORD_VIDEO)
        except Exception:
            pass
        await send_step(bot, uid, TXT["after_v3_video"],
                        [(BTN["to_v3_next"], "go_v3_after", False)],
                        skip_pause=True, milestone="after_v3_video")
        set_step(uid, "v3")
        schedule_step_drips(app, uid, "v3")
    await run_uid_job(context, work)


async def _job_after_fork_circle(context: ContextTypes.DEFAULT_TYPE):
    async def work(uid, ctx):
        bot = ctx.application.bot
        app = ctx.application
        try:
            await bot.send_chat_action(uid, ChatAction.TYPING)
        except Exception:
            pass
        set_step(uid, "offer")
        await send_step(
            bot, uid, TXT["after_fork_circle"],
            fork_inline_rows(uid),
            skip_pause=True, skip_questions_hint=True,
            milestone="after_fork",
        )
        track_milestone(uid, "after_fork")
        await refresh_main_keyboard(
            bot, uid,
            "👇 Кнопки меню закреплены внизу — ими можно пользоваться "
            "в любой момент.",
        )
        schedule_bonus_remind(app, uid)
        schedule_step_drips(app, uid, "offer")
    await run_uid_job(context, work)


async def go_intro(update, context):
    uid = user_id_from(update)
    bot = context.bot
    cancel_drips(context.application, uid)
    try:
        await bot.send_chat_action(uid, ChatAction.RECORD_VIDEO)
    except Exception:
        pass
    if not await send_circle(bot, uid, "circle_intro"):
        try:
            await bot.send_message(
                uid, "Не удалось загрузить — нажмите /start ещё раз 👇",
            )
        except Exception:
            pass
        return
    schedule_funnel_pause(
        context.application, uid,
        funnel_pause_sec(uid, CIRCLE_PAUSE_SEC),
        _job_after_circle_intro, "circle_intro",
    )


async def go_v1_prep(update, context):
    """Старые кнопки в истории — сразу на видео 1."""
    await go_v1_play(update, context)


async def go_v1_play(update, context):
    """Видео 1 → кнопка к разбору скринов."""
    uid = update.effective_user.id
    bot = context.bot
    if not await send_media_file(bot, uid, "video_1"):
        return
    schedule_funnel_pause(
        context.application, uid,
        funnel_pause_sec(uid, MEDIA_TO_TEXT_PAUSE_SEC),
        _job_after_v1_video, "after_v1",
    )


async def go_v1_proofs(update, context):
    """После видео 1: intro → короткая пауза → 2 скрина → основной текст.
    Пользователь сам нажал кнопку — без долгого «печатает» и без 10 с ожидания."""
    uid = user_id_from(update)
    bot = context.bot
    rec = u(uid)
    if rec.get("milestone") in (
        "proofs_v1", "after_v1_proofs", "proofs_v1_caption", "bridge_v2", "v2",
    ):
        log.info("skip duplicate v1_proofs uid=%s milestone=%s", uid, rec.get("milestone"))
        return
    intro = TXT["proofs_v1_intro"]
    await bot.send_message(uid, intro)
    if uid not in _replaying_users and not is_funnel_locked(u(uid)):
        push_history(uid, {"t": "text", "body": intro, "rows": None})
    if pauses_enabled_for(uid) and not user_fast_mode(uid):
        await asyncio.sleep(PROOFS_V1_INTRO_PAUSE_SEC)
    await send_proofs(bot, uid, PROOFS_AFTER_V1, proofs_key="v1")
    if pauses_enabled_for(uid) and not user_fast_mode(uid):
        await asyncio.sleep(PROOFS_V1_BEFORE_MAIN_SEC)
    await send_step(
        bot, uid, TXT["proofs_v1_caption"],
        [(BTN["to_v2"], "go_v2_prep", False)],
        skip_pause=True, guide_teaser=True,
        milestone="after_v1_proofs",
    )


async def go_v2_prep(update, context):
    uid = update.effective_user.id
    bot = context.bot
    cancel_drips(context.application, uid)
    await send_step(bot, uid, TXT["bridge_v2"],
                    [(BTN["v2_watch"], "go_v2_video", False)],
                    skip_pause=False, guide_teaser=True,
                    milestone="bridge_v2")


async def go_v2_video(update, context):
    uid = update.effective_user.id
    bot = context.bot
    if not await send_media_file(bot, uid, "video_2"):
        return
    schedule_funnel_pause(
        context.application, uid,
        funnel_pause_sec(uid, MEDIA_TO_TEXT_PAUSE_SEC),
        _job_after_v2_video, "after_v2",
    )


async def go_v2_proofs(update, context):
    uid = update.effective_user.id
    bot = context.bot
    await send_proofs(bot, uid, PROOFS_AFTER_V2, proofs_key="proofs_v2")
    if pauses_enabled_for(uid) and not user_fast_mode(uid):
        await asyncio.sleep(PROOFS_BEFORE_CAPTION_SEC)
    await send_step(
        bot, uid, TXT["proofs_v2_caption"],
        [(BTN["v3_yes"], "go_v3_confirm", False)],
        skip_pause=True, guide_teaser=True,
        milestone="proofs_v2_caption",
    )


async def go_v3_confirm(update, context):
    """После «Готов?» — текст про причины + кнопка на видео 3."""
    uid = update.effective_user.id
    bot = context.bot
    await send_step(
        bot, uid, TXT["after_v2"],
        [(BTN["v3_watch"], "go_v3_video", False)],
        skip_pause=False, milestone="after_v2",
    )


async def go_v2_bridge(update, context):
    """Старые кнопки в истории → новый шаг."""
    await go_v3_confirm(update, context)


async def go_v3_prep(update, context):
    """Старый шаг воронки — сразу открываем видео (на случай старых кнопок)."""
    await go_v3_video(update, context)


async def go_v3_video(update, context):
    uid = update.effective_user.id
    bot = context.bot
    cancel_drips(context.application, uid)
    if not await send_media_file(bot, uid, "video_3"):
        return
    schedule_funnel_pause(
        context.application, uid,
        funnel_pause_sec(uid, MEDIA_TO_TEXT_PAUSE_SEC),
        _job_after_v3_video, "after_v3",
    )


async def go_v3_after(update, context):
    uid = update.effective_user.id
    bot = context.bot
    await send_step(bot, uid, TXT["after_v3"],
                    [(BTN["to_fork_how"], "go_calc", False)],
                    skip_pause=False, guide_teaser=True,
                    milestone="after_v3")


async def go_calc(update, context):
    """Шаг калькулятора перед оффером. Если HOWMANY настроен —
    кнопка-вебапп + «пропустить». Если нет — короткий текст и сразу к форку."""
    uid = update.effective_user.id
    bot = context.bot
    cancel_drips(context.application, uid)
    hm = howmany_webapp_url()
    if hm:
        rows = [
            [(BTN["calc_open"], hm, "webapp")],
            [(BTN["calc_skip"], "go_fork", False)],
        ]
        await send_step(bot, uid, TXT["calc_pitch"], rows,
                        skip_pause=False, milestone="calc_pitch")
    else:
        # калькулятор не настроен — не задерживаем, мягко ведём к форматам
        await send_step(bot, uid, TXT["calc_pitch_nourl"],
                        [(BTN["calc_to_fork"], "go_fork", False)],
                        skip_pause=False, milestone="calc_pitch")


async def go_fork(update, context):
    uid = update.effective_user.id
    bot = context.bot
    cancel_drips(context.application, uid)
    if not await send_circle(bot, uid, "circle_fork"):
        return
    schedule_funnel_pause(
        context.application, uid,
        funnel_pause_sec(uid, CIRCLE_PAUSE_SEC),
        _job_after_fork_circle, "fork_circle",
    )


async def go_offer_menu(update, context):
    """Старые inline-кнопки в истории → напоминание про меню внизу."""
    uid = update.effective_user.id
    bot = context.bot
    cancel_drips(context.application, uid)
    set_step(uid, "offer")
    await send_with_main_menu(bot, uid, TXT["after_fork_menu_hint"])
    schedule_step_drips(context.application, uid, "offer")


async def go_offer(update, context):
    await go_offer_menu(update, context)


async def go_offer_steps(update, context):
    await go_offer_menu(update, context)


async def go_offer_checks(update, context):
    await go_offer_menu(update, context)


async def go_offer_formats(update, context):
    await go_offer_menu(update, context)


async def go_programs(update, context):
    """Текстовый показ программ — fallback, если Mini App не настроен,
    либо по команде /programs когда WEBAPP_URL пуст."""
    uid = update.effective_user.id
    bot = context.bot
    # если Mini App настроен — лучше открыть его
    if WEBAPP_URL:
        await send_with_main_menu(
            bot, uid,
            "Форматы и инструменты — в мини-приложении. "
            "Нажмите «Форматы сотрудничества и обучения» в меню внизу 👇",
        )
        return
    # иначе — тарифы текстом + старый показ результатов фото
    await send_text(bot, uid, TXT["programs_text"])
    await send_proofs(bot, uid, PROOFS_STUDENTS, TXT["students_caption"])
    await pause_text(bot, uid)
    await send_proofs(bot, uid, [SITE_SCREEN], TXT["site_caption"])
    await pause_text(bot, uid)
    await send_with_main_menu(bot, uid, TXT["back_to_offer"])
    await send_step(bot, uid, "Сайт с результатами 👇",
                    [(BTN["site"], SITE_LINK, True)])


async def go_students(update, context):
    uid = update.effective_user.id
    bot = context.bot
    await send_proofs(bot, uid, PROOFS_STUDENTS, TXT["students_caption"])
    await pause_text(bot, uid)
    await send_proofs(bot, uid, [SITE_SCREEN], TXT["site_caption"])
    await pause_text(bot, uid)
    await send_with_main_menu(bot, uid, TXT["back_to_offer"])
    await send_step(bot, uid, "Сайт с результатами 👇",
                    [(BTN["site"], SITE_LINK, True)])


async def on_webapp_data(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Данные из Mini App (кнопка «Закрепить скидку»)."""
    msg = update.effective_message
    if not msg or not msg.web_app_data:
        return
    uid = update.effective_user.id
    data = (msg.web_app_data.data or "").strip()
    if data == "webapp_open":
        await mark_webapp_opened(context.bot, uid, context.application)
        return
    if data == "webapp_ready":
        await handle_webapp_ready(context.bot, uid, context.application)
        return
    if data == "open_howmany":
        await mark_webapp_opened(context.bot, uid, context.application)
        hm = howmany_webapp_url()
        if hm:
            await context.bot.send_message(
                uid,
                "💸 Калькулятор — нажмите «💸 Посчитать мой доход» "
                "в меню внизу 👇",
                reply_markup=main_reply_keyboard(uid),
            )
        else:
            await context.bot.send_message(
                uid,
                "Калькулятор пока настраивается. Напишите Вадиму 👇",
                reply_markup=kb([(BTN["contact"], CALL_LINK, True)]),
            )
        return
    if data != "claim_promo":
        return
    await mark_webapp_opened(context.bot, uid, context.application)
    user = update.effective_user
    rec = u(uid)
    promo = rec.get("promo") or {}
    if promo.get("deadline", 0) > time.time():
        await context.bot.send_message(
            uid,
            "Скидка уже закреплена — смотрите сообщение с таймером выше 👆\n\n"
            "Можно снова открыть «💎 Посмотреть форматы» — цены со скидкой.",
        )
        return
    if not PROMO_SECRET:
        await send_step(
            context.bot, uid,
            "Скидка пока настраивается. Напишите мне — подскажу по "
            "форматам 👇",
            [(BTN["contact"], CALL_LINK, True)],
        )
        return
    if not rec.get("temperature"):
        rec["temperature"] = "warm"
    save_state(STATE)
    await show_promo(context, uid, user, rec.get("temperature", "warm"),
                     from_app=True)


async def go_lead(update, context):
    """Забрать персональную скидку на обучение."""
    uid = update.effective_user.id
    bot = context.bot
    user = update.effective_user
    cancel_drips(context.application, uid)
    rec = u(uid)
    if is_funnel_locked(rec) and not is_exempt_user(user):
        await send_with_main_menu(bot, uid, TXT["return_locked"])
        return
    if promo_is_active(rec) and rec.get("bonus_claimed"):
        await send_with_main_menu(
            bot, uid,
            f"Скидка уже закреплена — осталось {fmt_left(rec['promo']['deadline'])} 👆",
        )
        return
    rec["full_name"] = user.full_name
    rec["username"] = user.username or ""
    rec["temperature"] = "warm"
    set_step(uid, "qualified")
    save_state(STATE)

    await show_promo(context, uid, user, "warm")
    track_milestone(uid, "qualified")
    schedule_step_drips(context.application, uid, "qualified")

    # уведомление тебе
    if ADMIN_ID:
        uname = f"@{user.username}" if user.username else "(без username)"
        dl = rec.get("promo", {}).get("deadline")
        promo_line = ""
        if dl:
            promo_line = (f"\nСкидка до: {datetime.fromtimestamp(dl):%d.%m %H:%M} "
                          f"(осталось {fmt_left(dl)})")
        try:
            await bot.send_message(
                ADMIN_ID,
                f"🔥 НОВАЯ ЗАЯВКА — скидка −{PROMO_DISCOUNT}%\n"
                f"Имя: {user.full_name}\n"
                f"Username: {uname}\n"
                f"ID: {user.id}\n"
                f"Чат: tg://user?id={user.id}"
                f"{promo_line}",
            )
        except Exception as e:
            log.error("notify admin failed: %s", e)


async def on_main_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Нижнее меню: результаты, гайд, подсказка по форматам."""
    msg = update.effective_message
    if not msg or not msg.text:
        return
    uid = update.effective_user.id
    text = msg.text.strip()
    if text not in (
        MENU_FORMATS, MENU_RESULTS, MENU_GUIDE, MENU_ABOUT, MENU_EARN,
        MENU_QUESTIONS,
    ) and not is_menu_formats_text(text):
        return
    bot = context.bot
    if text == MENU_QUESTIONS:
        await send_with_main_menu(
            bot, uid,
            "Напишите мне — отвечу лично 👇",
            clear_inline=False, skip_questions_hint=True,
        )
        await bot.send_message(
            uid, "👇",
            reply_markup=kb([(BTN["contact"], CALL_LINK, True)]),
        )
        return
    if text == MENU_EARN:
        hm = howmany_webapp_url()
        if hm:
            await send_with_main_menu(bot, uid, TXT["menu_earn"], clear_inline=False)
        else:
            await send_with_main_menu(
                bot, uid,
                "Калькулятор скоро будет в меню. Пока — напишите Вадиму 👇",
                clear_inline=False,
            )
            await bot.send_message(
                uid, "👇",
                reply_markup=kb([(BTN["contact"], CALL_LINK, True)]),
            )
        return
    if text == MENU_ABOUT:
        await send_with_main_menu(bot, uid, TXT["menu_about"], clear_inline=False)
        await bot.send_message(
            uid, "👇",
            reply_markup=InlineKeyboardMarkup([[
                InlineKeyboardButton(BTN["about_open"], url=ABOUT_LINK),
            ]]),
        )
        return
    if text == MENU_RESULTS:
        await send_with_main_menu(bot, uid, TXT["menu_results"], clear_inline=False)
        await bot.send_message(
            uid, "👇",
            reply_markup=InlineKeyboardMarkup([[
                InlineKeyboardButton(BTN["results_open"], url=RESULTS_LINK),
            ]]),
        )
        return
    if text == MENU_GUIDE:
        rec = u(uid)
        if rec.get("got_guide"):
            await send_guide(bot, uid)
            await send_with_main_menu(
                bot, uid,
                "Гайд уже у вас — отправил ещё раз 👇",
                clear_inline=False, skip_questions_hint=True,
            )
            return
        set_step(uid, "offer")
        await show_lead_magnet_offer(bot, uid)
        return
    if is_menu_formats_text(text):
        set_step(uid, "offer")
        await mark_webapp_opened(bot, uid, context.application)
        if WEBAPP_URL:
            label = formats_menu_label(uid)
            await refresh_main_keyboard(
                bot, uid,
                f"👇 «{label}» — нажмите ещё раз, если приложение "
                f"открылось без скидки",
            )
        else:
            await go_programs(update, context)
        return


async def go_guide(update, context):
    """Человек нажал «Забрать гайд» — показываем лид-магнит (подписка → гайд)."""
    uid = update.effective_user.id
    bot = context.bot
    rec = u(uid)
    if rec.get("got_guide"):
        await send_guide(bot, uid)
        await send_with_main_menu(
            bot, uid,
            "Гайд уже у вас — отправил ещё раз 👇",
        )
        return
    set_step(uid, "offer")
    await show_lead_magnet_offer(bot, uid)


async def on_button(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    d = q.data or ""
    await safe_answer_callback(q, d)
    uid = user_id_from(update)
    await _on_button_impl(update, context, d, uid)


async def _on_button_impl(update: Update, context: ContextTypes.DEFAULT_TYPE,
                          d, uid):
    q = update.callback_query
    if not d.startswith("mk_"):
        active = u(uid).get("active_callbacks") or []
        if active and d not in active:
            try:
                await context.bot.send_message(
                    uid,
                    "👆 Эта кнопка уже неактивна — нажмите кнопку "
                    "в последнем сообщении ниже.",
                )
            except Exception:
                pass
            return
    routes = {
        "go_intro":         go_intro,
        "go_v1_prep":       go_v1_prep,
        "go_v1_play":       go_v1_play,
        "go_v1_proofs":     go_v1_proofs,
        "go_v2_prep":       go_v2_prep,
        "go_v2_video":      go_v2_video,
        "go_v2_proofs":     go_v2_proofs,
        "go_v2_bridge":     go_v2_bridge,
        "go_v3_confirm":    go_v3_confirm,
        "go_v3_prep":       go_v3_prep,
        "go_v3_video":      go_v3_video,
        "go_v3_after":      go_v3_after,
        "go_calc":          go_calc,
        "go_fork":          go_fork,
        "go_offer":         go_offer,
        "go_offer_menu":    go_offer_menu,
        "go_offer_steps":   go_offer_steps,
        "go_offer_checks":  go_offer_checks,
        "go_offer_formats": go_offer_formats,
        "to_offer":         go_offer_menu,
        "go_programs":      go_programs,
        "go_students":      go_students,
        "go_lead":          go_lead,
        "activate_bonus":   activate_bonus,
        "go_guide":         go_guide,
        "lm_want":          lm_want,
        "lm_skip":          lm_skip,
        "lm_check":         lm_check,
    }
    if d in routes:
        await run_funnel_step(routes[d], update, context)
        return
    if d.startswith("mk_"):
        # mk_{lead_id}_{status} — только админ
        if not is_bot_admin(update.effective_user):
            return
        _, lead_id, status = d.split("_", 2)
        rec = STATE.get(lead_id)
        if rec:
            rec["outcome"] = status
            save_state(STATE)
            names = {"paid": "✅ оплатил", "booked": "📅 записан",
                     "noshow": "🚫 не пришёл", "lost": "❌ отказ"}
            await q.edit_message_text(
                f"{q.message.text}\n\n➡️ Статус обновлён: "
                f"{names.get(status, status)}")


# ---------------- АДМИН-КОМАНДЫ ----------------

async def cmd_id(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_bot_admin(update.effective_user):
        return
    me = await context.bot.get_me()
    await update.message.reply_text(
        f"Режим file_id для @{me.username}.\n\n"
        "Пришли сюда кружок или видео (прикрепить → Видео, не «Файл») — "
        "ответом пришлю file_id для MEDIA в bot.py.\n\n"
        "После правок в коде — redeploy на Railway.\n"
        "Проверка без отправки гигабайтов: /checkmedia"
    )


async def cmd_bot(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_bot_admin(update.effective_user):
        return
    me = await context.bot.get_me()
    token_bot_id = BOT_TOKEN.split(":", 1)[0] if BOT_TOKEN and ":" in BOT_TOKEN else "?"
    await update.message.reply_text(
        f"Сейчас работает: @{me.username} (telegram id {me.id})\n"
        f"ID в BOT_TOKEN: {token_bot_id}\n\n"
        "file_id в MEDIA действуют только для этого бота. "
        "Если видео снимали с другого токена — будет "
        "«Wrong file identifier».\n\n"
        "/checkmedia — проверить все ролики\n"
        "/id — заново снять file_id"
    )


async def cmd_checkmedia(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_bot_admin(update.effective_user):
        return
    me = await context.bot.get_me()
    lines = [f"Проверка MEDIA для @{me.username}:\n"]
    for key, ref in MEDIA.items():
        fid = ref.get("file_id")
        kind = ref.get("kind") or detect_kind(fid or "")
        ok, msg = await probe_file_id(context.bot, fid)
        icon = "✅" if ok else "❌"
        lines.append(f"{icon} {key} ({kind}): {msg}")
    lines.append("\nHOWMANY_SCREENS (калькулятор):")
    for i, item in enumerate(HOWMANY_SCREENS, 1):
        fid = item.get("file_id", "")
        ok, msg = await probe_file_id(context.bot, fid)
        icon = "✅" if ok else "❌"
        lines.append(f"{icon} howmany_{i}: {msg}")
    lines.append(
        "\n❌ = file_id не от этого бота или устарел.\n"
        "Исправление: перешли ролик ЭТОМУ боту → /id → вставь в MEDIA → redeploy."
    )
    await update.message.reply_text("\n".join(lines))


async def grab_file_id(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_bot_admin(update.effective_user):
        return
    m = update.message
    cap = (m.caption or m.text or "").strip().lower()
    if not cap.startswith("/fid") and not cap.startswith("fid"):
        return
    out = None
    if m.video_note:
        out = (
            f"КРУЖОК (video_note, {m.video_note.duration} сек)\n"
            f"file_id:\n{m.video_note.file_id}\n\n"
            f'В MEDIA: "sec": {m.video_note.duration}\n'
            "После вставки — redeploy, /checkmedia."
        )
    elif m.video:
        out = (
            f"ВИДЕО ({m.video.duration} сек)\n"
            f"file_id:\n{m.video.file_id}\n\n"
            f'В MEDIA: "kind": "video", "sec": {m.video.duration}\n\n'
            "Вставь в bot.py и сделай redeploy на Railway.\n"
            "Потом /checkmedia — должно быть ✅."
        )
    elif m.photo:
        out = (
            f"ФОТО\nfile_id:\n{m.photo[-1].file_id}\n\n"
            "Для калькулятора — в HOWMANY_SCREENS в bot.py (4 штуки)."
        )
    elif m.document:
        mt = m.document.mime_type or ""
        extra = ""
        if "pdf" in mt:
            extra = ("\n\nЭто PDF — можешь использовать как GUIDE_FILE_ID "
                     "(env), чтобы не хранить файл.")
        else:
            extra = ("\n\nЕсли это видео — пришли через «прикрепить → Видео», "
                     "чтобы играло inline.")
        out = (f"ДОКУМЕНТ ({mt})\nfile_id:\n{m.document.file_id}{extra}")
    if out:
        await m.reply_text(out)


async def cmd_stats(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_bot_admin(update.effective_user):
        return
    counts = {}
    guide_count = 0
    temp = {"hot": 0, "warm": 0, "cold": 0}
    promo_issued = promo_active = 0
    outcomes = {}
    now = time.time()
    for rec in STATE.values():
        s = rec.get("step", "start")
        counts[s] = counts.get(s, 0) + 1
        if rec.get("got_guide"):
            guide_count += 1
        t = rec.get("temperature")
        if t in temp:
            temp[t] += 1
        promo = rec.get("promo")
        if promo:
            promo_issued += 1
            if promo.get("deadline", 0) > now:
                promo_active += 1
        oc = rec.get("outcome")
        if oc:
            outcomes[oc] = outcomes.get(oc, 0) + 1
    order = ["start", "intro", "v1", "v2", "v3", "fork",
             "offer", "lead", "qualified", "qualified_cold"]
    lines = ["📊 Воронка (кто на каком шаге сейчас):"]
    for s in order:
        lines.append(f"{s}: {counts.get(s, 0)}")
    lines.append(f"\n🌡 Тёплых: {temp['warm']} · Горячих: {temp['hot']} · "
                 f"Холодных: {temp['cold']}")
    lines.append(f"🔥 Промо выдано: {promo_issued} (активно сейчас: {promo_active})")
    lines.append(f"🎁 Забрали гайд: {guide_count}")
    app_opened = sum(1 for r in STATE.values() if r.get("webapp_opened"))
    app_engaged = sum(1 for r in STATE.values() if r.get("webapp_engaged"))
    lines.append(
        f"📱 Открыли Mini App: {app_opened} · "
        f"30+ сек в аппке: {app_engaged}"
    )
    if outcomes:
        oc_str = " · ".join(f"{k}: {v}" for k, v in outcomes.items())
        lines.append(f"📌 Статусы: {oc_str}")
    lines.append(f"\nВсего людей: {len(STATE)}")
    lines.append("\n/report — все лиды (Excel, листы по месяцам)")
    lines.append("Авто: 09:00 — 24ч | пн — 7д | 1-е — прошлый месяц")
    lines.append(f"UTM: {BOT_LINK}?start=tg")
    lines.append(f"     {BOT_LINK}?start=you")
    lines.append(f"     {BOT_LINK}?start=inst")
    lines.append("/lead ID — карточка лида + смена статуса")
    await update.message.reply_text("\n".join(lines))


async def cmd_report(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Все лиды: Excel с листом «Все» и отдельными листами по месяцам входа."""
    if not is_bot_admin(update.effective_user):
        return
    leads = list(STATE.items())
    if not leads:
        await update.message.reply_text("База лидов пуста.")
        return
    sections = build_report_sections(leads, include_all_sheet=True)
    fname = f"leads_all_{datetime.now():%Y%m%d_%H%M}"
    try:
        bio = build_report_xlsx(sections)
        ext = "xlsx"
    except ImportError:
        await update.message.reply_text(
            "Нужен пакет openpyxl (pip install openpyxl). "
            "На Railway — redeploy после обновления requirements.txt.")
        return
    bio.name = f"{fname}.{ext}"
    await context.bot.send_document(
        update.effective_user.id, bio,
        caption=(
            f"📊 Все лиды: {len(leads)} чел.\n"
            "Листы: «Все лиды» + по месяцам (Май 2026, Июнь 2026…)."
        ),
    )


async def cmd_lead(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Карточка одного лида + кнопки смены статуса."""
    if not is_bot_admin(update.effective_user):
        return
    parts = (update.message.text or "").split()
    if len(parts) < 2:
        await update.message.reply_text("Использование: /lead ID\n"
                                        "ID берётся из уведомления о заявке.")
        return
    lead_id = parts[1].strip()
    rec = STATE.get(lead_id)
    if not rec:
        await update.message.reply_text("Лид с таким ID не найден.")
        return
    a = rec.get("answers", {})
    promo = rec.get("promo") or {}
    dl = promo.get("deadline")
    dl_str = (f"{datetime.fromtimestamp(dl):%d.%m %H:%M} "
              f"({fmt_left(dl)})") if dl else "—"
    uname = f"@{rec['username']}" if rec.get("username") else "—"
    txt = (
        f"👤 {rec.get('full_name','—')}  {uname}\n"
        f"ID: {lead_id}\n"
        f"Чат: tg://user?id={lead_id}\n\n"
        f"Температура: {rec.get('temperature','—')}\n"
        f"Шаг: {rec.get('step','—')}\n"
        f"Бюджет: {a.get('q1','—')} · Время: {a.get('q2','—')} · "
        f"Старт: {a.get('q3','—')}\n"
        f"Гайд забрал: {'да' if rec.get('got_guide') else 'нет'}\n"
        f"Промо: {'выдано, до '+dl_str if promo else 'нет'}\n"
        f"Статус: {rec.get('outcome','не задан')}\n\n"
        f"Отметить статус:"
    )
    await update.message.reply_text(txt, reply_markup=kb([
        [("✅ Оплатил", f"mk_{lead_id}_paid", False),
         ("📅 Записан", f"mk_{lead_id}_booked", False)],
        [("🚫 Не пришёл", f"mk_{lead_id}_noshow", False),
         ("❌ Отказ", f"mk_{lead_id}_lost", False)],
    ]))


async def cmd_reset(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_bot_admin(update.effective_user):
        return
    uid = str(update.effective_user.id)
    cancel_drips(context.application, update.effective_user.id)
    if uid in STATE:
        del STATE[uid]
        save_state(STATE)
    await update.message.reply_text(
        "Готово. Напиши /start — воронка пойдёт заново."
    )


async def cmd_clean(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Админ @vadjik: сброс прогресса, скидки, меню и localStorage аппки."""
    if not is_bot_admin(update.effective_user):
        return
    uid = update.effective_user.id
    bot = context.bot
    await full_reset_user_for_test(bot, uid, context.application)
    await update.message.reply_text(
        "🧹 Готово. Меню обновлено — «Форматы» без скидки.\n"
        "Нажми «💎 Форматы…» внизу (новая кнопка), затем /start или /check."
    )


async def _admin_prepare_jump(bot, uid, application):
    """Общая подготовка перед тестовым прыжком по воронке."""
    cancel_drips(application, uid)
    cancel_funnel_pause_jobs(application, uid)
    rec = u(uid)
    rec["funnel_claims"] = []
    rec["last_kb_msg"] = None
    rec["active_callbacks"] = []
    invalidate_active_callbacks(uid)
    await clear_nudge(bot, uid)
    set_user_fast_mode(uid, True)
    save_state(STATE)


async def _admin_jump_offer_after_fork(bot, uid, application):
    """2-й кружок → оффер + меню (для /check)."""
    await _admin_prepare_jump(bot, uid, application)
    if not await send_circle(bot, uid, "circle_fork"):
        await bot.send_message(
            uid,
            "⚠️ Кружок circle_fork не загрузился — проверь /checkmedia",
        )
        return False
    set_step(uid, "offer")
    track_milestone(uid, "after_fork")
    await send_step(
        bot, uid, TXT["after_fork_circle"],
        fork_inline_rows(uid),
        skip_pause=True, skip_questions_hint=True,
        milestone="after_fork",
    )
    await refresh_main_keyboard(
        bot, uid,
        "👇 Кнопки меню закреплены внизу — ими можно пользоваться "
        "в любой момент.",
    )
    schedule_bonus_remind(application, uid)
    return True


async def _admin_jump_calc_pitch(bot, uid, application):
    """Шаг «откройте калькулятор» (для /calculator)."""
    await _admin_prepare_jump(bot, uid, application)
    set_step(uid, "v3")
    track_milestone(uid, "calc_pitch")
    hm = howmany_webapp_url()
    if hm:
        rows = [
            [(BTN["calc_open"], hm, "webapp")],
            [(BTN["calc_skip"], "go_fork", False)],
        ]
        await send_step(
            bot, uid, TXT["calc_pitch"], rows,
            skip_pause=True, milestone="calc_pitch",
        )
    else:
        await send_step(
            bot, uid, TXT["calc_pitch_nourl"],
            [(BTN["calc_to_fork"], "go_fork", False)],
            skip_pause=True, milestone="calc_pitch",
        )
    return True


async def cmd_check(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Админ: FAST + последний кружок → оффер и меню (тест аппки)."""
    if not is_bot_admin(update.effective_user):
        return
    uid = update.effective_user.id
    bot = context.bot
    ok = await _admin_jump_offer_after_fork(bot, uid, context.application)
    if ok:
        await update.message.reply_text(
            "✅ /check — FAST включён, 2-й кружок и оффер отправлены.\n"
            "Меню внизу: форматы, калькулятор, гайд.\n"
            "Сброс: /clean → /start"
        )


async def cmd_calculator(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Админ: FAST + шаг «откройте калькулятор»."""
    if not is_bot_admin(update.effective_user):
        return
    uid = update.effective_user.id
    bot = context.bot
    await _admin_jump_calc_pitch(bot, uid, context.application)
    hm = howmany_webapp_url()
    if hm:
        await update.message.reply_text(
            "✅ /calculator — FAST включён, шаг калькулятора отправлен.\n"
            "Дальше: «Узнать мою цифру» или «Пропустить» → к форматам."
        )
    else:
        await update.message.reply_text(
            "✅ Шаг калькулятора отправлен, но HOWMANY_URL не настроен — "
            "кнопка вебапп не появится."
        )


async def cmd_programs(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Открыть витрину программ в любой момент."""
    await go_programs(update, context)


async def cmd_howmany(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Калькулятор — кнопка «Сколько заработать» в меню (Mini App)."""
    uid = update.effective_user.id
    bot = context.bot
    if not howmany_webapp_url():
        await bot.send_message(
            uid,
            "Калькулятор пока не подключён.",
        )
        return
    await send_with_main_menu(
        bot, uid,
        "💸 Нажмите «💸 Посчитать мой доход» в меню внизу — "
        "откроется "
        "калькулятор со скринами 👇",
        clear_inline=False,
    )


async def cmd_webappcheck(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Админ: проверить, что на WEBAPP_URL лежит актуальный index.html."""
    if not is_bot_admin(update.effective_user):
        return
    url = webapp_url_full()
    if not url:
        await update.message.reply_text("WEBAPP_URL не задан.")
        return
    try:
        import urllib.request
        req = urllib.request.Request(
            url, headers={"User-Agent": "TelegramBot/WebAppCheck"},
        )
        with urllib.request.urlopen(req, timeout=15) as resp:
            body = resp.read(12000).decode("utf-8", errors="replace")
    except Exception as e:
        await update.message.reply_text(
            f"❌ Не удалось открыть Mini App:\n{url}\n\n{e}"
        )
        return
    issues = []
    if "sendData('webapp_open')" in body and "wa=1" not in body:
        issues.append("⚠️ sendData('webapp_open') закрывает аппку — лучше wa=1 + меню")
    if "setTimeout(function(){ pingBot('webapp_ready')" in body:
        issues.append("⚠️ webapp_ready через 30 сек — лишнее")
    build = "не найдена"
    m = re.search(r"app-build:([\w]+)", body)
    if m:
        build = m.group(1)
    ok = build == WEBAPP_BUILD and not issues
    lines = [
        f"{'✅' if ok else '❌'} Mini App: {WEBAPP_URL}",
        f"Сборка на сервере: {build}",
        f"Ожидается: {WEBAPP_BUILD}",
        f"Размер ответа: {len(body)} байт",
    ]
    if issues:
        lines.append("")
        lines.extend(issues)
    if not ok:
        lines.append(
            "\nЗалей свежий index.html из Desktop\\ббб на GitHub Pages "
            "(репо apppp) и подожди 1–2 мин."
        )
    await update.message.reply_text("\n".join(lines))


async def cmd_pauses(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Паузы только для твоего chat_id — клиенты не затрагиваются."""
    user = update.effective_user
    if not is_bot_admin(user):
        return
    uid = user.id
    rec = u(uid)
    rec["pauses_off"] = not rec.get("pauses_off")
    rec["fast_mode"] = False
    save_state(STATE)
    if not rec["pauses_off"]:
        txt = (
            f"⏳ Паузы для тебя — как у клиентов:\n"
            f"кружок → {int(CIRCLE_PAUSE_SEC)}с, видео → {int(MEDIA_TO_TEXT_PAUSE_SEC)}с, "
            f"текст → {int(MIN_TEXT_PAUSE)}–{int(SHORT_TEXT_MAX_PAUSE)}с (короткий) / до {int(MAX_TEXT_PAUSE)}с (длинный).\n\n"
            f"/pauses — выкл всё для себя · /fast — без пауз только на видео/кружки."
        )
    else:
        txt = (
            "⚡ Паузы выключены только для тебя — воронка летит без задержек.\n\n"
            "/pauses — вернуть как у клиентов."
        )
    await update.message.reply_text(txt)


async def cmd_fast(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """FAST: /fast — себе (переключить), /fast @user — включить другому."""
    user = update.effective_user
    if not is_bot_admin(user):
        return
    args = context.args or []
    if args:
        needle = normalize_username(args[0])
        target = find_uid_by_username(needle)
        if not target:
            await update.message.reply_text(
                f"@{needle} не найден в базе бота.\n"
                "Человек должен хотя бы раз нажать /start."
            )
            return
        set_user_fast_mode(target, True)
        uname = u(target).get("username") or needle
        await update.message.reply_text(
            f"⏩ FAST включён для @{normalize_username(uname)} (id {target}).\n"
            f"Выключить: /fastoff @{normalize_username(uname)}"
        )
        return
    uid = user.id
    rec = u(uid)
    rec["fast_mode"] = not rec.get("fast_mode")
    if rec["fast_mode"]:
        rec["pauses_off"] = False
    save_state(STATE)
    if rec["fast_mode"]:
        await update.message.reply_text(
            "⏩ FAST для тебя — видео и кружки без пауз, текст по длине.\n\n"
            "/fast — выкл · /fast @username — включить другому."
        )
    else:
        await update.message.reply_text(
            "FAST выключен для тебя."
        )


async def cmd_fastoff(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """/fastoff @user — выключить FAST у пользователя."""
    user = update.effective_user
    if not is_bot_admin(user):
        return
    args = context.args or []
    if not args:
        await update.message.reply_text(
            "Использование: /fastoff @username\n"
            "Пример: /fastoff @CREAT113"
        )
        return
    needle = normalize_username(args[0])
    target = find_uid_by_username(needle)
    if not target:
        await update.message.reply_text(
            f"@{needle} не найден в базе бота."
        )
        return
    set_user_fast_mode(target, False)
    uname = u(target).get("username") or needle
    await update.message.reply_text(
        f"FAST выключен для @{normalize_username(uname)} (id {target})."
    )


async def on_error(update, context):
    """Логирует ошибки аккуратно, без пугающих трейсбеков в консоль.
    409 Conflict при редеплое (на секунду два экземпляра) — не страшно."""
    err = context.error
    if "Conflict" in str(err):
        log.error(
            "409 Conflict — бот запущен в ДВУХ местах одновременно! "
            "Останови лишний экземпляр (Railway + локальный ПК, или два деплоя). "
            "Пока два процесса живы — апдейты теряются и кажется, что бот «завис»."
        )
        return
    err_s = str(err).lower()
    if "too old" in err_s or "query id is invalid" in err_s:
        log.debug("Протухшая inline-кнопка (после redeploy или долгой очереди): %s", err)
        return
    log.error("Ошибка при обработке апдейта: %s", err)


async def post_init(application):
    """При старте: кто мы в Telegram и валидны ли file_id для этого токена."""
    try:
        me = await application.bot.get_me()
        log.info(
            "Telegram @%s (id=%s) — MEDIA file_id должны быть сняты у ЭТОГО бота",
            me.username, me.id,
        )
        bad = []
        for key, ref in MEDIA.items():
            fid = ref.get("file_id")
            if not fid:
                continue
            ok, msg = await probe_file_id(application.bot, fid)
            if not ok:
                bad.append(f"{key}: {msg}")
        if bad:
            log.error(
                "MEDIA невалидны для текущего BOT_TOKEN: %s",
                "; ".join(bad),
            )
        bad_hm = []
        for i, item in enumerate(HOWMANY_SCREENS, 1):
            fid = item.get("file_id")
            if not fid:
                continue
            ok, msg = await probe_file_id(application.bot, fid)
            if not ok:
                bad_hm.append(f"howmany_{i}: {msg}")
        if bad_hm:
            log.error(
                "HOWMANY_SCREENS невалидны для BOT_TOKEN: %s",
                "; ".join(bad_hm),
            )
        await refresh_howmany_img_urls(application.bot)
        await asyncio.to_thread(refresh_flow_cache_sync)
    except Exception as e:
        log.warning("post_init: %s", e)
    setup_auto_reports(application)
    restore_bonus_reminds(application)
    restore_step_drips(application)
    asyncio.create_task(_state_flush_loop())
    log.info("Фоновое сохранение users.json включено (не блокирует других пользователей)")


async def post_shutdown(application):
    await flush_state_now()


def restore_bonus_reminds(application):
    if not application.job_queue:
        return
    count = 0
    for uid, rec in STATE.items():
        if should_bonus_remind(rec):
            schedule_bonus_remind(application, uid)
            count += 1
    if count:
        log.info("bonus_remind: восстановлено для %s пользователей", count)


def main():
    if not BOT_TOKEN:
        print("ОШИБКА: задай BOT_TOKEN в Railway Variables или .env")
        return

    if not WEBAPP_URL:
        log.warning("WEBAPP_URL не задан — Mini App не откроется, форматы текстом.")

    if not PROMO_SECRET:
        log.warning("PROMO_SECRET не задан — персональные скидки не выдаются.")

    from telegram.request import HTTPXRequest
    tg_request = HTTPXRequest(
        connection_pool_size=64,
        read_timeout=90,
        write_timeout=90,
        connect_timeout=30,
        pool_timeout=30,
    )

    app = (
        Application.builder()
        .token(BOT_TOKEN)
        .request(tg_request)
        .concurrent_updates(True)
        .post_init(post_init)
        .post_shutdown(post_shutdown)
        .build()
    )

    app.add_handler(CommandHandler("start", cmd_start))
    app.add_handler(CommandHandler("programs", cmd_programs))
    app.add_handler(CommandHandler("howmany", cmd_howmany))
    app.add_handler(CommandHandler("webappcheck", cmd_webappcheck))
    app.add_handler(CommandHandler("pauses", cmd_pauses))
    app.add_handler(CommandHandler("fast", cmd_fast))
    app.add_handler(CommandHandler("fastoff", cmd_fastoff))
    app.add_handler(CommandHandler("id",    cmd_id))
    app.add_handler(CommandHandler("bot", cmd_bot))
    app.add_handler(CommandHandler("checkmedia", cmd_checkmedia))
    app.add_handler(CommandHandler("stats", cmd_stats))
    app.add_handler(CommandHandler("report", cmd_report))
    app.add_handler(CommandHandler("lead", cmd_lead))
    app.add_handler(CommandHandler("reset", cmd_reset))
    app.add_handler(CommandHandler("clean", cmd_clean))
    app.add_handler(CommandHandler("check", cmd_check))
    app.add_handler(CommandHandler("calculator", cmd_calculator))
    app.add_handler(CallbackQueryHandler(on_button))
    app.add_handler(MessageHandler(filters.StatusUpdate.WEB_APP_DATA, on_webapp_data))
    app.add_handler(MessageHandler(main_menu_filter(), on_main_menu))
    app.add_handler(MessageHandler(
        filters.VIDEO | filters.VIDEO_NOTE | filters.PHOTO
        | filters.Document.ALL,
        grab_file_id,
    ))
    app.add_error_handler(on_error)

    log.info("Бот запущен. ADMIN_ID=%s, канал=%s, DATA=%s",
             ADMIN_ID, CHANNEL_USERNAME, STATE_FILE)
    app.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    main()
