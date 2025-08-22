import logging
import asyncio
from bot import dp, bot

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

async def main():
    logging.info("Starting bot...")
    try:
        await dp.start_polling(bot, skip_pending=True)
    except Exception as e:
        logging.error(f"Error in main: {e}")
        raise
    finally:
        # Close the database connection when the bot stops
        from bot import db
        if db:
            db.close()
            logging.info("Database connection closed")

if __name__ == '__main__':
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logging.info("Bot stopped by user")
    except Exception as e:
        logging.error(f"Fatal error: {e}")
        raise
