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
from io import StringIO

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

# Participant data file
PARTICIPANTS_FILE = 'participants.json'

# Global participants list
participants = []

def save_participants():
    """Saves the participants list to a JSON file."""
    try:
        with open(PARTICIPANTS_FILE, 'w', encoding='utf-8') as f:
            json.dump(participants, f, indent=4, ensure_ascii=False)
        logger.info("Participants data saved successfully.")
    except Exception as e:
        logger.error(f"Error saving participants data: {e}")

def load_participants():
    """Loads participants from a JSON file."""
    global participants
    try:
        if os.path.exists(PARTICIPANTS_FILE):
            with open(PARTICIPANTS_FILE, 'r', encoding='utf-8') as f:
                participants = json.load(f)
            logger.info("Participants data loaded successfully.")
    except Exception as e:
        logger.error(f"Error loading participants data: {e}")
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
    registration_type = message.text
    await state.update_data(registration_type=registration_type)

    if registration_type.lower() == 'team':
        await message.answer(
            "What is your team's name?",
            reply_markup=ReplyKeyboardRemove()
        )
        await state.set_state(RegistrationForm.team_name)
    else: # Individual
        participant_data = await state.get_data()
        await finalize_registration(message, participant_data)
        await state.clear()

# Handle team name
@dp.message(RegistrationForm.team_name)
async def process_team_name(message: types.Message, state: FSMContext):
    """Process team name and ask for team members."""
    await state.update_data(team_name=message.text)
    await message.answer(
        "Please list your team members' full names, separated by commas.",
        reply_markup=ReplyKeyboardRemove()
    )
    await state.set_state(RegistrationForm.team_members)

# Handle team members
@dp.message(RegistrationForm.team_members)
async def process_team_members(message: types.Message, state: FSMContext):
    """Process team members and finalize registration."""
    team_members = [{'name': name.strip()} for name in message.text.split(',')]
    await state.update_data(team_members=team_members)
    
    participant_data = await state.get_data()
    await finalize_registration(message, participant_data)
    await state.clear()

# Admin panel
@dp.message(Command("admin"))
async def admin_panel(message: types.Message):
    """Admin panel with advanced controls."""
    if not is_admin(message.from_user.id):
        await message.answer("You are not authorized to use this command.")
        return

    admin_keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📊 View Participants", callback_data="view_participants")],
        [InlineKeyboardButton(text="📈 Get Statistics", callback_data="get_stats")],
        [InlineKeyboardButton(text="🔍 Filter by Region", callback_data="filter_by_region")],
        [InlineKeyboardButton(text="📄 Export Data", callback_data="export_data")],
        [InlineKeyboardButton(text="🗑️ Clear All Data", callback_data="confirm_clear_all")]
    ])
    
    await message.answer("Welcome to the Admin Panel!", reply_markup=admin_keyboard)

# Callback for viewing participants
@dp.callback_query(F.data == "view_participants")
async def view_participants_callback(callback_query: types.CallbackQuery):
    """Displays the list of registered participants."""
    if not participants:
        await callback_query.answer("No participants registered yet.")
        return

    response = "<b>Registered Participants:</b>\n\n"
    for p in participants:
        response += (
            f"<b>Name:</b> {escape_html(p.get('full_name', 'N/A'))}\n"
            f"<b>Username:</b> @{escape_html(p.get('username', 'N/A'))}\n"
            f"<b>Region:</b> {escape_html(p.get('region', 'N/A'))}\n"
            f"<b>Phone:</b> {escape_html(p.get('phone', 'N/A'))}\n"
            f"<b>Team:</b> {escape_html(p.get('team_name', 'Individual'))}\n"
            f"--------------------\n"
        )
    
    await callback_query.message.answer(response, parse_mode='HTML')
    await callback_query.answer()

