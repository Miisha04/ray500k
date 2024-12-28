import asyncio
import logging
import sys
from io import StringIO
from aiogram import Bot, Dispatcher, types, exceptions
from aiogram.enums import ParseMode
from aiogram.filters import Command
from aiogram.client.bot import DefaultBotProperties
from chainstack_ws_handler import connect_chainstack_ws
from config import TELEGRAM_TOKEN

# Global variables
subscribers = set()  # Set of all subscribed chat IDs
is_bot_active = False  # Tracks if the bot is active

# Setting up the bot and dispatcher
bot = Bot(
    token=TELEGRAM_TOKEN,
    default=DefaultBotProperties(parse_mode=ParseMode.HTML)
)
dp = Dispatcher()

# Setup logger
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger("TelegramBot")


async def send_message_to_telegram(message: str):
    """Send a message to all subscribed Telegram bot chats."""
    if not subscribers:
        return

    for chat_id in subscribers:
        try:
            await bot.send_message(chat_id, message)
        except exceptions.TelegramAPIError as e:
            logger.error(f"Failed to send message to chat {chat_id}: {e}")


class TelegramConsoleRedirector(StringIO):
    """Redirect `sys.stdout` and `sys.stderr` to both console and Telegram."""

    def write(self, message):
        """Send the output to both console and Telegram."""
        if message.strip():  # Ignore empty messages
            sys.__stdout__.write(message)  # Standard console output
            asyncio.create_task(send_message_to_telegram(message))


# Redirect console output
sys.stdout = TelegramConsoleRedirector()
sys.stderr = TelegramConsoleRedirector()


@dp.message(Command("start"))
async def start_command_handler(message: types.Message):
    """Handle /start command."""
    global subscribers, is_bot_active

    chat_id = message.chat.id
    if chat_id in subscribers:
        await message.reply("You are already subscribed to updates.")
        return

    subscribers.add(chat_id)
    await message.reply("You have subscribed to updates.")

    if not is_bot_active:
        is_bot_active = True
        await message.reply("Bot started. Monitoring for blockchain events...")
        asyncio.create_task(run_chainstack_ws())


@dp.message()
async def handle_messages(message: types.Message):
    """Handle all other messages."""
    if message.chat.id not in subscribers:
        return  # Ignore messages from non-subscribers
    await message.reply("Command not recognized. Use /start to subscribe to updates.")


async def run_chainstack_ws():
    """Run the connect_chainstack_ws function and log outputs to Telegram."""
    try:
        await connect_chainstack_ws()
    except Exception as e:
        logger.error(f"Error in connect_chainstack_ws: {e}")


async def main():
    """Main entry point to run the bot."""
    logging.info("Starting Telegram bot...")
    await bot.delete_webhook(drop_pending_updates=True)
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
