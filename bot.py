import os
import logging
import asyncio
from aiogram import Bot, Dispatcher, types, F, Router
from aiogram.filters import Command, StateFilter, CommandStart
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.types import (
    ReplyKeyboardMarkup, 
    KeyboardButton, 
    ReplyKeyboardRemove, 
    InputFile, 
    Message, 
    CallbackQuery
)
from aiogram.utils.keyboard import ReplyKeyboardBuilder
from dotenv import load_dotenv
from database import Database

# Load environment variables first
load_dotenv()

# Configure logging
logging.basicConfig(level=logging.INFO)

# Directly use the token for now
BOT_TOKEN = '7605069387:AAF4h9zO99LrqWg8JCVYmvYIrpFo1FN8YGc'

# Initialize bot, storage and router
bot = Bot(token=BOT_TOKEN)
storage = MemoryStorage()
dp = Dispatcher(storage=storage)
router = Router()
dp.include_router(router)

# States
class Form(StatesGroup):
    language = State()
    full_name = State()
    contact = State()
    english_level = State()
    age = State()
    has_team = State()
    team_name = State()
    team_member_name = State()
    team_member_phone = State()
    add_another_member = State()

# Alias for state
form = Form()

# Initialize database
db = Database('users.db')

# Admin user IDs (replace with your own admin user ID)
# To find your ID, start the bot and send /myid command
# Then add your ID to this list and restart the bot
# Admin user IDs (as strings for safety)
# Add your Telegram user ID here (you can get it by sending /myid to the bot)
ADMIN_IDS = [
    1769729434,  # Add your ID here (as number, not string)
    # Add more admin IDs as needed, one per line
]

# Debug function to check admin status
def debug_admin_check(user_id):
    try:
        user_id = int(user_id)
        return {
            'user_id': user_id,
            'user_type': type(user_id).__name__,
            'admin_ids': ADMIN_IDS,
            'admin_types': [type(x).__name__ for x in ADMIN_IDS],
            'is_admin': user_id in ADMIN_IDS,
            'strict_equality': any(user_id is x for x in ADMIN_IDS)
        }
    except Exception as e:
        return {'error': str(e)}

# Language selection with emojis
languages = {
    'English': '🇬🇧 English',
    'Узбек': '🇺🇿 O\'zbek',
    'Русский': '🇷🇺 Русский'
}

language_keyboard = ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=True, row_width=2)
for code, lang in languages.items():
    language_keyboard.add(KeyboardButton(lang))

# English level selection with emojis
english_levels = {
    'Beginner': '🌱 Beginner (A1-A2)',
    'Intermediate': '📚 Intermediate (B1-B2)',
    'Advanced': '🎓 Advanced (C1-C2)'
}

english_level_keyboard = ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=True, row_width=2)
for code, level in english_levels.items():
    english_level_keyboard.add(KeyboardButton(level))

# Contact sharing with emoji
contact_keyboard = ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=True)
contact_keyboard.add(KeyboardButton("📱 Share Contact", request_contact=True))

@router.message(CommandStart())
async def send_welcome(message: Message, state: FSMContext):
    """Handler for /start command with enhanced welcome message"""
    # Check if user is already registered
    user = db.get_user(message.from_user.id)
    
    if user and user.get('registration_complete'):
        # User is already registered
        welcome_text = (
            "🌟 *Welcome back!* \n\n"
            "You are already registered. "
            "If you need to update your information, please contact support."
        )
    else:
        # New user or incomplete registration
        welcome_text = (
            "👋 *Welcome to the Registration Bot!* \n\n"
            "Please select your preferred language:"
        )
    
    # Create language selection keyboard
    keyboard = ReplyKeyboardMarkup(resize_keyboard=True)
    for lang in languages.values():
        keyboard.add(KeyboardButton(text=lang))
    
    # Set initial state
    await state.set_state(form.language)
    await message.reply(
        welcome_text,
        reply_markup=keyboard,
        parse_mode='Markdown'
    )

