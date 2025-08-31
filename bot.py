print("--- Script execution started ---")
import os
import logging
from aiogram import Bot, Dispatcher, types, F, html
from datetime import datetime
import json
from aiogram.filters import Command, StateFilter, CommandStart
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton, ReplyKeyboardRemove, InlineKeyboardMarkup, InlineKeyboardButton
from dotenv import load_dotenv
from apscheduler.schedulers.asyncio import AsyncIOScheduler
import pytz

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Load environment variables
load_dotenv()

# Bot token from .env file
BOT_TOKEN = os.getenv('BOT_TOKEN')
if not BOT_TOKEN:
    logger.critical("BOT_TOKEN not found in .env file. The bot cannot start.")
    exit()

# Load channel username from environment
CHANNEL_USERNAME = os.getenv('CHANNEL_USERNAME')
if not CHANNEL_USERNAME:
    logger.warning("CHANNEL_USERNAME not found in .env file.")

CHANNEL_ID = os.getenv('CHANNEL_ID') # Optional fallback

# Admin user IDs from environment
ADMIN_IDS_STR = os.getenv('ADMIN_IDS')
if not ADMIN_IDS_STR:
    logger.critical("ADMIN_IDS not found in .env file. The bot cannot start.")
    exit()
ADMIN_IDS = [int(id.strip()) for id in ADMIN_IDS_STR.split(',') if id.strip()]

# Global participants list
participants = []

# Initialize bot and dispatcher
bot = Bot(token=BOT_TOKEN)
dp = Dispatcher(storage=MemoryStorage())

def is_admin(user_id):
    """Check if user is admin"""
    return user_id in ADMIN_IDS

def is_registered(user_id):
    """Check if user is registered"""
    return any(p.get('telegram_id') == user_id for p in participants)

def get_participant_info(user_id):
    """Get participant info by user ID"""
    for p in participants:
        if p.get('telegram_id') == user_id:
            return p
    return None

async def notify_channel(participant_data):
    """Send notification to channel about new registration"""
    if not CHANNEL_USERNAME:
        logger.warning("CHANNEL_USERNAME not set, skipping channel notification")
        return
        
    try:
        # Format the notification message using HTML
        def escape_html(text):
            """Escape HTML special characters"""
            if not text or text == 'N/A':
                return text
            return str(text).replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;')
        
        message = [
            "🎉 <b>New Registration!</b> 🎉",
            f"👤 <b>Name:</b> {escape_html(participant_data.get('full_name', 'N/A'))}",
            f"👤 <b>Username:</b> @{escape_html(participant_data.get('username', 'N/A'))}",
            f"🆔 <b>Telegram ID:</b> {participant_data.get('telegram_id', 'N/A')}",
            f"📱 <b>Phone:</b> {escape_html(participant_data.get('phone', 'N/A'))}",
            f"📊 <b>English Level:</b> {escape_html(participant_data.get('english_level', 'N/A'))}",
            f"🎂 <b>Age:</b> {participant_data.get('age', 'N/A')}",
        ]
        
        if 'team_name' in participant_data:
            message.append(f"🏆 <b>Team:</b> {escape_html(participant_data['team_name'])}")
            
            # Add team members if any
            team_members = participant_data.get('team_members', [])
            if team_members:
                message.append("\n👥 <b>Team Members:</b>")
                for i, member in enumerate(team_members, 1):
                    member_info = f"{i}. {escape_html(member.get('name', 'N/A'))}"
                    if 'phone' in member:
                        member_info += f" - {escape_html(member['phone'])}"
                    message.append(member_info)
        
        # Try sending to channel username first
        logger.info(f"Attempting to send to channel: {CHANNEL_USERNAME}")
        try:
            await bot.send_message(
                chat_id=CHANNEL_USERNAME,
                text="\n".join(message),
                parse_mode='HTML'
            )
            logger.info("Successfully sent to channel via username")
        except Exception as username_error:
            logger.error(f"Failed to send via username {CHANNEL_USERNAME}: {username_error}")
            
            # Try with CHANNEL_ID if available
            if CHANNEL_ID:
                try:
                    await bot.send_message(
                        chat_id=int(CHANNEL_ID),
                        text="\n".join(message),
                        parse_mode='HTML'
                    )
                    logger.info("Successfully sent to channel via ID")
                except Exception as id_error:
                    logger.error(f"Failed to send via ID {CHANNEL_ID}: {id_error}")
                    raise id_error
            else:
                raise username_error
                
    except Exception as e:
        logger.error(f"Error sending to channel: {e}")
        print(f"Error sending to channel: {e}")
        # Send error notification to admins
        for admin_id in ADMIN_IDS:
            try:
                await bot.send_message(
                    chat_id=admin_id,
                    text=f"⚠️ Failed to send registration notification to channel: {e}"
                )
            except:
                pass

