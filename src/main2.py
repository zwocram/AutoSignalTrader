import logging
import json
import re
from telegram import Update
from telegram.ext import Application, MessageHandler, filters, ContextTypes

# Enable logging
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO
)
logger = logging.getLogger(__name__)

# Load configuration
with open("config.json", "r") as config_file:
    config = json.load(config_file)

CHANNELS = config["channels"]  # List of channel usernames (e.g., ["channel_1", "channel_2"])
PATTERN = config["pattern"]  # Regex pattern to match messages
TOKEN = config["api_token"]

# Function to monitor specific channels and parse messages
async def monitor_channels(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Monitor messages from specific channels and parse for a pattern."""
    print('THIS METHOD IS CALLED')
    chat_username = update.effective_chat.username  # Get the username of the chat
    message_text = update.message.text  # Get the message text
    print(f"Message from {chat_username}: {message_text}")

    # Check if the message is from one of the monitored channels
    if chat_username in CHANNELS:
        # Check if the message matches the regex pattern
        if re.search(PATTERN, message_text):
            # Print the matched message to the console (or take other actions)
            logger.info(f"Matched message from @{chat_username}: {message_text}")
            await update.message.reply_text(f"Matched message: {message_text}")  # Optional: Reply in the channel

def main() -> None:
    """Start the bot."""
    # Create the Application and pass it your bot's token.
    application = Application.builder().token(TOKEN).build()

    # Add a handler to process all text messages
    application.add_handler(MessageHandler(filters.ALL, monitor_channels))

    # Run the bot until the user presses Ctrl-C
    application.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == "__main__":
    main()
