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
import hmac
import json
import logging
import os
import time
from datetime import datetime

from urllib.parse import quote, urlencode
from telegram import (
    Update, InlineKeyboardButton, InlineKeyboardMarkup, InputMediaPhoto,
    WebAppInfo,
)
from telegram.constants import ChatAction
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

# Ссылка для созвона/контакта — на твою личку.
CALL_LINK = os.getenv("CALL_LINK", "").strip() or "https://t.me/vadjik"

# Ссылка на твой сайт с результатами учеников.
SITE_LINK = os.getenv("SITE_LINK", "").strip() or "https://vadjik.com/"

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
#   Бонус к скидке — личный созвон с Вадимом (текст в TXT["promo_*"]).
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
#      - если задан GUIDE_FILE_ID (env) — отправляет его (быстрее);
#      - иначе — отправляет файл guide.pdf, лежащий рядом с bot.py.
#    Просто положи guide.pdf в репозиторий рядом с этим файлом.
# ──────────────────────────────────────────────────────────────────────

CHANNEL_USERNAME = os.getenv("CHANNEL_USERNAME", "").strip() or "@ВПИШИ_КАНАЛ"

GUIDE_FILE_ID = os.getenv("GUIDE_FILE_ID", "").strip()  # опционально
GUIDE_FILENAME = "guide.pdf"  # имя файла рядом с bot.py


# ──────────────────────────────────────────────────────────────────────
# 3) ВИДЕО И КРУЖКИ — твои file_id уже вставлены.
#
#    Поле "kind": "video" / "document" / нет (авто-детект по префиксу).
#    Твои видео отправлены КАК ФАЙЛ → kind="document".  Они работают,
#    но в чате выглядят как карточка-файл. Чтобы играли inline —
#    перешли боту через «прикрепить → Видео» и обнови file_id.
# ──────────────────────────────────────────────────────────────────────

