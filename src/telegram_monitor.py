import json
import re
import asyncio
import signal
import tradingbot
import logger
import pdb
import logger_setup
from tradesignalparser import TradeSignalParser1000PipBuilder, get_parser
from telethon.sync import TelegramClient, events
from telethon.errors import FloodWaitError

from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, filters, ContextTypes

from datetime import datetime

logger = logger_setup.LoggerSingleton.get_logger()

class MessageFilter:
    pass

class ChannelMonitor:

    def __init__(self, config_file, mt5, strategy, channel_params):
        self.tb = tradingbot.ProcessTradeSignal(mt5)
        self.mt5 = mt5
        self.strategy = strategy
        self.tradingbot = tradingbot.ProcessTradeSignal(mt5)
        self.channel_usernames = self.load_channels(config_file, channel_params)
        

        self.api_id = float(config_file['api_id'])
        self.api_hash = config_file['api_hash']
        self.client = TelegramClient('mz', self.api_id, self.api_hash)
        self.is_running = True  # Vlag om de bot netjes te stoppen

    def load_channels(self, config_file, channel_params):
        # Laad de channels uit de config file
        channels = config_file['channels']

        # Als er geen channels zijn opgegeven, geef dan alle channels terug
        if not channel_params:
            return [channel['name'] for channel in channels]

        # Filter de channels op basis van de opgegeven channel_params
        filtered_channels = [
            channel['name'] for channel in channels
            if channel['param_name'] in channel_params
        ]

        return filtered_channels
    
    async def load_messages_from_channel(self, channel, limit=10):
        try:
            entity = await self.client.get_entity(channel)
            print(f"Fetching messages from: {entity.username}")

            async for message in self.client.iter_messages(entity, limit=limit):
                timestamp = message.date.strftime('%Y-%m-%d %H:%M:%S')
                print(f"[{timestamp}] {message.sender_id}: {message.text}")

        except Exception as e:
            print(f"Error fetching messages from {channel}: {e}")

    async def handle_new_message(self, event):
        message = event.message.message
        channelName = event.chat.title or event.chat.username

        parser = get_parser(channelName)
        message_stripped = parser.clean_message(message)

        try:
            tradeSignal = parser.parse_trade_signal(message)
            logger.info(f"=============================================================")
            logger.info(f"Received a valid trade signal in '{channelName}' :\n{message}")
            logger.info(f'Created a trade signal:\n{tradeSignal}')
            logger.info(f"=============================================================")
            self.tradingbot.start_order_entry_process(tradeSignal, self.strategy)
        except ValueError as e:
            logger.info(f"Received a nong tradeable message in '{channelName}' :\n{message}")

    async def force_update(self):
        """Force updates for all configured channels."""
        print("Forcing updates for all channels...")
        for channel in self.channel_usernames:
            try:
                entity = await self.client.get_entity(channel)
                if entity.username == "TopTradingSignalsvip":
                    print(f"Forcing update for {entity.username}")
                    await self.client.catch_up()  # Synchronize session state
            except FloodWaitError as e:
                print(f"FloodWaitError: Waiting for {e.seconds} seconds before retrying...")
                await asyncio.sleep(e.seconds)
            except Exception as e:
                print(f"Error forcing update for {channel}: {e}")

    async def start_monitoring(self):
        await self.client.start()
        logger.info(f"Monitoring channels: {', '.join(self.channel_usernames)}")

        # Schedule periodic updates
        # 20241222: disable for a while
        # asyncio.create_task(self.periodic_force_update())

        # just force tradingbot to start 
        # self.tb.start_process()

        async with self.client:
            for channel in self.channel_usernames:
                await self.client.get_entity(channel)

            self.client.add_event_handler(self.handle_new_message, events.NewMessage(chats=self.channel_usernames))

            # Houd de hoofdloop actief en controleer de vlag
            while self.is_running:
                await asyncio.sleep(1)

    async def periodic_force_update(self, interval=300):
        """Periodically force updates every `interval` seconds."""
        while self.is_running:  # Controleer de vlag
            await self.force_update()
            await asyncio.sleep(interval)

    async def graceful_shutdown(self):
        """Zorg voor een nette afsluiting."""
        print("Shutting down TelegramTrader...")
        self.is_running = False  # Zet de vlag op False
        self.mt5.shutdown()

        await self.client.disconnect()  # Ontkoppel de Telegram-client
        print("Client disconnected. Goodbye!")

class BotMonitor:

    message_filter = MessageFilter()

    def __init__(self, token: str, mt5):
        self.token = token
        self.application = ApplicationBuilder().token(self.token).build()
        self.mt5 = mt5

    async def start(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        await update.message.reply_text('Hello! You can forward messages to me.')

    async def handle_message(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        # Get the text of the forwarded message
        
        message_text = update.message.text

        parser = get_parser()

        # Parse the message and perform actions
        if message_text:
            await update.message.reply_text(f'Receive message:\n{message_text}')
            message_stripped = parser.clean_message(message_text)
            logger.info(f'Message received by the bot:\n{message_stripped}')
            if parser.parse_message(message_text):
                logger.info(f'VALID trade signal.')
            else:
                logger.info('NOT a valid trade signal.')


    def start_bot_monitoring(self) -> None:
        # Add command and message handlers
        self.application.add_handler(CommandHandler("start", self.start))
        self.application.add_handler(MessageHandler(filters.TEXT & filters.FORWARDED, self.handle_message))

        # Start the bot
        self.application.run_polling()