@router.message(form.language)
async def process_language(message: Message, state: FSMContext):
    """Process language selection with better validation"""
    # Map display names back to language codes
    reverse_languages = {v: k for k, v in languages.items()}
    selected_language = reverse_languages.get(message.text, message.text)
    
    if selected_language not in languages:
        await message.reply(
            "⚠️ *Please select a valid language from the options below.*",
            parse_mode='Markdown',
            reply_markup=language_keyboard
        )
        return
    
    # Update language in database
    db.update_user_data(message.from_user.id, language=selected_language)
    
    # Store language in state
    async with state.proxy() as data:
        data['language'] = selected_language
    
    # Get appropriate message based on selected language
    if selected_language == 'English':
        text = "👤 *Full Name*\n\nPlease enter your full name as it appears on official documents:"
    elif selected_language == 'Русский':
        text = "👤 *Полное имя*\n\nПожалуйста, введите ваше полное имя, как в документах:"
    else:  # Uzbek
        text = "👤 *To'liq ism*\n\nIltimos, hujjatlardagidek to'liq ismingizni kiriting:"
    
    await Form.next()
    await message.reply(
        text,
        reply_markup=ReplyKeyboardRemove(),
        parse_mode='Markdown'
    )

@router.message(form.full_name)
async def process_full_name(message: Message, state: FSMContext):
    """Process full name with validation"""
    full_name = message.text.strip()
    
    # Basic validation
    if len(full_name) < 2 or len(full_name) > 100:
        await message.reply(
            "⚠️ Please enter a valid full name (2-100 characters).\n"
            "Example: John Doe"
        )
        return
    
    # Store full name in state
    await state.update_data(full_name=full_name)
    
    # Ask for contact
    text = "📱 *Contact Information*\n\nPlease share your contact by pressing the button below."
    
    await message.reply(
        text,
        reply_markup=contact_keyboard,
        parse_mode='Markdown'
    )

@router.message(F.contact, form.contact)
async def process_contact(message: Message, state: FSMContext):
    """Process contact information with better UX"""
    contact = message.contact
    phone_number = contact.phone_number or ''
    
    # Store contact info in state
    await state.update_data(
        phone=phone_number,
        user_id=contact.user_id or message.from_user.id
    )
    
    # Get language from state
    data = await state.get_data()
    language = data.get('language', 'English')
    
    # Ask for English level
    if language == 'Russian':
        text = "🌐 *Уровень английского*\n\nПожалуйста, выберите ваш уровень английского:"
    elif language == 'Uzbek':
        text = "🌐 *Ingliz tili darajangiz*\n\nIltimos, ingliz tili darajangizni tanlang:"
    else:  # English
        text = "🌐 *English Level*\n\nPlease select your English level:"
    
    await message.reply(
        text,
        reply_markup=english_level_keyboard,
        parse_mode='Markdown'
    )
    
    # Move to next state
    await state.set_state(form.english_level)