# Callback for getting statistics
@dp.callback_query(F.data == "get_stats")
async def get_stats_callback(callback_query: types.CallbackQuery):
    """Provides statistics about registrations."""
    total_participants = len(participants)
    
    # Region stats
    region_counts = {}
    for p in participants:
        region = p.get('region', 'Unknown')
        region_counts[region] = region_counts.get(region, 0) + 1
    
    region_stats = "\n".join([f"- {region}: {count}" for region, count in region_counts.items()])
    
    # Team vs Individual
    team_count = sum(1 for p in participants if p.get('registration_type') == 'Team')
    individual_count = total_participants - team_count
    
    stats_message = (
        f"<b>Registration Statistics:</b>\n\n"
        f"- <b>Total Participants:</b> {total_participants}\n"
        f"- <b>Individuals:</b> {individual_count}\n"
        f"- <b>Teams:</b> {team_count}\n\n"
        f"<b>Region Breakdown:</b>\n{region_stats}"
    )
    
    await callback_query.message.answer(stats_message, parse_mode='HTML')
    await callback_query.answer()

# Callback to initiate region filtering
@dp.callback_query(F.data == "filter_by_region")
async def filter_by_region_callback(callback_query: types.CallbackQuery):
    """Shows buttons for each available region to filter by."""
    # Get unique regions from participants
    regions = sorted(list(set(p.get('region') for p in participants if p.get('region'))))
    
    if not regions:
        await callback_query.answer("No regions available to filter by.")
        return

    region_buttons = [[InlineKeyboardButton(text=region, callback_data=f"view_region_{region}")] for region in regions]
    
    await callback_query.message.answer(
        "Select a region to view participants:",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=region_buttons)
    )
    await callback_query.answer()

# Callback to view participants from a specific region
@dp.callback_query(F.data.startswith("view_region_"))
async def view_region_participants_callback(callback_query: types.CallbackQuery):
    """Displays participants filtered by the selected region."""
    region = callback_query.data.split("_")[-1]
    
    filtered_participants = [p for p in participants if p.get('region') == region]
    
    if not filtered_participants:
        await callback_query.answer(f"No participants found for {region}.")
        return

    response = f"<b>Participants in {escape_html(region)}:</b>\n\n"
    for p in filtered_participants:
        response += (
            f"<b>Name:</b> {escape_html(p.get('full_name', 'N/A'))}\n"
            f"<b>Username:</b> @{escape_html(p.get('username', 'N/A'))}\n"
            f"<b>Phone:</b> {escape_html(p.get('phone', 'N/A'))}\n"
            f"<b>Team:</b> {escape_html(p.get('team_name', 'Individual'))}\n"
            f"--------------------\n"
        )
        
    await callback_query.message.answer(response, parse_mode='HTML')
    await callback_query.answer()

# Callback for exporting data
@dp.callback_query(F.data == "export_data")
async def export_data_callback(callback_query: types.CallbackQuery):
    """Exports participant data to a text file."""
    if not is_admin(callback_query.from_user.id):
        await callback_query.answer("Access denied.", show_alert=True)
        return

    if not participants:
        await callback_query.answer("No data to export.")
        return

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
                    export_text.append(f"  - {member.get('name', 'N/A')}")
        else:
            export_text.append("Team: Solo")
        export_text.append("-" * 20)

    file_content = "\n".join(export_text)
    file_to_send = types.BufferedInputFile(file_content.encode('utf-8'), filename=f"participants_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt")
    
    await callback_query.message.answer_document(file_to_send)
    await callback_query.answer("Data exported successfully!")

# Callback for confirming data clearance
@dp.callback_query(F.data == "confirm_clear_all")
async def confirm_clear_all_callback(callback_query: types.CallbackQuery):
    """Asks for confirmation before clearing all data."""
    confirm_keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="✅ Yes, Clear All", callback_data="clear_all_confirmed")],
        [InlineKeyboardButton(text="❌ No, Cancel", callback_data="cancel_clear")]
    ])
    await callback_query.message.answer(
        "⚠️ <b>Are you sure you want to clear all participant data?</b> This action cannot be undone.",
        reply_markup=confirm_keyboard,
        parse_mode='HTML'
    )
    await callback_query.answer()

