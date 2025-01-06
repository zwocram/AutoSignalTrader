import pdb
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

    def get_price(self, symbol):
        tick_info = self.mt5.symbol_info_tick(symbol)
        if tick_info is None:
            return None
        return (tick_info.bid, tick_info.ask)


    def place_trade_order(self, symbol, entry_price, stop_loss, target_profit, volume, trade_direction, trade_ref_number):
        
        order = {
            "action": self.mt5.TRADE_ACTION_DEAL,
            "symbol": symbol,
            "volume": volume,
            "type": self.mt5.ORDER_TYPE_BUY if trade_direction=="Long" else self.mt5.ORDER_TYPE_SELL,
            "price": entry_price,
            "sl": stop_loss,
            "tp": target_profit,
            "deviation": 5,
            "magic": 234000,
            "comment": trade_ref_number,
            "type_time": self.mt5.ORDER_TIME_GTC,
            "type_filling": self.mt5.ORDER_FILLING_IOC
        }

        result = self.mt5.order_send(order)

        if result.retcode != mt5.TRADE_RETCODE_DONE:
            logger.info(f"Order failed, retcode={result}")
        else:
            logger.info(f'Trade was placed successfully:\n{result}')
            return result

    def shutdown(self):
        self.mt5.shutdown()
