import logging
import pdb
import logger_setup
from mt5handler import MT5Handler
import MetaTrader5 as mt5

logger = logger_setup.LoggerSingleton.get_logger()

class PositionSize:

    def calculate_position_size(self, lot_size, account_equity, risk_percentage, stop_loss_price, eur_base_price, symbol_price):
        stopLossPips = round(abs(symbol_price - float(stop_loss_price)), 5)
        stopLossPipsEur = stopLossPips / eur_base_price
        logger.info(f'Stop Losses:\nstoploss: {round(stopLossPips, 5)}\nstoploss in EUR: {round(stopLossPipsEur, 5)}')
        
        riskLevelAmount = (account_equity * risk_percentage) / stopLossPipsEur / lot_size
        
        return riskLevelAmount

class ProcessTradeSignal:
    log_width = 30

    def __init__(self, mt5):
        self.mt5handler = MT5Handler(mt5)
        self.positionSizer = PositionSize()
        self.lotSize = 100000

    def start_order_entry_process(self, tradeSignal, strategy, split_lot_size=False):
        logger.info("Starting the order entry process.")

        baseCurrency = tradeSignal.forexSymbol[-3:]
        bidEURBase = self.get_bid_eur_base(baseCurrency)
        if bidEURBase is None:
            return

        price = self.get_trade_price(tradeSignal)
        if price is None:
            return

        accountInfo = self.mt5handler.get_account_info()
        positionSize = self.calculate_position_size(accountInfo, tradeSignal, strategy, bidEURBase, price)

        """
        # eventuele uitbreiding als positionSize een array is.
        if self.can_place_order(strategy):
            # Controleer of positionSize een lijst is
            if isinstance(positionSize, list):
                # Loop door elk element in de positionSize array
                for size in positionSize:
                    placeOrderResult = self.place_order(tradeSignal, price, size, strategy)
                    if placeOrderResult:
                        self.log_order_summary(placeOrderResult, tradeSignal, accountInfo, strategy, bidEURBase)
            else:
                # Als positionSize geen lijst is, plaats dan gewoon één order
                placeOrderResult = self.place_order(tradeSignal, price, positionSize, strategy)
                if placeOrderResult:
                    self.log_order_summary(placeOrderResult, tradeSignal, accountInfo, strategy, bidEURBase)
        """

        if self.can_place_order(strategy):
            placeOrderResult = self.place_order(tradeSignal, price, positionSize, strategy)
            if placeOrderResult:
                self.log_order_summary(placeOrderResult, tradeSignal, accountInfo, strategy, bidEURBase)

    def get_bid_eur_base(self, baseCurrency: str) -> float:
        bidEURBasePrices = self.mt5handler.get_price("EUR" + baseCurrency)
        if not bidEURBasePrices:
            logger.info(f"Error: Could not retrieve tick info for symbol EUR{baseCurrency}.")
            return None
        return bidEURBasePrices[1]

    def get_trade_price(self, tradeSignal) -> float:
        bidaskPrice = self.mt5handler.get_price(tradeSignal.forexSymbol)
        if not bidaskPrice:
            logger.info(f'Could not get prices for {tradeSignal.forexSymbol}.')
            return None
        return bidaskPrice[1] if tradeSignal.tradeDirection == "Long" else bidaskPrice[0]

    def calculate_position_size(self, accountInfo, tradeSignal, strategy, bidEURBase, price) -> float:
        return self.positionSizer.calculate_position_size(
            self.lotSize, accountInfo.equity, strategy.risklevel, 
            tradeSignal.stop_loss, bidEURBase, price
        )

    def can_place_order(self, strategy) -> bool:
        nrOpenPositions = self.mt5handler.get_open_positions()
        return (nrOpenPositions * strategy.risklevel) < strategy.portfolioheat

    def place_order(self, tradeSignal, price, positionSize, strategy):
        return self.mt5handler.place_trade_order(
            tradeSignal.forexSymbol, price, tradeSignal.stop_loss, 
            tradeSignal.target_profits[strategy.tpLevel - 1], 
            round(positionSize, 2), tradeSignal.tradeDirection, 
            tradeSignal.ref_number
        )

    def log_order_summary(self, placeOrderResult, tradeSignal, accountInfo, strategy, bidEURBase):
        netAbsStoploss = round(abs(placeOrderResult.price - tradeSignal.stop_loss), 5)
        netAbsStoplossEUR = netAbsStoploss / bidEURBase
        realPositionRisk = 100 * (self.lotSize * placeOrderResult.volume * netAbsStoplossEUR / accountInfo.equity)
        
        netTargetProfits = [abs(t - placeOrderResult.price) for t in tradeSignal.target_profits]
        netRR = [round((net_t / netAbsStoploss), 3) for net_t in netTargetProfits]
        averageRR = sum(netRR) / len(netRR) if netRR else 0

        logger.info(
            'SUMMARY:\n'
            f'Successfully placed {placeOrderResult.volume} units of {tradeSignal.forexSymbol}.\n'
            f'Account Balance: {accountInfo.balance}\n'
            f'Account Equity: {accountInfo.equity}\n'
            f'Price: {placeOrderResult.price}\n'
            f'Net position risk: {realPositionRisk:.2f}%\n'
            f'Net Risk Rewards: {netRR}\n'
            f'Average Risk Reward: {averageRR:.2f}\n'
            f'Net stop loss: {round(netAbsStoploss, 5)}\n'
            f'Net stop loss (EUR): {round(netAbsStoplossEUR, 5)}\n'
        )


class OrderEntry():
    def __init__(self):
        pass

    def start_order_entry_process(self):
        pass

class OrderManagement():
    pass

class OrderExit():
    pass

class PositionSizing():
    pass

if __name__ == '__main__':

    if not mt5.initialize():
        logger.info("initialize mt5 failed")
        mt5.shutdown()
        exit()

    from  tradesignalparser import TradeSignal
    exTradeSignal =  TradeSignal("EURCAD", "Long", open_price=1.5018, stop_loss=1.4989, target_profits=[1.5034, 1.5063, 1.5089], ref_number='EURNZD1.5018', tp_level_hit=3)

    from strategy import Strategy
    exStrategy = Strategy(0.015, 0.05, 3)

    pts = ProcessTradeSignal(mt5)
    pts.start_order_entry_process(exTradeSignal, exStrategy)