@router.message(form.english_level)
async def process_english_level(message: Message, state: FSMContext):
    """Process English level with better validation"""
    # Get the selected level text
    selected_level_text = message.text
    
    # Debug logging
    print(f"Selected level text: {selected_level_text}")
    print(f"Available levels: {list(english_levels.values())}")
    
    # Check if the selected text matches any of our level display texts
    if selected_level_text not in english_levels.values():
        # If not, show error and ask again
        data = await state.get_data()
        language = data.get('language', 'English')
        
        if language == 'Russian':
            error_msg = "⚠️ *Пожалуйста, выберите уровень английского из предложенных вариантов.*"
        elif language == 'Uzbek':
            error_msg = "⚠️ *Iltimos, quyidagi darajalardan birini tanlang.*"
        else:  # English
            error_msg = "⚠️ *Please select a valid English level from the options below:*"
        
        await message.reply(
            error_msg,
            parse_mode='Markdown',
            reply_markup=english_level_keyboard
        )
        return
    
    # Update the state with the selected level
    async with state.proxy() as data:
        data['english_level'] = selected_level_text
        language = data.get('language', 'English')
    
    # Update in database
    db.update_user_data(message.from_user.id, english_level=selected_level_text)
    
    # Prepare age request message based on language
    if language == 'English':
        text = "🎂 *Age*\n\nPlease enter your age (12-100):"
    elif language == 'Русский':
        text = "🎂 *Возраст*\n\nПожалуйста, введите ваш возраст (12-100):"
    else:  # Uzbek
        text = "🎂 *Yosh*\n\nIltimos, yoshingizni kiriting (12-100):"
    
    # Move to age state and ask for age
    await Form.next()
    await message.reply(
        text,
        reply_markup=ReplyKeyboardRemove(),
        parse_mode='Markdown'
    )

    try:
        age = int(message.text.strip())
        if age < 12 or age > 120:
            raise ValueError("Age out of range")
            
        # Store age in state
        await state.update_data(age=age)
        data = await state.get_data()
        language = data.get('language', 'English')
        
        # Ask if user has a team
        if language == 'Russian':
            text = ("👥 *Команда*\n\n"
                   "У вас уже есть команда? Если да, введите название команды. "
                   "Если нет, нажмите кнопку 'Нет команды'.")
        elif language == 'Uzbek':
            text = ("👥 *Jamoa*\n\n"
                   "Sizda jamoangiz bormi? Agar ha, jamoa nomini kiriting. "
                   "Agar yo'q bo'lsa, 'Jamoam yo\'q' tugmasini bosing.")
        else:  # English
            text = ("👥 *Team*\n\n"
                   "Do you already have a team? If yes, enter your team name. "
                   "If not, click 'No Team'.")
        
        # Create keyboard
        keyboard = ReplyKeyboardMarkup(resize_keyboard=True)
        if language == 'Russian':
            keyboard.add(KeyboardButton(text='Нет команды'))
        elif language == 'Uzbek':
            keyboard.add(KeyboardButton(text='Jamoam yo\'q'))
        else:  # English
            keyboard.add(KeyboardButton(text='No Team'))
        
        await message.reply(
            text,
            reply_markup=keyboard,
            parse_mode='Markdown'
        )
        
        # Move to next state
        await state.set_state(form.has_team)
        
    except ValueError:
        # Get language for error message
        data = await state.get_data()
        return

@router.message(form.has_team)
async def process_has_team(message: Message, state: FSMContext):
    """Process team choice"""
    data = await state.get_data()
    language = data.get('language', 'English')
    
    # Check response
    user_response = message.text.lower()
    
    if any(word in user_response for word in ['no', 'нет', 'yo\'q']):
        # No team, complete registration
        await complete_registration(message, state)
    else:
        # User wants to enter a team name
        if language == 'Russian':
            text = "🏷 *Название команды*\n\nВведите название вашей команды:"
        elif language == 'Uzbek':
            text = "🏷 *Jamoa nomi*\n\nJamoangiz nomini kiriting:"
        else:  # English
            text = "🏷 *Team Name*\n\nPlease enter your team name:"
            
        await message.reply(
            text,
            reply_markup=ReplyKeyboardRemove(),
            parse_mode='Markdown'
        )
        
        # Move to team name state
        await state.set_state(form.team_name)

@router.message(form.team_name)
async def process_team_name(message: Message, state: FSMContext):
    """Process team name and ask if they want to add team members"""
    team_name = message.text.strip()
    
    # Basic validation
    if len(team_name) < 2 or len(team_name) > 50:
        await message.reply("⚠️ Please enter a valid team name (2-50 characters).")
        return
    
    # Store team name in state
    await state.update_data(team_name=team_name)
    data = await state.get_data()
    language = data.get('language', 'English')
    
    # Ask if they want to add team members
    if language == 'Russian':
        text = (f"✅ *Команда сохранена: {team_name}*\n\n"
               "Хотите добавить участников команды?\n"
               "\nВы можете добавить до 2 человек в свою команду.")
        keyboard = ReplyKeyboardMarkup(resize_keyboard=True)
        keyboard.add(KeyboardButton(text='✅ Да, добавить'), KeyboardButton(text='❌ Нет, только я'))
    elif language == 'Uzbek':
        text = (f"✅ *Jamoa saqlandi: {team_name}*\n\n"
               "Jamoa a'zolarini qo'shmoqchimisiz? (Maksimal 2 ta qo'shimcha a'zo)\n"
               "\nJamoaingizga yana 2 kishigacha qo'shishingiz mumkin.")
        keyboard = ReplyKeyboardMarkup(resize_keyboard=True)
        keyboard.add(KeyboardButton(text="✅ Ha, qo'shaman"), KeyboardButton(text="❌ Yo'q, faqat men"))
    else:  # English
        text = (f"✅ *Team saved: {team_name}*\n\n"
               "Would you like to add team members?\n"
               "\nYou can add up to 2 people to your team.")
        keyboard = ReplyKeyboardMarkup(resize_keyboard=True)
        keyboard.add(KeyboardButton(text='✅ Yes, add members'), KeyboardButton(text='❌ No, just me'))
    
    await state.set_state(form.add_another_member)
    await message.reply(
        text,
        reply_markup=keyboard,
        parse_mode='Markdown'
    )

