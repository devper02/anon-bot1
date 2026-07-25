"""
Telegram Bot — Анонимные сообщения с деанонимизацией

Бот работает как @voprosy, но владелец ссылки получает полные данные отправителя.
Теперь с красивым интерфейсом, inline-кнопками и Web App!
"""
import asyncio
import logging
import sys
import json

from aiogram import Bot, Dispatcher, F
from aiogram.types import Message, WebAppData
from aiogram.enums import ParseMode

from config import BOT_TOKEN
from database import db
from handlers import user_router, admin_router

# Настройка логирования
logging.basicConfig(level=logging.INFO, stream=sys.stdout)
logger = logging.getLogger(__name__)


async def main():
    # Инициализация базы данных
    await db.init()
    logger.info("База данных инициализирована")

    # Создание бота и диспетчера
    bot = Bot(token=BOT_TOKEN, parse_mode=ParseMode.HTML)
    dp = Dispatcher()

    # Подключение роутеров
    dp.include_router(user_router)
    dp.include_router(admin_router)

    logger.info("Бот запущен!")
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