MEDIA = {

    # КРУЖОК «КТО Я» (47 сек) — после /start.
    "circle_intro":  {
        "file_id": "DQACAgIAAxkBAAMhahhQfhCycqexkKysYDi_MMFQ4WwAAlmZAAJBpaBIUqucIOryZbc7BA",
        "sec": 58,
    },

    # ВИДЕО 1 — история Игоря. ⬇️ ВПИШИ в "sec" реальную длину видео в секундах.
    "video_1":       {
        "file_id": "BQACAgIAAxkBAAMjahha-z4qjKU5N0vdaA2BpkP991oAAh2ZAAKUislIlXFwBBtVE3Y7BA",
        "kind": "document",
        "sec": 90,
    },

    # ВИДЕО 2 — как работает механика. ⬇️ впиши реальную длину в "sec".
    "video_2":       {
        "file_id": "BQACAgIAAxkBAAMdahhQWH8nZmU6aCjyKcSi87oVqCYAAsuhAAIcf7hI4NDb87GMAgs7BA",
        "kind": "document",
        "sec": 90,
    },

    # ВИДЕО 3 — кому НЕ стоит. ⬇️ впиши реальную длину в "sec".
    "video_3":       {
        "file_id": "BQACAgIAAxkBAAMbahhQRlHSqn8kmwABaqjx-J74TjOjAALHoQACHH-4SDBaQh9qb6shOwQ",
        "kind": "document",
        "sec": 90,
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

# Блок B — после видео 2.
PROOFS_AFTER_V2 = [
    {"url": "https://i.postimg.cc/MZM2sQwp/photo-2024-05-09-21-42-26.jpg"},
    {"url": "https://i.postimg.cc/5N8cJWjT/photo-2024-05-09-21-42-27.jpg"},
    {"url": "https://i.postimg.cc/2SYs89ZY/photo-2026-05-26-17-43-48.jpg"},
    {"url": "https://i.postimg.cc/nh16sK4k/photo-2026-05-26-17-44-17.jpg"},
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
        "$750 чистыми.\n\n"
        "Знаю, кому-то это «мало», кому-то — «отлично». Спорить не "
        "буду — лучше покажу.\n\n"
        "Это первый результат Игоря. Парень с нуля, без опыта. Через "
        "несколько месяцев та же сумма стала его ДНЕВНОЙ выручкой. "
        "А другой человек закрыл год на €472 000.\n\n"
        "$750 → $750 в день → €472 000 в год.\n\n"
        "И все они прошли один и тот же путь. В трёх коротких видео "
        "покажу, какой именно:\n\n"
        "🎬 С чего Игорь начал и как добрался до первой прибыли\n"
        "⚙️ Что превращает $750 в стабильный доход\n"
        "🙅 Кому за это лучше НЕ браться\n\n"
        "15 минут — и картина сложится. Сначала пара слов о том, кто я 👇"
    ),
    "after_circle_intro": (
        "Теперь вы знаете, кто перед вами 🙂\n\n"
        "Прежде чем покажу историю Игоря — гляньте, к чему ребята "
        "приходят, когда механика отлажена. Это и есть тот «потолок», "
        "к которому Игорь идёт со своих первых $750 👇"
    ),
    "proofs_v1_caption": (
        "Разные страны, разные суммы, разные сроки. Но все они начинали "
        "ровно там же, где Игорь — с нуля и с первой небольшой прибыли.\n\n"
        "А теперь — как именно начинался путь у Игоря. Это одна минута 👇"
    ),
    "before_v1": (
        "Включайте 👇\n\n"
        "Тут без монтажа и красивых обещаний — просто шаг за шагом: с "
        "чего человек начал, где ошибся, как исправил и к чему пришёл."
    ),
    "after_v1": (
        "Вот почему этот пример важен.\n\n"
        "Игорь не нашёл хороший товар с первого раза. Первый список был "
        "слабый: где-то не сходились цифры, где-то товар был не тот, "
        "где-то покупка просто не имела смысла.\n\n"
        "Но он получил правки, переделал работу — и уже во второй раз "
        "нашёл несколько нормальных вариантов.\n\n"
        "Дальше всё пошло по шагам:\n\n"
        "1. закупка товара\n"
        "2. подготовка для Amazon\n"
        "3. отправка на склад Amazon\n"
        "4. продажи\n"
        "5. чистая прибыль\n\n"
        "Это нормальный живой путь: сделал, ошибся, исправил, получил "
        "результат. Теперь покажу, откуда вообще берётся прибыль на "
        "Amazon и что именно делает продавец 👇"
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
        "В следующем видео разберу эти причины честно 👇"
    ),
    "bridge_v3": (
        "Это финальное видео перед тем, как двигаться дальше.\n\n"
        "Я разберу главные причины, почему люди даже не доходят до "
        "первого шага.\n\n"
        "Посмотрите честно.\n\n"
        "Если узнаете себя — это не страшно. Главное понять: это "
        "настоящая причина или просто страх, который держит вас на месте.\n\n"
        "После этого станет понятно, стоит ли вам вообще заходить в "
        "Amazon сейчас 👇"
    ),
    "after_v3": (
        "Если досмотрели до этого места — это уже хороший знак 🙌\n\n"
        "Теперь у вас есть база:\n\n"
        "— вы увидели путь Игоря;\n"
        "— поняли, как работает схема;\n"
        "— увидели главные страхи, которые мешают старту;\n"
        "— и понимаете, что тут нет магии, но есть конкретные шаги.\n\n"
        "Дальше главный вопрос: как пройти этот путь без хаоса, без "
        "лишних ошибок и без попыток собирать всё по кускам?\n\n"
        "Об этом — коротко в следующем кружке 👇"
    ),
    "after_fork_circle": (
        "Смотрите.\n\n"
        "Разобраться самому можно. В интернете есть видео, статьи, чаты "
        "и куски информации.\n\n"
        "Проблема в другом: новичок обычно не понимает, что важно, а что "
        "нет.\n\n"
        "Где нормальный поставщик, а где риск.\n"
        "Где товар действительно можно брать, а где цифры красивые только "
        "на первый взгляд.\n"
        "Где всё безопасно, а где потом могут быть проблемы с Amazon.\n\n"
        "Поэтому я сделал формат, где можно пройти этот путь со мной: по "
        "шагам, с проверками, инструментами и поддержкой.\n\n"
        "Сейчас покажу, что туда входит 👇"
    ),
    "offer_text": (
        "Что мы делаем внутри:\n\n"
        "✅ разбираем, как устроен заработок на Amazon\n"
        "✅ помогаем с регистрацией и базовыми настройками\n"
        "✅ ищем поставщиков и понимаем, кому можно доверять\n"
        "✅ проверяем товары до закупки\n"
        "✅ считаем прибыль, расходы и риски\n"
        "✅ готовим первую отправку на Amazon\n"
        "✅ разбираем ошибки, чтобы не слить бюджет на старте\n\n"
        "Цель — не просто «посмотреть уроки».\n\n"
        "Цель — понять систему, сделать первые правильные действия и "
        "дойти до продаж без хаоса."
    ),
    "offer_app_bridge": (
        "Форматы есть разные: от самостоятельного прохождения до более "
        "плотной работы со мной.\n\n"
        "Я не буду грузить вас длинным списком прямо в чате — это неудобно "
        "читать.\n\n"
        "Я собрал всё в мини-приложении:\n\n"
        "— какие есть форматы;\n"
        "— что входит в каждый;\n"
        "— чем они отличаются;\n"
        "— какие бонусы идут внутри;\n"
        "— какие результаты уже есть у учеников;\n"
        "— какой вариант чаще всего выбирают.\n\n"
        "Откройте, спокойно пролистайте и посмотрите, что подходит вам 👇"
    ),
    "offer_gift": (
        "🎁 Внутри также есть бонусы-инструменты.\n\n"
        "Это помощники для поиска товаров, проверки перед закупкой, "
        "работы с поставщиками и контроля цены.\n\n"
        "То, что обычно собирают месяцами, уже собрано в одном месте — "
        "чтобы вы не начинали с пустого листа."
    ),
    "offer_risk": (
        "Если после просмотра форматов захотите понять, что подходит "
        "именно вам, можно забрать бонус — скидка и личный созвон со мной.\n\n"
        "На созвоне смотрим:\n\n"
        "— ваш бюджет;\n"
        "— сколько времени есть на старт;\n"
        "— с чего лучше начинать;\n"
        "— какие риски есть именно у вас;\n"
        "— какой формат будет самым адекватным.\n\n"
        "И честно решаем: стоит вам заходить сейчас или лучше пока не "
        "спешить."
    ),
    "programs_text": (
        "Вот варианты обучения — от «разберусь сам» до «под ключ» 👇\n\n"
        "1️⃣ Обучаюсь сам — $750\n"
        "Все уроки, программы-помощники, записи прошлых занятий, доступ "
        "навсегда. Свой темп.\n\n"
        "2️⃣ Поток — $1100\n"
        "Всё то же + группа, 2 личных созвона со мной, один поставщик на "
        "старт, поддержка. До первых продаж.\n\n"
        "3️⃣ Продвинутый — $1700 ⭐ (чаще всего)\n"
        "Всё из «Потока» + 4 созвона, три поставщика, рынок США или "
        "Европа, поддержка 4 месяца.\n\n"
        "4️⃣ Под ключ — $4200 💎\n"
        "12 созвонов, 10 поставщиков, помощь с 50 товарами, сайт и учёт, "
        "поддержка полгода. Цель — $15 000+ продаж в месяц.\n\n"
        "🎁 В каждый вариант — бонусы-помощники.\n\n"
        "Что вам подойдёт — подскажу в бонусе, когда разберём вашу "
        "ситуацию 🙂"
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
        "Посмотрели форматы? Если готовы разобрать вашу ситуацию — "
        "заберите бонус: скидка на обучение и личный созвон 👇"
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
        "Вижу, вы посмотрели информацию, но пока не забрали бонус 🙂\n\n"
        "Если есть сомнения — это нормально. Можно начать мягче: "
        "заберите гайд по ошибкам перед первой закупкой.\n\n"
        "А если хотите сразу разобрать вашу ситуацию — заберите бонус "
        "и личный созвон 👇"
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
        "Закрепляю для вас бонус на {hours} часов: скидка на обучение + "
        "личный созвон со мной в подарок.\n\n"
        "На созвоне посмотрим вашу ситуацию: бюджет, время, риски и "
        "какой формат старта будет адекватным.\n\n"
        "Кнопка ниже 👇"
    ),
    "promo_warm": (
        "Отлично 🙂\n\n"
        "Закрепляю для вас бонус на {hours} часов: скидка на обучение + "
        "личный созвон со мной в подарок.\n\n"
        "На созвоне посмотрим вашу ситуацию: бюджет, время, риски и "
        "какой формат старта будет адекватным.\n\n"
        "Кнопка ниже 👇"
    ),
    "promo_pinned": (
        "⏳ Ваш бонус активен: скидка на обучение + личный созвон.\n"
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
        "Если хотите забрать скидку и личный созвон — кнопка выше 👆"
    ),
}


# ──────────────────────────────────────────────────────────────────────
# 7) НАДПИСИ НА КНОПКАХ.
# ──────────────────────────────────────────────────────────────────────

BTN = {
    "start":      "Покажи, с чего начать",
    "to_v1":      "Давайте посмотрим",
    "to_v2":      "Как это работает",
    "to_v3":      "Кому не стоит этим заниматься",
    "to_fork":    "Что дальше",
    "to_offer":   "Расскажи подробнее",
    "students":   "Результаты учеников",
    "programs":   "💎 Посмотреть форматы обучения",
    "site":       "Открыть сайт с результатами",
    "to_lead":    "🎁 Скидка −20% + личный созвон (24ч)",
    "lm_get":     "📘 Забрать гайд",
    "contact":    "Написать @vadjik",
    # лид-магнит
    "lm_grab":    "Забрать топ-3 ошибки (бесплатно)",
    "lm_want":    "Хочу забрать",
    "lm_skip":    "Пропустить",
    "lm_goto":    "Перейти в канал",
    "lm_check":   "Я подписался ✅",
    # промо
    "promo_get":  "🔥 Забрать скидку + созвон",
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


async def send_step(bot, uid, text, rows=None, skip_pause=False, **kwargs):
    """Отправляет сообщение и гарантирует, что активные кнопки есть только
    у ПОСЛЕДНЕГО сообщения. Перед отправкой снимает кнопки с предыдущего
    сообщения, у которого они были, — чтобы из истории нельзя было
    наклацать старых кнопок и сбить воронку."""
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
# Фиксированные паузы (не от длины видео в MEDIA):
#   после кружка — CIRCLE_PAUSE_SEC (15)
#   после видео  — VIDEO_PAUSE_SEC (40)
#   между текстами — TEXT_PAUSE_SEC (4) + «печатает…»
# Выключить: PAUSES=0  |  /pauses — переключатель для админа

PAUSES_ON = os.getenv("PAUSES", "1").strip().lower() not in ("0", "false", "no", "")
# FAST_MODE: только медиа (видео+кружки) идут без пауз, текст с обычными
# (для быстрого ручного теста воронки). Переключатель — команда /fast.
FAST_MODE = False
CIRCLE_PAUSE_SEC = float(os.getenv("CIRCLE_PAUSE", "35") or "35")
VIDEO_PAUSE_SEC = float(os.getenv("VIDEO_PAUSE", "90") or "90")
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


async def pause_after_video(bot, chat_id):
    """После видео — дать досмотреть. В FAST_MODE — без паузы."""
    if not PAUSES_ON or FAST_MODE:
        return
    try:
        await bot.send_chat_action(chat_id, ChatAction.RECORD_VIDEO)
    except Exception:
        pass
    await asyncio.sleep(VIDEO_PAUSE_SEC)


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


async def send_media_file(bot, chat_id, key):
    ref = MEDIA.get(key, {})
    file_id = ref.get("file_id")
    if not file_id:
        path = ref.get("path")
        if path and os.path.exists(path):
            with open(path, "rb") as f:
                await bot.send_video(chat_id, f)
        return
    kind = ref.get("kind") or detect_kind(file_id)
    try:
        if kind == "document":
            await bot.send_document(chat_id, file_id)
        else:
            await bot.send_video(chat_id, file_id)
    except Exception as e:
        log.error("send_media_file %s failed: %s", key, e)


async def send_circle(bot, chat_id, key):
    ref = MEDIA.get(key, {})
    fid = ref.get("file_id")
    if not fid:
        return
    try:
        await bot.send_video_note(chat_id, fid)
    except Exception as e:
        log.error("send_circle %s failed: %s", key, e)


def _resolve_photo_source(item):
    if item.get("file_id"):
        return item["file_id"]
    if item.get("url"):
        return item["url"]
    if item.get("path") and os.path.exists(item["path"]):
        return item["path"]
    return None


async def send_proofs(bot, chat_id, proofs, caption=None):
    sources = [_resolve_photo_source(p) for p in proofs]
    sources = [s for s in sources if s]
    if not sources:
        if caption:
            await bot.send_message(chat_id, caption)
        return
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
            "А пока, если хотите забрать бонус и созвон со мной, "
            "кнопка ниже 👇",
        )
    except Exception as e:
        log.error("send_guide failed: %s", e)


# ---------------- ПОКАЗ ПРОМО ----------------

async def show_promo(context, uid, user, temperature):
    """Выдаёт персональную скидку: ссылка с подписью, закреп, таймер."""
    bot = context.bot
    rec = u(uid)

    if not PROMO_SECRET:
        # секрет не задан — не выдаём кривую ссылку, ведём на созвон
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
    }
    save_state(STATE)

    intro = TXT["promo_hot"] if temperature == "hot" else TXT["promo_warm"]
    intro = intro.format(hours=PROMO_HOURS)

    # кнопки: оформить со скидкой, программы со скидкой (Mini App), контакт
    rows = [(BTN["promo_get"], link, True)]
    if WEBAPP_URL:
        rows.append((BTN["promo_app"], webapp_promo_url(uid, deadline, link), "webapp"))
    rows.append((BTN["contact"], CALL_LINK, True))

    await send_step(bot, uid, intro, rows)

    # закреплённое сообщение с таймером (обычным send_message, чтобы НЕ
    # снять кнопки с промо-сообщения выше)
    try:
        await pause_text(bot, uid)
        pin = await bot.send_message(
            uid, TXT["promo_pinned"].format(left=fmt_left(deadline)))
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
        # истекло — финальный текст, открепить, остановить
        try:
            await bot.edit_message_text(TXT["promo_expired"], uid, pin_id)
            await bot.unpin_chat_message(uid, pin_id)
        except Exception as e:
            log.error("promo expire failed: %s", e)
        return
    try:
        await bot.edit_message_text(
            TXT["promo_pinned"].format(left=fmt_left(deadline)), uid, pin_id)
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
    if time.time() >= deadline:
        return
    try:
        await send_step(context.bot, uid, TXT["promo_drip"],
                        [(BTN["promo_get"], promo.get("link"), True)])
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
            await send_step(bot, uid, TXT["drip_after_v1"], [(BTN["to_v2"], "go_v2", False)])
        elif tag == "after_v3":
            await send_step(bot, uid, TXT["drip_after_v3"], [(BTN["to_fork"], "go_fork", False)])
        elif tag == "after_offer":
            await send_step(bot, uid, TXT["drip_after_offer"], [
                    (BTN["to_lead"], "go_lead", False),
                    (BTN["lm_get"], "go_guide", False),
                    (BTN["contact"], CALL_LINK, True),
                ])
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
    await send_circle(bot, uid, "circle_intro")
    await pause_after_circle(bot, uid)
    # Мост: "вот к чему приходят, когда механика отлажена"
    await send_text(bot, uid, TXT["after_circle_intro"])
    # СРАЗУ скрины с большими цифрами — чтобы $750 в видео ниже
    # воспринимались как начало пути, а не как «потолок».
    await send_proofs(bot, uid, PROOFS_AFTER_V1, TXT["proofs_v1_caption"])
    await pause_text(bot, uid, text=TXT["proofs_v1_caption"])
    await send_step(bot, uid, TXT["before_v1"],
                    [(BTN["to_v1"], "go_v1", False)], skip_pause=True)
    set_step(uid, "intro")


