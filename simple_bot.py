import os
import logging
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command, StateFilter, CommandStart
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.types import (
    ReplyKeyboardMarkup, 
    KeyboardButton, 
    ReplyKeyboardRemove
)
from aiogram.utils.keyboard import ReplyKeyboardBuilder
from dotenv import load_dotenv

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Load environment variables
load_dotenv()

# Bot token (replace with your actual token or use .env)
BOT_TOKEN = os.getenv('BOT_TOKEN', 'YOUR_BOT_TOKEN')

# Initialize bot and dispatcher
bot = Bot(token=BOT_TOKEN)
dp = Dispatcher(storage=MemoryStorage())

# States
class Form(StatesGroup):
    full_name = State()
    contact = State()
    english_level = State()
    age = State()
    has_team = State()
    team_name = State()
    team_member = State()
    add_another = State()

# Start command
@dp.message(CommandStart())
async def cmd_start(message: types.Message, state: FSMContext):
    """Handler for /start command"""
    await message.answer(
        "👋 Welcome to the Registration Bot!\n\n"
        "Please enter your full name:"
    )
    await state.set_state(Form.full_name)

# Handle full name
@dp.message(Form.full_name)
async def process_name(message: types.Message, state: FSMContext):
    """Process user's full name"""
    await state.update_data(full_name=message.text)
    
    # Create contact keyboard
    contact_keyboard = ReplyKeyboardMarkup(
        keyboard=[[KeyboardButton(text="📱 Share Contact", request_contact=True)]],
        resize_keyboard=True,
        one_time_keyboard=True
    )
    
    await message.answer(
        "📱 Please share your contact information:",
        reply_markup=contact_keyboard
    )
    await state.set_state(Form.contact)

# Handle contact sharing
@dp.message(Form.contact, F.contact)
async def process_contact(message: types.Message, state: FSMContext):
    """Process user's contact"""
    contact = message.contact
    await state.update_data(
        phone=contact.phone_number,
        user_id=contact.user_id
    )
    
    # English level keyboard
    english_levels = ["Beginner (A1-A2)", "Intermediate (B1-B2)", "Advanced (C1-C2)"]
    keyboard = ReplyKeyboardMarkup(
        keyboard=[[KeyboardButton(text=level)] for level in english_levels],
        resize_keyboard=True,
        one_time_keyboard=True
    )
    
    await message.answer(
        "📊 What is your English level?",
        reply_markup=keyboard
    )
    await state.set_state(Form.english_level)

# Handle English level
@dp.message(Form.english_level)
async def process_english_level(message: types.Message, state: FSMContext):
    """Process English level"""
    await state.update_data(english_level=message.text)
    await message.answer(
        "🎂 How old are you? (Enter a number)",
        reply_markup=ReplyKeyboardRemove()
    )
    await state.set_state(Form.age)

# Handle age
@dp.message(Form.age)
async def process_age(message: types.Message, state: FSMContext):
    """Process user's age"""
    try:
        age = int(message.text)
        await state.update_data(age=age)
        
        # Team selection keyboard
        keyboard = ReplyKeyboardMarkup(
            keyboard=[
                [KeyboardButton(text="Yes, I have a team")],
                [KeyboardButton(text="No, I'm alone")]
            ],
            resize_keyboard=True,
            one_time_keyboard=True
        )
        
        await message.answer(
            "👥 Do you have a team?",
            reply_markup=keyboard
        )
        await state.set_state(Form.has_team)
    except ValueError:
        await message.answer("Please enter a valid number for your age.")

# Handle team selection
@dp.message(Form.has_team)
async def process_team_choice(message: types.Message, state: FSMContext):
    """Process team choice"""
    if message.text.lower() in ["yes", "yes, i have a team"]:
        await message.answer(
            "🏆 Please enter your team name:",
            reply_markup=ReplyKeyboardRemove()
        )
        await state.set_state(Form.team_name)
    else:
        # Complete registration without team
        await complete_registration(message, state)

