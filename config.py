"""
Конфигурационный файл для телеграм-бота бронирования домов
"""
import os
from dotenv import load_dotenv

load_dotenv()

# Токен бота из переменных окружения
BOT_TOKEN = os.getenv('BOT_TOKEN', '')

# Путь к базе данных
DATABASE_PATH = os.getenv('DATABASE_PATH', 'house_reserv.db')

# Максимальное количество фотографий на объект
MAX_PHOTOS = 10

# Максимальное количество видео на объект
MAX_VIDEOS = 2

# ID администраторов (можно добавить через команду)
ADMIN_IDS = set()
