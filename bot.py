# -*- coding: utf-8 -*-
"""
Amazon-воронка: Telegram-бот.  Боевая сборка для @vadjik.

╔══════════════════════════════════════════════════════════════════════╗
║  Перед запуском задай переменную окружения BOT_TOKEN.                 ║
║  Локальный запуск:  BOT_TOKEN=твой_токен python bot.py                ║
║  Деплой на Railway: переменные задаются в Variables                   ║
║                                                                       ║
║  Подробнее: ДЕПЛОЙ.md / НАСТРОЙКА.md                                  ║
╚══════════════════════════════════════════════════════════════════════╝
"""

import asyncio
import hashlib
import re
import hmac
import json
import logging
import os
import time
from datetime import datetime

from urllib.parse import quote, urlencode
from telegram import (
    Update, InlineKeyboardButton, InlineKeyboardMarkup, InputMediaPhoto,
    KeyboardButton, ReplyKeyboardMarkup, WebAppInfo,
)
from telegram.constants import ChatAction
from telegram.error import BadRequest
from telegram.ext import (
    Application, CommandHandler, CallbackQueryHandler,
    MessageHandler, ContextTypes, filters,
)

# ╔══════════════════════════════════════════════════════════════════════╗
# ║                          C   O   N   F   I   G                       ║
# ║                 Редактируй только то, что в этом блоке.              ║
# ╚══════════════════════════════════════════════════════════════════════╝


# ──────────────────────────────────────────────────────────────────────
# 1) СЕКРЕТЫ И ССЫЛКИ.
#    BOT_TOKEN — только через переменную окружения (не светим в коде).
#    Остальное — дефолты в коде, можно переопределить через env.
# ──────────────────────────────────────────────────────────────────────

BOT_TOKEN = os.getenv("BOT_TOKEN", "").strip()

ADMIN_ID  = int(os.getenv("ADMIN_ID", "0") or "0") or 630926654

# Ссылка для контакта — на твою личку.
CALL_LINK = os.getenv("CALL_LINK", "").strip() or "https://t.me/vadjik"

# Ссылка на твой сайт с результатами учеников.
SITE_LINK = os.getenv("SITE_LINK", "").strip() or "https://vadjik.com/"

RESULTS_LINK = os.getenv("RESULTS_URL", "").strip() or "https://vadjik.com/results"

# Подписи нижнего меню (Reply Keyboard) — должны совпадать с кнопками.
MENU_FORMATS = "💎 Форматы сотрудничества и обучения"
MENU_RESULTS = "📈 Результаты учеников"
MENU_GUIDE = "📘 Забрать гайд"

# Ссылка на Telegram Mini App (витрина тарифов + результатов).
# Это HTTPS-адрес, где захостен mini_app/index.html (см. MINI_APP.md).
# Если пусто — кнопка «Что входит» покажет тарифы текстом (fallback).
WEBAPP_URL = os.getenv("WEBAPP_URL", "").strip()


# ──────────────────────────────────────────────────────────────────────
# ПРОМО-СКИДКА (персональная ссылка со скидкой + таймер, синхрон с сайтом).
#
#   PROMO_SECRET   — ОБЩИЙ секрет с сайтом. Должен совпадать байт-в-байт.
#                    Задаётся ТОЛЬКО через переменную окружения.
#   DISCOUNT_URL   — страница скидок на сайте.
#   PROMO_HOURS    — на сколько часов даётся персональная скидка.
#
#   Бонус — персональная скидка на обучение (текст в TXT["promo_*"]).
#   Промо выдаётся ТЁПЛЫМ и ГОРЯЧИМ после квиза (не холодным).
# ──────────────────────────────────────────────────────────────────────

PROMO_SECRET = os.getenv("PROMO_SECRET", "").strip()
DISCOUNT_URL = os.getenv("DISCOUNT_URL", "").strip() or "https://vadjik.com/faster_discount"
PROMO_HOURS  = int(os.getenv("PROMO_HOURS", "24") or "24")
# Процент скидки — ТОЛЬКО для показа в Mini App (зачёркнутая цена → новая).
# ⚠️ Должен совпадать со скидкой, которую ты выставил на сайте, иначе
# в аппе человек увидит одну цену, а на сайте другую.
PROMO_DISCOUNT = int(os.getenv("PROMO_DISCOUNT", "20") or "20")


# ──────────────────────────────────────────────────────────────────────
# 2) ЛИД-МАГНИТ (подписка на канал в обмен на гайд).
#
#    CHANNEL_USERNAME — публичный @username твоего канала.
#    Бот ДОЛЖЕН быть админом этого канала, иначе не сможет проверять
#    подписку.
#
#    Гайд бот берёт так:
#      - GUIDE_FILE_ID (env или дефолт ниже) — отправка по file_id;
#      - иначе — файл guide.pdf рядом с bot.py.
#    file_id только от ЭТОГО бота → /id после пересылки PDF.
# ──────────────────────────────────────────────────────────────────────

CHANNEL_USERNAME = os.getenv("CHANNEL_USERNAME", "").strip() or "@ВПИШИ_КАНАЛ"

GUIDE_FILE_ID = (
    os.getenv("GUIDE_FILE_ID", "").strip()
    or "BQACAgIAAxkBAAIBMGoYngYvtSejdbzTGF6F_FKBc-LqAALYmwAClIrJSDEbEaQrNI_jOwQ"
)
GUIDE_FILENAME = "guide.pdf"  # имя файла рядом с bot.py


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


# ──────────────────────────────────────────────────────────────────────
# 5) ЗАДЕРЖКИ ДОГОНЯЮЩИХ (в часах).
# ──────────────────────────────────────────────────────────────────────

DRIP_HOURS = {
    "after_v1":     3,
    "after_v3":     6,
    "after_offer":  24,
    "after_lead":   12,
}


# ──────────────────────────────────────────────────────────────────────
# 6) ТЕКСТЫ. Меняй формулировки свободно.
# ──────────────────────────────────────────────────────────────────────

