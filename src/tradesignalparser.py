import re
import pdb
from typing import Optional, Dict, Any


class TradeSignal:
    def __init__(self, forexSymbol, tradeDirection, open_price, stop_loss, target_profits, ref_number):
        self.forexSymbol = forexSymbol
        self.tradeDirection = tradeDirection
        self.open_price = open_price
        self.stop_loss = stop_loss
        self.target_profits = target_profits  # This will be an array
        self.ref_number = ref_number

    def __repr__(self):
        return (f"TradeSignal(forexSymbol={self.forexSymbol}, tradeDirection={self.tradeDirection}, open_price={self.open_price}, " 
                f"stop_loss={self.stop_loss}, target_profits={self.target_profits}, ref_number={self.ref_number})")

class BaseTradeSignalParser:
    def parse_trade_signal(self, message):
        raise NotImplementedError("Subclasses should implement this method.")

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

        if None in [forexSymbol, tradeDirection, open_price, stop_loss, ref_number] or len(target_profits) < 3:
            raise ValueError("Invalid trade signal format: missing required fields")

        return TradeSignal(forexSymbol, tradeDirection, open_price, stop_loss, target_profits, ref_number)

class TelegramChannel2Parser(BaseTradeSignalParser):
    def parse_trade_signal(self, message):
        # Implement parsing logic specific to Telegram Channel 2
        # This is just an example; the actual parsing logic will depend on the message format
        lines = message.strip().split('\n')
        
        if len(lines) < 5:
            raise ValueError("Invalid trade signal format: not enough lines")
        
        open_price = None
        stop_loss = None
        target_profits = []
        ref_number = None

        for line in lines:
            if line.startswith("Entry Price:"):
                open_price = line.split(":")[1].strip()
            elif line.startswith("Stop Loss:"):
                stop_loss = line.split(":")[1].strip()
            elif line.startswith("Take Profit:"):
                target_profits.append(line.split(":")[1].strip())
            elif line.startswith("Reference:"):
                ref_number = line.split(":")[1].strip()

        if None in [open_price, stop_loss, ref_number] or len(target_profits) < 1:
            raise ValueError("Invalid trade signal format: missing required fields")

        return TradeSignal(open_price, stop_loss, target_profits, ref_number)


# Factory function to get the appropriate parser
def get_parser(channelName):
    if channelName == "Forex Signals - 1000 pip Builder":
        return TradeSignalParser1000PipBuilder()
    elif channelName == "channel2":
        return TelegramChannel2Parser()
    else:
        raise ValueError("Unknown channel name")

# Example usage
if __name__ == '__main__':

    # Create a TradeSignalParser with rules
    parser = get_parser("Forex Signals - 1000 pip Builder")

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
            trade_signal = parser.parse_trade_signal(message)
            print(trade_signal)
        except ValueError as e:
            print(e)

            