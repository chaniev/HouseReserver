"""
Модуль для работы с базой данных
"""
import sqlite3
from datetime import datetime
from typing import List, Optional, Tuple
from contextlib import contextmanager
import config
from models import Admin, Property, Booking, PropertyPhoto, PropertyVideo


class Database:
    """Класс для работы с базой данных"""
    
    def __init__(self, db_path: str = config.DATABASE_PATH):
        self.db_path = db_path
        self.init_database()
    
    @contextmanager
    def get_connection(self):
        """Контекстный менеджер для работы с БД"""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        try:
            yield conn
            conn.commit()
        except Exception:
            conn.rollback()
            raise
        finally:
            conn.close()
    
    def init_database(self):
        """Инициализация базы данных и создание таблиц"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            
            # Таблица администраторов
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS admins (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER UNIQUE NOT NULL,
                    phone TEXT,
                    telegram_username TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            
            # Таблица объектов
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS properties (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT NOT NULL,
                    description TEXT,
                    admin_id INTEGER,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (admin_id) REFERENCES admins(id)
                )
            ''')
            
            # Таблица бронирований
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS bookings (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    property_id INTEGER NOT NULL,
                    user_id INTEGER NOT NULL,
                    user_username TEXT,
                    user_phone TEXT,
                    start_date DATE NOT NULL,
                    end_date DATE NOT NULL,
                    advance_paid BOOLEAN DEFAULT 0,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (property_id) REFERENCES properties(id)
                )
            ''')
            
            # Таблица фотографий объектов
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS property_photos (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    property_id INTEGER NOT NULL,
                    file_id TEXT NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (property_id) REFERENCES properties(id)
                )
            ''')
            
            # Таблица видео объектов
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS property_videos (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    property_id INTEGER NOT NULL,
                    file_id TEXT NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (property_id) REFERENCES properties(id)
                )
            ''')
    
    # Методы для работы с администраторами
    def add_admin(self, user_id: int, phone: Optional[str] = None, 
                  telegram_username: Optional[str] = None) -> bool:
        """Добавить администратора"""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    INSERT OR REPLACE INTO admins (user_id, phone, telegram_username)
                    VALUES (?, ?, ?)
                ''', (user_id, phone, telegram_username))
                config.ADMIN_IDS.add(user_id)
                return True
        except Exception as e:
            print(f"Ошибка при добавлении администратора: {e}")
            return False
    
    def get_admin(self, user_id: int) -> Optional[Admin]:
        """Получить администратора по user_id"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('SELECT * FROM admins WHERE user_id = ?', (user_id,))
            row = cursor.fetchone()
            if row:
                return Admin(
                    id=row['id'],
                    user_id=row['user_id'],
                    phone=row['phone'],
                    telegram_username=row['telegram_username'],
                    created_at=datetime.fromisoformat(row['created_at']) if row['created_at'] else None
                )
            return None
    
    def update_admin_contacts(self, user_id: int, phone: Optional[str] = None,
                             telegram_username: Optional[str] = None) -> bool:
        """Обновить контактные данные администратора"""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                updates = []
                params = []
                if phone is not None:
                    updates.append('phone = ?')
                    params.append(phone)
                if telegram_username is not None:
                    updates.append('telegram_username = ?')
                    params.append(telegram_username)
                if updates:
                    params.append(user_id)
                    cursor.execute(f'''
                        UPDATE admins SET {', '.join(updates)}
                        WHERE user_id = ?
                    ''', params)
                return True
        except Exception as e:
            print(f"Ошибка при обновлении контактов администратора: {e}")
            return False
    
    def get_all_admins(self) -> List[Admin]:
        """Получить всех администраторов"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('SELECT * FROM admins')
            return [
                Admin(
                    id=row['id'],
                    user_id=row['user_id'],
                    phone=row['phone'],
                    telegram_username=row['telegram_username'],
                    created_at=datetime.fromisoformat(row['created_at']) if row['created_at'] else None
                )
                for row in cursor.fetchall()
            ]
    
    # Методы для работы с объектами
    def add_property(self, name: str, admin_id: int, description: Optional[str] = None) -> Optional[int]:
        """Добавить объект"""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    INSERT INTO properties (name, description, admin_id)
                    VALUES (?, ?, ?)
                ''', (name, description, admin_id))
                return cursor.lastrowid
        except Exception as e:
            print(f"Ошибка при добавлении объекта: {e}")
            return None
    
    def delete_property(self, property_id: int) -> bool:
        """Удалить объект"""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                # Удаляем связанные данные
                cursor.execute('DELETE FROM property_photos WHERE property_id = ?', (property_id,))
                cursor.execute('DELETE FROM property_videos WHERE property_id = ?', (property_id,))
                cursor.execute('DELETE FROM bookings WHERE property_id = ?', (property_id,))
                cursor.execute('DELETE FROM properties WHERE id = ?', (property_id,))
                return True
        except Exception as e:
            print(f"Ошибка при удалении объекта: {e}")
            return False
    
    def get_property(self, property_id: int) -> Optional[Property]:
        """Получить объект по ID"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('SELECT * FROM properties WHERE id = ?', (property_id,))
            row = cursor.fetchone()
            if row:
                return Property(
                    id=row['id'],
                    name=row['name'],
                    description=row['description'],
                    admin_id=row['admin_id'],
                    created_at=datetime.fromisoformat(row['created_at']) if row['created_at'] else None
                )
            return None
    
    def get_all_properties(self) -> List[Property]:
        """Получить все объекты"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('SELECT * FROM properties ORDER BY id')
            return [
                Property(
                    id=row['id'],
                    name=row['name'],
                    description=row['description'],
                    admin_id=row['admin_id'],
                    created_at=datetime.fromisoformat(row['created_at']) if row['created_at'] else None
                )
                for row in cursor.fetchall()
            ]
    
    def update_property_description(self, property_id: int, description: str) -> bool:
        """Обновить описание объекта"""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    UPDATE properties SET description = ? WHERE id = ?
                ''', (description, property_id))
                return True
        except Exception as e:
            print(f"Ошибка при обновлении описания: {e}")
            return False
    
    # Методы для работы с фотографиями
    def add_property_photo(self, property_id: int, file_id: str) -> bool:
        """Добавить фотографию к объекту"""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                # Проверяем количество фотографий
                cursor.execute('SELECT COUNT(*) as count FROM property_photos WHERE property_id = ?', 
                             (property_id,))
                count = cursor.fetchone()['count']
                if count >= config.MAX_PHOTOS:
                    return False
                cursor.execute('''
                    INSERT INTO property_photos (property_id, file_id)
                    VALUES (?, ?)
                ''', (property_id, file_id))
                return True
        except Exception as e:
            print(f"Ошибка при добавлении фотографии: {e}")
            return False
    
    def get_property_photos(self, property_id: int) -> List[str]:
        """Получить все фотографии объекта"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('SELECT file_id FROM property_photos WHERE property_id = ?', (property_id,))
            return [row['file_id'] for row in cursor.fetchall()]
    
    def delete_property_photo(self, property_id: int, file_id: str) -> bool:
        """Удалить фотографию объекта"""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    DELETE FROM property_photos WHERE property_id = ? AND file_id = ?
                ''', (property_id, file_id))
                return True
        except Exception as e:
            print(f"Ошибка при удалении фотографии: {e}")
            return False
    
    # Методы для работы с видео
    def add_property_video(self, property_id: int, file_id: str) -> bool:
        """Добавить видео к объекту"""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                # Проверяем количество видео
                cursor.execute('SELECT COUNT(*) as count FROM property_videos WHERE property_id = ?', 
                             (property_id,))
                count = cursor.fetchone()['count']
                if count >= config.MAX_VIDEOS:
                    return False
                cursor.execute('''
                    INSERT INTO property_videos (property_id, file_id)
                    VALUES (?, ?)
                ''', (property_id, file_id))
                return True
        except Exception as e:
            print(f"Ошибка при добавлении видео: {e}")
            return False
    
    def get_property_videos(self, property_id: int) -> List[str]:
        """Получить все видео объекта"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('SELECT file_id FROM property_videos WHERE property_id = ?', (property_id,))
            return [row['file_id'] for row in cursor.fetchall()]
    
    def delete_property_video(self, property_id: int, file_id: str) -> bool:
        """Удалить видео объекта"""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    DELETE FROM property_videos WHERE property_id = ? AND file_id = ?
                ''', (property_id, file_id))
                return True
        except Exception as e:
            print(f"Ошибка при удалении видео: {e}")
            return False
    
    # Методы для работы с бронированиями
    def add_booking(self, property_id: int, user_id: int, user_username: Optional[str],
                   user_phone: Optional[str], start_date: datetime, end_date: datetime) -> Optional[int]:
        """Добавить бронирование"""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    INSERT INTO bookings (property_id, user_id, user_username, user_phone, 
                                         start_date, end_date)
                    VALUES (?, ?, ?, ?, ?, ?)
                ''', (property_id, user_id, user_username, user_phone, 
                     start_date.date(), end_date.date()))
                return cursor.lastrowid
        except Exception as e:
            print(f"Ошибка при добавлении бронирования: {e}")
            return None
    
    def check_date_availability(self, property_id: int, start_date: datetime, 
                               end_date: datetime, exclude_booking_id: Optional[int] = None) -> bool:
        """Проверить доступность дат для бронирования"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            if exclude_booking_id:
                cursor.execute('''
                    SELECT COUNT(*) as count FROM bookings
                    WHERE property_id = ? 
                    AND id != ?
                    AND (
                        (start_date <= ? AND end_date >= ?)
                        OR (start_date <= ? AND end_date >= ?)
                        OR (start_date >= ? AND end_date <= ?)
                    )
                ''', (property_id, exclude_booking_id, start_date.date(), start_date.date(),
                     end_date.date(), end_date.date(), start_date.date(), end_date.date()))
            else:
                cursor.execute('''
                    SELECT COUNT(*) as count FROM bookings
                    WHERE property_id = ? 
                    AND (
                        (start_date <= ? AND end_date >= ?)
                        OR (start_date <= ? AND end_date >= ?)
                        OR (start_date >= ? AND end_date <= ?)
                    )
                ''', (property_id, start_date.date(), start_date.date(),
                     end_date.date(), end_date.date(), start_date.date(), end_date.date()))
            return cursor.fetchone()['count'] == 0
    
    def get_property_bookings(self, property_id: int) -> List[Booking]:
        """Получить все бронирования объекта"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                SELECT * FROM bookings WHERE property_id = ? ORDER BY start_date
            ''', (property_id,))
            return [
                Booking(
                    id=row['id'],
                    property_id=row['property_id'],
                    user_id=row['user_id'],
                    user_username=row['user_username'],
                    user_phone=row['user_phone'],
                    start_date=datetime.fromisoformat(row['start_date']) if isinstance(row['start_date'], str) 
                             else datetime.combine(row['start_date'], datetime.min.time()),
                    end_date=datetime.fromisoformat(row['end_date']) if isinstance(row['end_date'], str)
                           else datetime.combine(row['end_date'], datetime.min.time()),
                    advance_paid=bool(row['advance_paid']),
                    created_at=datetime.fromisoformat(row['created_at']) if row['created_at'] else None
                )
                for row in cursor.fetchall()
            ]
    
    def get_user_bookings(self, user_id: int) -> List[Booking]:
        """Получить все бронирования пользователя"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                SELECT * FROM bookings WHERE user_id = ? ORDER BY start_date
            ''', (user_id,))
            return [
                Booking(
                    id=row['id'],
                    property_id=row['property_id'],
                    user_id=row['user_id'],
                    user_username=row['user_username'],
                    user_phone=row['user_phone'],
                    start_date=datetime.fromisoformat(row['start_date']) if isinstance(row['start_date'], str)
                             else datetime.combine(row['start_date'], datetime.min.time()),
                    end_date=datetime.fromisoformat(row['end_date']) if isinstance(row['end_date'], str)
                           else datetime.combine(row['end_date'], datetime.min.time()),
                    advance_paid=bool(row['advance_paid']),
                    created_at=datetime.fromisoformat(row['created_at']) if row['created_at'] else None
                )
                for row in cursor.fetchall()
            ]
    
    def delete_booking(self, booking_id: int, user_id: int) -> bool:
        """Удалить бронирование (только свое)"""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    DELETE FROM bookings WHERE id = ? AND user_id = ?
                ''', (booking_id, user_id))
                return cursor.rowcount > 0
        except Exception as e:
            print(f"Ошибка при удалении бронирования: {e}")
            return False
    
    def set_advance_paid(self, booking_id: int, paid: bool) -> bool:
        """Установить признак оплаты аванса"""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    UPDATE bookings SET advance_paid = ? WHERE id = ?
                ''', (1 if paid else 0, booking_id))
                return True
        except Exception as e:
            print(f"Ошибка при установке признака оплаты: {e}")
            return False
    
    def get_booking_statistics(self) -> List[dict]:
        """Получить статистику бронирований"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                SELECT 
                    p.id as property_id,
                    p.name as property_name,
                    COUNT(b.id) as bookings_count,
                    SUM(CASE WHEN b.advance_paid = 1 THEN 1 ELSE 0 END) as paid_count
                FROM properties p
                LEFT JOIN bookings b ON p.id = b.property_id
                GROUP BY p.id, p.name
                ORDER BY p.id
            ''')
            return [
                {
                    'property_id': row['property_id'],
                    'property_name': row['property_name'],
                    'bookings_count': row['bookings_count'],
                    'paid_count': row['paid_count']
                }
                for row in cursor.fetchall()
            ]
