# Ibrat Quiz Bot

A Telegram bot for managing quiz participants and teams with multi-language support and admin panel.

## Features

- Multi-language support (English, Uzbek, Russian)
- Team registration and management
- Admin panel for user management
- Data export functionality
- Form-based data collection with validation
- Webhook support for production

## Prerequisites

- Python 3.11+
- pip (Python package manager)
- A Telegram bot token from [@BotFather](https://t.me/botfather)

## Local Development

1. Clone the repository
2. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```
3. Create a `.env` file with your configuration:
   ```
   BOT_TOKEN=your_bot_token_here
   CHANNEL_USERNAME=@your_channel_username
   ```
4. Run the bot:
   ```bash
   python main.py
   ```

## Deployment on Railway

[![Deploy on Railway](https://railway.app/button.svg)](https://railway.app/new/template?template=YOUR_RAILWAY_TEMPLATE_ID&envs=BOT_TOKEN,CHANNEL_USERNAME&optionalEnvs=CHANNEL_USERNAME)

1. Click the "Deploy on Railway" button above or create a new Railway project manually
2. Add the following environment variables:
   - `BOT_TOKEN`: Your Telegram bot token
   - `CHANNEL_USERNAME`: Your Telegram channel username (optional)
   - `ADMIN_IDS`: Comma-separated list of admin Telegram user IDs (optional)
3. Deploy the application
4. Set the webhook URL in your bot's settings (if not automatically set):
   ```
   https://your-railway-url.railway.app/webhook/YOUR_BOT_TOKEN
   ```

## Environment Variables

| Variable | Required | Description |
|----------|----------|-------------|
| `BOT_TOKEN` | Yes | Your Telegram bot token from @BotFather |
| `CHANNEL_USERNAME` | No | Username of your Telegram channel (with @) |
| `ADMIN_IDS` | No | Comma-separated list of admin Telegram user IDs |
| `WEBHOOK_URL` | No | Base URL for webhook (automatically set on Railway) |

## Admin Commands

- `/admin` - Show admin panel
- `/stats` - Show registration statistics
- `/export` - Export user data
- `/teams` - List all registered teams

## License

MIT

1. Clone this repository or download the files
2. Install the required packages:
   ```
   pip install -r requirements.txt
   ```
3. Create a `.env` file in the project root and add your bot token:
   ```
   BOT_TOKEN=your_bot_token_here
   ```
   Replace `your_bot_token_here` with the token you got from @BotFather

## Running Locally

1. Make sure you've completed the installation steps above
2. Run the bot:
   ```
   python bot.py
   ```
3. The bot should now be running and respond to the /start command

## Deployment

For 24/7 uptime, you can deploy your bot to a cloud server. Here are some options:

### Option 1: PythonAnywhere (Free tier available)
1. Create an account at [PythonAnywhere](https://www.pythonanywhere.com/)
2. Upload your files using the web interface or Git
3. Set up a web app with Flask
4. In the web app configuration, point it to your `bot.py` file
5. Set up environment variables in the web app settings
6. The bot will run continuously

### Option 2: VPS (e.g., DigitalOcean, Linode, AWS EC2)
1. Set up a Linux server (Ubuntu 20.04 recommended)
2. Install Python and required packages:
   ```
   sudo apt update
   sudo apt install python3-pip python3-venv
   ```
3. Clone your repository or upload files
4. Create a virtual environment and install requirements:
   ```
   python3 -m venv venv
   source venv/bin/activate
   pip install -r requirements.txt
   ```
5. Install a process manager like PM2:
   ```
   npm install -g pm2
   pm2 start bot.py --interpreter=python3 --name="telegram-bot"
   pm2 startup
   pm2 save
   ```
6. Set up Nginx as a reverse proxy if needed

## Usage

1. Start a chat with your bot on Telegram
2. Send the `/start` command
3. Follow the bot's prompts to complete the registration

## Data Storage

This bot currently stores user data in memory (a Python dictionary). For a production environment, you should:

1. Use a proper database (e.g., PostgreSQL, SQLite, MongoDB)
2. Implement proper data validation and sanitization
3. Add error handling for database operations

## License

MIT License - feel free to use this code for any purpose.