async def go_v1(update, context):
    uid = update.effective_user.id
    bot = context.bot
    await send_media_file(bot, uid, "video_1")
    await pause_after_video(bot, uid)
    # Скрины уже показаны ДО видео — здесь сразу к выводу про Игоря.
    await send_step(bot, uid, TXT["after_v1"],
                    [(BTN["to_v2"], "go_v2", False)], skip_pause=True)
    set_step(uid, "v1")
    schedule_drip(context.application, uid, "after_v1", DRIP_HOURS["after_v1"])


async def go_v2(update, context):
    uid = update.effective_user.id
    bot = context.bot
    cancel_drips(context.application, uid)
    await send_text(bot, uid, TXT["bridge_v2"])
    await send_media_file(bot, uid, "video_2")
    await pause_after_video(bot, uid)
    await send_proofs(bot, uid, PROOFS_AFTER_V2, TXT["proofs_v2_caption"])
    await pause_text(bot, uid)
    await send_step(bot, uid, TXT["after_v2"],
                    [(BTN["to_v3"], "go_v3", False)], skip_pause=True)
    set_step(uid, "v2")


async def go_v3(update, context):
    uid = update.effective_user.id
    bot = context.bot
    await send_text(bot, uid, TXT["bridge_v3"])
    await send_media_file(bot, uid, "video_3")
    await pause_after_video(bot, uid)
    await send_step(bot, uid, TXT["after_v3"],
                    [(BTN["to_fork"], "go_fork", False)], skip_pause=True)
    set_step(uid, "v3")
    schedule_drip(context.application, uid, "after_v3", DRIP_HOURS["after_v3"])