@router.message(form.team_member_name)
async def process_team_member_name(message: Message, state: FSMContext):
    """Process team member information (name and phone in one message)"""
    input_text = message.text.strip()
    
    # Get language from state
    """Process whether to add team members or complete registration"""
    # Get language from state
    data = await state.get_data()
    language = data.get('language', 'English')
    team_members = data.get('team_members', [])
    
    # Check user response
    user_response = message.text.lower()
    
    # Check for positive responses in different languages
    positive_responses = ['yes', 'да', 'ha', 'y', 'д', 'х', 'add', 'qo\'shish', 'добавить']
    negative_responses = ['no', 'нет', 'yo\'q', 'n', 'н', 'й', 'stop', 'стоп', 'to\'xtatish']
    
    if any(resp in user_response for resp in positive_responses):
        # User wants to add another member
        if language == 'Russian':
            text = ("👤 *Добавление участника*\n\n"
                   "Пожалуйста, введите имя и номер телефона участника "
                   "в формате:\n\n"
                   "Имя, +1234567890\n"
                   "или по отдельности (сначала имя, затем номер)")
        elif language == 'Uzbek':
            text = ("👤 *Jamoa a\'zosini qo\'shish*\n\n"
                   "Iltimos, jamoa a\'zosining ismi va telefon raqamini "
                   "quyidagi formatda kiriting:\n\n"
                   "Ism, +998901234567\n"
                   "yoki alohida-alohida (avval ism, keyin raqam)")
        else:  # English
            text = ("👤 *Add Team Member*\n\n"
                   "Please enter the team member's name and phone number "
                   "in the format:\n\n"
                   "Name, +1234567890\n"
                   "or separately (name first, then number)")
        
        await message.reply(
            text,
            reply_markup=ReplyKeyboardRemove(),
            parse_mode='Markdown'
        )
        await state.set_state(form.team_member_name)
        
    elif any(resp in user_response for resp in negative_responses):
        # User doesn't want to add more members
        await complete_registration(message, state)
        
    else:
        # Invalid response
        if language == 'Russian':
            error_msg = ("⚠️ Пожалуйста, ответьте 'Да' или 'Нет'."
                       "\n\nХотите добавить еще одного участника?")
