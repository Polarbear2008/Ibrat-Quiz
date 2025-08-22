from aiogram import Bot
import asyncio
import os
from dotenv import load_dotenv

load_dotenv()
bot = Bot(token=os.getenv('BOT_TOKEN'))
channel = os.getenv('CHANNEL_USERNAME', '@quizibratparticipants')

async def test_send():
    try:
        await bot.send_message(
            chat_id=channel,
            text="🔧 Test message from bot!"
        )
        print("Test message sent successfully!")
    except Exception as e:
        print(f"Error sending test message: {e}")

asyncio.run(test_send())