async def notify_admin(participant_data):
    """Send notification to admin about new registration"""
    try:
        # Escape function for admin notifications
        def escape_html(text):
            """Escape HTML special characters"""
            if not text or text == 'N/A':
                return text
            return str(text).replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;')
        
        # Format the notification message for admin
        message = [
            "🎉 <b>New Registration!</b> 🎉",
            f"👤 <b>Name:</b> {escape_html(participant_data.get('full_name', 'N/A'))}",
            f"👤 <b>Username:</b> @{escape_html(participant_data.get('username', 'N/A'))}",
            f"🆔 <b>Telegram ID:</b> {participant_data.get('telegram_id', 'N/A')}",
            f"📱 <b>Phone:</b> {escape_html(participant_data.get('phone', 'N/A'))}",
            f"📊 <b>English Level:</b> {escape_html(participant_data.get('english_level', 'N/A'))}",
            f"🎂 <b>Age:</b> {escape_html(participant_data.get('age', 'N/A'))}",
            f"📍 <b>Region:</b> {escape_html(participant_data.get('region', 'N/A'))}",
            f"📅 <b>Registered:</b> {escape_html(participant_data.get('registration_date', 'N/A'))}",
        ]
        
        if 'team_name' in participant_data:
            message.append(f"🏆 <b>Team:</b> {escape_html(participant_data['team_name'])}")
            
            # Add team members if any
            team_members = participant_data.get('team_members', [])
            if team_members:
                message.append("\n👥 <b>Team Members:</b>")
                for i, member in enumerate(team_members, 1):
                    member_info = f"{i}. {escape_html(member['name'])} - {escape_html(member.get('phone', 'N/A'))}"
                    message.append(member_info)
        
        # Send the message to all admins
        for admin_id in ADMIN_IDS:
            try:
                await bot.send_message(
                    chat_id=admin_id,
                    text="\n".join(message),
                    parse_mode='HTML'
                )
            except Exception as e:
                logger.error(f"Error sending to admin {admin_id}: {e}")
                
    except Exception as e:
        logger.error(f"Error in notify_admin: {e}")

# Main menu keyboard
main_menu_keyboard = ReplyKeyboardMarkup(
    keyboard=[
        [KeyboardButton(text="📝 Register"), KeyboardButton(text="📨 Contact")]
    ],
    resize_keyboard=True
)

# Region keyboard
region_keyboard = ReplyKeyboardMarkup(
    keyboard=[
        [KeyboardButton(text="Tashkent"), KeyboardButton(text="Andijan")],
        [KeyboardButton(text="Fergana"), KeyboardButton(text="Khorazm")]
    ],
    resize_keyboard=True,
    one_time_keyboard=True
)

# Registration type keyboard
registration_type_keyboard = ReplyKeyboardMarkup(
    keyboard=[
        [KeyboardButton(text="Individual"), KeyboardButton(text="Team")],
    ],
    resize_keyboard=True,
    one_time_keyboard=True
)

# States
class RegistrationForm(StatesGroup):
    full_name = State()
    phone = State()
    english_level = State()
    age = State()
    region = State()
    registration_type = State()
    team_name = State()
    team_members = State()

class ContactForm(StatesGroup):
    contact_message = State()

# Start command
@dp.message(CommandStart())
async def cmd_start(message: types.Message, state: FSMContext):
    """Handler for /start command, shows main menu."""
    await state.clear()  # Clear any previous state
    await message.answer(
        "👋 Welcome to the Quiz Bot!\n\n"
        "Please choose an option from the menu below:",
        reply_markup=main_menu_keyboard
    )

