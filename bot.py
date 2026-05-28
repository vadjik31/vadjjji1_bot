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
# Процент скидки — ТОЛЬКО для показа в Mini App (зачёркнутая цена → новая).
# Должен совпадать со скидкой, которую ты выставил на сайте в админке!
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
        "file_id": "DQACAgIAAxkBAAMfahhQbWjfCilhcGCa5i6O7rDJJTcAAlqaAAJBpahI4aN9dQb-NTs7BA",
        "sec": 47,
    },

    # ВИДЕО 1 — кейс. ⬇️ ВПИШИ в "sec" реальную длину видео в секундах.
    "video_1":       {
        "file_id": "BQACAgIAAxkBAAMjahha-z4qjKU5N0vdaA2BpkP991oAAh2ZAAKUislIlXFwBBtVE3Y7BA",
        "kind": "document",
        "sec": 90,
    },

    # ВИДЕО 2 — как работает механика. ⬇️ впиши реальную длину в "sec".
    "video_2":       {
        "file_id": "BQACAgIAAxkBAAMbahhQRlHSqn8kmwABaqjx-J74TjOjAALHoQACHH-4SDBaQh9qb6shOwQ",
        "kind": "document",
        "sec": 90,
    },

    # ВИДЕО 3 — кому НЕ стоит. ⬇️ впиши реальную длину в "sec".
    "video_3":       {
        "file_id": "BQACAgIAAxkBAAMdahhQWH8nZmU6aCjyKcSi87oVqCYAAsuhAAIcf7hI4NDb87GMAgs7BA",
        "kind": "document",
        "sec": 90,
    },

    # КРУЖОК-РАЗВИЛКА (58 сек) — после видео 3, мост к офферу.
    "circle_fork":   {
        "file_id": "DQACAgIAAxkBAAMhahhQfhCycqexkKysYDi_MMFQ4WwAAlmZAAJBpaBIUqucIOryZbc7BA",
        "sec": 58,
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
        "€472 000.\n\n"
        "Столько сделал на Amazon один человек. Не корпорация, не "
        "инвестор с миллионами — обычный парень, начавший с нуля. "
        "Кто-то делает $65 000 за месяц, кто-то пока только $236 за "
        "первую неделю — но это уже их первые деньги.\n\n"
        "Понимаю, о чём вы подумали: «ну вот, опять про миллионы». "
        "Поэтому доказывать словами не буду — просто покажу, как это "
        "устроено, а выводы сделаете сами.\n\n"
        "Три коротких видео:\n\n"
        "🎬 Реальный человек, который начал с $1000 и нуля опыта — и что "
        "из этого вышло\n"
        "⚙️ Как тут всё работает: откуда берутся деньги и где в этом ваше "
        "место\n"
        "🙅 Кому за это браться НЕ стоит — честно, без прикрас\n\n"
        "15 минут — и картина сложится. Но сначала пара слов о том, кто "
        "я такой, чтобы вы понимали, с кем говорите 👇"
    ),
    "after_circle_intro": (
        "Теперь вы знаете, кто перед вами 🙂\n\n"
        "А сейчас — та самая история. Обычный парень, не гуру и не "
        "миллионер. Взял около $1000, начал с полного нуля.\n\n"
        "Что у него вышло за несколько месяцев — честно, удивляет даже "
        "меня. Смотрите сами, это минута 👇"
    ),
    "before_v1": (
        "Включайте 👇\n\n"
        "Тут нет монтажа и красивых обещаний — просто человек по шагам "
        "рассказывает, что делал. Досмотрите до конца: финальная цифра "
        "того стоит."
    ),
    "proofs_v1_caption": (
        "И это ещё спокойный старт новичка.\n\n"
        "А вот к чему люди приходят, когда уже разобрались 👇 Разные "
        "страны, разные суммы — и каждая из этих цифр настоящая.\n\n"
        "Сразу честно: результат у всех свой. Кто вкладывает больше сил — "
        "у того и цифры выше, волшебной кнопки нет. Но путь к ним у всех "
        "один. И как именно по нему пройти — покажу в следующем видео 👇"
    ),
    "after_v1": (
        "Ну как, зацепило? 🙂\n\n"
        "Вы только что увидели, что это реально. Логичный вопрос: «окей, "
        "а как начать мне самому, с нуля?»\n\n"
        "Как раз об этом — следующее видео. Покажу, как тут всё устроено "
        "и с чего начинается путь, по которому прошли все эти люди 👇"
    ),
    "bridge_v2": (
        "Смотрите, как это работает — по-простому.\n\n"
        "Есть товары, которые в одном месте стоят дешевле, а на Amazon "
        "уходят дороже. Вы находите такой товар, выгодно берёте и "
        "отправляете на склад Amazon. Дальше Amazon всё делает сам: "
        "хранит, упаковывает, доставляет. Вы — посередине, и забираете "
        "разницу.\n\n"
        "В основе всё просто. Но есть две-три тонкости, на которых "
        "новички сливают деньги в ноль. Покажу их в видео — чтобы вы "
        "так не попали 👇"
    ),
    "proofs_v2_caption": (
        "И это не только Америка 👇 Германия, Италия, Польша, Канада — "
        "люди зарабатывают по всему миру.\n\n"
        "Но прежде чем вы загоритесь — посмотрите следующее видео. Оно "
        "честно скажет, стоит ли вам вообще в это лезть."
    ),
    "after_v2": (
        "Теперь вы понимаете, как это работает 🙂\n\n"
        "Но вот что интересно: даже зная всё это, большинство так и не "
        "начинает. Почему?\n\n"
        "За 6 лет я насмотрелся на это столько, что вывел 5 главных "
        "причин. В следующем видео честно их разберу — и, возможно, "
        "узнаете в них себя 👇"
    ),
    "bridge_v3": (
        "Вот они — 5 причин, по которым люди так и не доходят до первых "
        "денег. За 6 лет я видел их снова и снова.\n\n"
        "Посмотрите честно: если узнаете в этом себя — ничего страшного, "
        "это поправимо. А если поймёте, что вас это не останавливает — "
        "значит, вы из тех, у кого получается.\n\n"
        "И тогда дальше будет уже предметный разговор 👇"
    ),
    "after_v3": (
        "Досмотрели? Снимаю шляпу 🙌\n\n"
        "Большинство закрывает на первой минуте — как только понимают, "
        "что придётся что-то делать. Вы дошли. Это уже говорит о вас "
        "больше, чем любые слова.\n\n"
        "И вот что у вас теперь есть: живой пример, понимание, как всё "
        "устроено, и честная картина рисков. Это уже больше, чем у 90% "
        "тех, кто «думал про Amazon».\n\n"
        "Остался один шаг — и он решает всё. Минута 👇"
    ),
    "after_fork_circle": (
        "Итак, главный вопрос — как вам повторить их результаты?\n\n"
        "Не «попробовать и бросить через неделю», а реально дойти до "
        "первых продаж. Сейчас расскажу, как это работает со мной: что "
        "входит, сколько стоит и что вы получаете в итоге.\n\n"
        "Читайте дальше — там всё по делу 👇"
    ),
    "offer_text": (
        "Коротко — что вы получаете и чем я помогаю:\n\n"
        "✅ Находим, у кого закупать товар, и проходим все проверки\n"
        "✅ Подбираем товары, на которых реально заработать, и считаем "
        "всё заранее — чтобы вы не ушли в минус\n"
        "✅ Делаем первую отправку на Amazon правильно — без ошибок, из-за "
        "которых блокируют новичков\n"
        "✅ И я всё время рядом: отвечаю на вопросы, разбираю сложные "
        "моменты\n\n"
        "Со мной вас доводят за руку до первых реальных продаж. А сколько "
        "это стоит — скажу честно, прямо сейчас 👇"
    ),
    "offer_price_and_call": (
        "Про деньги — честно.\n\n"
        "Обучение стоит в пределах [X–Y]. Точная цифра зависит от "
        "формата: группа с другими ребятами или работа со мной один на "
        "один. Назову её на созвоне — когда увижу вашу ситуацию и пойму, "
        "что вам реально нужно, а за что не стоит переплачивать.\n\n"
        "Сам созвон — 30 минут по видео:\n\n"
        "👉 Вы рассказываете, где сейчас: бюджет, время, опыт\n"
        "👉 Я честно говорю — подходит вам Amazon или нет\n"
        "👉 Если да — показываю план по шагам\n"
        "👉 Если нет — подскажу, чем заняться вместо этого\n\n"
        "Даже если не пойдёте дальше — уйдёте с готовым планом и "
        "ясностью. Это уже того стоит."
    ),
    "offer_risk": (
        "Всё официально, по договору — без «на честном слове».\n\n"
        "А на созвоне можете задавать любые неудобные вопросы — про "
        "деньги, риски, гарантии. Чем жёстче спросите, тем полезнее вам "
        "будет ответ. Я к этому готов 🙂"
    ),
    "offer_gift": (
        "🎁 И ещё кое-что.\n\n"
        "В любой вариант обучения входит набор инструментов на ~$1839 — "
        "бесплатно, в подарок. Это готовые помощники: подсказывают, какие "
        "товары брать, помогают находить поставщиков и держать выгодную "
        "цену. То, на что новички обычно тратят месяцы, у вас будет "
        "сразу.\n\n"
        "Посмотрите, что именно входит и сколько уже заработали "
        "ученики — кнопка ниже 👇 Там всё простыми словами и с реальными "
        "цифрами."
    ),
    "programs_text": (
        "Вот варианты обучения — от «разберусь сам» до «сделаем всё "
        "вместе под ключ» 👇\n\n"
        "1️⃣ Обучаюсь сам — $750\n"
        "Все уроки, программы-помощники, записи прошлых занятий, доступ "
        "навсегда. Идёте в своём темпе.\n\n"
        "2️⃣ Поток — $1100\n"
        "Всё то же + занятия в группе и 2 личных созвона со мной, один "
        "проверенный поставщик на старт и поддержка. Ведём до первых "
        "продаж.\n\n"
        "3️⃣ Продвинутый — $1700 ⭐ (берут чаще всего)\n"
        "Всё из «Потока» + 4 личных созвона, три поставщика, выбор рынка "
        "(Америка или Европа) и поддержка 4 месяца.\n\n"
        "4️⃣ Под ключ — $4200 💎 (всё включено)\n"
        "Делаем бизнес вместе: 12 личных созвонов, 10 поставщиков и "
        "помощь с подбором 50 товаров, личный сайт и программа учёта, "
        "поддержка полгода. Цель — $15 000+ продаж в месяц.\n\n"
        "🎁 И в каждый вариант входят подарки-помощники на ~$1839.\n\n"
        "Что подойдёт именно вам — разберём на созвоне, помогу выбрать 🙂"
    ),
    "students_caption": (
        "США, Франция, Германия, Италия, Канада 👇 Кто-то рванул быстро, "
        "кто-то шёл спокойно — но все они начинали ровно там, где вы "
        "сейчас. Разница только в том, что они уже сделали первый шаг."
    ),
    "site_caption": (
        "И это лишь часть 👇 На сайте — десятки историй и живых отзывов, "
        "некоторые впечатляют куда сильнее. Загляните, если хочется "
        "убедиться окончательно."
    ),
    "back_to_offer": (
        "Ну что, готовы? 🙂 Созвон ни к чему не обязывает — но именно с "
        "него у большинства учеников всё и началось."
    ),

    "q1": (
        "Окей, давайте по делу 🙂\n\n"
        "Сколько примерно готовы вложить в первый товар? Это не плата за "
        "обучение — это деньги на саму первую закупку. От этого зависит, "
        "с чего вам стартовать."
    ),
    "q1_opts": ["до $300", "$300–1000", "$1000+", "Пока не готов"],
    "q2": (
        "Понял 🙂 А сколько времени в день реально сможете уделять? "
        "Честно — лучше меньше, но стабильно. От этого зависит, как "
        "быстро пойдут результаты."
    ),
    "q2_opts": ["меньше часа", "1–2 часа", "2+ часа"],
    "q3": (
        "И последнее — когда хотите начать? От этого зависит, что именно "
        "я вам предложу на созвоне."
    ),
    "q3_opts": ["сейчас", "в течение месяца", "просто изучаю"],

    "after_quiz": (
        "Отлично, спасибо! 🙌 Посмотрю ваши ответы и свяжусь с вами "
        "лично — подберу, что подойдёт именно вам. А если не хотите "
        "ждать, напишите мне прямо сейчас 👇"
    ),
    "cold_finish": (
        "Понимаю — спешить некуда, и это нормально 🙂 Раз вы пока "
        "присматриваетесь, держите кое-что полезное на это время — чтобы "
        "потом стартовать уже подготовленным."
    ),

    "drip_after_v1": (
        "Вы остановились на самом интересном 🙂 Дальше — то, ради чего всё "
        "и затевалось: где в этой схеме лежат деньги и как их забрать. "
        "Пара минут, и многое прояснится 👇"
    ),
    "drip_after_v3": (
        "Вы почти у цели 🙌 Остался один шаг — и он решает всё. "
        "Посмотрим, что дальше?"
    ),
    "drip_after_offer": (
        "Вижу, вы всё посмотрели, но пока не написали 🙂 Бывает!\n\n"
        "Если остался вопрос или что-то останавливает — напишите мне "
        "лично, разберёмся. Или сразу запишитесь на созвон, пока есть "
        "место. А если пока приглядываетесь — заберите подарок ниже 👇"
    ),
    "drip_after_lead": (
        "Вы оставили заявку — я уже на связи 🙌 Если так удобнее, "
        "напишите мне сами, вот прямой контакт 👇"
    ),

    "lm_offer": (
        "Держите кое-что действительно полезное 🎁\n\n"
        "Это разбор ошибок, которые я чаще всего видел за 6 лет — тех "
        "самых, из-за которых люди теряют все вложенные деньги.\n\n"
        "И это не просто список «не делай так». Внутри по каждой ошибке: "
        "как люди делали и к чему это приводило, как надо было сделать "
        "правильно, и чего не стоит делать вообще никогда.\n\n"
        "Прочитаете до старта — сэкономите и деньги, и нервы. Отдаю "
        "бесплатно, нужен один простой шаг 👇"
    ),
    "lm_subscribe": (
        "Супер! 🙌 Всё, что нужно — подписаться на мой канал. Подпишетесь, "
        "нажмёте кнопку ниже — и подарок сразу прилетит сюда. Заодно "
        "будете видеть свежие разборы и истории учеников."
    ),
    "lm_not_subscribed": (
        "Хм, пока не вижу подписку 🤔 Загляните в канал по кнопке выше и "
        "нажмите «Я подписался» ещё разок."
    ),
    "lm_delivered": (
        "Держите! 🎁 Внутри — три ошибки, на которых теряют деньги, и как "
        "их обойти.\n\n"
        "Прочитаете — и если захотите разобрать уже вашу ситуацию, я на "
        "связи. Один созвон часто экономит больше, чем стоит сам 👇"
    ),
    "lm_skip": (
        "Без проблем 🙂 Передумаете — подарок никуда не денется. А будут "
        "вопросы, просто пишите, помогу 👇"
    ),
    "lm_error": (
        "Что-то не получилось проверить подписку — возможно, канал ещё "
        "настраивается. Напишите мне лично, и я пришлю подарок руками 👇"
    ),

    "promo_hot": (
        "🔥 А вот теперь — лично для вас.\n\n"
        "Раз вы настроены серьёзно, держите: 24 часа скидки на обучение, "
        "и сверху личный созвон со мной в подарок — разберём именно вашу "
        "ситуацию.\n\n"
        "Цены уже пересчитаны, таймер пошёл 👇 Через {hours} часа всё "
        "вернётся к обычной цене. Успеете — заберёте по максимуму."
    ),
    "promo_warm": (
        "Раз вам откликается — кое-что лично для вас 🙂\n\n"
        "На 24 часа: скидка на обучение плюс личный созвон со мной в "
        "подарок, разберём вашу ситуацию вживую.\n\n"
        "Цены со скидкой и таймер — по кнопке ниже 👇 Через {hours} часа "
        "предложение закроется."
    ),
    "promo_pinned": (
        "⏳ Ваша скидка и личный созвон в подарок — активны.\n"
        "Осталось: {left}\n\n"
        "Забрать — кнопка в сообщении выше 👆"
    ),
    "promo_expired": (
        "⌛ Время скидки вышло.\n\n"
        "Но дверь не закрыта — запишитесь на разбор, и мы вместе "
        "придумаем, как вам помочь. Напишите мне 👇"
    ),
    "promo_drip": (
        "Тикает ⏳ Ваша скидка и созвон в подарок ещё в силе, но скоро "
        "закроются. Если хотите успеть — самое время 👇"
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
    "programs":   "💎 Что входит в обучение",
    "site":       "Открыть сайт с результатами",
    "to_lead":    "🎁 Получить бонус и начать с Вадимом",
    "lm_get":     "📘 Забрать гайд по ошибкам",
    "contact":    "Написать @vadjik",
    # лид-магнит
    "lm_grab":    "Забрать топ-3 ошибки (бесплатно)",
    "lm_want":    "Хочу забрать",
    "lm_skip":    "Пропустить",
    "lm_goto":    "Перейти в канал",
    "lm_check":   "Я подписался ✅",
    # промо
    "promo_get":  "🔥 Забрать скидку + созвон",
    "promo_app":  "💎 Программы со скидкой",
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


async def send_step(bot, uid, text, rows=None, **kwargs):
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
    msg = await bot.send_message(uid, text, reply_markup=markup, **kwargs)
    if rows:
        rec["last_kb_msg"] = msg.message_id
        save_state(STATE)
    return msg


# ---------------- ПАУЗЫ МЕЖДУ СООБЩЕНИЯМИ ----------------
# Бот «дышит»: даёт человеку время посмотреть кружок/видео и прочитать
# текст, прежде чем слать следующее сообщение. Без этого всё валится
# разом и выглядит как робот.

# Выключить паузы (для быстрых тестов): переменная окружения PAUSES=0
PAUSES_ON = os.getenv("PAUSES", "1").strip().lower() not in ("0", "false", "no", "")
READ_WPM = 200            # скорость чтения, слов в минуту (выше = пауза короче)
MIN_TEXT_PAUSE = 1.0      # сек — минимум между сообщениями
MAX_TEXT_PAUSE = 6        # сек — потолок паузы на чтение текста
MAX_MEDIA_PAUSE = 55      # сек — потолок паузы после видео/кружка
# Доля длины видео/кружка, которую ждём (0.7 = «чуть минус», человек не
# обязан досматривать до последней секунды). Настраивается через env.
MEDIA_PAUSE_FACTOR = float(os.getenv("MEDIA_PAUSE_FACTOR", "0.7") or "0.7")


async def hold(seconds):
    """Тихая пауза (без 'печатает'). Уважает потолок и флаг PAUSES."""
    if PAUSES_ON and seconds and seconds > 0:
        await asyncio.sleep(min(seconds, MAX_MEDIA_PAUSE))


def read_time(text):
    """Сколько секунд человеку нужно, чтобы прочитать этот текст."""
    words = max(1, len((text or "").split()))
    t = words / READ_WPM * 60
    return max(MIN_TEXT_PAUSE, min(t, MAX_TEXT_PAUSE))


def media_sec(key):
    """Длительность кружка/видео (сек)."""
    return MEDIA.get(key, {}).get("sec", 0)


def media_pause(key):
    """Пауза после видео/кружка — чуть меньше его длины."""
    return media_sec(key) * MEDIA_PAUSE_FACTOR


def webapp_url_full():
    """URL Mini App с подставленными ссылками contact/site."""
    if not WEBAPP_URL:
        return ""
    return (f"{WEBAPP_URL}?contact={quote(CALL_LINK, safe='')}"
            f"&site={quote(SITE_LINK, safe='')}")


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
    try:
        if GUIDE_FILE_ID:
            await bot.send_document(chat_id, GUIDE_FILE_ID)
            return
        if os.path.exists(GUIDE_PATH):
            with open(GUIDE_PATH, "rb") as f:
                await bot.send_document(chat_id, f, filename=GUIDE_FILENAME)
            return
        log.error("guide not found: GUIDE_FILE_ID пуст и нет %s", GUIDE_PATH)
        await bot.send_message(
            chat_id,
            "Гайд временно недоступен — напишите мне лично, пришлю вручную.",
            reply_markup=kb([(BTN["contact"], CALL_LINK, True)]),
        )
    except Exception as e:
        log.error("send_guide failed: %s", e)


# ---------------- ПОКАЗ ПРОМО ----------------

async def show_promo(context, uid, user, temperature):
    """Выдаёт персональную скидку: ссылка с подписью, закреп, таймер."""
    bot = context.bot
    rec = u(uid)

    if not PROMO_SECRET:
        # секрет не задан — не выдаём кривую ссылку, ведём на разбор
        await send_step(bot, uid, TXT["after_quiz"], [(BTN["contact"], CALL_LINK, True)])
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
    await hold(read_time(intro))

    # закреплённое сообщение с таймером (обычным send_message, чтобы НЕ
    # снять кнопки с промо-сообщения выше)
    try:
        pin = await bot.send_message(
            uid, TXT["promo_pinned"].format(left=fmt_left(deadline)))
        await bot.pin_chat_message(uid, pin.message_id,
                                   disable_notification=True)
        rec["promo"]["pin_msg_id"] = pin.message_id
        save_state(STATE)
        # обновляем закреп раз в 30 минут (не чаще — бережём лимиты Telegram)
        context.application.job_queue.run_repeating(
            promo_tick, interval=1800, first=1800,
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
    """Обновляет закреплённое сообщение с обратным отсчётом."""
    uid = context.job.data["uid"]
    rec = u(uid)
    promo = rec.get("promo") or {}
    pin_id = promo.get("pin_msg_id")
    deadline = promo.get("deadline", 0)
    if not pin_id:
        context.job.schedule_removal()
        return
    bot = context.bot
    if time.time() >= deadline:
        # истекло — финальный текст, открепить, остановить джоб
        try:
            await bot.edit_message_text(TXT["promo_expired"], uid, pin_id)
            await bot.unpin_chat_message(uid, pin_id)
        except Exception as e:
            log.error("promo expire failed: %s", e)
        context.job.schedule_removal()
        return
    try:
        await bot.edit_message_text(
            TXT["promo_pinned"].format(left=fmt_left(deadline)), uid, pin_id)
    except Exception:
        pass  # текст не изменился или сообщение удалено — не страшно


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
            # текст + 3 кнопки: разбор / лид-магнит / личка
            await send_step(bot, uid, TXT["drip_after_offer"], [
                    (BTN["to_lead"], "go_lead", False),
                    (BTN["lm_grab"], "lm_want", False),
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
                    [(BTN["start"], "go_intro", False)])


async def go_intro(update, context):
    uid = update.effective_user.id
    bot = context.bot
    await send_circle(bot, uid, "circle_intro")
    await hold(media_pause("circle_intro"))     # даём посмотреть кружок
    await send_step(bot, uid, TXT["after_circle_intro"],
                    [(BTN["to_v1"], "go_v1", False)])
    set_step(uid, "intro")


async def go_v1(update, context):
    uid = update.effective_user.id
    bot = context.bot
    await bot.send_message(uid, TXT["before_v1"])
    await hold(read_time(TXT["before_v1"]))
    await send_media_file(bot, uid, "video_1")
    await hold(media_pause("video_1"))          # даём посмотреть видео
    await send_proofs(bot, uid, PROOFS_AFTER_V1, TXT["proofs_v1_caption"])
    await hold(len(PROOFS_AFTER_V1) * 2 + 2)  # даём разглядеть скрины
    await send_step(bot, uid, TXT["after_v1"],
                    [(BTN["to_v2"], "go_v2", False)])
    set_step(uid, "v1")
    schedule_drip(context.application, uid, "after_v1", DRIP_HOURS["after_v1"])


async def go_v2(update, context):
    uid = update.effective_user.id
    bot = context.bot
    cancel_drips(context.application, uid)
    await bot.send_message(uid, TXT["bridge_v2"])
    await hold(read_time(TXT["bridge_v2"]))
    await send_media_file(bot, uid, "video_2")
    await hold(media_pause("video_2"))
    await send_proofs(bot, uid, PROOFS_AFTER_V2, TXT["proofs_v2_caption"])
    await hold(len(PROOFS_AFTER_V2) * 2 + 2)
    await send_step(bot, uid, TXT["after_v2"],
                    [(BTN["to_v3"], "go_v3", False)])
    set_step(uid, "v2")


async def go_v3(update, context):
    uid = update.effective_user.id
    bot = context.bot
    await bot.send_message(uid, TXT["bridge_v3"])
    await hold(read_time(TXT["bridge_v3"]))
    await send_media_file(bot, uid, "video_3")
    await hold(media_pause("video_3"))
    await send_step(bot, uid, TXT["after_v3"],
                    [(BTN["to_fork"], "go_fork", False)])
    set_step(uid, "v3")
    schedule_drip(context.application, uid, "after_v3", DRIP_HOURS["after_v3"])


async def go_fork(update, context):
    uid = update.effective_user.id
    bot = context.bot
    cancel_drips(context.application, uid)
    await send_circle(bot, uid, "circle_fork")
    await hold(media_pause("circle_fork"))      # даём посмотреть кружок
    await send_step(bot, uid, TXT["after_fork_circle"],
                    [(BTN["to_offer"], "go_offer", False)])
    set_step(uid, "fork")


async def go_offer(update, context):
    uid = update.effective_user.id
    bot = context.bot
    cancel_drips(context.application, uid)
    await bot.send_message(uid, TXT["offer_text"])
    await hold(read_time(TXT["offer_text"]))
    await bot.send_message(uid, TXT["offer_price_and_call"])
    await hold(read_time(TXT["offer_price_and_call"]))
    await bot.send_message(uid, TXT["offer_gift"])
    await hold(read_time(TXT["offer_gift"]))

    # Кнопка «Что входит»: Mini App если есть URL, иначе текстовый показ.
    if WEBAPP_URL:
        programs_btn = (BTN["programs"], webapp_url_full(), "webapp")
    else:
        programs_btn = (BTN["programs"], "go_programs", False)

    await send_step(bot, uid, TXT["offer_risk"], [
        programs_btn,
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
        await send_step(bot, uid, "Открываю программы и результаты:", [
                (BTN["programs"], webapp_url_full(), "webapp"),
                (BTN["to_lead"], "go_lead", False),
            ])
        return
    # иначе — тарифы текстом + старый показ результатов фото
    await bot.send_message(uid, TXT["programs_text"])
    await hold(read_time(TXT["programs_text"]))
    await send_proofs(bot, uid, PROOFS_STUDENTS, TXT["students_caption"])
    await hold(len(PROOFS_STUDENTS) * 1.5 + 2)
    await send_proofs(bot, uid, [SITE_SCREEN], TXT["site_caption"])
    await hold(3)
    await send_step(bot, uid, TXT["back_to_offer"], [
        (BTN["site"], SITE_LINK, True),
        (BTN["to_lead"], "go_lead", False),
    ])


async def go_students(update, context):
    uid = update.effective_user.id
    bot = context.bot
    await send_proofs(bot, uid, PROOFS_STUDENTS, TXT["students_caption"])
    await hold(len(PROOFS_STUDENTS) * 1.5 + 2)
    await send_proofs(bot, uid, [SITE_SCREEN], TXT["site_caption"])
    await hold(3)
    await send_step(bot, uid, TXT["back_to_offer"], [
        (BTN["site"],    SITE_LINK, True),
        (BTN["to_lead"], "go_lead", False),
    ])


async def go_lead(update, context):
    """Человек нажал «Записаться на разбор» — выдаём промо (скидка + созвон).
    Квиза больше нет: дошёл до этого шага → значит заинтересован."""
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
                f"🔥 НОВАЯ ЗАЯВКА — выдана скидка + созвон\n"
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
    global PAUSES_ON
    if update.effective_user.id != ADMIN_ID:
        return
    PAUSES_ON = not PAUSES_ON
    if PAUSES_ON:
        txt = ("⏳ Паузы ВКЛЮЧЕНЫ — бот делает живые задержки между "
               "сообщениями, как видят клиенты.\n\nНапиши /pauses ещё раз, "
               "чтобы выключить и пролистать воронку быстро.")
    else:
        txt = ("⚡ Паузы ВЫКЛЮЧЕНЫ — сообщения идут сразу, удобно быстро "
               "просмотреть всю воронку.\n\nНапиши /pauses ещё раз, чтобы "
               "вернуть живой темп для клиентов.")
    await update.message.reply_text(txt)


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
