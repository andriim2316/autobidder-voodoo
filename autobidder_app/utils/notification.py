import logging
from aiogram import Bot
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from decouple import config

# Configure logging
logger = logging.getLogger("telegram_bot")

# Load environment variables
TOKEN = config("TELEGRAM_TOKEN")
GROUP_CHAT_ID = int(config("GROUP_CHAT_ID"))

# Initialize Telegram Bot
bot = Bot(TOKEN)

async def send_bet_exceeded_message(domain_name, current_bet, max_bet, domain_id):
    """Send a Telegram notification when a bet exceeds the maximum allowed."""
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="Cancel Bet", callback_data=f"cancel_{domain_id}")],
        [InlineKeyboardButton(text="+ 100 UAH", callback_data=f"increase_100_{domain_id}_{current_bet}")],
        [InlineKeyboardButton(text="+ 1000 UAH", callback_data=f"increase_1000_{domain_id}_{current_bet}")]
    ])

    async with bot:  # Ensures proper session management
        await bot.send_message(
            GROUP_CHAT_ID,
            f"⚠️ Current bet ({current_bet} UAH) exceeds our max bet ({max_bet} UAH).\n"
            f"Domain: {domain_name}\nWhat would you like to do?",
            reply_markup=keyboard
        )

    logger.info(f"Notification sent for {domain_name} (ID: {domain_id})")