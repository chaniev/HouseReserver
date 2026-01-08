FROM python:3.11-slim

WORKDIR /app

# Копируем файл зависимостей
COPY requirements.txt .

# Устанавливаем зависимости
RUN pip install --no-cache-dir -r requirements.txt

# Копируем весь код приложения
COPY *.py ./

# Создаем директорию для базы данных
RUN mkdir -p /app/data

# Устанавливаем переменную окружения для базы данных по умолчанию
ENV DATABASE_PATH=/app/data/house_reserv.db

# Запускаем бота
CMD ["python", "bot.py"]
