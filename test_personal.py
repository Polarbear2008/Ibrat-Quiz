from aiogram import Bot
import asyncio

async def test_personal():
    # Using your bot token directly for testing
    bot = Bot(token='7605069387:AAF4h9zO99LrqWg8JCVYmvYIrpFo1FN8YGc')
    try:
        # Sending to your personal chat (replace with your actual chat ID)
        await bot.send_message(
            chat_id=1769729434,  # Your Telegram user ID
            text="🔧 Test direct message to personal chat"
        )
        print("Test message sent to your personal chat!")
    except Exception as e:
        print(f"Error sending message: {e}")
    finally:
        await bot.session.close()

asyncio.run(test_personal())
