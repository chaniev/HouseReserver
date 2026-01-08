"""
Главный файл телеграм-бота для бронирования домов
"""
import logging
from telegram import Update
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, MessageHandler, filters, ContextTypes
from database import Database
from admin_handlers import AdminHandlers
from user_handlers import UserHandlers
import config

# Настройка логирования из config
logging.basicConfig(
    format=config.LOG_FORMAT,
    level=getattr(logging, config.LOG_LEVEL.upper(), logging.INFO)
)
logger = logging.getLogger(__name__)


class HouseReservBot:
    """Главный класс бота"""
    
    def __init__(self):
        self.db = Database()
        self.admin_handlers = AdminHandlers(self.db)
        self.user_handlers = UserHandlers(self.db)
        self.application = None
    
    def setup_handlers(self):
        """Настройка обработчиков команд"""
        # Команды для пользователей
        self.application.add_handler(CommandHandler("start", self.user_handlers.start))
        self.application.add_handler(CommandHandler("my_bookings", self._show_my_bookings))
        
        # Команды для администраторов
        self.application.add_handler(CommandHandler("admin", self.admin_handlers.start_admin))
        self.application.add_handler(CommandHandler("register_admin", self.admin_handlers.register_admin))
        self.application.add_handler(CommandHandler("set_phone", self._set_phone))
        self.application.add_handler(CommandHandler("set_username", self._set_username))
        
        # Callback обработчики
        self.application.add_handler(CallbackQueryHandler(self.admin_handlers.admin_callback, pattern="^admin_"))
        self.application.add_handler(CallbackQueryHandler(self.user_handlers.user_callback, pattern="^user_"))
        
        # Обработчики сообщений
        self.application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, self._handle_text))
        self.application.add_handler(MessageHandler(filters.PHOTO, self._handle_photo))
        self.application.add_handler(MessageHandler(filters.VIDEO, self._handle_video))
    
    async def _show_my_bookings(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Показать бронирования пользователя через команду"""
        from telegram import InlineKeyboardButton, InlineKeyboardMarkup
        
        user_id = update.effective_user.id
        bookings = self.db.get_user_bookings(user_id)
        
        if not bookings:
            await update.message.reply_text("📅 У вас пока нет бронирований.")
            return
        
        text = "📅 Ваши бронирования:\n\n"
        
        keyboard = []
        for booking in bookings:
            prop = self.db.get_property(booking.property_id)
            text += f"🏠 {prop.name if prop else 'Неизвестно'}\n"
            text += f"   Период: {booking.start_date.strftime('%d.%m.%Y')} - {booking.end_date.strftime('%d.%m.%Y')}\n"
            text += f"   Статус оплаты: {'✅ Оплачено' if booking.advance_paid else '❌ Не оплачено'}\n"
            
            # Получаем контакты администратора
            if prop and prop.admin_id:
                admin = self.db.get_admin(prop.admin_id)
                if admin:
                    text += "   📞 Контакты владельца:\n"
                    if admin.phone:
                        text += f"      Телефон: {admin.phone}\n"
                    if admin.telegram_username:
                        text += f"      Telegram: @{admin.telegram_username}\n"
            
            text += "\n"
            
            keyboard.append([
                InlineKeyboardButton(
                    f"❌ Отменить: {prop.name if prop else 'Бронирование'}",
                    callback_data=f"user_cancel_booking_{booking.id}"
                )
            ])
        
        keyboard.append([InlineKeyboardButton("◀️ Назад", callback_data="user_back")])
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await update.message.reply_text(text, reply_markup=reply_markup)
    
    async def _set_phone(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Установить телефон администратора"""
        user_id = update.effective_user.id
        
        if not self.admin_handlers.is_admin(user_id):
            await update.message.reply_text("❌ У вас нет прав администратора.")
            return
        
        if not context.args:
            await update.message.reply_text("❌ Укажите номер телефона. Пример: /set_phone +79991234567")
            return
        
        phone = ' '.join(context.args)
        if self.db.update_admin_contacts(user_id, phone=phone):
            await update.message.reply_text(f"✅ Телефон успешно установлен: {phone}")
        else:
            await update.message.reply_text("❌ Ошибка при установке телефона.")
    
    async def _set_username(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Установить username администратора"""
        user_id = update.effective_user.id
        
        if not self.admin_handlers.is_admin(user_id):
            await update.message.reply_text("❌ У вас нет прав администратора.")
            return
        
        if not context.args:
            await update.message.reply_text("❌ Укажите username. Пример: /set_username myusername")
            return
        
        username = context.args[0].replace('@', '')
        if self.db.update_admin_contacts(user_id, telegram_username=username):
            await update.message.reply_text(f"✅ Username успешно установлен: @{username}")
        else:
            await update.message.reply_text("❌ Ошибка при установке username.")
    
    async def _handle_text(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обработка текстовых сообщений"""
        user_id = update.effective_user.id
        
        # Проверяем, является ли пользователь администратором
        if self.admin_handlers.is_admin(user_id):
            # Проверяем, ожидает ли админ ввода (название объекта, описание и т.д.)
            if (context.user_data.get('waiting_for_property_name') or 
                context.user_data.get('waiting_for_property_description')):
                await self.admin_handlers.handle_text(update, context)
                return
        
        # Проверяем, ожидает ли пользователь ввода дат для бронирования
        if context.user_data.get('booking_property_id'):
            await self.user_handlers.handle_booking_text(update, context)
            return
        
        # Если это не команда и не ожидаемый ввод, показываем подсказку
        await update.message.reply_text(
            "Используйте /start для начала работы с ботом."
        )
    
    async def _handle_photo(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обработка фотографий"""
        user_id = update.effective_user.id
        
        if self.admin_handlers.is_admin(user_id):
            await self.admin_handlers.handle_photo(update, context)
    
    async def _handle_video(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обработка видео"""
        user_id = update.effective_user.id
        
        if self.admin_handlers.is_admin(user_id):
            await self.admin_handlers.handle_video(update, context)
    
    def run(self):
        """Запуск бота"""
        if not config.BOT_TOKEN:
            logger.error("BOT_TOKEN не установлен! Установите его в переменных окружения или в .env файле.")
            return
        
        # Создаем Application с правильными параметрами
        self.application = (
            Application.builder()
            .token(config.BOT_TOKEN)
            .build()
        )
        self.setup_handlers()
        
        logger.info("Бот запущен...")
        # Используем run_polling() - он сам управляет жизненным циклом
        try:
            self.application.run_polling(drop_pending_updates=True)
        except KeyboardInterrupt:
            logger.info("Бот остановлен пользователем")
        except Exception as e:
            logger.error(f"Ошибка при запуске бота: {e}")
            raise


def main():
    """Главная функция"""
    bot = HouseReservBot()
    bot.run()


if __name__ == '__main__':
    main()