# Handle team name
@dp.message(Form.team_name)
async def process_team_name(message: types.Message, state: FSMContext):
    """Process team name"""
    await state.update_data(
        team_name=message.text,
        team_members=[]  # Initialize empty list for team members
    )
    await message.answer(
        "👥 Please enter team member details in this format:\n"
        "Full Name, Phone Number\n\n"
        "Example:\n"
        "John Doe, +1234567890"
    )
    await state.set_state(Form.team_member)

# Handle team member details
@dp.message(Form.team_member)
async def process_team_member(message: types.Message, state: FSMContext):
    """Process team member details"""
    try:
        # Parse the input
        parts = [p.strip() for p in message.text.split(',', 1)]
        if len(parts) != 2:
            raise ValueError("Invalid format")
            
        name, phone = parts
        
        # Add to team members list
        data = await state.get_data()
        team_members = data.get('team_members', [])
        team_members.append({
            'name': name,
            'phone': phone
        })
        await state.update_data(team_members=team_members)
        
        # Ask if they want to add another member
        keyboard = ReplyKeyboardMarkup(
            keyboard=[
                [KeyboardButton(text="Yes, add another")],
                [KeyboardButton(text="No, that's all")]
            ],
            resize_keyboard=True,
            one_time_keyboard=True
        )
        
        await message.answer(
            f"✅ Added {name} to the team.\n\n"
            "Do you want to add another team member?",
            reply_markup=keyboard
        )
        await state.set_state(Form.add_another)
        
    except Exception as e:
        await message.answer(
            "❌ Invalid format. Please enter in this format:\n"
            "Full Name, Phone Number\n\n"
            "Example:\n"
            "John Doe, +1234567890"
        )

# Handle add another team member
@dp.message(Form.add_another)
async def process_add_another(message: types.Message, state: FSMContext):
    """Process whether to add another team member"""
    if message.text.lower().startswith('y'):  # Yes, add another
        await message.answer(
            "👥 Please enter the next team member's details:\n"
            "Full Name, Phone Number"
        )
        await state.set_state(Form.team_member)
    else:
        # Complete registration with team
        await complete_registration(message, state)

async def complete_registration(message: types.Message, state: FSMContext):
    """Complete the registration process"""
    # Get all user data
    user_data = await state.get_data()
    
    # Create response message
    response = [
        "✅ Registration Complete! ✅",
        "\n📋 Your Details:",
        f"👤 Name: {user_data.get('full_name', 'N/A')}",
        f"📱 Phone: {user_data.get('phone', 'N/A')}",
        f"📊 English Level: {user_data.get('english_level', 'N/A')}",
        f"🎂 Age: {user_data.get('age', 'N/A')}",
    ]
    
    if 'team_name' in user_data:
        response.append(f"\n🏆 Team: {user_data['team_name']}")
        
        # Add team members if any
        team_members = user_data.get('team_members', [])
        if team_members:
            response.append("\n👥 Team Members:")
            for i, member in enumerate(team_members, 1):
                response.append(f"{i}. {member['name']} - {member['phone']}")
    
    # Send confirmation
    await message.answer(
        "\n".join(response),
        reply_markup=ReplyKeyboardRemove()
    )
    
    # Clear the state
    await state.clear()

# Error handler
@dp.message()
async def handle_other_messages(message: types.Message):
    """Handle all other messages"""
    await message.answer(
        "I don't understand that command. Send /start to begin registration."
    )

# Main function
async def main():
    logger.info("Starting bot...")
    try:
        await dp.start_polling(bot, skip_pending=True)
    finally:
        await bot.session.close()

if __name__ == '__main__':
    try:
        import asyncio
        asyncio.run(main())
    except (KeyboardInterrupt, SystemExit):
        logger.info("Bot stopped")
    except Exception as e:
        logger.error(f"Error: {e}")
        raise
