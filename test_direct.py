from aiogram import Bot
import asyncio
import os
from dotenv import load_dotenv

load_dotenv()

async def test_channel():
    bot = Bot(token=os.getenv('BOT_TOKEN'))
    try:
        await bot.send_message(
            chat_id=os.getenv('CHANNEL_ID'),
            text="🔧 Test message using ID"
        )
        print("Message sent to channel successfully!")
    except Exception as e:
        print(f"Error sending to channel: {e}")
    await bot.session.close()

asyncio.run(test_channel())