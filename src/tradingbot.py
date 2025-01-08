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

    def __init__(self, mt5):
        self.mt5handler = MT5Handler(mt5)
        self.positionSizer = PositionSize()
        self.lotSize = 100000

    def start_order_entry_process(self, tradeSignal, strategy):
        logger.info("Starting the order entry proces.")

        # get the base currency (last 3 characters of the forex symbol)
        # and retrieve the EURXXX price for that currency
        baseCurrency = tradeSignal.forexSymbol[-3:]
        bidEURBasePrices = self.mt5handler.get_price("EUR" + baseCurrency)
        if not bidEURBasePrices:
            logger.info(f"Error: Could not retrieve tick info for symbol EUR{baseCurrency}'. Probably not added in the MetaTrader 5 terminal.")
            return
        bidEURBase = bidEURBasePrices[1]

        accountInfo = self.mt5handler.get_account_info()
        accountBalance = accountInfo.balance
        accountEquity = accountInfo.equity

        bidaskPrice = self.mt5handler.get_price(tradeSignal.forexSymbol)
        price = bidaskPrice[1] if tradeSignal.tradeDirection == "Long" else bidaskPrice[0]

        positionSize = self.positionSizer.calculate_position_size(self.lotSize, accountEquity, strategy.risklevel, 
            tradeSignal.stop_loss, bidEURBase, price)

        nrOpenPositions = self.mt5handler.get_open_positions()

        # make sure there are not too many positions open (portfolio heat)
        if (nrOpenPositions * strategy.risklevel) < strategy.portfolioheat:
            placeOrderResult = self.mt5handler.place_trade_order(tradeSignal.forexSymbol, price, tradeSignal.stop_loss, 
                tradeSignal.target_profits[1], round(positionSize, 2), tradeSignal.tradeDirection, tradeSignal.ref_number)
            if placeOrderResult:
                netAbsStoploss = round(abs(placeOrderResult.price - tradeSignal.stop_loss), 5)
                netAbsStoplossEUR = netAbsStoploss / bidEURBase
                realPositionRisk = 100 * (
                        self.lotSize * placeOrderResult.volume * 
                        netAbsStoplossEUR / accountEquity
                )
                optimalTPDistribution = 0
                if len(tradeSignal.target_profits) == 3:
                    takeProfit1 = tradeSignal.target_profits[1]
                    takeProfit2 = tradeSignal.target_profits[2]
                    optimalTPDistribution = 100 * (1 - takeProfit2) / (takeProfit1 - takeProfit2)
                netTargetProfits = [abs(t - placeOrderResult.price) for t in tradeSignal.target_profits]
                netRR = [round((net_t / netAbsStoploss), 3) for net_t in netTargetProfits]
                logger.info(
                    'SUMMARY:\n'
                    f'Successfully placed {round(positionSize, 2)} units (rounded from {round(positionSize, 4)}) of {tradeSignal.forexSymbol}.\n'
                    f'Account Balance: {accountBalance}\n'
                    f'Account Equity: {accountEquity}\n'
                    f'{tradeSignal.forexSymbol} prices: {bidaskPrice}\n'
                    f'EUR{baseCurrency} prices: {bidEURBasePrices} (we use the ask)\n'
                    f'Risk Level: {strategy.risklevel}\n'
                    f'Portfolio Heat: {strategy.portfolioheat}\n'
                    f'Number of current open positions: {nrOpenPositions}\n'
                    f'Net position risk: {realPositionRisk:.2f}%\n'
                    f'Net Risk Rewards: {netRR}\n'
                    f'Net stop loss: {round(netAbsStoploss, 5)}\n'
                    f'Net stop loss (EUR): {round(netAbsStoplossEUR, 5)}\n'
                    f'Optimal take profit percentage for a 1:1 risk reward: {optimalTPDistribution:.1f}%\n'
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
    exTradeSignal =  TradeSignal("EURCAD", "Short", open_price=1.4915, stop_loss=1.4935, target_profits=[1.4889, 1.4835, 1.4815], ref_number='EURNZD1.8512')

    from strategy import Strategy
    exStrategy = Strategy(0.015, 0.05)

    pts = ProcessTradeSignal(mt5)
    pts.start_order_entry_process(exTradeSignal, exStrategy)
