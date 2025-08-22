import os
import logging
from aiogram import Bot, Dispatcher
from aiogram.enums import ParseMode
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Initialize bot with parse mode
bot = Bot(
    token=os.getenv('BOT_TOKEN', '7605069387:AAF4h9zO99LrqWg8JCVYmvYIrpFo1FN8YGc'),
    parse_mode=ParseMode.HTML
)
dp = Dispatcher()

# Import handlers
from bot import *  # This imports all handlers from bot.py
from admin_panel import *  # This imports admin panel handlers

# Webhook setup for Railway
async def set_webhook():
    webhook_url = os.getenv('WEBHOOK_URL')
    if webhook_url:
        webhook_path = f"/webhook/{bot.token}"
        await bot.set_webhook(
            url=webhook_url + webhook_path,
            drop_pending_updates=True
        )
        logger.info(f"Webhook set to: {webhook_url + webhook_path}")
    else:
        logger.info("Running in polling mode")

async def on_startup():
    await set_webhook()
    logger.info("Bot started")

async def on_shutdown():
    await bot.session.close()
    logger.info("Bot stopped")

# Main function
def main():
    # Check if running on Railway
    if os.getenv('RAILWAY_ENVIRONMENT'):
        from aiogram.webhook.aiohttp_server import setup_application as setup_webhook
        from aiohttp import web
        
        app = web.Application()
        webhook_path = f"/webhook/{bot.token}"
        
        # Register webhook handler
        dp.startup.register(on_startup)
        dp.shutdown.register(on_shutdown)
        
        # Set up webhook handler
        dp.include_router(router)
        app.router.add_post(webhook_path, dp.get_webhook_handle())
        
        # Start the server
        port = int(os.getenv('PORT', 8000))
        web.run_app(app, host='0.0.0.0', port=port)
    else:
        # Local development with polling
        import asyncio
        
        async def start():
            await on_startup()
            await dp.start_polling(bot, skip_updates=True)
            
        try:
            asyncio.run(start())
        except KeyboardInterrupt:
            logger.info("Bot stopped by user")
        except Exception as e:
            logger.error(f"Error: {e}", exc_info=True)
        finally:
            asyncio.run(on_shutdown())

if __name__ == "__main__":
    main()
