import unittest
from unittest.mock import patch
from datetime import datetime  # Voeg deze import toe
from src.tradesignalparser import TradeSignalParser1000PipBuilder, TradeSignal

class Test1000PipBuilderParser(unittest.TestCase):

    def setUp(self):
        # Maak een instantie van de parser
        self.parser = TradeSignalParser1000PipBuilder()

    @patch('src.tradesignalparser.datetime')
    def test_parse_trade_signal_valid(self, mock_datetime):
        # Stel de mock in om een specifieke tijd te retourneren
        mock_datetime.now.return_value = datetime(2023, 1, 1, 12, 0, 0)

        # Dit is een geldig trade signal message
        message = """EURUSD Long
Open Price: 1.2000
SL: 1.1950 (50pips)
Start Exit Zone TP: 1.2050
1:1 Risk:Reward TP: 1.2100
End Exit Zone TP: 1.2150
Ref#: EURUSD1.2000"""

        # Voer de parsing uit
        trade_signal = self.parser.parse_trade_signal(message)

        # Controleer of het resultaat een geldig TradeSignal object is
        self.assertIsInstance(trade_signal, TradeSignal)
        self.assertEqual(trade_signal.forexSymbol, 'EURUSD')
        self.assertEqual(trade_signal.tradeDirection, 'Long')
        self.assertEqual(trade_signal.open_price, 1.2000)
        self.assertEqual(trade_signal.stop_loss, 1.1950)
        self.assertEqual(trade_signal.target_profits, [1.2050, 1.2100, 1.2150])
        self.assertEqual(trade_signal.ref_number, '230101120000_EURUSD1.2000')

    def test_parse_trade_signal_invalid(self):
        # Dit is een ongeldig trade signal message
        message = """EURUSD Long
Open Price: 1.2000
SL: 1.1950 (50pips)
Ref#: EURUSD1.2000"""

        # Voer de parsing uit en verwacht een ValueError
        with self.assertRaises(ValueError):
            self.parser.parse_trade_signal(message)

if __name__ == '__main__':
    unittest.main()
