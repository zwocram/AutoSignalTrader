import pdb
from datetime import datetime, timedelta
import asyncio
import MetaTrader5 as mt5
from logger_setup import LoggerSingleton

# Verkrijg de logger-instantie zonder log_file argument
logger = LoggerSingleton.get_logger()  # Gebruik de standaard log_file

class MT5Connection:
    _instance = None

    def __new__(cls, login=None, password=None, server=None):
        if cls._instance is None:
            cls._instance = super(MT5Connection, cls).__new__(cls)
            if not mt5.initialize():
                logger.warning("MetaTrader 5 kon niet worden geïnitialiseerd")
                raise Exception("MetaTrader 5 initialization failed")
        return cls._instance

    @staticmethod
    def get_instance(login=None, password=None, server=None):
        if MT5Connection._instance is None:
            MT5Connection(login, password, server)
        return MT5Connection._instance

    def login(self, login, password):

        if not mt5.login(int(login), password):
            error_code = mt5.last_error()  # Verkrijg de laatste fout
            logger.warning(f"Login mislukt: {error_code}")  # Log de foutmelding
            raise Exception(f"Login failed: {error_code}")
        logger.info("Login succesvol")

class MT5Handler:

    def __init__(self, mt5):
        # self.connection = MT5Connection.get_instance()  # Haal de singleton verbinding op
        self.mt5 = mt5

    def get_account_info(self):
        accountInfo = self.mt5.account_info()
        return accountInfo

    def get_open_positions(self):
        nrOpenPositions = self.mt5.positions_total()
        return nrOpenPositions

    def get_digts(self, symbol):
        nr_digits = self.mt5.symbol_info(symbol).digits
        return nr_digits

    def get_contract_size(self, symbol):
        trade_contract_size = self.mt5.symbol_info(symbol).trade_contract_size
        return trade_contract_size

    def get_minimal_volume_size(self, symbol):
        min_volume_size = self.mt5.symbol_info(symbol).volume_min
        return min_volume_size

    def get_price(self, symbol):
        tick_info = self.mt5.symbol_info_tick(symbol)
        if tick_info is None:
            return None
        return (tick_info.bid, tick_info.ask)

    def place_trade_order(self, symbol, entry_price, stop_loss, target_profit, volume, trade_direction, trade_ref_number):
        
        digits = self.get_digts(symbol)

        order = {
            "action": self.mt5.TRADE_ACTION_DEAL,
            "symbol": symbol,
            "volume": volume,
            "type": self.mt5.ORDER_TYPE_BUY if trade_direction in ['Long', 'Buy'] else self.mt5.ORDER_TYPE_SELL,
            "price": entry_price,
            "sl": float(f"{round(stop_loss, 2):.{digits}f}"),
            "tp":  float(f"{round(target_profit, 2):.{digits}f}"),
            "deviation": 5,
            "magic": 234000,
            "comment": trade_ref_number,
            "type_time": self.mt5.ORDER_TIME_GTC,
            "type_filling": self.mt5.ORDER_FILLING_IOC
        }

        result = self.mt5.order_send(order)
        logger.info(self.mt5.last_error())

        if result.retcode != mt5.TRADE_RETCODE_DONE:
            logger.info(f"Order failed, retcode={result}, last error:\n{self.mt5.last_error()}")
        else:
            logger.info(f'Trade was placed successfully:\n{result}')
            return result

    def shutdown(self):
        self.mt5.shutdown()

class MT5Scheduler:
    def __init__(self, mt5, interval=300):
        self.mt5 = mt5  # Verwijzing naar de MT5-terminal
        self.interval = interval  # Interval in seconden
        self.is_running = True  # Vlag om de loop te controleren

    async def fetch_data(self):
        while self.is_running:
            logger.info('Running inside the fetch_data function. Do stuff here like retrieving position information.')
            """
            # Hier kun je de logica toevoegen om gegevens op te halen van de MT5-terminal
            price = self.get_price()  # Voorbeeldfunctie om de prijs op te halen
            logger.info(f"Opgehaalde prijs: {price}")

            # Controleer of het bijna het einde van de handelsdag of week is
            if self.is_near_end_of_trading_day():
                logger.info("Bijna einde van de handelsdag!")
            if self.is_near_end_of_trading_week():
                logger.info("Bijna einde van de handelsweek!")
            """
            await asyncio.sleep(self.interval)

    def get_price(self):
        # Voeg hier de logica toe om de prijs op te halen van de MT5-terminal
        # Dit is een placeholder
        return self.mt5.get_last_price()  # Voorbeeldfunctie

    def is_near_end_of_trading_day(self):
        # Voeg hier de logica toe om te controleren of het bijna het einde van de handelsdag is
        now = datetime.now()
        end_of_day = now.replace(hour=23, minute=59, second=59)  # Voorbeeld: einde van de dag
        return now >= end_of_day - timedelta(minutes=2)  # Controleer of het binnen 2 minuten is

    def is_near_end_of_trading_week(self):
        # Voeg hier de logica toe om te controleren of het bijna het einde van de handelsweek is
        now = datetime.now()
        end_of_week = now + timedelta(days=(5 - now.weekday()))  # Einde van de week (zaterdag)
        end_of_week = end_of_week.replace(hour=23, minute=59, second=59)
        return now >= end_of_week - timedelta(minutes=2)  # Controleer of het binnen 2 minuten is

    async def start(self):
        await self.fetch_data()

    def stop(self):
        self.is_running = False
