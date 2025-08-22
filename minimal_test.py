import asyncio
import logging
from aiogram import Bot, Dispatcher, types

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize bot and dispatcher
bot = Bot(token='7605069387:AAF4h9zO99LrqWg8JCVYmvYIrpFo1FN8YGc')
dp = Dispatcher()

@dp.message(commands=['start'])
async def cmd_start(message: types.Message):
    logger.info(f"Received /start from {message.from_user.id}")
    await message.answer("🤖 Bot is working! This is a test message.")

async def main():
    logger.info("Starting bot...")
    try:
        await dp.start_polling(bot, skip_updates=True)
    except Exception as e:
        logger.error(f"Error: {e}")
    finally:
        await bot.session.close()

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Bot stopped by user")
