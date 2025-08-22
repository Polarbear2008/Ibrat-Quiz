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
BOT_TOKEN = "7605069387:AAF4h9zO99LrqWg8JCVYmvYIrpFo1FN8YGc"
CHANNEL_USERNAME = "@quizibratparticipants"

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
    try:
        with open('participants.json', 'w', encoding='utf-8') as f:
            json.dump(participants, f, ensure_ascii=False, indent=2)
    except Exception as e:
        logger.error(f"Error saving participants: {e}")

async def notify_channel(participant_data):
    try:
        message = [
            "🎉 *New Registration!* 🎉",
            f"👤 *Name:* {participant_data.get('full_name', 'N/A')}",
            f"📱 *Phone:* {participant_data.get('phone', 'N/A')}",
            f"📅 *Registered:* {participant_data.get('registration_date', 'N/A')}",
        ]
        
        if 'team_name' in participant_data:
            message.append(f"🏆 *Team:* {participant_data['team_name']}")
            
            team_members = participant_data.get('team_members', [])
            if team_members:
                message.append("\n👥 *Team Members:*")
                for i, member in enumerate(team_members, 1):
                    member_info = f"{i}. {member.get('name', 'N/A')}"
                    if 'phone' in member:
                        member_info += f" - {member['phone']}"
                    message.append(member_info)
        
        await bot.send_message(
            chat_id=CHANNEL_USERNAME,
            text="\n".join(message),
            parse_mode='Markdown'
        )
    except Exception as e:
        logger.error(f"Error sending to channel: {e}")

@dp.message(CommandStart())
async def cmd_start(message: types.Message, state: FSMContext):
    await message.answer(
        "👋 Welcome to the Registration Bot!\n\n"
        "Please enter your full name:",
        reply_markup=ReplyKeyboardRemove()
    )
    await state.set_state(Form.full_name)

@dp.message(Form.full_name)
async def process_name(message: types.Message, state: FSMContext):
    await state.update_data(full_name=message.text)
    contact_keyboard = ReplyKeyboardMarkup(
        keyboard=[[KeyboardButton(text="📱 Share Contact", request_contact=True)]],
        resize_keyboard=True,
        one_time_keyboard=True
    )
    await message.answer("📱 Please share your contact:", reply_markup=contact_keyboard)
    await state.set_state(Form.contact)

@dp.message(Form.contact, F.contact)
async def process_contact(message: types.Message, state: FSMContext):
    contact = message.contact
    await state.update_data(
        phone=contact.phone_number,
        user_id=contact.user_id
    )
    
    keyboard = ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="Yes, I have a team")],
            [KeyboardButton(text="No, I'm alone")]
        ],
        resize_keyboard=True,
        one_time_keyboard=True
    )
    await message.answer("👥 Do you have a team?", reply_markup=keyboard)
    await state.set_state(Form.has_team)

@dp.message(Form.has_team)
async def process_team_choice(message: types.Message, state: FSMContext):
    if message.text.lower() in ["yes", "yes, i have a team"]:
        await message.answer("🏆 Please enter your team name:", reply_markup=ReplyKeyboardRemove())
        await state.set_state(Form.team_name)
    else:
        await complete_registration(message, state)

@dp.message(Form.team_name)
async def process_team_name(message: types.Message, state: FSMContext):
    await state.update_data(team_name=message.text)
    await message.answer(
        "👥 Please enter your team members (one per line):\n"
        "Format: Name, Phone\n"
        "Example:\n"
        "John Doe, +1234567890"
    )
    await state.set_state(Form.team_members)

@dp.message(Form.team_members)
async def process_team_members(message: types.Message, state: FSMContext):
    try:
        lines = [line.strip() for line in message.text.split('\n') if line.strip()]
        members = []
        
        for line in lines:
            parts = [p.strip() for p in line.split(',', 1)]
            if len(parts) == 2:
                name, phone = parts
                members.append({'name': name, 'phone': phone})
        
        if not members:
            raise ValueError("No valid team members provided")
            
        await state.update_data(team_members=members)
        await complete_registration(message, state)
        
    except Exception as e:
        logger.error(f"Error processing team members: {e}")
        await message.answer(
            "❌ Invalid format. Please try again. Format should be:\n"
            "Name, Phone\n"
            "Example:\n"
            "John Doe, +1234567890"
        )

async def complete_registration(message: types.Message, state: FSMContext):
    user_data = await state.get_data()
    user_data['registration_date'] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    user_data['telegram_id'] = message.from_user.id
    
    participants.append(user_data)
    save_participants()
    
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
    
    # Send notification to channel
    await notify_channel(user_data)
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
