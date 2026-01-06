"""
Обработчики команд для пользователей
"""
from datetime import datetime
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
from database import Database
from date_utils import parse_date, format_date, get_available_dates, find_nearest_available_dates, format_date_range, validate_date_range
import config


class UserHandlers:
    """Класс обработчиков пользователя"""
    
    def __init__(self, db: Database):
        self.db = db
    
    async def start(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Начало работы с ботом"""
        keyboard = [
            [InlineKeyboardButton("🏠 Список объектов", callback_data="user_properties")],
            [InlineKeyboardButton("📅 Мои бронирования", callback_data="user_bookings")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await update.message.reply_text(
            "👋 Добро пожаловать в бот бронирования домов!\n\n"
            "Выберите действие:",
            reply_markup=reply_markup
        )
    
    async def user_callback(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обработка callback от пользователя"""
        query = update.callback_query
        await query.answer()
        
        data = query.data
        
        if data == "user_properties":
            await self._show_properties_list(query)
        elif data == "user_bookings":
            await self._show_user_bookings(query)
        elif data.startswith("user_property_"):
            property_id = int(data.split("_")[-1])
            await self._show_property_info(query, property_id)
        elif data.startswith("user_book_"):
            property_id = int(data.split("_")[-1])
            await self._start_booking(query, property_id, context)
        elif data.startswith("user_cancel_booking_"):
            booking_id = int(data.split("_")[-1])
            await self._cancel_booking(query, booking_id)
        elif data == "user_back":
            await self._show_main_menu(query)
        elif data.startswith("user_available_dates_"):
            property_id = int(data.split("_")[-1])
            await self._show_available_dates_callback(query, property_id)
    
    async def _show_main_menu(self, query):
        """Показать главное меню"""
        keyboard = [
            [InlineKeyboardButton("🏠 Список объектов", callback_data="user_properties")],
            [InlineKeyboardButton("📅 Мои бронирования", callback_data="user_bookings")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await query.edit_message_text(
            "👋 Главное меню\n\nВыберите действие:",
            reply_markup=reply_markup
        )
    
    async def _show_properties_list(self, query):
        """Показать список объектов"""
        properties = self.db.get_all_properties()
        
        if not properties:
            await query.edit_message_text(
                "📭 Пока нет доступных объектов для бронирования."
            )
            return
        
        keyboard = []
        for prop in properties:
            keyboard.append([
                InlineKeyboardButton(
                    f"🏠 {prop.name}",
                    callback_data=f"user_property_{prop.id}"
                )
            ])
        
        keyboard.append([InlineKeyboardButton("◀️ Назад", callback_data="user_back")])
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        text = "🏠 Доступные объекты:\n\n"
        for prop in properties:
            text += f"• {prop.name}\n"
        
        await query.edit_message_text(text, reply_markup=reply_markup)
    
    async def _show_property_info(self, query, property_id: int):
        """Показать информацию об объекте"""
        property_obj = self.db.get_property(property_id)
        if not property_obj:
            await query.edit_message_text("❌ Объект не найден.")
            return
        
        # Получаем фотографии и видео
        photos = self.db.get_property_photos(property_id)
        videos = self.db.get_property_videos(property_id)
        
        # Получаем забронированные даты
        bookings = self.db.get_property_bookings(property_id)
        booked_dates = []
        for booking in bookings:
            booked_dates.append(f"{format_date(booking.start_date)} - {format_date(booking.end_date)}")
        
        text = f"🏠 {property_obj.name}\n\n"
        
        if property_obj.description:
            text += f"📄 Описание:\n{property_obj.description}\n\n"
        
        if booked_dates:
            text += "📅 Забронированные периоды:\n"
            for dates in booked_dates:
                text += f"   • {dates}\n"
            text += "\n"
        else:
            text += "✅ Объект свободен для бронирования\n\n"
        
        # Получаем контакты администратора
        admin = self.db.get_admin(property_obj.admin_id) if property_obj.admin_id else None
        if admin:
            text += "📞 Контакты владельца:\n"
            if admin.phone:
                text += f"   Телефон: {admin.phone}\n"
            if admin.telegram_username:
                text += f"   Telegram: @{admin.telegram_username}\n"
        
        keyboard = [
            [InlineKeyboardButton("📅 Забронировать", callback_data=f"user_book_{property_id}")],
            [InlineKeyboardButton("📅 Свободные даты", callback_data=f"user_available_dates_{property_id}")],
            [InlineKeyboardButton("◀️ Назад к списку", callback_data="user_properties")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        # Отправляем сообщение с текстом
        await query.edit_message_text(text, reply_markup=reply_markup)
        
        # Отправляем фотографии, если есть
        if photos:
            for photo_id in photos[:5]:  # Отправляем первые 5 фотографий
                try:
                    await query.message.reply_photo(photo_id)
                except Exception:
                    pass
        
        # Отправляем видео, если есть
        if videos:
            for video_id in videos:
                try:
                    await query.message.reply_video(video_id)
                except Exception:
                    pass
    
    async def _start_booking(self, query, property_id: int, context: ContextTypes.DEFAULT_TYPE):
        """Начать процесс бронирования"""
        # Сохраняем property_id в user_data
        context.user_data['booking_property_id'] = property_id
        
        property_obj = self.db.get_property(property_id)
        property_name = property_obj.name if property_obj else "объект"
        
        await query.edit_message_text(
            f"📅 Бронирование: {property_name}\n\n"
            "Введите даты бронирования в формате:\n"
            "DD.MM.YYYY - DD.MM.YYYY\n\n"
            "Например: 01.12.2024 - 05.12.2024"
        )
    
    async def _cancel_booking(self, query, booking_id: int):
        """Отменить бронирование"""
        user_id = query.from_user.id
        
        if self.db.delete_booking(booking_id, user_id):
            await query.answer("✅ Бронирование отменено")
            await self._show_user_bookings(query)
        else:
            await query.answer("❌ Не удалось отменить бронирование")
    
    async def _show_user_bookings(self, query):
        """Показать бронирования пользователя"""
        user_id = query.from_user.id
        bookings = self.db.get_user_bookings(user_id)
        
        if not bookings:
            keyboard = [[InlineKeyboardButton("◀️ Назад", callback_data="user_back")]]
            reply_markup = InlineKeyboardMarkup(keyboard)
            await query.edit_message_text(
                "📅 У вас пока нет бронирований.",
                reply_markup=reply_markup
            )
            return
        
        text = "📅 Ваши бронирования:\n\n"
        
        keyboard = []
        for booking in bookings:
            prop = self.db.get_property(booking.property_id)
            text += f"🏠 {prop.name if prop else 'Неизвестно'}\n"
            text += f"   Период: {format_date(booking.start_date)} - {format_date(booking.end_date)}\n"
            text += f"   Статус оплаты: {'✅ Оплачено' if booking.advance_paid else '❌ Не оплачено'}\n\n"
            
            keyboard.append([
                InlineKeyboardButton(
                    f"❌ Отменить: {prop.name if prop else 'Бронирование'}",
                    callback_data=f"user_cancel_booking_{booking.id}"
                )
            ])
        
        keyboard.append([InlineKeyboardButton("◀️ Назад", callback_data="user_back")])
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await query.edit_message_text(text, reply_markup=reply_markup)
    
    async def handle_booking_text(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обработка текста с датами бронирования"""
        user_id = update.effective_user.id
        text = update.message.text.strip()
        
        # Проверяем формат дат
        if " - " not in text and " -" not in text and "- " not in text:
            await update.message.reply_text(
                "❌ Неверный формат. Используйте: DD.MM.YYYY - DD.MM.YYYY"
            )
            return
        
        # Парсим даты
        try:
            parts = text.replace(" - ", "-").replace(" -", "-").replace("- ", "-").split("-")
            if len(parts) != 2:
                raise ValueError
            
            start_date = parse_date(parts[0].strip())
            end_date = parse_date(parts[1].strip())
            
            if not validate_date_range(start_date, end_date):
                await update.message.reply_text(
                    "❌ Неверный диапазон дат. Дата начала должна быть раньше или равна дате окончания, "
                    "и не раньше сегодняшнего дня."
                )
                return
            
        except ValueError:
            await update.message.reply_text(
                "❌ Неверный формат даты. Используйте формат DD.MM.YYYY"
            )
            return
        
        # Получаем property_id из user_data
        property_id = context.user_data.get('booking_property_id')
        
        if not property_id:
            # Если property_id не сохранен, просим пользователя выбрать объект
            await update.message.reply_text(
                "❌ Сначала выберите объект для бронирования из списка."
            )
            return
        
        # Проверяем доступность дат
        if not self.db.check_date_availability(property_id, start_date, end_date):
            # Находим ближайшие доступные даты
            nearest_dates = find_nearest_available_dates(property_id, start_date, end_date, self.db)
            
            text = "❌ Выбранные даты уже забронированы.\n\n"
            
            if nearest_dates:
                text += "📅 Ближайшие доступные периоды:\n"
                for period_start, period_end in nearest_dates[:5]:  # Показываем первые 5
                    text += f"   • {format_date_range(period_start, period_end)}\n"
            else:
                text += "К сожалению, свободных дат в ближайшее время нет."
            
            await update.message.reply_text(text)
            return
        
        # Создаем бронирование
        username = update.effective_user.username
        phone = None  # Можно добавить запрос телефона
        
        booking_id = self.db.add_booking(
            property_id, user_id, username, phone, start_date, end_date
        )
        
        if booking_id:
            property_obj = self.db.get_property(property_id)
            
            # Очищаем состояние
            context.user_data.pop('booking_property_id', None)
            
            # Отправляем уведомление администраторам
            await self._notify_admins(update, context, property_obj, start_date, end_date, username)
            
            await update.message.reply_text(
                f"✅ Бронирование успешно создано!\n\n"
                f"🏠 Объект: {property_obj.name}\n"
                f"📅 Период: {format_date_range(start_date, end_date)}\n\n"
                f"Используйте /my_bookings для просмотра ваших бронирований."
            )
        else:
            await update.message.reply_text("❌ Ошибка при создании бронирования.")
    
    async def _notify_admins(self, update: Update, context: ContextTypes.DEFAULT_TYPE,
                            property_obj, start_date: datetime, end_date: datetime, username: str):
        """Отправить уведомление администраторам о новом бронировании"""
        admins = self.db.get_all_admins()
        
        message = (
            f"🔔 Новое бронирование!\n\n"
            f"🏠 Объект: {property_obj.name}\n"
            f"📅 Период: {format_date_range(start_date, end_date)}\n"
            f"👤 Пользователь: @{username if username else 'не указан'}\n"
            f"🆔 ID пользователя: {update.effective_user.id}"
        )
        
        # Отправляем уведомления всем администраторам
        for admin in admins:
            try:
                await context.bot.send_message(
                    chat_id=admin.user_id,
                    text=message
                )
            except Exception as e:
                print(f"Ошибка при отправке уведомления администратору {admin.user_id}: {e}")
        
        # Также отправляем всем администраторам из config.ADMIN_IDS
        for admin_id in config.ADMIN_IDS:
            try:
                await context.bot.send_message(chat_id=admin_id, text=message)
            except Exception:
                pass
    
    async def _show_available_dates_callback(self, query, property_id: int):
        """Показать свободные даты для объекта через callback"""
        # Получаем бронирования
        bookings = self.db.get_property_bookings(property_id)
        
        if not bookings:
            await query.edit_message_text("✅ Объект полностью свободен для бронирования!")
            return
        
        # Находим свободные периоды
        today = datetime.now().date()
        end_search = datetime(today.year + 1, 1, 1)  # Ищем до конца года
        
        available = get_available_dates(
            property_id, 
            datetime.combine(today, datetime.min.time()),
            end_search,
            self.db
        )
        
        if available:
            text = "📅 Свободные периоды:\n\n"
            for period_start, period_end in available[:10]:  # Показываем первые 10
                text += f"   • {format_date_range(period_start, period_end)}\n"
        else:
            text = "❌ Свободных дат не найдено в ближайшее время."
        
        keyboard = [[InlineKeyboardButton("◀️ Назад", callback_data=f"user_property_{property_id}")]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await query.edit_message_text(text, reply_markup=reply_markup)
