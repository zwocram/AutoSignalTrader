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

    log_width=30

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

        bidaskPrice = self.mt5handler.get_price(tradeSignal.forexSymbol)
        if not bidaskPrice:
            logger.info(f'Could not get prices for {tradeSignal.forexSymbol}. Is this pair defined in the MT5 terminal?')
            return
        price = bidaskPrice[1] if tradeSignal.tradeDirection == "Long" else bidaskPrice[0]

        accountInfo = self.mt5handler.get_account_info()
        accountBalance = accountInfo.balance
        accountEquity = accountInfo.equity

        positionSize = self.positionSizer.calculate_position_size(self.lotSize, accountEquity, strategy.risklevel, 
            tradeSignal.stop_loss, bidEURBase, price)

        nthTPLevel = strategy.tpLevel

        nrOpenPositions = self.mt5handler.get_open_positions()

        # make sure there are not too many positions open (portfolio heat)
        if (nrOpenPositions * strategy.risklevel) < strategy.portfolioheat:
            placeOrderResult = self.mt5handler.place_trade_order(tradeSignal.forexSymbol, price, tradeSignal.stop_loss, 
                tradeSignal.target_profits[nthTPLevel-1], round(positionSize, 2), tradeSignal.tradeDirection, tradeSignal.ref_number)
            if placeOrderResult:
                # TO DO
                # store the tradeSignal with reference to order id

                netAbsStoploss = round(abs(placeOrderResult.price - tradeSignal.stop_loss), 5)
                netAbsStoplossEUR = netAbsStoploss / bidEURBase
                realPositionRisk = 100 * (
                        self.lotSize * placeOrderResult.volume * 
                        netAbsStoplossEUR / accountEquity
                )
                optimalTPDistribution = 0
                netTargetProfits = [abs(t - placeOrderResult.price) for t in tradeSignal.target_profits]
                netRR = [round((net_t / netAbsStoploss), 3) for net_t in netTargetProfits]
                if len(netRR) == 3:
                    takeProfit1 = netRR[1]
                    takeProfit2 = netRR[2]
                    optimalTPDistribution = 100 * (1 - takeProfit2) / (takeProfit1 - takeProfit2)
                logger.info(
                    'SUMMARY:\n'
                    f'Successfully placed {round(positionSize, 2)} units (rounded from {round(positionSize, 4)}) of {tradeSignal.forexSymbol}.\n'
                    f'Account Balance: {accountBalance}\n'
                    f'Account Equity: {accountEquity}\n'
                    f'Price: {placeOrderResult.price}\n'
                    f'{tradeSignal.forexSymbol} prices: {bidaskPrice}\n'
                    f'EUR{baseCurrency} prices: {bidEURBasePrices} (we use the ask)\n'
                    f'Risk Level: {strategy.risklevel}\n'
                    f'Portfolio Heat: {strategy.portfolioheat}\n'
                    f'# open positions: {nrOpenPositions}\n'
                    f'Net position risk: {realPositionRisk:.2f}%\n'
                    f'Net Risk Rewards: {netRR}\n'
                    f'Net stop loss: {round(netAbsStoploss, 5)}\n'
                    f'Net stop loss (EUR): {round(netAbsStoplossEUR, 5)}\n'
                    f'Optimal 1:1 RR %: {optimalTPDistribution:.1f}%\n'
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
    exTradeSignal =  TradeSignal("EURCAD", "Short", open_price=1.4915, stop_loss=1.0000, target_profits=[2, 3, 4], ref_number='EURNZD1.8512')

    from strategy import Strategy
    exStrategy = Strategy(0.015, 0.05, 3)

    pts = ProcessTradeSignal(mt5)
    pts.start_order_entry_process(exTradeSignal, exStrategy)
