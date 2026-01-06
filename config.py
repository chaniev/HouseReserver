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
MAX_PHOTOS = int(os.getenv('MAX_PHOTOS', '10'))

# Максимальное количество видео на объект
MAX_VIDEOS = int(os.getenv('MAX_VIDEOS', '2'))

# ID администраторов (можно добавить через команду)
# Формат: ADMIN_IDS=123456789,987654321 (через запятую)
ADMIN_IDS_STR = os.getenv('ADMIN_IDS', '')
ADMIN_IDS = set(int(admin_id.strip()) for admin_id in ADMIN_IDS_STR.split(',') if admin_id.strip()) if ADMIN_IDS_STR else set()

# Настройки логирования
LOG_LEVEL = os.getenv('LOG_LEVEL', 'INFO')
LOG_FORMAT = os.getenv('LOG_FORMAT', '%(asctime)s - %(name)s - %(levelname)s - %(message)s')
