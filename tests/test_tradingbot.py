import unittest
from unittest.mock import MagicMock, patch
from src.tradesignalparser import TradeSignal
from src.tradingbot import ProcessTradeSignal, logger_setup
import src.logger_setup 

class TestProcessTradeSignal(unittest.TestCase):

    def setUp(self):
        """Voorbereiding van testobject en mocks"""
        self.mt5_mock = MagicMock()
        self.tradeProcessor = ProcessTradeSignal(self.mt5_mock)

        # Mock strategie en trade signal
        self.strategy = MagicMock()
        self.strategy.splitPositionSize = False  # Default geen splitsing

        self.tradeSignal = MagicMock()
        self.tradeSignal.forexSymbol = "EURUSD"
        self.tradeSignal.target_profits = [1.2, 1.3, 1.3]

        # Mock methodes van ProcessTradeSignal
        self.tradeProcessor.get_bid_eur_base = MagicMock(return_value=1.1)
        self.tradeProcessor.get_trade_price = MagicMock(return_value=1.2345)
        self.tradeProcessor.calculate_position_size = MagicMock(return_value=0.1)
        self.tradeProcessor.split_position_size = MagicMock(return_value=[0.05, 0.05, 0.06])
        self.tradeProcessor.can_place_order = MagicMock(return_value=True)
        self.tradeProcessor.place_order = MagicMock(return_value={"order_id": 123})
        self.tradeProcessor.log_order_summary = MagicMock()

    def test_order_without_split(self):
        """Test order zonder splitsing"""
        self.tradeProcessor.start_order_entry_process(self.tradeSignal, self.strategy)

        # Controleer of de berekening correct werd uitgevoerd
        self.tradeProcessor.calculate_position_size.assert_called_once()
        self.tradeProcessor.split_position_size.assert_not_called()  # Geen splitsing verwacht
        self.tradeProcessor.place_order.assert_called_once_with(self.tradeSignal, 1.2345, 0.1, self.strategy)
        self.tradeProcessor.log_order_summary.assert_called_once()

    def test_order_with_split(self):
        """Test order met splitsing in meerdere delen"""
        self.strategy.splitPositionSize = True  # Simuleer splitsing
        self.tradeProcessor.start_order_entry_process(self.tradeSignal, self.strategy)

        # Controleer of splitsing werd uitgevoerd
        self.tradeProcessor.split_position_size.assert_called_once()
        self.assertEqual(self.tradeProcessor.place_order.call_count, 2)  # Twee orders

    def test_no_order_placed_if_cannot_trade(self):
        """Test dat er geen order geplaatst wordt als can_place_order False is"""
        self.tradeProcessor.can_place_order.return_value = False
        self.tradeProcessor.start_order_entry_process(self.tradeSignal, self.strategy)

        self.tradeProcessor.place_order.assert_not_called()
        self.tradeProcessor.log_order_summary.assert_not_called()

    def test_no_order_if_missing_bidEurBase(self):
        """Test dat er geen order wordt geplaatst als bidEURBase ontbreekt"""
        self.tradeProcessor.get_bid_eur_base.return_value = None
        self.tradeProcessor.start_order_entry_process(self.tradeSignal, self.strategy)

        self.tradeProcessor.calculate_position_size.assert_not_called()
        self.tradeProcessor.place_order.assert_not_called()

if __name__ == '__main__':
    unittest.main()