async def notify_admin_about_registration(bot, user_data):
    """Send notification to admin about new registration"""
    if not ADMIN_IDS:
        return  # No admin IDs configured
        
    admin_id = ADMIN_IDS[0]  # Get the first admin ID
    
    # Prepare team info if exists
    team_info = ""
    if 'team_name' in user_data and user_data['team_name']:
        team_info = f"\n🏆 *Team:* {user_data['team_name']}"
        if 'team_members' in user_data and user_data['team_members']:
            team_info += "\n\n👥 *Team Members:*"
            for i, member in enumerate(user_data['team_members'], 1):
                team_info += f"\n{i}. {member.get('name', 'N/A')} - {member.get('phone', 'N/A')}"
    
    # Prepare message based on language
    language = user_data.get('language', 'English')
    
    if language == 'Russian':
        response = [
            "✨ *Новая регистрация!* ✨",
            "\n📋 *Данные пользователя:*",
            f"🌐 *Язык:* {user_data.get('language', 'Н/Д')}",
            f"👤 *Полное имя:* {user_data.get('full_name', 'Н/Д')}",
            f"📱 *Телефон:* {user_data.get('phone', 'Н/Д')}",
            f"📊 *Уровень английского:* {user_data.get('english_level', 'Н/Д')}",
            f"🎂 *Возраст:* {user_data.get('age', 'Н/Д')}",
            team_info.replace("Team:", "Команда:").replace("Team Members:", "Участники команды:")
        ]
    elif language == 'Uzbek':
        response = [
            "✨ *Yangi ro'yxatdan o'tish!* ✨",
            "\n📋 *Foydalanuvchi ma'lumotlari:*",
            f"🌐 *Til:* {user_data.get('language', 'Mavjud emas')}",
            f"👤 *To'liq ism:* {user_data.get('full_name', 'Mavjud emas')}",
            f"📱 *Telefon:* {user_data.get('phone', 'Mavjud emas')}",
            f"📊 *Ingliz tili darajasi:* {user_data.get('english_level', 'Mavjud emas')}",
            f"🎂 *Yosh:* {user_data.get('age', 'Mavjud emas')}",
            team_info.replace("Team:", "Jamoa:").replace("Team Members:", "Jamoa a'zolari:")
        ]
    else:  # English
        response = [
            "✨ *New Registration!* ✨",
            "\n📋 *User Details:*",
            f"🌐 *Language:* {user_data.get('language', 'N/A')}",
            f"👤 *Full Name:* {user_data.get('full_name', 'N/A')}",
            f"📱 *Phone:* {user_data.get('phone', 'N/A')}",
            f"📊 *English Level:* {user_data.get('english_level', 'N/A')}",
            f"🎂 *Age:* {user_data.get('age', 'N/A')}",
            team_info
        ]
    
    # Send message to admin
    try:
        await bot.send_message(
            chat_id=admin_id,
            text='\n'.join([line for line in response if line]),
            parse_mode='Markdown'
        )
    except Exception as e:
        print(f"Error sending notification to admin: {e}")
    
    # Finish the state if it was passed in user_data
    if 'state' in user_data:
        await user_data['state'].finish()

def is_admin(user_id):
    """Check if user is admin with improved type handling"""
    try:
        # Convert user_id to int for comparison
{{ ... }}
        user_id = int(user_id)
        
        # Convert all admin IDs to int for comparison
        admin_ids = [int(admin_id) for admin_id in ADMIN_IDS]
        
        # Check if user is admin
        is_admin_user = user_id in admin_ids
        
        # Debug logging
        print(f"\n🔍 Admin Check:")
        print(f"- User ID: {user_id} (type: {type(user_id)})")
        print(f"- ADMIN_IDS: {admin_ids} (types: {[type(x) for x in admin_ids]})")
        print(f"- Is Admin: {is_admin_user}")
        
        return is_admin_user
        
    except Exception as e:
        print(f"❌ Error in is_admin: {str(e)}")
        return False

@dp.message_handler(commands=['myid', 'debug'])
async def get_my_id(message: types.Message):
    """Get your Telegram user ID and debug info"""
    user = message.from_user
    
    # Get debug info
    debug_info = debug_admin_check(user.id)
    
    # Format response
    response = [
        "🔍 <b>Debug Information</b>\n",
        f"👤 <b>Your Telegram ID:</b> <code>{user.id}</code>",
        f"📝 <b>Username:</b> @{user.username or 'Not set'}",
        f"👋 <b>Name:</b> {user.first_name or ''} {user.last_name or ''}\n",
        "\n<b>Admin Check:</b>"
    ]
    
    if 'error' in debug_info:
        response.append(f"❌ Error: {debug_info['error']}")
    else:
        response.extend([
            f"• Your ID: {debug_info['user_id']} (type: {debug_info['user_type']})",
            f"• Admin IDs: {debug_info['admin_ids']}",
            f"• Admin ID types: {debug_info['admin_types']}",
            f"• Is admin: {'✅ Yes' if debug_info['is_admin'] else '❌ No'}",
            f"• Strict equality check: {debug_info['strict_equality']}\n",
            "\n💡 <i>If you're not an admin, make sure to add your ID to the ADMIN_IDS list in the code and restart the bot.</i>"
        ])
    
    # Send the response
    await message.reply("\n".join(response), parse_mode='HTML')
    
    # Additional debug info in console
    print("\n" + "="*50)
    print("DEBUG INFORMATION:")
    print(f"User ID: {user.id} (type: {type(user.id)})")
    """Export user data (admin only)"""
    if not is_admin(message.from_user.id):
        return
        
    # Create export keyboard
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="Export as CSV", callback_data="export_csv")],
        [InlineKeyboardButton(text="Export as Excel", callback_data="export_excel")]
    ])
    
    await message.reply(
        "📊 *Export Data*\n\n"
        "Select the format to export user data:",
        reply_markup=keyboard,
        parse_mode='Markdown'
    )

