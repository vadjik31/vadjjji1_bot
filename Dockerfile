# Лёгкий образ с Python 3.11
FROM python:3.11-slim

# Рабочая папка внутри контейнера
WORKDIR /app

# Кладём данные пользователей в /data — туда мы будем подключать Volume
ENV DATA_DIR=/data
RUN mkdir -p /data

# Сначала зависимости (для кэша слоёв Docker)
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Потом сам код
COPY . .

# Не от root, для безопасности
RUN useradd -m -u 1000 bot && chown -R bot:bot /app /data
USER bot

CMD ["python", "bot.py"]