TXT = {
    "start": (
        "$750 чистыми на Amazon.\n\n"
        "Это не история про миллионные обороты и не «кнопку, которая "
        "печатает деньги».\n\n"
        "Также покажу учеников, которые выходят на $5 000–7 000 в месяц "
        "торговлей на Amazon — с реальными скриншотами из кабинета "
        "продавца.\n\n"
        "А начнём с первого нормального результата Игоря. Он пришёл без "
        "опыта и сначала вообще не понимал, с чего начать: где искать "
        "товар, как не купить ерунду и как не потерять деньги на первой "
        "закупке.\n\n"
        "Внутри — путь простыми словами:\n\n"
        "🎬 как Игорь вышел на первую прибыль\n"
        "⚙️ как работает заработок на Amazon\n"
        "🙅 почему многие так и не начинают, хотя могли бы\n\n"
        "Сначала коротко расскажу, кто я и почему вообще могу об этом "
        "говорить 👇\n\n"
        "🎁 В конце пути — бесплатный PDF «3 ошибки новичка на Amazon»: "
        "что ломает старт и как действовать правильно до первой закупки."
    ),
    "after_circle_intro": (
        "Теперь вы понимаете, кто я и почему занимаюсь Amazon 🙂\n\n"
        "Дальше — как именно начинался путь у Игоря. Это около 4 минут 👇"
    ),
    "before_v1": (
        "Включайте 👇\n\n"
        "Сейчас покажу историю Игоря коротко и по делу:\n\n"
        "1. с чего он начал;\n"
        "2. почему первый выбор товаров не подошёл;\n"
        "3. что он исправил;\n"
        "4. как вышел на первые чистые деньги."
    ),
    "after_v1_video": (
        "Досмотрели? 👇\n\n"
        "Дальше — разбор: почему первый список товаров не сработал и "
        "что изменилось после правок."
    ),
    "proofs_v1_caption": (
        "Вот почему этот пример важен.\n\n"
        "Кстати, выше — реальные результаты учеников на Amazon. Такого "
        "уровня можно достичь, если идти по шагам, а не «угадывать» "
        "товар наугад.\n\n"
        "Игорь не нашёл хороший товар с первого раза. Первый список был "
        "слабый: где-то не сходились цифры, где-то товар был не тот, "
        "где-то покупка просто не имела смысла.\n\n"
        "Но он получил правки, переделал работу — и уже во второй раз "
        "нашёл несколько нормальных вариантов.\n\n"
        "Дальше всё пошло по цепочке:\n\n"
        "закупка → подготовка товара → отправка на Amazon → продажи → "
        "чистая прибыль.\n\n"
        "Это нормальный живой путь. Не «нажал кнопку и заработал», а "
        "сделал шаги, исправил ошибки и получил результат."
    ),
    "after_v1": (
        "Смысл не в том, что Игорь сразу всё понял.\n\n"
        "Сначала он ошибся — и именно поэтому пример нормальный.\n\n"
        "Теперь разберём саму схему: откуда берётся прибыль на Amazon "
        "и что делает продавец 👇"
    ),
    "after_v2_video": (
        "Досмотрели? 👇\n\n"
        "Дальше — примеры: как эта модель выглядит на разных рынках."
    ),
    "bridge_v2": (
        "Суть простая.\n\n"
        "На Amazon уже есть покупатели. Люди каждый день заходят и "
        "покупают товары.\n\n"
        "Вам не нужно создавать новый товар, делать бренд и уговаривать "
        "людей купить.\n\n"
        "Задача другая:\n\n"
        "1. найти товар, который уже покупают\n"
        "2. найти место, где его можно купить дешевле\n"
        "3. проверить расходы\n"
        "4. отправить товар на склад Amazon\n"
        "5. забрать разницу после продажи\n\n"
        "В следующем видео покажу всю схему по шагам 👇"
    ),
    "proofs_v2_caption": (
        "Вот в этом и смысл модели.\n\n"
        "Вы не пытаетесь создать спрос с нуля. Спрос уже есть. Покупатели "
        "уже есть. Товары уже продаются.\n\n"
        "Ваша задача — найти товар, где сходятся три вещи:\n\n"
        "1. его можно купить дешевле;\n"
        "2. его уже покупают на Amazon;\n"
        "3. после всех расходов остаётся прибыль.\n\n"
        "Когда такой товар найден, дальше начинается понятный цикл:\n\n"
        "купили → подготовили → отправили → продали → часть денег снова "
        "вложили в товар."
    ),
    "after_v2": (
        "Теперь вы понимаете, как это работает 🙂\n\n"
        "Но есть важный момент: даже когда человек понимает схему, он "
        "часто всё равно не начинает.\n\n"
        "Обычно мешают одни и те же страхи:\n\n"
        "«нет денег»\n"
        "«нет времени»\n"
        "«я не знаю язык»\n"
        "«а вдруг заблокируют»\n"
        "«уже поздно заходить»\n"
        "«там слишком много конкурентов»\n\n"
        "Дальше — честный разбор этих причин (~7 мин). Нажмите кнопку — "
        "видео сразу откроется 👇"
    ),
    "v3_loading": (
        "▶️ Загружаю разбор страхов (~7 мин).\n\n"
        "Подождите несколько секунд — видео появится следующим сообщением."
    ),
    "after_v3_video": (
        "Досмотрели? 👇\n\n"
        "Если дошли до конца — у вас уже есть база: путь Игоря, схема "
        "и честный разбор страхов."
    ),
    "after_v3": (
        "Дальше — как пройти этот путь без хаоса и лишних ошибок 👇"
    ),
    "after_v1_proofs": (
        "Готовы к следующему шагу? 👇\n\n"
        "Покажу, откуда вообще берётся прибыль на Amazon — простыми "
        "словами."
    ),
    "after_v2_proofs": (
        "Видели примеры по странам? 👇\n\n"
        "Дальше — честный разбор: почему люди понимают схему, но не "
        "начинают."
    ),
    "after_fork_circle": (
        "Смотрите.\n\n"
        "Разобраться самому можно. Но проблема не в том, что информации "
        "мало.\n\n"
        "Новичок часто не понимает, где ошибка станет дорогой:\n\n"
        "— плохой поставщик;\n"
        "— товар, который не продаётся;\n"
        "— ошибки в документах;\n"
        "— неправильный расчёт прибыли.\n\n"
        "Поэтому я сделал формат, где можно идти по шагам, с проверками "
        "и поддержкой.\n\n"
        "Разделы — в меню внизу 👇\n\n"
        "🔥🔥 Кстати, зайдите в «Форматы сотрудничества и обучения» — "
        "для вас там супер-бонус! 🔥🔥"
    ),
    "after_fork_menu_hint": (
        "Всё подробно — в меню внизу 👇\n\n"
        "• форматы и обучение — мини-приложение\n"
        "• результаты учеников — сайт\n"
        "• PDF-гайд — бесплатно"
    ),
    "menu_results": (
        "Результаты учеников — на сайте, со скринами и цифрами 👇"
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
    "drip_after_v1": (
        "Вы остановились на важном месте 🙂\n\n"
        "Дальше я объясняю, откуда вообще берётся прибыль на Amazon и "
        "почему Игорь смог выйти на результат не через удачу, а через "
        "понятную схему.\n\n"
        "Посмотрите следующее видео 👇"
    ),
    "drip_after_v3": (
        "Вы почти дошли до конца 🙌\n\n"
        "Остался шаг, где я объясняю, как можно пройти этот путь не "
        "самому в хаосе, а по структуре и с поддержкой.\n\n"
        "Продолжим? 👇"
    ),
    "drip_after_offer": (
        "Если ещё смотрите — откройте раздел в меню внизу или заберите "
        "скидку 👇"
    ),
    "drip_after_lead": (
        "Вы забрали бонус — я на связи 🙌\n\n"
        "Если удобнее написать напрямую, вот мой контакт 👇"
    ),
    "lm_offer": (
        "Перед стартом дам полезный материал 🎁\n\n"
        "Это гайд по ошибкам, из-за которых новички чаще всего теряют "
        "деньги на Amazon.\n\n"
        "Внутри не просто «что не делать», а разбор:\n\n"
        "— как обычно ошибаются;\n"
        "— к чему это приводит;\n"
        "— как действовать правильно;\n"
        "— что проверить до первой закупки.\n\n"
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
        "Если захотите разобрать вашу ситуацию — нажмите кнопку ниже 👇"
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
}

# Напоминания о PDF-гайде в воронке (ротация, до GUIDE_TEASER_MAX раз).
GUIDE_TEASER_MAX = 5
GUIDE_TEASERS = [
    (
        "Некоторые ошибки на Amazon стоят очень дорого. В конце вы получите "
        "бесплатный гайд с 3 ошибками, которые лучше узнать до первой закупки."
    ),
    (
        "3 ошибки амазонщика — для кого-то это десятки тысяч долларов. "
        "Для вас в конце пути — бесплатно."
    ),
    (
        "🎁 Напоминаю: после воронки — бесплатный PDF «3 ошибки новичка». "
        "Что проверить до первой закупки, чтобы не слить бюджет на старте."
    ),
]


# ──────────────────────────────────────────────────────────────────────
# 7) НАДПИСИ НА КНОПКАХ.
# ──────────────────────────────────────────────────────────────────────

BTN = {
    "start":      "Покажи, с чего начать",
    "v1_watch":   "▶️ Смотреть историю Игоря (~4 мин)",
    "v1_proofs":  "📸 Разбор: что пошло не так",
    "to_v2":      "⚙️ Дальше — как работает схема",
    "v2_watch":   "▶️ Смотреть схему по шагам (~6 мин)",
    "v2_proofs":  "🌍 Примеры по странам",
    "v2_next":    "➡️ Дальше — к разбору страхов",
    "to_v3":      "🙅 Смотреть разбор страхов (~7 мин)",
    "v3_watch":   "▶️ Смотреть разбор страхов (~7 мин)",
    "to_fork":    "➡️ Дальше",
    "students":   "Результаты учеников",
    "programs":   "💎 Открыть мини-приложение",
    "site":       "Открыть сайт с результатами",
    "results_open": "Открыть результаты на сайте",
    "to_lead":    "🎁 Скидка −20% (24 ч)",
    "lm_get":     "📘 Забрать PDF-гайд",
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
GUIDE_PATH = os.path.join(BASE_DIR, GUIDE_FILENAME)

CHANNEL_LINK = "https://t.me/" + CHANNEL_USERNAME.lstrip("@")


def load_state():
    if os.path.exists(STATE_FILE):
        try:
            with open(STATE_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return {}
    return {}


def save_state(state):
    try:
        with open(STATE_FILE, "w", encoding="utf-8") as f:
            json.dump(state, f, ensure_ascii=False, indent=2)
    except Exception as e:
        log.error("save_state failed: %s", e)


STATE = load_state()


def _now():
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def u(uid):
    uid = str(uid)
    if uid not in STATE:
        STATE[uid] = {"step": "start", "answers": {}, "joined": _now()}
    return STATE[uid]


def set_step(uid, step):
    rec = u(uid)
    rec["step"] = step
    rec["step_at"] = _now()
    save_state(STATE)


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
                    guide_teaser=False, **kwargs):
    """Отправляет сообщение и гарантирует, что активные кнопки есть только
    у ПОСЛЕДНЕГО сообщения. Перед отправкой снимает кнопки с предыдущего
    сообщения, у которого они были, — чтобы из истории нельзя было
    наклацать старых кнопок и сбить воронку."""
    if guide_teaser:
        text = append_guide_teaser(uid, text)
    rec = u(uid)
    prev_id = rec.get("last_kb_msg")
    if prev_id:
        try:
            await bot.edit_message_reply_markup(uid, prev_id, reply_markup=None)
        except Exception:
            pass
        rec["last_kb_msg"] = None
    markup = kb(rows) if rows else None
    if not skip_pause:
        await pause_text(bot, uid)
    msg = await bot.send_message(uid, text, reply_markup=markup, **kwargs)
    if rows:
        rec["last_kb_msg"] = msg.message_id
        save_state(STATE)
    return msg


# ---------------- ПАУЗЫ МЕЖДУ СООБЩЕНИЯМИ ----------------
#   после кружка — CIRCLE_PAUSE_SEC
#   после видео  — доля длины из MEDIA["sec"] (VIDEO_PAUSE_FACTOR), с потолком
#   между текстами — по длине текста или TEXT_PAUSE_SEC
# Выключить: PAUSES=0  |  /pauses  |  /fast — без пауз на медиа

PAUSES_ON = os.getenv("PAUSES", "1").strip().lower() not in ("0", "false", "no", "")
FAST_MODE = False
CIRCLE_PAUSE_SEC = float(os.getenv("CIRCLE_PAUSE", "20") or "20")
VIDEO_PAUSE_FACTOR = float(os.getenv("VIDEO_PAUSE_FACTOR", "0.35") or "0.35")
VIDEO_PAUSE_MIN = float(os.getenv("VIDEO_PAUSE_MIN", "25") or "25")
VIDEO_PAUSE_MAX = float(os.getenv("VIDEO_PAUSE_MAX", "150") or "150")
VIDEO_PAUSE_SEC = float(os.getenv("VIDEO_PAUSE", "90") or "90")  # fallback без key
TEXT_PAUSE_SEC = float(os.getenv("TEXT_PAUSE", "4") or "4")

# Скорость чтения для индивидуальной паузы по тексту
READ_WPM = int(os.getenv("READ_WPM", "220") or "220")     # слов в минуту
MIN_TEXT_PAUSE = float(os.getenv("MIN_TEXT_PAUSE", "2") or "2")
MAX_TEXT_PAUSE = float(os.getenv("MAX_TEXT_PAUSE", "18") or "18")


def read_time(text):
    """Сколько секунд человеку нужно, чтобы прочитать этот текст.
    Длинный текст → длинная пауза (но не больше MAX_TEXT_PAUSE)."""
    if not text:
        return TEXT_PAUSE_SEC
    words = max(1, len(text.split()))
    t = words / READ_WPM * 60
    return max(MIN_TEXT_PAUSE, min(t, MAX_TEXT_PAUSE))


async def pause_text(bot, chat_id, text=None):
    """Пауза перед текстом: «печатает» + время на чтение ПРЕДЫДУЩЕГО.
    Если text задан — пауза по его длине (умно). Иначе — фикс TEXT_PAUSE_SEC."""
    if not PAUSES_ON:
        return
    try:
        await bot.send_chat_action(chat_id, ChatAction.TYPING)
    except Exception:
        pass
    await asyncio.sleep(read_time(text) if text else TEXT_PAUSE_SEC)


async def pause_after_circle(bot, chat_id):
    """После кружка — дать досмотреть, затем следующий текст.
    В FAST_MODE пауза пропускается (видео-паузы быстро, текст — нормально)."""
    if not PAUSES_ON or FAST_MODE:
        return
    try:
        await bot.send_chat_action(chat_id, ChatAction.TYPING)
    except Exception:
        pass
    await asyncio.sleep(CIRCLE_PAUSE_SEC)


def media_sec(key):
    return int(MEDIA.get(key, {}).get("sec", 0) or 0)


def video_pause_sec(key=None):
    """Пауза после видео: ~35% длины ролика (можно не досматривать до конца)."""
    sec = media_sec(key) if key else 0
    if sec > 0:
        t = sec * VIDEO_PAUSE_FACTOR
        return max(VIDEO_PAUSE_MIN, min(t, VIDEO_PAUSE_MAX))
    return VIDEO_PAUSE_SEC


async def pause_after_video(bot, chat_id, key=None):
    """После видео — дать досмотреть. В FAST_MODE — без паузы."""
    if not PAUSES_ON or FAST_MODE:
        return
    try:
        await bot.send_chat_action(chat_id, ChatAction.RECORD_VIDEO)
    except Exception:
        pass
    await asyncio.sleep(video_pause_sec(key))


async def send_text(bot, chat_id, text, **kwargs):
    """Текстовое сообщение с паузой по длине ТЕКСТА — больше текст,
    дольше пауза, чтобы человек успел прочитать предыдущее сообщение."""
    await pause_text(bot, chat_id, text=text)
    return await bot.send_message(chat_id, text, **kwargs)


def webapp_url_full():
    """URL Mini App с подставленными ссылками contact/site."""
    if not WEBAPP_URL:
        return ""
    return (f"{WEBAPP_URL}?contact={quote(CALL_LINK, safe='')}"
            f"&site={quote(SITE_LINK, safe='')}")


def programs_btn():
    """Кнопка Mini App или fallback на текстовый показ программ."""
    if WEBAPP_URL:
        return (BTN["programs"], webapp_url_full(), "webapp")
    return (BTN["programs"], "go_programs", False)


def main_menu_filter():
    """Только нажатия кнопок нижнего меню."""
    labels = "|".join(re.escape(x) for x in (MENU_FORMATS, MENU_RESULTS, MENU_GUIDE))
    return filters.Regex(f"^({labels})$")


def main_reply_keyboard():
    """Нижнее закреплённое меню (как на скрине)."""
    rows = []
    if WEBAPP_URL:
        rows.append([
            KeyboardButton(
                MENU_FORMATS,
                web_app=WebAppInfo(url=webapp_url_full()),
            ),
        ])
    else:
        rows.append([KeyboardButton(MENU_FORMATS)])
    rows.append([KeyboardButton(MENU_RESULTS), KeyboardButton(MENU_GUIDE)])
    return ReplyKeyboardMarkup(
        rows, resize_keyboard=True, is_persistent=True,
    )


async def send_with_main_menu(bot, chat_id, text, clear_inline=True):
    """Текст + нижнее меню (без inline-кнопок в этом сообщении)."""
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
    await pause_text(bot, chat_id, text=text)
    return await bot.send_message(
        chat_id, text, reply_markup=main_reply_keyboard(),
    )


# ---------------- ПРОМО ----------------

def promo_sig(uid, deadline):
    """HMAC-SHA256 от '{uid}.{deadline}', hex lowercase — как ждёт сайт."""
    msg = f"{uid}.{deadline}".encode("utf-8")
    return hmac.new(PROMO_SECRET.encode("utf-8"), msg,
                    hashlib.sha256).hexdigest()


def build_discount_link(uid, deadline):
    """Подписанная ссылка на скидочную страницу сайта."""
    sig = promo_sig(uid, deadline)
    qs = urlencode({"uid": uid, "deadline": deadline, "sig": sig})
    return f"{DISCOUNT_URL}?{qs}"


def webapp_promo_url(uid, deadline, discount_link):
    """URL Mini App с проброшенным дедлайном — чтобы там тикал таймер."""
    if not WEBAPP_URL:
        return ""
    sig = promo_sig(uid, deadline)
    return (f"{WEBAPP_URL}?contact={quote(CALL_LINK, safe='')}"
            f"&site={quote(SITE_LINK, safe='')}"
            f"&uid={uid}&deadline={deadline}&sig={sig}"
            f"&disc={PROMO_DISCOUNT}"
            f"&discount={quote(discount_link, safe='')}")


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
    """Проверка file_id без отправки 500 МБ в чат. Возвращает (ok, описание)."""
    if not file_id:
        return False, "пустой file_id"
    try:
        f = await bot.get_file(file_id)
        mb = (f.file_size or 0) / (1024 * 1024)
        return True, f"ok, ~{mb:.0f} МБ"
    except BadRequest as e:
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


async def send_media_file(bot, chat_id, key):
    """Отправка видео/документа. True = ушло, False = ошибка (file_id и т.д.)."""
    ref = MEDIA.get(key, {})
    file_id = ref.get("file_id")
    if not file_id:
        path = ref.get("path")
        if path and os.path.exists(path):
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
        if kind == "document":
            await bot.send_document(
                chat_id, file_id,
                read_timeout=300,
                write_timeout=300,
                connect_timeout=60,
            )
        else:
            await bot.send_video(
                chat_id, file_id,
                supports_streaming=True,
                read_timeout=300,
                write_timeout=300,
                connect_timeout=60,
            )
        return True
    except BadRequest as e:
        await notify_media_fail(bot, chat_id, key, e)
        return False
    except Exception as e:
        await notify_media_fail(bot, chat_id, key, e)
        return False


async def send_circle(bot, chat_id, key):
    ref = MEDIA.get(key, {})
    fid = ref.get("file_id")
    if not fid:
        return False
    try:
        await bot.send_chat_action(chat_id, ChatAction.RECORD_VIDEO)
        await bot.send_video_note(chat_id, fid)
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


async def send_proofs(bot, chat_id, proofs, caption=None):
    """Фото по URL/file_id. Если у элемента есть caption — шлём по одному."""
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


# ---------------- ЛИД-МАГНИТ ----------------

async def is_subscribed(bot, user_id) -> bool:
    """Проверяет, подписан ли пользователь на CHANNEL_USERNAME.
    Бот должен быть админом канала."""
    try:
        member = await bot.get_chat_member(CHANNEL_USERNAME, user_id)
        if member.status in ("creator", "administrator", "member"):
            return True
        if member.status == "restricted":
            return bool(getattr(member, "is_member", False))
        return False
    except Exception as e:
        log.error("is_subscribed failed (%s): %s", CHANNEL_USERNAME, e)
        return None  # None = не смогли проверить (канал/права)


async def show_lead_magnet_offer(bot, chat_id, intro=None):
    """Показывает предложение лид-магнита с выбором Хочу/Пропустить."""
    text = (intro + "\n\n" if intro else "") + TXT["lm_offer"]
    await send_step(bot, chat_id, text, [
        (BTN["lm_want"], "lm_want", False),
        (BTN["lm_skip"], "lm_skip", False),
    ])


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

    # ТЕСТОВЫЙ РЕЖИМ: канал ещё не настроен — пропускаем проверку подписки
    # и сразу выдаём гайд. Когда задашь CHANNEL_USERNAME в Railway,
    # проверка автоматически включится.
    if CHANNEL_USERNAME == "@ВПИШИ_КАНАЛ":
        log.warning("CHANNEL_USERNAME не задан — гайд выдаётся без проверки (тестовый режим)")
        await send_guide(bot, uid)
        rec = u(uid)
        rec["got_guide"] = True
        save_state(STATE)
        await send_step(bot, uid, TXT["lm_delivered"], [(BTN["to_lead"], "go_lead", False)])
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
    rec = u(uid)
    rec["got_guide"] = True
    save_state(STATE)
    await send_step(bot, uid, TXT["lm_delivered"], [(BTN["to_lead"], "go_lead", False)])


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

def cancel_promo_jobs(app, uid):
    """Снять таймер, напоминание и задачу удаления промо."""
    for job in app.job_queue.jobs():
        if not job.name:
            continue
        if job.name in (
            f"promotick_{uid}",
            f"promoremind_{uid}",
            f"promoexpire_{uid}",
        ):
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
    save_state(STATE)


async def promo_expire(context: ContextTypes.DEFAULT_TYPE):
    """Ровно в deadline: удалить промо-сообщения (таймер к этому моменту уже отработал)."""
    uid = context.job.data["uid"]
    rec = u(uid)
    promo = rec.get("promo") or {}
    if time.time() < promo.get("deadline", 0) - 2:
        return
    cancel_promo_jobs(context.application, uid)
    await expire_promo(context.bot, uid, rec)


async def show_promo(context, uid, user, temperature):
    """Выдаёт персональную скидку: ссылка с подписью, закреп, таймер."""
    bot = context.bot
    rec = u(uid)

    if not PROMO_SECRET:
        # секрет не задан — не выдаём кривую ссылку, ведём в личку
        await send_step(bot, uid, TXT["promo_fallback"],
                        [(BTN["contact"], CALL_LINK, True)])
        log.warning("PROMO_SECRET не задан — промо не выдано, отдан контакт")
        return

    deadline = int(time.time()) + PROMO_HOURS * 3600
    link = build_discount_link(uid, deadline)

    rec["promo"] = {
        "issued_at": int(time.time()),
        "deadline": deadline,
        "link": link,
        "temperature": temperature,
        "active": True,
    }
    save_state(STATE)
    cancel_promo_jobs(context.application, uid)

    intro = TXT["promo_hot"] if temperature == "hot" else TXT["promo_warm"]
    intro = intro.format(hours=PROMO_HOURS, discount=PROMO_DISCOUNT)

    # кнопки: оформить со скидкой, программы со скидкой (Mini App), контакт
    rows = [(BTN["promo_get"], link, True)]
    if WEBAPP_URL:
        rows.append((BTN["promo_app"], webapp_promo_url(uid, deadline, link), "webapp"))
    rows.append((BTN["contact"], CALL_LINK, True))

    promo_msg = await send_step(bot, uid, intro, rows)
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
        # «Живой» таймер: первые 5 минут — каждые 15 сек, дальше каждые 30 мин
        context.application.job_queue.run_once(
            promo_tick, when=15,
            name=f"promotick_{uid}", data={"uid": uid},
        )
    except Exception as e:
        log.error("promo pin failed: %s", e)

    # в момент окончания срока — удалить сообщения со скидкой и кнопкой аппки
    expire_in = max(1, deadline - int(time.time()))
    context.application.job_queue.run_once(
        promo_expire, when=expire_in,
        name=f"promoexpire_{uid}", data={"uid": uid},
    )

    # напоминание за пару часов до конца
    remind_in = max(60, (PROMO_HOURS - 2) * 3600)
    context.application.job_queue.run_once(
        promo_remind, when=remind_in,
        name=f"promoremind_{uid}", data={"uid": uid},
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
    context.application.job_queue.run_once(
        promo_tick, when=next_in,
        name=f"promotick_{uid}", data={"uid": uid},
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
    for job in app.job_queue.jobs():
        if job.name and job.name.startswith(f"drip_{uid}_"):
            job.schedule_removal()


def schedule_drip(app, uid, tag, hours):
    cancel_drips(app, uid)
    app.job_queue.run_once(
        drip_fire, when=hours * 3600,
        name=f"drip_{uid}_{tag}",
        data={"uid": uid, "tag": tag},
    )


async def drip_fire(context: ContextTypes.DEFAULT_TYPE):
    data = context.job.data
    uid = data["uid"]
    tag = data["tag"]
    rec = u(uid)

    expected_step = {
        "after_v1":    "v1",
        "after_v3":    "v3",
        "after_offer": "offer",
        "after_lead":  "qualified",
    }.get(tag)
    if rec.get("step") != expected_step:
        return

    bot = context.bot
    try:
        if tag == "after_v1":
            await send_step(bot, uid, TXT["drip_after_v1"],
                            [(BTN["to_v2"], "go_v2_prep", False)])
        elif tag == "after_v3":
            await send_step(bot, uid, TXT["drip_after_v3"],
                            [(BTN["to_fork"], "go_fork", False)],
                            guide_teaser=True)
        elif tag == "after_offer":
            await send_with_main_menu(bot, uid, TXT["drip_after_offer"])
            await send_step(
                bot, uid,
                "Скидка на обучение — по кнопке ниже 👇",
                [(BTN["to_lead"], "go_lead", False)],
            )
        elif tag == "after_lead":
            await send_step(bot, uid, TXT["drip_after_lead"], [(BTN["contact"], CALL_LINK, True)])
    except Exception as e:
        log.error("drip_fire failed: %s", e)


# ---------------- ШАГИ ВОРОНКИ ----------------

async def cmd_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    cancel_drips(context.application, uid)
    # сбрасываем память о прошлой клавиатуре — начинаем заново
    u(uid)["last_kb_msg"] = None
    set_step(uid, "start")
    await send_step(context.bot, uid, TXT["start"],
                    [(BTN["start"], "go_intro", False)], skip_pause=True)


async def go_intro(update, context):
    uid = update.effective_user.id
    bot = context.bot
    if not await send_circle(bot, uid, "circle_intro"):
        return
    await pause_after_circle(bot, uid)
    await send_step(bot, uid, TXT["after_circle_intro"],
                    [(BTN["v1_watch"], "go_v1_prep", False)],
                    skip_pause=True, guide_teaser=True)
    set_step(uid, "intro")


async def go_v1_prep(update, context):
    """Кнопка после кружка — текст перед видео 1."""
    uid = update.effective_user.id
    bot = context.bot
    await send_step(bot, uid, TXT["before_v1"],
                    [(BTN["v1_watch"], "go_v1_play", False)], skip_pause=True)


async def go_v1_play(update, context):
    """Видео 1 → кнопка к разбору скринов."""
    uid = update.effective_user.id
    bot = context.bot
    if not await send_media_file(bot, uid, "video_1"):
        return
    await send_step(bot, uid, TXT["after_v1_video"],
                    [(BTN["v1_proofs"], "go_v1_proofs", False)], skip_pause=True)
    set_step(uid, "v1")
    schedule_drip(context.application, uid, "after_v1", DRIP_HOURS["after_v1"])


async def go_v1_proofs(update, context):
    """Скрины после видео 1 → мост к видео 2."""
    uid = update.effective_user.id
    bot = context.bot
    await send_proofs(bot, uid, PROOFS_AFTER_V1, TXT["proofs_v1_caption"])
    await send_step(bot, uid, TXT["after_v1_proofs"],
                    [(BTN["to_v2"], "go_v2_prep", False)],
                    skip_pause=True, guide_teaser=True)


async def go_v2_prep(update, context):
    uid = update.effective_user.id
    bot = context.bot
    cancel_drips(context.application, uid)
    await send_step(bot, uid, TXT["bridge_v2"],
                    [(BTN["v2_watch"], "go_v2_video", False)],
                    skip_pause=True, guide_teaser=True)


async def go_v2_video(update, context):
    uid = update.effective_user.id
    bot = context.bot
    if not await send_media_file(bot, uid, "video_2"):
        return
    await send_step(bot, uid, TXT["after_v2_video"],
                    [(BTN["v2_proofs"], "go_v2_proofs", False)], skip_pause=True)
    set_step(uid, "v2")


async def go_v2_proofs(update, context):
    uid = update.effective_user.id
    bot = context.bot
    await send_proofs(bot, uid, PROOFS_AFTER_V2)
    await send_step(bot, uid, TXT["proofs_v2_caption"],
                    [(BTN["v2_next"], "go_v2_bridge", False)],
                    skip_pause=True, guide_teaser=True)


async def go_v2_bridge(update, context):
    """Мост к видео 3 — одна кнопка, сразу ролик."""
    uid = update.effective_user.id
    bot = context.bot
    await send_step(bot, uid, TXT["after_v2"],
                    [(BTN["v3_watch"], "go_v3_video", False)], skip_pause=True)


async def go_v3_prep(update, context):
    """Старый шаг воронки — сразу открываем видео (на случай старых кнопок)."""
    await go_v3_video(update, context)


async def go_v3_video(update, context):
    uid = update.effective_user.id
    bot = context.bot
    cancel_drips(context.application, uid)
    await send_step(bot, uid, TXT["v3_loading"], skip_pause=True)
    if not await send_media_file(bot, uid, "video_3"):
        return
    # Кнопку «дальше» сразу под видео — без паузы 2+ мин (иначе кажется, что не сработало)
    await send_step(bot, uid, TXT["after_v3_video"],
                    [(BTN["to_fork"], "go_v3_after", False)], skip_pause=True)
    set_step(uid, "v3")
    schedule_drip(context.application, uid, "after_v3", DRIP_HOURS["after_v3"])


async def go_v3_after(update, context):
    uid = update.effective_user.id
    bot = context.bot
    await send_step(bot, uid, TXT["after_v3"],
                    [(BTN["to_fork"], "go_fork", False)],
                    skip_pause=True, guide_teaser=True)


async def go_fork(update, context):
    uid = update.effective_user.id
    bot = context.bot
    cancel_drips(context.application, uid)
    if not await send_circle(bot, uid, "circle_fork"):
        return
    await pause_after_circle(bot, uid)
    await send_with_main_menu(bot, uid, TXT["after_fork_circle"])
    set_step(uid, "offer")
    schedule_drip(context.application, uid, "after_offer",
                  DRIP_HOURS["after_offer"])


async def go_offer_menu(update, context):
    """Старые inline-кнопки в истории → напоминание про меню внизу."""
    uid = update.effective_user.id
    bot = context.bot
    cancel_drips(context.application, uid)
    set_step(uid, "offer")
    await send_with_main_menu(bot, uid, TXT["after_fork_menu_hint"])
    schedule_drip(context.application, uid, "after_offer",
                  DRIP_HOURS["after_offer"])


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
    if data != "claim_promo":
        return
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
    await show_promo(context, uid, user, rec.get("temperature", "warm"))


async def go_lead(update, context):
    """Забрать персональную скидку на обучение."""
    uid = update.effective_user.id
    bot = context.bot
    user = update.effective_user
    cancel_drips(context.application, uid)
    rec = u(uid)
    rec["full_name"] = user.full_name
    rec["username"] = user.username or ""
    rec["temperature"] = "warm"
    set_step(uid, "qualified")
    save_state(STATE)

    await show_promo(context, uid, user, "warm")
    schedule_drip(context.application, uid, "after_lead",
                  DRIP_HOURS["after_lead"])

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
    if text not in (MENU_FORMATS, MENU_RESULTS, MENU_GUIDE):
        return
    bot = context.bot
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
        set_step(uid, "offer")
        await show_lead_magnet_offer(bot, uid)
        return
    if text == MENU_FORMATS:
        set_step(uid, "offer")
        if WEBAPP_URL:
            await send_with_main_menu(
                bot, uid,
                "Нажмите «Форматы сотрудничества и обучения» ещё раз — "
                "откроется мини-приложение со всеми форматами, инструментами "
                "и проверками 👇",
                clear_inline=False,
            )
        else:
            await go_programs(update, context)


async def go_guide(update, context):
    """Человек нажал «Забрать гайд» — показываем лид-магнит (подписка → гайд)."""
    uid = update.effective_user.id
    bot = context.bot
    set_step(uid, "offer")
    await show_lead_magnet_offer(bot, uid)


async def on_button(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    d = q.data
    if d in ("go_v1_play", "go_v2_video", "go_v3_video", "go_v3_prep"):
        await q.answer("Загружаю видео…", show_alert=False)
    else:
        await q.answer()
    # Убираем кнопки с этого сообщения, чтобы их нельзя было нажать
    # повторно из истории чата (кроме админских кнопок статуса лида).
    if not d.startswith("mk_"):
        try:
            await q.edit_message_reply_markup(reply_markup=None)
        except Exception:
            pass
    routes = {
        "go_intro":         go_intro,
        "go_v1_prep":       go_v1_prep,
        "go_v1_play":       go_v1_play,
        "go_v1_proofs":     go_v1_proofs,
        "go_v2_prep":       go_v2_prep,
        "go_v2_video":      go_v2_video,
        "go_v2_proofs":     go_v2_proofs,
        "go_v2_bridge":     go_v2_bridge,
        "go_v3_prep":       go_v3_prep,
        "go_v3_video":      go_v3_video,
        "go_v3_after":      go_v3_after,
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
        "go_guide":         go_guide,
        "lm_want":          lm_want,
        "lm_skip":          lm_skip,
        "lm_check":         lm_check,
    }
    if d in routes:
        await routes[d](update, context)
        return
    if d.startswith("mk_"):
        # mk_{lead_id}_{status} — только админ
        if update.effective_user.id != ADMIN_ID:
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
    if update.effective_user.id != ADMIN_ID:
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
    if update.effective_user.id != ADMIN_ID:
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
    if update.effective_user.id != ADMIN_ID:
        return
    me = await context.bot.get_me()
    lines = [f"Проверка MEDIA для @{me.username}:\n"]
    for key, ref in MEDIA.items():
        fid = ref.get("file_id")
        kind = ref.get("kind") or detect_kind(fid or "")
        ok, msg = await probe_file_id(context.bot, fid)
        icon = "✅" if ok else "❌"
        lines.append(f"{icon} {key} ({kind}): {msg}")
    lines.append(
        "\n❌ = file_id не от этого бота или устарел.\n"
        "Исправление: перешли ролик ЭТОМУ боту → /id → вставь в MEDIA → redeploy."
    )
    await update.message.reply_text("\n".join(lines))


async def grab_file_id(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID:
        return
    m = update.message
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
        out = f"ФОТО\nfile_id:\n{m.photo[-1].file_id}"
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
    if update.effective_user.id != ADMIN_ID:
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
    if outcomes:
        oc_str = " · ".join(f"{k}: {v}" for k, v in outcomes.items())
        lines.append(f"📌 Статусы: {oc_str}")
    lines.append(f"\nВсего людей: {len(STATE)}")
    lines.append("\n/report — выгрузить всех в файл (Excel)")
    lines.append("/lead ID — карточка лида + смена статуса")
    await update.message.reply_text("\n".join(lines))


async def cmd_report(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Выгрузка всех лидов в CSV (открывается в Excel)."""
    if update.effective_user.id != ADMIN_ID:
        return
    import csv
    import io
    buf = io.StringIO()
    w = csv.writer(buf)
    w.writerow(["telegram_id", "username", "имя", "температура", "шаг",
                "бюджет", "время_в_день", "когда_старт", "забрал_гайд",
                "промо_выдано", "промо_дедлайн", "статус", "вошёл",
                "последнее_действие"])
    for uid, rec in STATE.items():
        a = rec.get("answers", {})
        promo = rec.get("promo") or {}
        dl = promo.get("deadline")
        dl_str = datetime.fromtimestamp(dl).strftime("%Y-%m-%d %H:%M") if dl else ""
        w.writerow([
            uid, rec.get("username", ""), rec.get("full_name", ""),
            rec.get("temperature", ""), rec.get("step", ""),
            a.get("q1", ""), a.get("q2", ""), a.get("q3", ""),
            "да" if rec.get("got_guide") else "",
            "да" if promo else "", dl_str,
            rec.get("outcome", ""),
            rec.get("joined", ""), rec.get("step_at", ""),
        ])
    data = buf.getvalue().encode("utf-8-sig")  # BOM — чтобы Excel не ломал кириллицу
    import io as _io
    bio = _io.BytesIO(data)
    bio.name = f"leads_{datetime.now():%Y%m%d_%H%M}.csv"
    await context.bot.send_document(
        update.effective_user.id, bio,
        caption=f"Отчёт по {len(STATE)} лидам. Открывается в Excel.")


async def cmd_lead(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Карточка одного лида + кнопки смены статуса."""
    if update.effective_user.id != ADMIN_ID:
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
    if update.effective_user.id != ADMIN_ID:
        return
    uid = str(update.effective_user.id)
    cancel_drips(context.application, update.effective_user.id)
    if uid in STATE:
        del STATE[uid]
        save_state(STATE)
    await update.message.reply_text(
        "Готово. Напиши /start — воронка пойдёт заново."
    )


async def cmd_programs(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Открыть витрину программ в любой момент."""
    await go_programs(update, context)


async def cmd_pauses(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Переключает паузы между сообщениями (для тебя — посмотреть оба
    режима: с паузами как у клиентов, и без — для быстрого просмотра)."""
    global PAUSES_ON, FAST_MODE
    if update.effective_user.id != ADMIN_ID:
        return
    PAUSES_ON = not PAUSES_ON
    FAST_MODE = False  # сбрасываем fast при общем переключении
    if PAUSES_ON:
        txt = (
            f"⏳ Паузы ВКЛЮЧЕНЫ — как у клиентов:\n"
            f"кружок → {int(CIRCLE_PAUSE_SEC)}с, видео → {int(VIDEO_PAUSE_SEC)}с, "
            f"текст → индивидуально (2–18с) + «печатает».\n\n"
            f"Напиши /pauses — выкл всё / /fast — выкл только видео+кружки."
        )
    else:
        txt = (
            "⚡ Паузы ВЫКЛЮЧЕНЫ — сообщения идут сразу.\n\n"
            "Напиши /pauses ещё раз — вернуть."
        )
    await update.message.reply_text(txt)


async def cmd_fast(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Быстрый режим теста: видео и кружки проматываются мгновенно,
    но текст идёт с нормальной паузой по длине — чтобы читалось живо,
    а время не съедалось на ожидание медиа."""
    global FAST_MODE, PAUSES_ON
    if update.effective_user.id != ADMIN_ID:
        return
    FAST_MODE = not FAST_MODE
    PAUSES_ON = True
    if FAST_MODE:
        await update.message.reply_text(
            "⏩ FAST-режим ВКЛ — видео и кружки без пауз, текст по длине.\n"
            "Удобно быстро проходить воронку.\n\n/fast — выкл."
        )
    else:
        await update.message.reply_text(
            "FAST-режим ВЫКЛ — паузы как обычно (видео+кружки в полном)."
        )


async def on_error(update, context):
    """Логирует ошибки аккуратно, без пугающих трейсбеков в консоль.
    409 Conflict при редеплое (на секунду два экземпляра) — не страшно."""
    err = context.error
    if "Conflict" in str(err):
        log.warning("Conflict (обычно при перезапуске — два экземпляра на "
                    "секунду). Если повторяется постоянно — проверь, что бот "
                    "не запущен где-то ещё.")
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
    except Exception as e:
        log.warning("post_init: %s", e)


def main():
    if not BOT_TOKEN:
        print("ОШИБКА: переменная окружения BOT_TOKEN не задана.")
        print("Локально:  BOT_TOKEN=твой_токен python bot.py")
        print("Railway:   добавь BOT_TOKEN в Variables")
        return

    if CHANNEL_USERNAME == "@ВПИШИ_КАНАЛ":
        log.warning("CHANNEL_USERNAME не задан — лид-магнит не сможет "
                    "проверять подписку. Задай переменную CHANNEL_USERNAME.")

    if not WEBAPP_URL:
        log.warning("WEBAPP_URL не задан — кнопка «Что входит» покажет "
                    "программы текстом. Для Mini App см. MINI_APP.md.")

    if not PROMO_SECRET:
        log.warning("PROMO_SECRET не задан — промо-скидки выдаваться НЕ будут "
                    "(тёплым/горячим отдаётся контакт). Задай PROMO_SECRET.")

    app = Application.builder().token(BOT_TOKEN).post_init(post_init).build()

    app.add_handler(CommandHandler("start", cmd_start))
    app.add_handler(CommandHandler("programs", cmd_programs))
    app.add_handler(CommandHandler("pauses", cmd_pauses))
    app.add_handler(CommandHandler("fast", cmd_fast))
    app.add_handler(CommandHandler("id",    cmd_id))
    app.add_handler(CommandHandler("bot", cmd_bot))
    app.add_handler(CommandHandler("checkmedia", cmd_checkmedia))
    app.add_handler(CommandHandler("stats", cmd_stats))
    app.add_handler(CommandHandler("report", cmd_report))
    app.add_handler(CommandHandler("lead", cmd_lead))
    app.add_handler(CommandHandler("reset", cmd_reset))
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