# Handler for "Register" button
@dp.message(F.text == "📝 Register", StateFilter(None))
async def start_registration(message: types.Message, state: FSMContext):
    """Handler to start the registration process."""
    if is_registered(message.from_user.id):
        await message.answer("You are already registered!", reply_markup=main_menu_keyboard)
        return

    await message.answer(
        "Great! Let's get you registered.\n\n"
        "Please enter your full name:",
        reply_markup=ReplyKeyboardRemove()
    )
    await state.set_state(RegistrationForm.full_name)

# Handler for "Contact" button
@dp.message(F.text == "📨 Contact", StateFilter(None))
async def start_contact(message: types.Message, state: FSMContext):
    """Handler to start the contact flow."""
    await message.answer(
        "Please type your message below. It will be forwarded to the admins.",
        reply_markup=ReplyKeyboardRemove()
    )
    await state.set_state(ContactForm.contact_message)

# Handler for receiving the contact message
@dp.message(ContactForm.contact_message)
async def process_contact_message(message: types.Message, state: FSMContext):
    """Forwards the user's message to admins."""
    user_info = f"👤 From: {message.from_user.full_name} (@{message.from_user.username}, ID: {message.from_user.id})"
    message_text = message.text or "[No text content]"
    
    full_message = f"📨 New Contact Message 📨\n\n{user_info}\n\n💬 Message:\n{message_text}"
    
    for admin_id in ADMIN_IDS:
        try:
            await bot.send_message(admin_id, full_message)
        except Exception as e:
            logger.error(f"Failed to forward contact message to admin {admin_id}: {e}")
            
    await message.answer(
        "✅ Thank you! Your message has been sent to the admins.",
        reply_markup=main_menu_keyboard
    )
    await state.clear()

# Handle full name
@dp.message(RegistrationForm.full_name)
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
    await state.set_state(RegistrationForm.phone)

# Handle contact sharing
@dp.message(RegistrationForm.phone, F.contact)
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
    await state.set_state(RegistrationForm.english_level)

# Handle English level
@dp.message(RegistrationForm.english_level)
async def process_english_level(message: types.Message, state: FSMContext):
    """Process English level"""
    await state.update_data(english_level=message.text)
    await message.answer(
        "🎂 How old are you? (Enter a number)",
        reply_markup=ReplyKeyboardRemove()
    )
    await state.set_state(RegistrationForm.age)

# Handle age
@dp.message(RegistrationForm.age)
async def process_age(message: types.Message, state: FSMContext):
    """Process user's age"""
    try:
        age = int(message.text)
        await state.update_data(age=age)
        
        await message.answer(
            "Please select your region:",
            reply_markup=region_keyboard
        )
        await state.set_state(RegistrationForm.region)
    except ValueError:
        await message.answer("Please enter a valid number for your age.")

# Handle region
@dp.message(RegistrationForm.region)
async def process_region(message: types.Message, state: FSMContext):
    """Process user's region"""
    if message.text not in ["Tashkent", "Andijan", "Fergana", "Khorazm"]:
        await message.answer("Please select a valid region from the buttons.")
        return

    await state.update_data(region=message.text)
    await message.answer(
        "How would you like to register?",
        reply_markup=registration_type_keyboard
    )
    await state.set_state(RegistrationForm.registration_type)

# Handle registration type
@dp.message(RegistrationForm.registration_type)
async def process_registration_type(message: types.Message, state: FSMContext):
    """Process registration type"""
    if message.text.lower() in ["individual"]:
        # Complete registration without team
        await complete_registration(message, state)
    elif message.text.lower() in ["team"]:
        await message.answer(
            "🏆 Please enter your team name:",
            reply_markup=ReplyKeyboardRemove()
        )
        await state.set_state(RegistrationForm.team_name)
    else:
        await message.answer("Please select a valid registration type from the buttons.")

# Handle team name
@dp.message(RegistrationForm.team_name)
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
    await state.set_state(RegistrationForm.team_members)

