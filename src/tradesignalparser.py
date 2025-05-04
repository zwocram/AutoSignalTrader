from datetime import datetime
import re
import logger_setup
import pdb
from typing import Optional, Dict, Any

logger = logger_setup.LoggerSingleton.get_logger() 
class TradeSignal:
    def __init__(self, forexSymbol, tradeDirection, open_price, stop_loss, target_profits, ref_number, tp_level_hit):
        self.forexSymbol = forexSymbol
        self.tradeDirection = tradeDirection
        self.open_price = open_price
        self.stop_loss = stop_loss
        self.target_profits = target_profits  # This will be an array
        self.ref_number = ref_number
        self.tp_level_hit = tp_level_hit

    def __repr__(self):
        return (f"TradeSignal(forexSymbol={self.forexSymbol}, tradeDirection={self.tradeDirection}, open_price={self.open_price}, " 
                f"stop_loss={self.stop_loss}, target_profits={self.target_profits}, ref_number={self.ref_number}), tp_level_hist={self.tp_level_hit}")

class BaseTradeSignalParser:
    def parse_trade_signal(self, message):
        raise NotImplementedError("Subclasses should implement this method.")

    def _prefix_reference_number(self, referenceNumber: str) -> str:
        # Haal de huidige datum en tijd op
        now = datetime.now()
        
        # Formatteer de onderdelen
        year = now.strftime("%y")  # Laatste twee cijfers van het jaar
        month = now.strftime("%m")  # Maand in 2 cijfers
        day = now.strftime("%d")    # Dag in 2 cijfers
        hour = now.strftime("%H")   # Uur in 24-uursnotatie, 2 cijfers
        minute = now.strftime("%M")  # Minuten in 2 cijfers
        second = now.strftime("%S")  # Seconden in 2 cijfers
        
        # Maak de prefix
        prefix = f"{year}{month}{day}{hour}{minute}"
        
        # Voeg de prefix toe aan de originele string
        return f"{prefix}_{referenceNumber}"


    def clean_message(self, message):
        # Remove image URLs (assuming they start with http or https)
        message = re.sub(r'http[s]?://\S+\.(?:jpg|jpeg|png|gif)', '', message)

        # Remove any non-ASCII characters (or specify a different character set if needed)
        message = re.sub(r'[^\x00-\x7F]+', '', message)

        # Optionally, you can also strip leading/trailing whitespace
        return message.strip()

    def validate(self, message):
        # Common validation logic can go here
        pass

class TradeSignalParser1000PipBuilder(BaseTradeSignalParser):

    def parse_trade_signal(self, message):

        lines = message.strip().split('\n')
        
        if len(lines) < 7:
            raise ValueError("Invalid trade signal format: not enough lines")
        

        # Check the first line for the forex symbol and trade direction
        firstLine = lines[0]
        pattern = r'^\s*([A-Z]{6})\s+(Long|Short)\s*$'  # Regex pattern for 6 uppercase letters followed by 'long' or 'short'
        match = re.match(pattern, firstLine, re.IGNORECASE)

        if not match:
            raise ValueError("Invalid trade signal format: first line must contain a valid forex symbol and trade direction")

        # Extract forex symbol and trade direction
        forexSymbol, tradeDirection = match.groups()
        
        # Extracting values from the lines
        open_price = None
        stop_loss = None
        target_profits = []  # Initialize the target_profits array
        ref_number = None

        for line in lines:
            if line.startswith("Open Price:"):
                open_price = float(line.split(":")[1].strip())
            elif line.startswith("SL:"):
                stop_loss = float(line.split(":")[1].strip().split(" ")[0])  # Get the number before 'pips'
            elif line.startswith("Start Exit Zone TP:"):
                target_profits.append(float(line.split(":")[1].strip()))  # Add to target_profits
            elif line.startswith("1:1 Risk:Reward TP:"):
                target_profits.append(float(line.split()[-1]))  # Add to target_profits
            elif line.startswith("End Exit Zone TP:"):
                target_profits.append(float(line.split(":")[1].strip()))  # Add to target_profits
            elif line.startswith("Ref#:"):
                ref_number = line.split(":")[1].strip()
                # leave ref number as is for now
                # line below can be uncommented to prefix or suffix the ref number
                # prefixedRefNumber = self._prefix_reference_number(ref_number)
        
        tp_level_hit = [False for _ in target_profits]

        if None in [forexSymbol, tradeDirection, open_price, stop_loss, ref_number] or len(target_profits) < 3:
            raise ValueError("Invalid trade signal format: missing required fields")

        return TradeSignal(forexSymbol, tradeDirection, open_price, stop_loss, target_profits, ref_number, tp_level_hit)