# Callback for final data clearance
@dp.callback_query(F.data == "clear_all_confirmed")
async def clear_all_confirmed_callback(callback_query: types.CallbackQuery):
    """Clears all participant data after confirmation."""
    global participants
    participants.clear()
    save_participants()  # Overwrite with empty list
    await callback_query.message.edit_text("All participant data has been cleared.")
    await callback_query.answer("Data cleared.")

# Callback to cancel data clearance
@dp.callback_query(F.data == "cancel_clear")
async def cancel_clear_callback(callback_query: types.CallbackQuery):
    """Cancels the data clearance action."""
    await callback_query.message.edit_text("Data clearance cancelled.")
    await callback_query.answer()


async def finalize_registration(message: types.Message, participant_data: dict):
    """Finalizes the registration process."""
    # Add registration timestamp and user info
    participant_data['registration_date'] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    participant_data['telegram_id'] = message.from_user.id
    participant_data['username'] = message.from_user.username or "No username"
    participant_data['first_name'] = message.from_user.first_name or ""
    participant_data['last_name'] = message.from_user.last_name or ""
    
    # Store the participant
    participants.append(participant_data)
    
    # Save to file (in a real app, use a database)
    save_participants()
    
    # Send notification to channel
    await notify_channel(participant_data)
    
    # Send notification to admin
    await notify_admin(participant_data)
    
    # Create response message
    response = [
        "✅ Registration Complete! ✅",
        "\n📋 Your Details:",
        f"👤 Name: {participant_data.get('full_name', 'N/A')}",
        f"📱 Phone: {participant_data['phone']}",
        f"📊 English Level: {participant_data['english_level']}",
        f"🎂 Age: {participant_data['age']}",
        f"📍 Region: {participant_data['region']}",
    ]
    
    if 'team_name' in participant_data:
        response.append(f"\n🏆 Team: {participant_data['team_name']}")
        
        # Add team members if any
        team_members = participant_data.get('team_members', [])
        if team_members:
            response.append("\n👥 Team Members:")
            for i, member in enumerate(team_members, 1):
                response.append(f"{i}. {member.get('name', 'N/A')}")
    
    # Send confirmation
    await message.answer(
        "\n".join(response),
        reply_markup=main_menu_keyboard
    )


async def scheduled_clear_job():
    # This is a placeholder. Implement job logic if needed.
    logger.info("Scheduled job running...")

@dp.message()
async def handle_other_messages(message: types.Message):
    """Handle all other messages for unregistered users or unknown commands."""
    if message.text and message.text.startswith('/'):
        await message.answer(
            "❓ I don't understand that command.\n\n"
            "Available commands:\n"
            "• /start - Begin registration\n"
            "• /admin - Admin panel (admins only)"
        )
    else:
        await message.answer(
            "👋 Hi! You need to register first.\n"
            "Send /start to begin registration.",
            reply_markup=main_menu_keyboard
        )

async def main():
    """Main function to start the bot."""
    load_participants()

    scheduler = AsyncIOScheduler(timezone=pytz.utc)
    scheduler.add_job(save_participants, 'interval', minutes=15)
    # scheduler.add_job(scheduled_clear_job, 'cron', day_of_week='sun', hour=0, minute=0)
    scheduler.start()

    logger.info("Starting bot...")
    try:
        await dp.start_polling(bot, skip_pending=True)
    finally:
        scheduler.shutdown()
        await bot.session.close()

if __name__ == '__main__':
    import asyncio
    try:
        asyncio.run(main())
    except (KeyboardInterrupt, SystemExit):
        logger.info("Bot stopped by user")
    except Exception as e:
        logger.critical(f"Bot failed to start: {e}", exc_info=True)