# Handle team members
@dp.message(RegistrationForm.team_members)
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
    
    # Add registration timestamp and user info
    user_data['registration_date'] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    user_data['telegram_id'] = message.from_user.id
    user_data['username'] = message.from_user.username or "No username"
    user_data['first_name'] = message.from_user.first_name or ""
    user_data['last_name'] = message.from_user.last_name or ""
    
    # Store the participant
    participants.append(user_data)
    
    # Save to file (in a real app, use a database)
    save_participants()
    
    # Send notification to channel
    await notify_channel(user_data)
    
    # Send notification to admin
    await notify_admin(user_data)
    
    # Create response message
    response = [
        "✅ Registration Complete! ✅",
        "\n📋 Your Details:",
        f"👤 Name: {user_data.get('full_name', 'N/A')}",
        f"📱 Phone: {user_data['phone']}",
        f"📊 English Level: {user_data['english_level']}",
        f"🎂 Age: {user_data['age']}",
        f"📍 Region: {user_data['region']}",
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
        reply_markup=main_menu_keyboard
    )
    
    # Clear the state
    await state.clear()

def clear_all_data():
    """Clears the participants list and the storage file."""
    global participants
    participants = []
    save_participants()
    logger.info("All participant data has been cleared.")

@dp.message(Command("clear"))
async def clear_data_command(message: types.Message):
    """Admin command to clear all registration data."""
    if not is_admin(message.from_user.id):
        await message.answer("🚫 Access denied.")
        return

    # Add confirmation step
    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="⚠️ Yes, clear all data", callback_data="confirm_clear")],
            [InlineKeyboardButton(text="❌ Cancel", callback_data="cancel_clear")]
        ]
    )
    await message.answer(
        "❓ Are you sure you want to delete all registration data? This action cannot be undone.",
        reply_markup=keyboard
    )

@dp.callback_query(F.data == "confirm_clear")
async def confirm_clear_data(callback: types.CallbackQuery):
    """Handles confirmation of data clearing."""
    if not is_admin(callback.from_user.id):
        await callback.answer("Access denied.", show_alert=True)
        return
    
    clear_all_data()
    await callback.message.edit_text("✅ All registration data has been cleared.")
    await callback.answer()

@dp.callback_query(F.data == "cancel_clear")
async def cancel_clear_data(callback: types.CallbackQuery):
    """Handles cancellation of data clearing."""
    if not is_admin(callback.from_user.id):
        await callback.answer("Access denied.", show_alert=True)
        return

    await callback.message.edit_text("Action cancelled.")
    await callback.answer()

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
        ],
        [
            types.InlineKeyboardButton(text="📋 Export Data", callback_data="export"),
            types.InlineKeyboardButton(text="🔄 Reload Data", callback_data="reload")
        ],
        [
            types.InlineKeyboardButton(text="📍 Filter by Region", callback_data="show_region_filter")
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
            f"👤 Username: @{participant.get('username', 'No username')}",
            f"🆔 Telegram ID: {participant.get('telegram_id', 'N/A')}",
            f"📱 Phone: {participant.get('phone', 'N/A')}",
            f"📊 English: {participant.get('english_level', 'N/A')}",
            f"🎂 Age: {participant.get('age', 'N/A')}",
            f"📍 Region: {participant.get('region', 'N/A')}",
        ]
        
        if 'team_name' in participant:
            response.append(f"🏆 Team: {participant['team_name']}")
            team_members = participant.get('team_members', [])
            if team_members:
                response.append("👥 Team Members:")
                for j, member in enumerate(team_members, 1):
                    response.append(f"  {j}. {member['name']} - {member['phone']}")
        
        response.append("--------------------")
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
    
    # Count by age groups
    age_groups = {"Under 18": 0, "18-25": 0, "26-35": 0, "Over 35": 0}
    for p in participants:
        age = p.get('age', 0)
        if age < 18:
            age_groups["Under 18"] += 1
        elif age <= 25:
            age_groups["18-25"] += 1
        elif age <= 35:
            age_groups["26-35"] += 1
        else:
            age_groups["Over 35"] += 1
    
    response = [
        "📊 Registration Statistics",
        f"👥 Total Participants: {total}",
        f"🏆 Teams: {teams}",
        f"👤 Solo Participants: {solo}",
        "\n📚 English Levels:"
    ]
    
    for level, count in levels.items():
        response.append(f"• {level}: {count}")
    
    response.append("\n🎂 Age Groups:")
    for group, count in age_groups.items():
        response.append(f"• {group}: {count}")

    # Count by region
    regions = {}
    for p in participants:
        region = p.get('region', 'Not specified')
        regions[region] = regions.get(region, 0) + 1
    
    response.append("\n📍 Regions:")
    for region, count in regions.items():
        response.append(f"• {region}: {count}")
    
    await callback.message.answer("\n".join(response))
    await callback.answer()