@router.message(Command('teams'))
async def list_teams(message: Message):
    """List all teams and their members with detailed information"""
    if not is_admin(message.from_user.id):
        await message.reply("❌ You don't have permission to view teams.")
        return
    
    try:
        # Show typing action
        await bot.send_chat_action(message.chat.id, 'typing')
        
        # Get all teams with their members
        teams = db.get_all_teams()
        
        if not teams:
            await message.reply("ℹ️ No teams found in the database.")
            return
        
        # Prepare the response
        response = "*🏆 TEAMS DIRECTORY*\n\n"
        
        # Process each team
        for team in teams:
            # Add team header
            response += f"🔹 *{team['team_name']}* (ID: {team['team_id']})\n"
            response += f"📅 Created: {team['created_at']}\n"
            response += f"👥 Members: {team['member_count']}/3\n\n"
            
            # Add team leader
            response += "*👑 Team Leader:*\n"
            response += f"• {team['leader_name']} ({team['leader_phone']})\n\n"
            
            # Add team members if any
            members = [m for m in team['members'] if m['user_id'] != team['leader_id']]
            if members:
                response += "*👥 Team Members:*\n"
                for i, member in enumerate(members, 1):
                    member_type = "(Registered User)" if member['user_id'] else "(External Member)"
                    response += f"{i}. {member['full_name']} - {member['phone_number']} {member_type}\n"
            
            response += "\n" + "─" * 40 + "\n\n"
        
        # Add summary statistics
        total_teams = len(teams)
        total_members = sum(team['member_count'] for team in teams)
        avg_members = total_members / total_teams if total_teams > 0 else 0
        
        # Get team size distribution
        size_distribution = {}
        for team in teams:
            size = team['member_count']
            size_distribution[size] = size_distribution.get(size, 0) + 1
        
        # Format size distribution
        size_distribution_str = ", ".join([f"{k}: {v}" for k, v in sorted(size_distribution.items())])
        
        response += "*📊 TEAM STATISTICS*\n\n"
        response += f"• Total Teams: {total_teams}\n"
        response += f"• Total Members: {total_members}\n"
        response += f"• Average Team Size: {avg_members:.1f}\n"
        response += f"• Team Size Distribution: {size_distribution_str}"
        
        # Send the response in chunks if too long
        if len(response) > 4000:
            chunks = [response[i:i+4000] for i in range(0, len(response), 4000)]
            for chunk in chunks:
                await message.answer(chunk, parse_mode='Markdown')
                await asyncio.sleep(0.5)  # Small delay between messages
        else:
            await message.answer(response, parse_mode='Markdown')
            
    except Exception as e:
        logging.exception("Error in list_teams:")
        await message.answer(f"❌ An error occurred while retrieving team information. Please try again later.")
        
        # Log the full error for debugging
        error_msg = f"Error in /teams command: {str(e)}\n\n"
        error_msg += f"User: {message.from_user.id} (@{message.from_user.username or 'no_username'})\n"
        error_msg += f"Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
        
        # Send error to admin if not in production
        if message.from_user.id in ADMIN_IDS:
            await message.answer(f"🔍 Debug Info:\n```\n{error_msg}\n```", parse_mode='Markdown')