class GTMO(BaseTradeSignalParser):
    def parse_trade_signal(self, message):
        lines = [line.strip() for line in message.strip().split('\n') if line.strip()]
        
        if len(lines) < 3:
            raise ValueError("Invalid trade signal format: not enough lines")

        # Eerste regel: Gold buy now 3324 - 3321
        first_line = lines[0].lower()
        if not first_line.startswith("gold"):
            raise ValueError("Invalid trade signal format: first line must start with 'Gold'")
        if "buy" not in first_line and "sell" not in first_line:
            raise ValueError("Invalid trade signal format: must contain 'buy' or 'sell'")
        
        direction = "Buy" if "buy" in first_line else "Sell"
        forexSymbol = "XAUUSD"  # Aangenomen dat dit altijd zo is voor goud

        # find two decimals (entry prices) separated by dash
        pattern = r"\b(\d+(?:\.\d{1,3})?)\s{0,2}-\s{0,2}(\d+(?:\.\d{1,3})?)\b"
        match = re.search(pattern, first_line)    

        if match:
            signal_bid = match.group(1)
            signal_ask = match.group(2)
            range = match.group(0)
        else:
            raise ValueError(f"Invalid trade signal format: no valid prices found: \n{first_line}")

        open_price = signal_bid

        # Andere onderdelen initialiseren
        stop_loss = None
        target_profits = []
        ref_number = f'GTMO#{signal_bid}'

        for line in lines[1:]:
            lower = line.lower()
            if lower.startswith("sl"):
                try:
                    stop_loss = round(float(line.split(":")[1].strip()), 2)
                except Exception:
                    raise ValueError(f"Invalid stop loss format: {line}")
            elif lower.startswith("tp"):
                tp_value_str = line.split(":")[1].strip().lower()
                if tp_value_str == "open":
                    target_profits.append(None)
                else:
                    try:
                        target_profits.append(round(float(tp_value_str), 2))
                    except Exception:
                        raise ValueError(f"Invalid take profit format: {line}")
            elif lower.startswith("ref#:"):
                ref_number = line.split(":", 1)[1].strip()

        tp_level_hit = [False for _ in target_profits]

        if stop_loss is None or len(target_profits) == 0:
            raise ValueError("Missing stop loss or take profit(s)")

        # for the time being, skip the None values in the TradeSignal
        target_profits = [tp for tp in target_profits if tp is not None]

        return TradeSignal(forexSymbol, direction, open_price, stop_loss, target_profits, ref_number, tp_level_hit)

# Factory function to get the appropriate parser
def get_parser(channelName):
    if channelName == "Forex Signals - 1000 pip Builder":
        return TradeSignalParser1000PipBuilder()
    elif channelName == "GTMO VIP":
        return GTMO()
    else:
        raise ValueError("Unknown channel name")

# Example usage
if __name__ == '__main__':

    # Create a TradeSignalParser with rules
    pipbuilder_parser = get_parser("Forex Signals - 1000 pip Builder")

    # Test messages
    test_messages = [
        """EURUSD Short
Open Price: 1.0409
SL: 1.0424 (15pips)
Start Exit Zone TP: 1.0403
1:1 Risk:Reward TP: 1.0394
End Exit Zone TP: 1.0386
Ref#: EURUSD1.0409

This is not investment advice nor a general recommendation. Please see T&Cs for more information""",
        
        """GBPUSD Long
Open Price: 1.2540
SL: 1.2525 (15pips)
Start Exit Zone TP: 1.2546
1:1 Risk:Reward TP: 1.2555
End Exit Zone TP: 1.2562
Ref#: GBPUSD1.2540

This is not investment advice nor a general recommendation. Please see T&Cs for more information""",
        
        """AUDCAD Short
Open Price: 0.9500
SL: 0.9520 (20pips)
Start Exit Zone TP: 0.9490
1:1 Risk:Reward TP: 0.9480
End Exit Zone TP: 0.9470
Ref#: AUDCAD0.9500

This is not investment advice nor a general recommendation. Please see T&Cs for more information"""
    ]


    # Execute the parsing for each test message
    for message in test_messages:
        try:
            trade_signal = pipbuilder_parser.parse_trade_signal(message)
            print(trade_signal)
        except ValueError as e:
            print(e)


    # Create a TradeSignalParser with rules
    goldsignals_parser = get_parser("GTMO VIP")

    test_messages_gold = [
        """
Gold buy now 3302.5 - 3299

SL: 3296

TP: 3304
TP: 3306
TP: 3308
TP: 3310
TP: open
        """
    ]


    """
    import MetaTrader5 as mt5
    if not mt5.initialize():
        logger.info("initialize mt5 failed")
        mt5.shutdown()
        exit()
    """ 
    from strategy import Strategy
    exStrategy = Strategy(0.015, 0.1, 3, '', True, True, 50)

    from tradingbot import ProcessTradeSignal
    import manage_shelve
    import time

    # pts = ProcessTradeSignal(mt5)

    # Execute the parsing for each test message
    for message in test_messages_gold:
        try:
            message_stripped = goldsignals_parser.clean_message(message).encode('ascii', 'ignore').decode('ascii').strip()
            trade_signal = goldsignals_parser.parse_trade_signal(message_stripped)
            manage_shelve.store_data(manage_shelve.SIGNALS_DB, str(int(time.time())), (message_stripped, trade_signal))
            manage_shelve.show_all_data(manage_shelve.SIGNALS_DB)
           #  
            # pts.start_order_entry_process(trade_signal, exStrategy)
            print(trade_signal)
        except ValueError as e:
            print(e)