@dp.callback_query(F.data == "export")
async def export_data(callback: types.CallbackQuery):
    """Export participants data"""
    if not is_admin(callback.from_user.id):
        await callback.answer("Access denied.", show_alert=True)
        return
    
    if not participants:
        await callback.message.answer("No data to export.")
        return
    
    # Create a formatted text export
    export_text = ["📋 PARTICIPANTS EXPORT", "=" * 30, ""]
    
    for i, p in enumerate(participants, 1):
        export_text.append(f"#{i} - {p.get('full_name', 'N/A')}")
        export_text.append(f"Phone: {p.get('phone', 'N/A')}")
        export_text.append(f"English: {p.get('english_level', 'N/A')}")
        export_text.append(f"Age: {p.get('age', 'N/A')}")
        export_text.append(f"Region: {p.get('region', 'N/A')}")
        export_text.append(f"Date: {p.get('registration_date', 'N/A')}")
        
        if 'team_name' in p:
            export_text.append(f"Team: {p['team_name']}")
            if p.get('team_members'):
                export_text.append("Members:")
                for member in p['team_members']:
                    export_text.append(f"  - {member['name']} ({member.get('phone', 'N/A')})")
        else:
            export_text.append("Team: Solo")
        
        export_text.append("-" * 20)
    
    # Send as text file
    from io import StringIO
    file_content = "\n".join(export_text)
    
    await callback.message.answer_document(
        types.BufferedInputFile(
            file_content.encode('utf-8'),
            filename=f"participants_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"
        ),
        caption="📋 Participants data export"
    )
    
    await callback.answer("Data exported successfully!")

@dp.callback_query(F.data == "show_region_filter")
async def show_region_filter(callback: types.CallbackQuery):
    """Shows region filter options."""
    if not is_admin(callback.from_user.id):
        await callback.answer("Access denied.", show_alert=True)
        return

    regions = ["Tashkent", "Andijan", "Fergana", "Khorazm"]
    keyboard = [
        [types.InlineKeyboardButton(text=region, callback_data=f"filter_region_{region}")] for region in regions
    ]
    keyboard.append([types.InlineKeyboardButton(text="⬅️ Back to Admin Panel", callback_data="back_to_admin")])
    
    reply_markup = types.InlineKeyboardMarkup(inline_keyboard=keyboard)
    
    await callback.message.edit_text(
        "📍 Please select a region to filter by:",
        reply_markup=reply_markup
    )
    await callback.answer()

