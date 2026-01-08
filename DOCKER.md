# Быстрый старт с Docker

## Предварительные требования

- Docker и Docker Compose установлены на вашей системе
- Telegram Bot Token от [@BotFather](https://t.me/BotFather)

## Шаги для запуска

1. **Создайте файл `.env`** в корне проекта:
```bash
BOT_TOKEN=your_bot_token_here
DATABASE_PATH=/app/data/house_reserv.db
```

2. **Соберите и запустите контейнер:**
```bash
docker-compose up -d
```

3. **Проверьте логи:**
```bash
docker-compose logs -f
```

## Полезные команды

```bash
# Остановить контейнер
docker-compose down

# Перезапустить контейнер
docker-compose restart

# Просмотр логов
docker-compose logs -f

# Пересобрать образ после изменений в коде
docker-compose up -d --build

# Войти в контейнер (для отладки)
docker exec -it house_reserv_bot bash
```

## База данных

База данных сохраняется в директории `./data` на хосте. Это означает, что данные не потеряются при перезапуске контейнера.

## Обновление бота

После изменений в коде:

```bash
docker-compose up -d --build
```

Это пересоберет образ и перезапустит контейнер с новым кодом.
