import logging
from aiogram import Bot
import asyncio

# Enable detailed logging
logging.basicConfig(level=logging.DEBUG)

async def test_personal():
    bot = Bot(token='7605069387:AAF4h9zO99LrqWg8JCVYmvYIrpFo1FN8YGc')
    try:
        print("Attempting to send message...")
        # Try with your user ID
        result = await bot.send_message(
            chat_id=1769729434,
            text="🔧 Test direct message to personal chat"
        )
        print(f"Message sent successfully! Message ID: {result.message_id}")
    except Exception as e:
        print("\n=== ERROR DETAILS ===")
        print(f"Error type: {type(e).__name__}")
        print(f"Error message: {str(e)}")
        if hasattr(e, 'response') and hasattr(e.response, '__dict__'):
            print("\nResponse details:")
            for k, v in e.response.__dict__.items():
                print(f"{k}: {v}")
    finally:
        await bot.session.close()
        print("\nBot session closed.")

print("Starting test...")
asyncio.run(test_personal())
print("Test completed.")
