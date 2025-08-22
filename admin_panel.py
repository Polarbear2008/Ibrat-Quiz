import json
import os
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command
import logging
from dotenv import load_dotenv

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Load environment variables
load_dotenv()
BOT_TOKEN = os.getenv('BOT_TOKEN', '7605069387:AAF4h9zO99LrqWg8JCVYmvYIrpFo1FN8YGc')
ADMIN_IDS = [1769729434, 5747916482]  # List of admin user IDs

# Initialize bot and dispatcher
bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()

def load_participants():
    """Load participants from JSON file"""
    try:
        with open('participants.json', 'r', encoding='utf-8') as f:
            return json.load(f)
    except FileNotFoundError:
        return []
    except Exception as e:
        logger.error(f"Error loading participants: {e}")
        return []

@dp.message(Command("admin"))
async def admin_panel(message: types.Message):
    """Show admin panel"""
    if message.from_user.id not in ADMIN_IDS:
        await message.answer("⛔️ Access denied.")
        return
    
    keyboard = [
        [types.KeyboardButton(text="👥 View All Participants")],
        [types.KeyboardButton(text="📊 View Statistics")],
        [types.KeyboardButton(text="📥 Export Data")]
    ]
    reply_markup = types.ReplyKeyboardMarkup(keyboard=keyboard, resize_keyboard=True)
    await message.answer("👨‍💼 Admin Panel", reply_markup=reply_markup)

@dp.message(F.text == "👥 View All Participants")
async def view_participants(message: types.Message):
    """Show all registered participants"""
    if message.from_user.id not in ADMIN_IDS:
        return
    
    participants = load_participants()
    if not participants:
        await message.answer("No participants registered yet.")
        return
    
    for i, p in enumerate(participants, 1):
        response = [
            f"👤 Participant #{i}",
            f"📅 {p.get('registration_date', 'N/A')}",
            f"👤 Name: {p.get('full_name', 'N/A')}",
            f"📱 Phone: {p.get('phone', 'N/A')}",
            f"📊 English: {p.get('english_level', 'N/A')}",
            f"🎂 Age: {p.get('age', 'N/A')}",
        ]
        
        if 'team_name' in p:
            response.append(f"🏆 Team: {p['team_name']}")
            
            team_members = p.get('team_members', [])
            if team_members:
                response.append("👥 Team Members:")
                for j, member in enumerate(team_members, 1):
                    response.append(f"  {j}. {member.get('name', 'N/A')} - {member.get('phone', 'N/A')}")
        
        await message.answer("\n".join(response))

@dp.message(F.text == "📊 View Statistics")
async def view_stats(message: types.Message):
    """Show registration statistics"""
    if message.from_user.id not in ADMIN_IDS:
        return
    
    participants = load_participants()
    total = len(participants)
    teams = sum(1 for p in participants if 'team_name' in p)
    solo = total - teams
    
    # Count by English level
    levels = {}
    for p in participants:
        level = p.get('english_level', 'Not specified')
        levels[level] = levels.get(level, 0) + 1
    
    response = [
        "📊 Registration Statistics",
        f"👥 Total Participants: {total}",
        f"🏆 Teams: {teams}",
        f"👤 Solo: {solo}",
        "\n📚 English Levels:"
    ]
    
    for level, count in levels.items():
        response.append(f"• {level}: {count}")
    
    await message.answer("\n".join(response))

@dp.message(F.text == "📥 Export Data")
async def export_data(message: types.Message):
    """Export participants data as JSON"""
    if message.from_user.id not in ADMIN_IDS:
        return
    
    try:
        participants = load_participants()
        if not participants:
            await message.answer("No data to export.")
            return
            
        # Save to a temporary file
        with open('participants_export.json', 'w', encoding='utf-8') as f:
            json.dump(participants, f, ensure_ascii=False, indent=2)
        
        # Send the file
        with open('participants_export.json', 'rb') as f:
            await message.answer_document(
                document=types.BufferedInputFile(
                    f.read(),
                    filename="participants_export.json"
                ),
                caption="📤 Here's the exported data!"
            )
    except Exception as e:
        logger.error(f"Error exporting data: {e}")
        await message.answer(f"❌ Error exporting data: {e}")

async def main():
    logger.info("Starting admin panel...")
    await dp.start_polling(bot)

if __name__ == "__main__":
    import asyncio
    asyncio.run(main())
