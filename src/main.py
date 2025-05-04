import json
import asyncio
import signal
import os, sys
import pdb
import contextlib
import logger_setup
import argparse
import sys
import MetaTrader5 as mt5
from mt5handler import MT5Scheduler
from strategy import Strategy
from telegram_monitor import ChannelMonitor

logger = logger_setup.LoggerSingleton.get_logger()

def get_strategy_params(config, connection_name):
    strategy_name_from_connection = config['mt5_connections'].get(connection_name)['strategy']
    strategy_params = config['strategies'][strategy_name_from_connection]
    
    return strategy_params
    

def get_mt5_credentials(config, connection_name):
    mt5_connection = config['mt5_connections'].get(connection_name)
    if mt5_connection:
        return mt5_connection['login'], mt5_connection['password'], mt5_connection['server']
    else:
        raise ValueError(f'Geen verbinding gevonden met de naam: {connection_name}')

# suppress terminal output for wine programs
@contextlib.contextmanager
def suppress_output():
    with open(os.devnull, 'w') as fnull:
        with contextlib.redirect_stdout(fnull), contextlib.redirect_stderr(fnull):
            logger.info("suppressing....")
            yield

async def run_channel(channel_monitor):
    await channel_monitor.start_monitoring()

# experimental
async def run_mt5_scheduler(mt5):
    mt5_data_fetcher = MT5Scheduler(mt5)
    await mt5_data_fetcher.start()

def main():

    logger = logger_setup.LoggerSingleton.get_logger()

    with open('config.json', 'r') as config_file:
        config = json.load(config_file)

    available_connections = ', '.join(config['mt5_connections'].keys())
    available_channels = ', '.join(channel['param_name'] for channel in config['channels'])
    
    # Argument parser instellen
    parser = argparse.ArgumentParser(description='MT5 Connection')

    parser.add_argument(
        '--connection',
        type=str,
        required=True,  # Maak dit argument verplicht
        help=f'De MT5 connection name (available: {available_connections}).'
    )
    parser.add_argument(
        '--channels', 
        type=str, 
        nargs='*', 
        help=f'Channels to monitor (space-separated). Available: {available_channels}'
    )

    args = parser.parse_args()

    # Maak een MT5Connection object aan
    login, password, server = get_mt5_credentials(config, args.connection)

    strategy_params = get_strategy_params(config, args.connection)
    strategy = Strategy(**strategy_params)

    try:
        channel_monitor = ChannelMonitor(config, mt5, strategy, args.channels)
    except ValueError as e:
        logger.error(f'{e}')
        sys.exit(1)

    # Start de MT5 terminal
    if not mt5.initialize():
        logger.info("initialize mt5 failed")
        logger.info(mt5.last_error())
        mt5.shutdown()
        exit()

    if mt5.login(int(login), password=password, server=server):
        logger.info("Ingelogd op account:")
    else:
        logger.info("Inloggen mislukt. Fout:", mt5.last_error())

    # Start the telegram channel monitor
    logger.info('Starting the channel monitor.')

    loop = asyncio.get_event_loop()

    async def run_channel():
        await channel_monitor.start_monitoring()

    def connect():
        try:
            loop.run_until_complete(run_channel())
        except KeyboardInterrupt:
            logger.info("KeyboardInterrupt received. Exiting...")
        except ConnectionError as e:
            logger.info('Connection error, trying to reconnect...')
            connect()
        except ConnectionRefusedError as e:
            logger.info('Connection refused error, trying to reconnect...')
            connect()
        finally:
            loop.close()
            logger.info("Trading bot stopped.")

    connect()

    # Signal handler registreren
    def handle_signal(signum, frame):
        print(f"Signal {signum} received. Shutting down...")
        loop.create_task(channel_monitor.graceful_shutdown())  # Voeg de coroutine toe aan de eventloop
        loop.stop()  # Stop de hoofdloop netjes

    # Signal handlers instellen
    signal.signal(signal.SIGINT, handle_signal)
    signal.signal(signal.SIGTERM, handle_signal)

if __name__ == "__main__":
    main()
