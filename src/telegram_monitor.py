import manage_shelve
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
from telethon.tl.types import PeerChannel
from telethon import functions

from telegram import Update, Bot
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, filters, ContextTypes
from telegram.error import TelegramError

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
        self.channel_ids = self.load_channels(config_file, channel_params)

        self.telegram_token = config_file['api_token']
        self.telegram_chat_id = config_file['telegram_chat_id']        

        self.api_id = float(config_file['api_id'])
        self.api_hash = config_file['api_hash']
        self.client = TelegramClient('mz', self.api_id, self.api_hash)
        self.is_running = True  # Vlag om de bot netjes te stoppen

    def load_channels(self, config_file, channel_params):
        # Laad de channels uit de config file
        channels = config_file['channels']

        # Als er geen channels zijn opgegeven, geef dan alle channels terug
        if not channel_params:
            return [channel['id'] for channel in channels]

        # Filter de channels op basis van de opgegeven channel_params
        filtered_channels = [
            channel['id'] for channel in channels
            if channel['param_name'] in channel_params
        ]

        return filtered_channels
    
    async def send_bot_message(self, message):
        bot = Bot(token=self.telegram_token)
        try:
            await bot.send_message(chat_id=self.telegram_chat_id, text=message)
            logger.info("Bot message sent successfully.")
        except TelegramError as e:
            logger.error(f"Failed to send the bot message: {e}")    
    
    async def load_messages_from_channel(self, channel, limit=10):
        try:
            entity = await self.client.get_entity(channel)
            print(f"Fetching messages from: {entity.username}")

            async for message in self.client.iter_messages(entity, limit=limit):
                timestamp = message.date.strftime('%Y-%m-%d %H:%M:%S')
                print(f"[{timestamp}] {message.sender_id}: {message.text}")

        except Exception as e:
            print(f"Error fetching messages from {channel}: {e}")

    async def handle_edited_message(self, event):
        message = event.message.text
        messageId = event.message.id
        channelName = event.chat.title or event.chat.username
        channelNameStripped = channelName.encode('ascii', 'ignore').decode('ascii').strip()

        parser = get_parser(channelNameStripped)
        message_stripped = parser.clean_message(message).encode('ascii', 'ignore').decode('ascii').strip()

        existing_message = manage_shelve.get_item(manage_shelve.SIGNALS_DB, str(messageId))
        if existing_message:
            last_existing_message = existing_message[len(existing_message) - 1]
            if last_existing_message != message_stripped:
                existing_message.append(message_stripped)
                manage_shelve.store_data(manage_shelve.SIGNALS_DB, str(messageId), existing_message)
                await self.send_bot_message(
                    f"Een bestaand trade signal in '{channelNameStripped}' "
                    f"werd zojuist aangepast!\n"
                    f"New value:\n{message_stripped}\n"
                    f"Old value:\n{last_existing_message}"
                )
                
                logger.info(f"A trade message (ID: {messageId}) was edited.")
                logger.info(f"Old value: \n{existing_message}")
                logger.info(f"New value: \n{message_stripped}")

    async def handle_new_message(self, event):
        message = event.message.text
        messageId = event.message.id
        channelName = event.chat.title or event.chat.username
        channelNameStripped = channelName.encode('ascii', 'ignore').decode('ascii').strip()

        parser = get_parser(channelNameStripped)
        message_stripped = parser.clean_message(message).encode('ascii', 'ignore').decode('ascii').strip()

        try:
            tradeSignal = parser.parse_trade_signal(message_stripped)
            manage_shelve.store_data(manage_shelve.SIGNALS_DB, str(messageId), [message_stripped])
            logger.info(f"=============================================================")
            logger.info(f"Received a valid trade signal in '{channelNameStripped}' :\n{message_stripped}")
            logger.info(f'Created a trade signal:\n{tradeSignal}')
            logger.info(f"=============================================================")
            await self.send_bot_message(f"Trade signal \n{tradeSignal} gevormd voor bericht \n{message_stripped}.")
            self.tradingbot.start_order_entry_process(tradeSignal, self.strategy)
        except ValueError as e:
            if channelNameStripped == 'GTMO VIP':
                # check if it's an update on a sl or tp levl
                if message_stripped.lower().startswith('adjust sl'):
                    await self.send_bot_message(f"Adjusting SL: \n'{message_stripped}'!")
                    logger.info(f"Adjusting SL: \n'{message_stripped}")
                else:
                    logger.info(f"Skipping irrelevant message in {channelNameStripped}.")
            elif channelNameStripped == 'Forex Signals - 1000 pip Builder':
                if message_stripped.startswith('The 1:1 Risk:Reward Target has been reached'):
                    await self.send_bot_message(f"Adjusting stop losses for 1000 pip builder: \n{message_stripped}!")
                    logger.info(f"Adjusting SL is justified for 1000 pip builder: \n{message_stripped}")
            else:
                logger.info(f"Skipping irrelevant message.")
                # print('stripped message: \n' + message_stripped)

    async def force_update(self):
        """Force updates for all configured channels."""
        print("Forcing updates for all channels...")
        for channel in self.channel_ids:
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
        dialogs = await self.client.get_dialogs() # refresh/update cache
        logger.info(f"Monitoring channels: {', '.join(str(channel_id) for channel_id in self.channel_ids)}")

        # Schedule periodic updates
        # 20241222: disable for a while
        # asyncio.create_task(self.periodic_force_update())

        # just force tradingbot to start 
        # self.tb.start_process()

        async with self.client:
            for channel in self.channel_ids:
                await self.client.get_input_entity(channel)

            self.client.add_event_handler(self.handle_new_message, events.NewMessage(chats=self.channel_ids))
            self.client.add_event_handler(self.handle_edited_message, events.MessageEdited(chats=self.channel_ids))

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

