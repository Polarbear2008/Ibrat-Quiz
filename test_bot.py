import asyncio
import logging
from aiogram import Bot, Dispatcher, types
from aiogram.enums import ParseMode

# Configure logging
logging.basicConfig(level=logging.INFO)

# Bot token (temporary for testing)
BOT_TOKEN = '7605069387:AAF4h9zO99LrqWg8JCVYmvYIrpFo1FN8YGc'

async def main():
    # Initialize bot and dispatcher
    bot = Bot(token=BOT_TOKEN, parse_mode=ParseMode.HTML)
    dp = Dispatcher()
    
    @dp.message(types.Message, commands=["start"])
    async def cmd_start(message: types.Message):
        await message.answer("🤖 Bot is working! This is a test message.")
    
    try:
        logging.info("Starting test bot...")
        await dp.start_polling(bot)
    finally:
        await bot.session.close()

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\nBot stopped by user")
    except Exception as e:
        print(f"Error: {e}")
        raise