async def go_fork(update, context):
    uid = update.effective_user.id
    bot = context.bot
    cancel_drips(context.application, uid)
    await send_circle(bot, uid, "circle_fork")
    await pause_after_circle(bot, uid)
    await send_step(bot, uid, TXT["after_fork_circle"],
                    [(BTN["to_offer"], "go_offer", False)], skip_pause=True)
    set_step(uid, "fork")


async def go_offer(update, context):
    uid = update.effective_user.id
    bot = context.bot
    cancel_drips(context.application, uid)
    await send_text(bot, uid, TXT["offer_text"])
    await send_step(bot, uid, TXT["offer_app_bridge"], [programs_btn()])
    await send_text(bot, uid, TXT["offer_gift"])
    await send_step(bot, uid, TXT["offer_risk"], [
        programs_btn(),
        (BTN["to_lead"], "go_lead", False),
        (BTN["lm_get"], "go_guide", False),
    ])
    set_step(uid, "offer")
    schedule_drip(context.application, uid, "after_offer",
                  DRIP_HOURS["after_offer"])


async def go_programs(update, context):
    """Текстовый показ программ — fallback, если Mini App не настроен,
    либо по команде /programs когда WEBAPP_URL пуст."""
    uid = update.effective_user.id
    bot = context.bot
    # если Mini App настроен — лучше открыть его
    if WEBAPP_URL:
        await send_step(bot, uid, TXT["offer_app_bridge"], [
                programs_btn(),
                (BTN["to_lead"], "go_lead", False),
            ])
        return
    # иначе — тарифы текстом + старый показ результатов фото
    await send_text(bot, uid, TXT["programs_text"])
    await send_proofs(bot, uid, PROOFS_STUDENTS, TXT["students_caption"])
    await pause_text(bot, uid)
    await send_proofs(bot, uid, [SITE_SCREEN], TXT["site_caption"])
    await pause_text(bot, uid)
    await send_step(bot, uid, TXT["back_to_offer"], [
        (BTN["site"], SITE_LINK, True),
        (BTN["to_lead"], "go_lead", False),
    ])


