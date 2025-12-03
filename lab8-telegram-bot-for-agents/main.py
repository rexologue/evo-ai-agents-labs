import asyncio
from contextlib import suppress
from config.config import config
from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from src.handlers import router
from src.services.request_manager import request_manager

async def cleanup_task():
    """Periodically clean up old requests"""
    while True:
        await asyncio.sleep(60)  # Clean up every minute
        request_manager.cleanup_old_requests()

async def main():
    bot = Bot(
        token=config.TELEGRAM_BOT_TOKEN,
        default=DefaultBotProperties(parse_mode="Markdown"),
    )
    dp = Dispatcher()
    dp.include_router(router)
    await bot.delete_webhook()
    
    # Запускаем фоновую задачу очистки
    cleanup_task_obj = asyncio.create_task(cleanup_task())
    
    try:
        print("Bot started with request manager")
        await dp.start_polling(bot)
    finally:
        cleanup_task_obj.cancel()
        with suppress(asyncio.CancelledError):
            await cleanup_task_obj

if __name__ == "__main__":
    try:
        print("Bot started")
        asyncio.run(main())
    except KeyboardInterrupt:
        print("Bot stopped")