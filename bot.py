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

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Load environment variables
load_dotenv()

# Bot token from .env file (fallback to hardcoded if .env not available)
BOT_TOKEN = os.getenv('BOT_TOKEN', "7605069387:AAF4h9zO99LrqWg8JCVYmvYIrpFo1FN8YGc")

# Load channel username from environment
CHANNEL_USERNAME = os.getenv('CHANNEL_USERNAME', '@quizibratparticipants')
CHANNEL_ID = os.getenv('CHANNEL_ID', '5747916482')

# Admin user IDs from environment
ADMIN_IDS_STR = os.getenv('ADMIN_IDS', '1769729434,5747916482')
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
            f"🎂 <b>Age:</b> {participant_data.get('age', 'N/A')}",
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
        ],
        [
            types.InlineKeyboardButton(text="📋 Export Data", callback_data="export"),
            types.InlineKeyboardButton(text="🔄 Reload Data", callback_data="reload")
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

# Message forwarding handler
@dp.message()
async def handle_other_messages(message: types.Message):
    """Handle all other messages"""
    user_id = message.from_user.id
    
    # Check if user is registered
    if is_registered(user_id):
        participant = get_participant_info(user_id)
        if participant:
            try:
                # Format forwarded message
                username = participant.get('username', 'No username')
                full_name = participant.get('full_name', 'Unknown')
                
                forward_text = f"📩 *Message from registered user:*\n"
                forward_text += f"👤 *Name:* {full_name}\n"
                forward_text += f"👤 *Username:* @{username}\n"
                forward_text += f"🆔 *ID:* {user_id}\n"
                forward_text += f"💬 *Message:* {message.text or '[Media/File]'}"
                
                # Forward to channel/group
                if CHANNEL_USERNAME:
                    await bot.send_message(
                        chat_id=CHANNEL_USERNAME,
                        text=forward_text,
                        parse_mode='Markdown'
                    )
                
                # Also forward to admins
                for admin_id in ADMIN_IDS:
                    try:
                        await bot.send_message(
                            chat_id=admin_id,
                            text=forward_text,
                            parse_mode='Markdown'
                        )
                    except Exception as e:
                        logger.error(f"Error forwarding to admin {admin_id}: {e}")
                
                # Confirm to user
                await message.answer("✅ Your message has been forwarded to the group!")
                
            except Exception as e:
                logger.error(f"Error forwarding message: {e}")
                await message.answer("❌ Error forwarding your message. Please try again.")
    else:
        # Handle unregistered users
        if message.text and message.text.startswith('/'):
            await message.answer(
                "❓ I don't understand that command.\n\n"
                "Available commands:\n"
                "• /start - Begin registration\n"
                "• /admin - Admin panel (admins only)"
            )
        else:
            await message.answer(
                "👋 Hi! You need to register first to send messages to the group.\n"
                "Send /start to begin registration."
            )

# Main function
async def main():
    logger.info("Starting registration bot...")
    load_participants()
    try:
        await dp.start_polling(bot, skip_pending=True)
    except Exception as e:
        logger.error(f"Error during polling: {e}")
        raise
    finally:
        await bot.session.close()

if __name__ == '__main__':
    try:
        import asyncio
        asyncio.run(main())
    except (KeyboardInterrupt, SystemExit):
        logger.info("Bot stopped by user")
    except Exception as e:
        logger.error(f"Fatal error: {e}")
        raise
