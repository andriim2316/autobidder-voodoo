
import requests
from aiogram import Bot, Dispatcher, types
from decouple import config
from aiogram.filters import Command

from autobidder_app.management.commands.make_bets import run_bet_processing
import asyncio
from concurrent.futures import ThreadPoolExecutor

from autobidder_app.utils.logger import setup_logger

# loggins
logger = setup_logger("telegram", log_directory="logs/telegram", days=7)

TOKEN = config("TELEGRAM_TOKEN")
GROUP_CHAT_ID = int(config("GROUP_CHAT_ID"))
BASE_URL = config("BASE_URL", default="http://127.0.0.1:8000")

bot = Bot(TOKEN)
dp = Dispatcher()

async def test_command_handler(message: types.Message):
    if message.chat.id != GROUP_CHAT_ID:
        return

    await message.reply(f"✅ The bot is working correctly! Your chat ID: {message.chat.id}")


executor = ThreadPoolExecutor()

@dp.callback_query()
async def handle_callback_query(callback_query: types.CallbackQuery):
    """Handle inline button clicks for bidding, updating, or deleting bets."""
    callback_data = callback_query.data
    logger.info(f"Received callback: {callback_data}")

    try:
        parts = callback_data.split("_")
        action = parts[0]
        response_text = "⚠️ Unknown response."

        if action == "increase":
            if len(parts) != 4:
                logger.error(f"Invalid callback format: {callback_data}")
                await callback_query.answer("❌ Error: Invalid format.")
                return

            amount = int(parts[1])
            domain_id = int(parts[2])
            current_bet = int(parts[3])
            new_max_bet = current_bet + amount

            # Extract domain name from message text
            message_text = callback_query.message.text
            domain_name = next(
                (line.split(":")[-1].strip() for line in message_text.split("\n") if "Domain:" in line),
                f"ID {domain_id}"
            )

            logger.info(f"Increasing bet for {domain_name} (Domain ID: {domain_id}) by {amount}, New max bet: {new_max_bet}")

            # Send max bet update request
            response = requests.post(
                f"{BASE_URL}/update-max-bet/{domain_id}/",
                data={"max_bet": new_max_bet}
            )
            logger.info(f"Update response: {response.status_code}, {response.text}")

            if response.status_code == 200:
                response_text = f"✅ Bet updated to {new_max_bet} UAH for {domain_name}."

                loop = asyncio.get_running_loop()
                await loop.run_in_executor(executor, run_bet_processing, domain_id)

            else:
                response_text = f"❌ Failed to update bet. Server error: {response.text}"

        elif action == "cancel":
            domain_id = int(parts[1])
            response = requests.post(f"{BASE_URL}/delete-bet/{domain_id}/")
            response_text = f"🗑 Bet deleted." if response.status_code == 200 else f"❌ Delete failed: {response.text}"

        # Send response to user
        await callback_query.message.edit_text(response_text, reply_markup=None)
        await callback_query.answer()

    except Exception as e:
        logger.error(f"Callback handler error: {e}", exc_info=True)
        await callback_query.answer("⚠️ An error occurred. Check logs.")



async def main():
    dp.message.register(test_command_handler, Command("test"))
    dp.callback_query.register(handle_callback_query)
    await dp.start_polling(bot)