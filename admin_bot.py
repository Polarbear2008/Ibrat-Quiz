import json
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Bot token from .env file
BOT_TOKEN = "7605069387:AAF4h9zO99LrqWg8JCVYmvYIrpFo1FN8YGc"

# Initialize bot and dispatcher
bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()

# Admin user ID (replace with your Telegram ID)
ADMIN_IDS = [1769729434]  # Your Telegram ID

# Load participants
def load_participants():
    try:
        with open('participants.json', 'r', encoding='utf-8') as f:
            return json.load(f)
    except FileNotFoundError:
        return []
    except Exception as e:
        logger.error(f"Error loading participants: {e}")
        return []

# Admin commands
@dp.message(Command("admin"))
async def admin_panel(message: types.Message):
    if message.from_user.id not in ADMIN_IDS:
        await message.answer("🚫 Access denied.")
        return
    
    keyboard = [
        [types.InlineKeyboardButton(text="👥 View All Participants", callback_data="view_all")],
        [types.InlineKeyboardButton(text="📊 View Statistics", callback_data="stats")],
        [types.InlineKeyboardButton(text="📥 Export Data", callback_data="export")]
    ]
    reply_markup = types.InlineKeyboardMarkup(inline_keyboard=keyboard)
    await message.answer("👨‍💼 Admin Panel", reply_markup=reply_markup)

@dp.callback_query(F.data == "view_all")
async def view_all(callback: types.CallbackQuery):
    if callback.from_user.id not in ADMIN_IDS:
        await callback.answer("Access denied.")
        return
    
    participants = load_participants()
    if not participants:
        await callback.message.answer("No participants registered yet.")
        return
    
    for p in participants:
        response = [
            f"👤 {p.get('full_name')}",
            f"📱 {p.get('phone')}",
            f"📅 {p.get('registration_date', 'N/A')}",
            f"🏆 Team: {p.get('team_name', 'Solo')}",
            "--------------------"
        ]
        if 'team_members' in p and p['team_members']:
            response.insert(3, f"👥 Team Members: {len(p['team_members'])}")
        await callback.message.answer("\n".join(response))
    
    await callback.answer()

@dp.callback_query(F.data == "stats")
async def stats(callback: types.CallbackQuery):
    if callback.from_user.id not in ADMIN_IDS:
        await callback.answer("Access denied.")
        return
    
    participants = load_participants()
    total = len(participants)
    teams = sum(1 for p in participants if 'team_name' in p)
    
    # Count by English level
    levels = {}
    for p in participants:
        level = p.get('english_level', 'Not specified')
        levels[level] = levels.get(level, 0) + 1
    
    response = [
        "📊 Registration Statistics",
        f"👥 Total Participants: {total}",
        f"🏆 Teams: {teams}",
        f"👤 Solo Participants: {total - teams}",
        "\n📚 English Levels:"
    ]
    
    for level, count in levels.items():
        response.append(f"• {level}: {count}")
    
    await callback.message.answer("\n".join(response))
    await callback.answer()

@dp.callback_query(F.data == "export")
async def export_data(callback: types.CallbackQuery):
    if callback.from_user.id not in ADMIN_IDS:
        await callback.answer("Access denied.")
        return
    
    participants = load_participants()
    try:
        with open('participants_export.json', 'w', encoding='utf-8') as f:
            json.dump(participants, f, ensure_ascii=False, indent=2)
        
        with open('participants_export.json', 'rb') as f:
            await callback.message.answer_document(
                document=types.BufferedInputFile(
                    f.read(),
                    filename="participants_export.json"
                ),
                caption="📤 Here's the exported data!"
            )
    except Exception as e:
        await callback.message.answer(f"❌ Error exporting data: {str(e)}")
    
    await callback.answer()

async def main():
    await dp.start_polling(bot)

if __name__ == '__main__':
    import asyncio
    asyncio.run(main())
