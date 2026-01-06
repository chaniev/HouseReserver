"""
Обработчики команд для администраторов
"""
from datetime import datetime
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
from database import Database
from date_utils import format_date
import config


class AdminHandlers:
    """Класс обработчиков администратора"""
    
    def __init__(self, db: Database):
        self.db = db
    
    def is_admin(self, user_id: int) -> bool:
        """Проверить, является ли пользователь администратором"""
        return user_id in config.ADMIN_IDS or self.db.get_admin(user_id) is not None
    
    async def start_admin(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Начало работы администратора"""
        user_id = update.effective_user.id
        
        if not self.is_admin(user_id):
            await update.message.reply_text(
                "❌ У вас нет прав администратора.\n\n"
                "Для получения прав администратора используйте команду /register_admin"
            )
            return
        
        keyboard = [
            [InlineKeyboardButton("📝 Управление объектами", callback_data="admin_properties")],
            [InlineKeyboardButton("📊 Статистика бронирований", callback_data="admin_stats")],
            [InlineKeyboardButton("👤 Мои контакты", callback_data="admin_contacts")],
            [InlineKeyboardButton("⚙️ Изменить контакты", callback_data="admin_edit_contacts")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await update.message.reply_text(
            "👋 Добро пожаловать в панель администратора!\n\n"
            "Выберите действие:",
            reply_markup=reply_markup
        )
    
    async def register_admin(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Регистрация администратора"""
        user_id = update.effective_user.id
        username = update.effective_user.username
        
        if self.db.add_admin(user_id, telegram_username=username):
            config.ADMIN_IDS.add(user_id)
            await update.message.reply_text(
                "✅ Вы успешно зарегистрированы как администратор!\n\n"
                "Используйте /admin для доступа к панели управления."
            )
        else:
            await update.message.reply_text("❌ Ошибка при регистрации администратора.")
    
    async def admin_callback(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обработка callback от администратора"""
        query = update.callback_query
        await query.answer()
        user_id = query.from_user.id
        
        if not self.is_admin(user_id):
            await query.edit_message_text("❌ У вас нет прав администратора.")
            return
        
        data = query.data
        
        if data == "admin_back" or data == "admin_properties":
            await self._show_properties_menu(query)
        elif data == "admin_stats":
            await self._show_statistics(query)
        elif data == "admin_contacts":
            await self._show_contacts(query)
        elif data == "admin_edit_contacts":
            await self._edit_contacts(query)
        elif data.startswith("admin_property_") and not data.startswith("admin_delete_property_") and not data.startswith("admin_edit_property_"):
            property_id = int(data.split("_")[-1])
            await self._show_property_details(query, property_id)
        elif data.startswith("admin_delete_property_"):
            property_id = int(data.split("_")[-1])
            await self._delete_property(query, property_id)
        elif data == "admin_add_property":
            await self._add_property_start(query, context)
        elif data.startswith("admin_edit_property_"):
            parts = data.split("_")
            property_id = int(parts[-1])
            action = parts[-2]
            await self._edit_property_action(query, property_id, action, context)
        elif data.startswith("admin_booking_"):
            booking_id = int(data.split("_")[-1])
            action = data.split("_")[-2]
            await self._booking_action(query, booking_id, action)
    
    async def _show_properties_menu(self, query):
        """Показать меню управления объектами"""
        properties = self.db.get_all_properties()
        
        keyboard = []
        for prop in properties:
            keyboard.append([
                InlineKeyboardButton(
                    f"🏠 {prop.name}",
                    callback_data=f"admin_property_{prop.id}"
                )
            ])
        
        keyboard.append([InlineKeyboardButton("➕ Добавить объект", callback_data="admin_add_property")])
        keyboard.append([InlineKeyboardButton("◀️ Назад", callback_data="admin_back")])
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        text = "📝 Управление объектами\n\n"
        if properties:
            text += "Выберите объект для редактирования:"
        else:
            text += "Объектов пока нет. Добавьте первый объект!"
        
        await query.edit_message_text(text, reply_markup=reply_markup)
    
    async def _show_property_details(self, query, property_id: int):
        """Показать детали объекта"""
        property_obj = self.db.get_property(property_id)
        if not property_obj:
            await query.edit_message_text("❌ Объект не найден.")
            return
        
        photos = self.db.get_property_photos(property_id)
        videos = self.db.get_property_videos(property_id)
        
        text = f"🏠 {property_obj.name}\n\n"
        if property_obj.description:
            text += f"📄 Описание:\n{property_obj.description}\n\n"
        text += f"📷 Фотографий: {len(photos)}/{config.MAX_PHOTOS}\n"
        text += f"🎥 Видео: {len(videos)}/{config.MAX_VIDEOS}\n"
        
        keyboard = [
            [InlineKeyboardButton("✏️ Изменить описание", callback_data=f"admin_edit_property_desc_{property_id}")],
            [InlineKeyboardButton("📷 Управление фото", callback_data=f"admin_edit_property_photos_{property_id}")],
            [InlineKeyboardButton("🎥 Управление видео", callback_data=f"admin_edit_property_videos_{property_id}")],
            [InlineKeyboardButton("🗑️ Удалить объект", callback_data=f"admin_delete_property_{property_id}")],
            [InlineKeyboardButton("◀️ Назад", callback_data="admin_properties")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await query.edit_message_text(text, reply_markup=reply_markup)
    
    async def _add_property_start(self, query, context: ContextTypes.DEFAULT_TYPE):
        """Начать добавление объекта"""
        context.user_data['waiting_for_property_name'] = True
        await query.edit_message_text(
            "➕ Добавление нового объекта\n\n"
            "Отправьте название объекта:"
        )
    
    async def _delete_property(self, query, property_id: int):
        """Удалить объект"""
        if self.db.delete_property(property_id):
            await query.edit_message_text("✅ Объект успешно удален.")
        else:
            await query.edit_message_text("❌ Ошибка при удалении объекта.")
    
    async def _edit_property_action(self, query, property_id: int, action: str, context: ContextTypes.DEFAULT_TYPE):
        """Действие редактирования объекта"""
        if action == "desc":
            context.user_data['waiting_for_property_description'] = property_id
            await query.edit_message_text(
                "✏️ Изменение описания\n\n"
                "Отправьте новое описание объекта:"
            )
        elif action == "photos":
            context.user_data['waiting_for_property_photo'] = property_id
            await query.edit_message_text(
                "📷 Управление фотографиями\n\n"
                "Отправьте фотографию для добавления (максимум 10 штук)."
            )
        elif action == "videos":
            context.user_data['waiting_for_property_video'] = property_id
            await query.edit_message_text(
                "🎥 Управление видео\n\n"
                "Отправьте видео для добавления (максимум 2 штуки)."
            )
    
    async def _show_statistics(self, query):
        """Показать статистику бронирований"""
        stats = self.db.get_booking_statistics()
        
        text = "📊 Статистика бронирований\n\n"
        
        if not stats:
            text += "Нет данных для отображения."
        else:
            for stat in stats:
                text += f"🏠 {stat['property_name']}\n"
                text += f"   Бронирований: {stat['bookings_count']}\n"
                text += f"   С оплатой: {stat['paid_count']}\n\n"
        
        # Получаем все бронирования для детального просмотра
        all_bookings = []
        for prop in self.db.get_all_properties():
            bookings = self.db.get_property_bookings(prop.id)
            all_bookings.extend(bookings)
        
        if all_bookings:
            text += "\n📋 Детали бронирований:\n\n"
            for booking in all_bookings[:10]:  # Показываем первые 10
                prop = self.db.get_property(booking.property_id)
                text += f"🏠 {prop.name if prop else 'Неизвестно'}\n"
                text += f"   Период: {format_date(booking.start_date)} - {format_date(booking.end_date)}\n"
                user_info = booking.user_username or booking.user_phone or f"ID: {booking.user_id}"
                text += f"   Пользователь: {user_info}\n"
                text += f"   Оплата: {'✅' if booking.advance_paid else '❌'}\n\n"
                
                keyboard = [
                    [InlineKeyboardButton(
                        f"{'❌' if booking.advance_paid else '✅'} Оплата",
                        callback_data=f"admin_booking_payment_{booking.id}"
                    )]
                ]
        
        keyboard = [[InlineKeyboardButton("◀️ Назад", callback_data="admin_back")]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await query.edit_message_text(text, reply_markup=reply_markup)
    
    async def _booking_action(self, query, booking_id: int, action: str):
        """Действие с бронированием"""
        if action == "payment":
            # Переключаем статус оплаты
            booking = None
            for prop in self.db.get_all_properties():
                bookings = self.db.get_property_bookings(prop.id)
                for b in bookings:
                    if b.id == booking_id:
                        booking = b
                        break
                if booking:
                    break
            
            if booking:
                new_status = not booking.advance_paid
                if self.db.set_advance_paid(booking_id, new_status):
                    await query.answer(f"Статус оплаты изменен на {'оплачено' if new_status else 'не оплачено'}")
                    await self._show_statistics(query)
                else:
                    await query.answer("Ошибка при изменении статуса оплаты")
    
    async def _show_contacts(self, query):
        """Показать контакты администратора"""
        user_id = query.from_user.id
        admin = self.db.get_admin(user_id)
        
        if admin:
            text = "👤 Мои контактные данные:\n\n"
            text += f"Телефон: {admin.phone or 'не указан'}\n"
            text += f"Telegram: @{admin.telegram_username or 'не указан'}\n"
        else:
            text = "❌ Контактные данные не найдены."
        
        keyboard = [[InlineKeyboardButton("◀️ Назад", callback_data="admin_back")]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await query.edit_message_text(text, reply_markup=reply_markup)
    
    async def _edit_contacts(self, query):
        """Редактирование контактов"""
        await query.edit_message_text(
            "⚙️ Изменение контактных данных\n\n"
            "Отправьте команду:\n"
            "/set_phone <номер телефона> - установить телефон\n"
            "/set_username <username> - установить username"
        )
    
    async def handle_text(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обработка текстовых сообщений администратора"""
        user_id = update.effective_user.id
        
        if not self.is_admin(user_id):
            return
        
        text = update.message.text
        
        # Проверяем, ожидаем ли мы название объекта
        if context.user_data.get('waiting_for_property_name'):
            property_id = self.db.add_property(text, user_id)
            if property_id:
                await update.message.reply_text(f"✅ Объект '{text}' успешно добавлен!")
                context.user_data.pop('waiting_for_property_name', None)
            else:
                await update.message.reply_text("❌ Ошибка при добавлении объекта.")
            return
        
        # Проверяем, ожидаем ли мы описание объекта
        property_id = context.user_data.get('waiting_for_property_description')
        if property_id:
            if self.db.update_property_description(property_id, text):
                await update.message.reply_text("✅ Описание успешно обновлено!")
                context.user_data.pop('waiting_for_property_description', None)
            else:
                await update.message.reply_text("❌ Ошибка при обновлении описания.")
            return
    
    async def handle_photo(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обработка фотографий от администратора"""
        user_id = update.effective_user.id
        
        if not self.is_admin(user_id):
            return
        
        # Проверяем, ожидаем ли мы фотографию для объекта
        property_id = context.user_data.get('waiting_for_property_photo')
        if property_id:
            file_id = update.message.photo[-1].file_id
            
            if self.db.add_property_photo(property_id, file_id):
                photos_count = len(self.db.get_property_photos(property_id))
                await update.message.reply_text(
                    f"✅ Фотография добавлена! ({photos_count}/{config.MAX_PHOTOS})"
                )
            else:
                await update.message.reply_text(
                    f"❌ Не удалось добавить фотографию. "
                    f"Максимум {config.MAX_PHOTOS} фотографий на объект."
                )
            context.user_data.pop('waiting_for_property_photo', None)
            return
    
    async def handle_video(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обработка видео от администратора"""
        user_id = update.effective_user.id
        
        if not self.is_admin(user_id):
            return
        
        # Проверяем, ожидаем ли мы видео для объекта
        property_id = context.user_data.get('waiting_for_property_video')
        if property_id:
            file_id = update.message.video.file_id
            
            if self.db.add_property_video(property_id, file_id):
                videos_count = len(self.db.get_property_videos(property_id))
                await update.message.reply_text(
                    f"✅ Видео добавлено! ({videos_count}/{config.MAX_VIDEOS})"
                )
            else:
                await update.message.reply_text(
                    f"❌ Не удалось добавить видео. "
                    f"Максимум {config.MAX_VIDEOS} видео на объект."
                )
            context.user_data.pop('waiting_for_property_video', None)
            return
