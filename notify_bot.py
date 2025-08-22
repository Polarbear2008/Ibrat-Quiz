import os
import json
import logging
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command, StateFilter, CommandStart
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton, ReplyKeyboardRemove
from datetime import datetime
from dotenv import load_dotenv

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Load environment variables
load_dotenv()
BOT_TOKEN = os.getenv('BOT_TOKEN')
GROUP_ID = os.getenv('GROUP_ID')

# Initialize bot and dispatcher
bot = Bot(token=BOT_TOKEN)
dp = Dispatcher(storage=MemoryStorage())

# States
class Form(StatesGroup):
    full_name = State()
    contact = State()
    has_team = State()
    team_name = State()
    team_members = State()

# In-memory storage (use a database in production)
participants = []

def save_participants():
    """Save participants to a JSON file"""
    try:
        with open('participants.json', 'w', encoding='utf-8') as f:
            json.dump(participants, f, ensure_ascii=False, indent=2)
    except Exception as e:
        logger.error(f"Error saving participants: {e}")

async def notify_group(participant_data):
    """Send notification to group about new registration"""
    if not GROUP_ID:
        return
        
    try:
        # Format the notification message
        message = [
            "🎉 *New Registration!* 🎉",
            f"👤 *Name:* {participant_data.get('full_name', 'N/A')}",
            f"📱 *Phone:* {participant_data.get('phone', 'N/A')}",
            f"📅 *Registered:* {participant_data.get('registration_date', 'N/A')}",
        ]
        
        if 'team_name' in participant_data:
            message.append(f"🏆 *Team:* {participant_data['team_name']}")
            
            # Add team members if any
            team_members = participant_data.get('team_members', [])
            if team_members:
                message.append("\n👥 *Team Members:*")
                for i, member in enumerate(team_members, 1):
                    member_info = f"{i}. {member.get('name', 'N/A')}"
                    if 'phone' in member:
                        member_info += f" - {member['phone']}"
                    message.append(member_info)
        
        # Send the message to the group
        await bot.send_message(
            chat_id=GROUP_ID,
            text="\n".join(message),
            parse_mode='Markdown'
        )
    except Exception as e:
        logger.error(f"Error sending notification: {e}")

# Start command
@dp.message(CommandStart())
async def cmd_start(message: types.Message, state: FSMContext):
    """Handler for /start command"""
    await message.answer(
        "👋 Welcome to the Registration Bot!\n\n"
        "Please enter your full name:",
        reply_markup=ReplyKeyboardRemove()
    )
    await state.set_state(Form.full_name)

# Rest of your existing handlers...
# [Previous handlers for name, contact, team selection, etc.]

async def complete_registration(message: types.Message, state: FSMContext):
    """Complete the registration process"""
    # Get all user data
    user_data = await state.get_data()
    
    # Add registration timestamp
    user_data['registration_date'] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    user_data['telegram_id'] = message.from_user.id
    
    # Store the participant
    participants.append(user_data)
    save_participants()
    
    # Send confirmation to user
    response = [
        "✅ Registration Complete!",
        "\n📋 Your Details:",
        f"👤 Name: {user_data.get('full_name', 'N/A')}",
        f"📱 Phone: {user_data.get('phone', 'N/A')}",
    ]
    
    if 'team_name' in user_data:
        response.append(f"🏆 Team: {user_data['team_name']}")
        team_members = user_data.get('team_members', [])
        if team_members:
            response.append("\n👥 Team Members:")
            for i, member in enumerate(team_members, 1):
                response.append(f"{i}. {member.get('name', 'N/A')} - {member.get('phone', 'N/A')")
    
    await message.answer("\n".join(response), reply_markup=ReplyKeyboardRemove())
    
    # Send notification to group
    await notify_group(user_data)
    
    # Clear the state
    await state.clear()

async def main():
    # Load existing participants
    global participants
    try:
        with open('participants.json', 'r', encoding='utf-8') as f:
            participants = json.load(f)
    except FileNotFoundError:
        participants = []
    
    logger.info("Starting bot...")
    await dp.start_polling(bot)

if __name__ == '__main__':
    import asyncio
    asyncio.run(main())