@dp.callback_query(F.data.startswith("filter_region_"))
async def view_participants_by_region(callback: types.CallbackQuery):
    """Shows participants filtered by a specific region."""
    if not is_admin(callback.from_user.id):
        await callback.answer("Access denied.", show_alert=True)
        return

    region = callback.data.split("_", 2)[2]
    
    filtered_participants = [p for p in participants if p.get('region') == region]

    if not filtered_participants:
        await callback.message.answer(f"No participants registered from {region}.")
        await callback.answer()
        return

    await callback.message.delete() # Delete the filter menu
    await callback.message.answer(f"👥 Participants from {region}:")

    for i, participant in enumerate(filtered_participants, 1):
        response = [
            f"👤 Participant #{i}",
            f"📅 Registered: {participant.get('registration_date', 'N/A')}",
            f"👤 Name: {participant.get('full_name', 'N/A')}",
            f"👤 Username: @{participant.get('username', 'No username')}",
            f"🆔 Telegram ID: {participant.get('telegram_id', 'N/A')}",
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
        
        response.append("--------------------")
        await callback.message.answer("\n".join(response))
    
    await callback.answer()

@dp.callback_query(F.data == "back_to_admin")
async def back_to_admin_panel(callback: types.CallbackQuery):
    """Returns to the main admin panel."""
    if not is_admin(callback.from_user.id):
        await callback.answer("Access denied.", show_alert=True)
        return

    keyboard = [
        [
            types.InlineKeyboardButton(text="👥 View All Participants", callback_data="view_all"),
            types.InlineKeyboardButton(text="📊 Statistics", callback_data="stats")
        ],
        [
            types.InlineKeyboardButton(text="📋 Export Data", callback_data="export"),
            types.InlineKeyboardButton(text="🔄 Reload Data", callback_data="reload")
        ],
        [
            types.InlineKeyboardButton(text="📍 Filter by Region", callback_data="show_region_filter")
        ]
    ]
    reply_markup = types.InlineKeyboardMarkup(inline_keyboard=keyboard)
    
    await callback.message.edit_text(
        "👨‍💼 Admin Panel",
        reply_markup=reply_markup
    )
    await callback.answer()

@dp.callback_query(F.data == "reload")
async def reload_data(callback: types.CallbackQuery):
    """Reload participants data from file"""
    if not is_admin(callback.from_user.id):
        await callback.answer("Access denied.", show_alert=True)
        return
    
    load_participants()
    await callback.message.answer(f"🔄 Data reloaded! Found {len(participants)} participants.")
    await callback.answer()

# Test channel connection command
@dp.message(Command("test_channel"))
async def test_channel(message: types.Message):
    """Test channel connection (admin only)"""
    if not is_admin(message.from_user.id):
        await message.answer("🚫 Access denied.")
        return
    
    test_data = {
        'full_name': 'Test User',
        'username': 'testuser',
        'telegram_id': 12345,
        'phone': '+1234567890',
        'english_level': 'Intermediate',
        'age': 25,
        'registration_date': datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    }
    
    await message.answer("🧪 Testing channel notification...")
    await notify_channel(test_data)
    await message.answer("✅ Test notification sent! Check the channel and logs.")

def save_participants():
    """Save participants to a JSON file"""
    try:
        with open('participants.json', 'w', encoding='utf-8') as f:
            json.dump(participants, f, ensure_ascii=False, indent=2)
        logger.info(f"Saved {len(participants)} participants to file")
    except Exception as e:
        logger.error(f"Error saving participants: {e}")

def load_participants():
    """Load participants from JSON file"""
    global participants
    try:
        with open('participants.json', 'r', encoding='utf-8') as f:
            participants = json.load(f)
        logger.info(f"Loaded {len(participants)} participants from file")
    except FileNotFoundError:
        participants = []
        logger.info("No existing participants file found, starting fresh")
    except Exception as e:
        logger.error(f"Error loading participants: {e}")
        participants = []

# Fallback handler for any other messages
@dp.message()
async def handle_other_messages(message: types.Message, state: FSMContext):
    """Handle messages that don't match any other handlers."""
    # If user is in a state, do nothing to avoid interrupting a form
    if await state.get_state() is not None:
        return

    await message.answer(
        "Please use the menu buttons to navigate.",
        reply_markup=main_menu_keyboard
    )

# Main function
async def scheduled_clear_job():
    """Scheduled job to clear all data and notify admins."""
    clear_all_data()
    for admin_id in ADMIN_IDS:
        try:
            await bot.send_message(admin_id, "🤖 Weekly registration data has been automatically cleared.")
        except Exception as e:
            logger.error(f"Failed to send weekly clear notification to admin {admin_id}: {e}")

async def main():
    logger.info("Starting registration bot...")
    load_participants()

    # Initialize scheduler
    scheduler = AsyncIOScheduler(timezone=pytz.utc)
    # Schedule job to run every Sunday at 00:00 server time
    scheduler.add_job(scheduled_clear_job, 'cron', day_of_week='sun', hour=0, minute=0)
    scheduler.start()

    try:
        await dp.start_polling(bot, skip_pending=True)
    except Exception as e:
        logger.error(f"Error during polling: {e}")
        raise
    finally:
        scheduler.shutdown()
        await bot.session.close()

if __name__ == '__main__':
    print("--- Attempting to start bot... ---")
    try:
        import asyncio
        asyncio.run(main())
    except (KeyboardInterrupt, SystemExit):
        logger.info("Bot stopped by user")
    except Exception as e:
        logger.error(f"Fatal error: {e}")
        raise
