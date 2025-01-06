import json
import asyncio
import signal
import os, sys
import pdb
import contextlib
import logger_setup
import argparse
import MetaTrader5 as mt5
from strategy import Strategy
from telegram_monitor import ChannelMonitor, BotMonitor

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

def main():

    with open('config.json', 'r') as config_file:
        config = json.load(config_file)

    logger = logger_setup.LoggerSingleton.get_logger()

    # Argument parser instellen
    parser = argparse.ArgumentParser(description='MT5 Connection')
    parser.add_argument('--connection', type=str, default='icmarkets-demo', 
                        help='De MT5 connection name (default: icmarkets-demo)')

    # Argumenten parseren
    args = parser.parse_args()

    # Maak een MT5Connection object aan
    login, password, server = get_mt5_credentials(config, args.connection)

    strategy_params = get_strategy_params(config, args.connection)
    strategy = Strategy(**strategy_params)

    # connect met MT5
    # mt5_connection = MT5Connection.get_instance(login, password)
    # mt5_connection.login(login, password)
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

    """
    Start the telegram channel monitor
    """
    logger.info('Starting the channel monitor.')

    channel_monitor = ChannelMonitor(config, mt5, strategy)

    loop = asyncio.get_event_loop()

    async def run_channel():
        await channel_monitor.start_monitoring()


    """
    Start the bot monitor
    """
    logger.info('Starting the bot monitor.')
    api_token = config.get('api_token')
    bot_monitor = BotMonitor(api_token, mt5)

    # loop_bot = asyncio.get_event_loop()

    # asyncio.run(bot_monitor.start_bot_monitoring())
    async def run_bot():
        await asyncio.gather(bot_monitor.start_bot_monitoring())

    # asyncio.run(runbots())
    try:
        loop.run_until_complete(run_channel())
    except KeyboardInterrupt:
        logger.info("KeyboardInterrupt received. Exiting...")
    finally:
        loop.close()
        logger.info("Trading bot stopped.")


    """
    asyncio.gather(
        bot_monitor.start_bot_monitoring(),
        channel_monitor.start_monitoring()
    )
    """

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