async def go_students(update, context):
    uid = update.effective_user.id
    bot = context.bot
    await send_proofs(bot, uid, PROOFS_STUDENTS, TXT["students_caption"])
    await pause_text(bot, uid)
    await send_proofs(bot, uid, [SITE_SCREEN], TXT["site_caption"])
    await pause_text(bot, uid)
    await send_step(bot, uid, TXT["back_to_offer"], [
        (BTN["site"],    SITE_LINK, True),
        (BTN["to_lead"], "go_lead", False),
    ])


async def go_lead(update, context):
    """«Получить скидка и созвон» — промо (скидка + личный созвон)."""
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
                f"🔥 НОВАЯ ЗАЯВКА — бонус (скидка + созвон)\n"
                f"Имя: {user.full_name}\n"
                f"Username: {uname}\n"
                f"ID: {user.id}\n"
                f"Чат: tg://user?id={user.id}"
                f"{promo_line}",
            )
        except Exception as e:
            log.error("notify admin failed: %s", e)


async def go_guide(update, context):
    """Человек нажал «Забрать гайд» — показываем лид-магнит (подписка → гайд)."""
    uid = update.effective_user.id
    bot = context.bot
    await show_lead_magnet_offer(bot, uid)


async def on_button(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()
    d = q.data
    # Убираем кнопки с этого сообщения, чтобы их нельзя было нажать
    # повторно из истории чата (кроме админских кнопок статуса лида).
    if not d.startswith("mk_"):
        try:
            await q.edit_message_reply_markup(reply_markup=None)
        except Exception:
            pass
    routes = {
        "go_intro":    go_intro,
        "go_v1":       go_v1,
        "go_v2":       go_v2,
        "go_v3":       go_v3,
        "go_fork":     go_fork,
        "go_offer":    go_offer,
        "go_programs": go_programs,
        "go_students": go_students,
        "go_lead":     go_lead,
        "go_guide":    go_guide,
        "lm_want":     lm_want,
        "lm_skip":     lm_skip,
        "lm_check":    lm_check,
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
    await update.message.reply_text(
        "Режим получения file_id включён.\n"
        "Пришли мне сюда видео, кружок, фото или PDF — отвечу его file_id."
    )


async def grab_file_id(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID:
        return
    m = update.message
    out = None
    if m.video_note:
        out = (f"КРУЖОК (video_note, {m.video_note.duration} сек)\n"
               f"file_id:\n{m.video_note.file_id}")
    elif m.video:
        out = (f"ВИДЕО ({m.video.duration} сек)\n"
               f"file_id:\n{m.video.file_id}\n\nkind: \"video\"")
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

    app = Application.builder().token(BOT_TOKEN).build()

    app.add_handler(CommandHandler("start", cmd_start))
    app.add_handler(CommandHandler("programs", cmd_programs))
    app.add_handler(CommandHandler("pauses", cmd_pauses))
    app.add_handler(CommandHandler("fast", cmd_fast))
    app.add_handler(CommandHandler("id",    cmd_id))
    app.add_handler(CommandHandler("stats", cmd_stats))
    app.add_handler(CommandHandler("report", cmd_report))
    app.add_handler(CommandHandler("lead", cmd_lead))
    app.add_handler(CommandHandler("reset", cmd_reset))
    app.add_handler(CallbackQueryHandler(on_button))
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
