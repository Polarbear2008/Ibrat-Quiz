import os
import logging
from aiogram import Bot, Dispatcher, types, F, html
from datetime import datetime
import json
from aiogram.filters import Command, StateFilter, CommandStart
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton, ReplyKeyboardRemove
from dotenv import load_dotenv
import os

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Load environment variables
load_dotenv()

# Bot token from .env file
BOT_TOKEN = os.getenv('BOT_TOKEN')
if not BOT_TOKEN:
    logger.error("No BOT_TOKEN found in .env file")
    exit(1)

# Load channel username from environment
load_dotenv()
CHANNEL_USERNAME = os.getenv('CHANNEL_USERNAME', '@quizibratparticipants')

# Initialize bot and dispatcher
bot = Bot(token=BOT_TOKEN)
dp = Dispatcher(storage=MemoryStorage())

async def notify_channel(participant_data):
    """Send notification to channel about new registration"""
    if not CHANNEL_USERNAME:
        return
        
    try:
        # Format the notification message
        message = [
            "🎉 *New Registration!* 🎉",
            f"👤 *Name:* {participant_data.get('full_name', 'N/A')}",
            f"📱 *Phone:* {participant_data.get('phone', 'N/A')}",
            f"📊 *English Level:* {participant_data.get('english_level', 'N/A')}",
            f"🎂 *Age:* {participant_data.get('age', 'N/A')}",
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
        
        # Send the message to the channel
        await bot.send_message(
            chat_id=CHANNEL_USERNAME,
            text="\n".join(message),
            parse_mode='Markdown'
        )
    except Exception as e:
        logger.error(f"Error sending to channel: {e}")
        print(f"Error sending to channel: {e}")

# States
class Form(StatesGroup):
    full_name = State()
    contact = State()
    english_level = State()
    age = State()
    has_team = State()
    team_name = State()
    team_members = State()

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
    """Process team name and ask for team members"""
    await state.update_data(team_name=message.text)
    
    await message.answer(
        "👥 Please enter your team members' details (one per line):\n"
        "Format: Full Name, Phone Number\n\n"
        "Example:\n"
        "John Doe, +1234567890\n"
        "Jane Smith, +1987654321"
    )
    await state.set_state(Form.team_members)

# Handle team members
@dp.message(Form.team_members)
async def process_team_members(message: types.Message, state: FSMContext):
    """Process team members"""
    try:
        # Parse team members
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
            "Full Name, Phone Number\n"
            "Example:\n"
            "John Doe, +1234567890"
        )

async def complete_registration(message: types.Message, state: FSMContext):
    """Complete the registration process"""
    # Get all user data
    user_data = await state.get_data()
    
    # Add registration timestamp
    user_data['registration_date'] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    user_data['telegram_id'] = message.from_user.id
    
    # Store the participant
    participants.append(user_data)
    
    # Save to file (in a real app, use a database)
    save_participants()
    
    # Send notification to channel
    await notify_channel(user_data)
    
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

# Admin commands
@dp.message(Command("admin"))
async def admin_panel(message: types.Message):
    """Show admin panel"""
    if not is_admin(message.from_user.id):
        await message.answer("🚫 Access denied.")
        return
    
    keyboard = [
        [
            types.InlineKeyboardButton(text="👥 View All Participants", callback_data="view_all"),
            types.InlineKeyboardButton(text="📊 Statistics", callback_data="stats")
        ]
    ]
    reply_markup = types.InlineKeyboardMarkup(inline_keyboard=keyboard)
    
    await message.answer(
        "👨‍💼 Admin Panel",
        reply_markup=reply_markup
    )

@dp.callback_query(F.data == "view_all")
async def view_all_participants(callback: types.CallbackQuery):
    """Show all participants"""
    if not is_admin(callback.from_user.id):
        await callback.answer("Access denied.", show_alert=True)
        return
    
    if not participants:
        await callback.message.answer("No participants registered yet.")
        return
    
    for i, participant in enumerate(participants, 1):
        response = [
            f"👤 Participant #{i}",
            f"📅 Registered: {participant.get('registration_date', 'N/A')}",
            f"👤 Name: {participant.get('full_name', 'N/A')}",
            f"📱 Phone: {participant.get('phone', 'N/A')}",
            f"📊 English: {participant.get('english_level', 'N/A')}",
            f"🎂 Age: {participant.get('age', 'N/A')}",
        ]
        
        if 'team_name' in participant:
            response.append(f"🏆 Team: {participant['team_name']}")
            team_members = participant.get('team_members', [])
            if team_members:
                response.append("👥 Team Members:")
                for j, member in enumerate(team_members, 1):
                    response.append(f"  {j}. {member['name']} - {member['phone']}")
        
        await callback.message.answer("\n".join(response))
    
    await callback.answer()

@dp.callback_query(F.data == "stats")
async def show_stats(callback: types.CallbackQuery):
    """Show registration statistics"""
    if not is_admin(callback.from_user.id):
        await callback.answer("Access denied.", show_alert=True)
        return
    
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
        f"👤 Solo Participants: {solo}",
        "\n📚 English Levels:"
    ]
    
    for level, count in levels.items():
        response.append(f"• {level}: {count}")
    
    await callback.message.answer("\n".join(response))
    await callback.answer()

def save_participants():
    """Save participants to a JSON file"""
    try:
        with open('participants.json', 'w', encoding='utf-8') as f:
            json.dump(participants, f, ensure_ascii=False, indent=2)
    except Exception as e:
        logger.error(f"Error saving participants: {e}")

def load_participants():
    """Load participants from JSON file"""
    global participants
    try:
        with open('participants.json', 'r', encoding='utf-8') as f:
            participants = json.load(f)
    except FileNotFoundError:
        participants = []
    except Exception as e:
        logger.error(f"Error loading participants: {e}")
        participants = []

# Error handler
@dp.message()
async def handle_other_messages(message: types.Message):
    """Handle all other messages"""
    if message.text and message.text.startswith('/'):
        await message.answer(
            "I don't understand that command. Send /start to begin registration or /admin for admin panel."
        )

# Main function
async def main():
    logger.info("Starting bot...")
    load_participants()
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
