"""
Утилиты для работы с датами
"""
from datetime import datetime, timedelta
from typing import List, Tuple
from database import Database


def parse_date(date_str: str) -> datetime:
    """Парсинг даты из строки формата DD.MM.YYYY"""
    try:
        return datetime.strptime(date_str.strip(), '%d.%m.%Y')
    except ValueError:
        raise ValueError("Неверный формат даты. Используйте DD.MM.YYYY")


def format_date(date: datetime) -> str:
    """Форматирование даты в строку DD.MM.YYYY"""
    return date.strftime('%d.%m.%Y')


def get_available_dates(property_id: int, start_date: datetime, 
                       end_date: datetime, db: Database) -> List[Tuple[datetime, datetime]]:
    """
    Получить список доступных периодов для бронирования
    Возвращает список кортежей (start, end) доступных периодов
    """
    bookings = db.get_property_bookings(property_id)
    
    # Сортируем бронирования по дате начала
    bookings.sort(key=lambda x: x.start_date)
    
    available_periods = []
    current_date = start_date
    
    for booking in bookings:
        # Если текущая дата до начала бронирования
        if current_date < booking.start_date:
            # Добавляем период от current_date до начала бронирования
            if current_date <= end_date:
                period_end = min(booking.start_date - timedelta(days=1), end_date)
                if period_end >= current_date:
                    available_periods.append((current_date, period_end))
        
        # Обновляем текущую дату на дату после окончания бронирования
        if booking.end_date >= current_date:
            current_date = booking.end_date + timedelta(days=1)
    
    # Добавляем оставшийся период после всех бронирований
    if current_date <= end_date:
        available_periods.append((current_date, end_date))
    
    return available_periods


def find_nearest_available_dates(property_id: int, start_date: datetime, 
                                 end_date: datetime, db: Database, 
                                 days_ahead: int = 30) -> List[Tuple[datetime, datetime]]:
    """
    Найти ближайшие доступные даты после запрошенного периода
    """
    # Ищем доступные даты в следующих N днях после запрошенного периода
    search_start = end_date + timedelta(days=1)
    search_end = search_start + timedelta(days=days_ahead)
    
    return get_available_dates(property_id, search_start, search_end, db)


def format_date_range(start: datetime, end: datetime) -> str:
    """Форматирование диапазона дат"""
    return f"{format_date(start)} - {format_date(end)}"


def validate_date_range(start_date: datetime, end_date: datetime) -> bool:
    """Проверка корректности диапазона дат"""
    today = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
    return start_date <= end_date and start_date.date() >= today.date()
