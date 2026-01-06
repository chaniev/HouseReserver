"""
Модели данных для базы данных
"""
from datetime import datetime
from typing import Optional
from dataclasses import dataclass


@dataclass
class Admin:
    """Модель администратора"""
    id: int
    user_id: int
    phone: Optional[str] = None
    telegram_username: Optional[str] = None
    created_at: Optional[datetime] = None


@dataclass
class Property:
    """Модель объекта недвижимости"""
    id: int
    name: str
    description: Optional[str] = None
    admin_id: int = None
    created_at: Optional[datetime] = None


@dataclass
class Booking:
    """Модель бронирования"""
    id: int
    property_id: int
    user_id: int
    user_username: Optional[str]
    user_phone: Optional[str]
    start_date: datetime
    end_date: datetime
    advance_paid: bool = False
    created_at: Optional[datetime] = None


@dataclass
class PropertyPhoto:
    """Модель фотографии объекта"""
    id: int
    property_id: int
    file_id: str
    created_at: Optional[datetime] = None


@dataclass
class PropertyVideo:
    """Модель видео объекта"""
    id: int
    property_id: int
    file_id: str
    created_at: Optional[datetime] = None