@router.callback_query(text_startswith="export_")
async def process_export(callback_query: CallbackQuery):
    """Handle export format selection"""
    if not is_admin(callback_query.from_user.id):
        await callback_query.answer("🚫 Permission denied", show_alert=True)
        return
    
    export_type = callback_query.data.split('_')[1]
    
    await callback_query.answer("⏳ Preparing your export...")
    
    if export_type == 'csv':
        success, result = db.export_to_csv()
        if success:
            with open('users_export.csv', 'rb') as file:
                await bot.send_document(
                    chat_id=callback_query.from_user.id,
                    document=InputFile(file, filename='users_export.csv'),
                    caption="📊 Here's your CSV export!"
                )
            os.remove('users_export.csv')  # Clean up
        else:
            await bot.send_message(callback_query.from_user.id, f"❌ {result}")
    
    elif export_type == 'excel':
        success, result = db.export_to_excel()
        if success:
            with open('users_export.xlsx', 'rb') as file:
                await bot.send_document(
                    chat_id=callback_query.from_user.id,
                    document=InputFile(file, filename='users_export.xlsx'),
                    caption="📈 Here's your Excel export!"
                )
            os.remove('users_export.xlsx')  # Clean up
        else:
            await bot.send_message(callback_query.from_user.id, f"❌ {result}")
    
    await callback_query.message.edit_reply_markup(reply_markup=None)

@router.message(Command('user'))
async def view_user(message: Message):
    """View specific user data (admin only)"""
    if not is_admin(message.from_user.id):
        return
        
    try:
        # Extract user ID from command arguments
        args = message.text.split()[1:]  # Skip the command itself
        if not args:
            await message.reply("Please provide a user ID. Example: /user 123456789")
            return
            
        user_id = int(args[0])
        user = db.get_user(user_id)
        
        if not user:
            await message.reply(f"User with ID {user_id} not found.")
            return
            
        # Format user data
        response = [
            f"👤 *User Information*\n",
            f"*ID:* `{user['user_id']}`",
            f"*Name:* {user.get('full_name', 'N/A')}",
            f"*Phone:* {user.get('phone', 'N/A')}",
            f"*English Level:* {user.get('english_level', 'N/A')}",
            f"*Age:* {user.get('age', 'N/A')}",
            f"*Team:* {user.get('team_name', 'No team')}",
            f"*Registration Date:* {user.get('registration_date', 'N/A')}"
        ]
        
        await message.reply("\n".join(response), parse_mode='Markdown')
        
    except (ValueError, IndexError):
        await message.reply("Invalid user ID. Please provide a valid numeric user ID.")
    except Exception as e:
        await message.reply(f"An error occurred: {str(e)}")

@router.message(Command('stats'))
async def show_stats(message: Message):
    """Show bot statistics (admin only)"""
    if not is_admin(message.from_user.id):
        return
        
    try:
        stats = db.get_statistics()
        
        response = [
            "📊 *Bot Statistics*\n",
            f"👥 Total Users: {stats.get('total_users', 0)}",
            f"📅 New Users (Last 24h): {stats.get('new_users_24h', 0)}",
            f"🏆 Total Teams: {stats.get('total_teams', 0)}",
            f"📈 Active Users (Last 7d): {stats.get('active_users_7d', 0)}",
            "\n*Language Distribution:*"
        ]
        
        # Add language stats if available
        for lang, count in stats.get('languages', {}).items():
            response.append(f"- {lang}: {count}")
            
        await message.reply("\n".join(response), parse_mode='Markdown')
        
    except Exception as e:
        await message.reply(f"❌ Error generating statistics: {str(e)}")
        "🌍 <b>Users by language:</b>"
    ]
    
    for lang, count in language_counts.items():
        response.append(f"• {lang}: <b>{count}</b>")
    
    # Add user list (first 20 users to avoid message being too long)
    response.append("\n👤 <b>Recent Users:</b>")
    response.extend(user_list[:20])
    
    if len(user_list) > 20:
        response.append(f"\n... and {len(user_list) - 20} more users")
    
    response.append("\n\nℹ️ Use <code>/user USER_ID</code> to view detailed information about a specific user.")
    response.append("Example: <code>/user 123456789</code>")
    
    await message.reply("\n".join(response), parse_mode='HTML')

async def main():
    # Start the bot
    logging.info("Starting bot...")
    try:
        await dp.start_polling(bot, skip_pending=True)
    except Exception as e:
        print(f"\n❌ Error: {str(e)}")
        raise
    finally:
        # Close the database connection when the bot stops
        db.close()
        print("🔒 Database connection closed")

if __name__ == '__main__':
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n🛑 Bot stopped by user")
    except Exception as e:
        print(f"\n❌ Error: {str(e)}")
