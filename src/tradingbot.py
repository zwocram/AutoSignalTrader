import logging
import time
import pdb
import logger_setup
import manage_shelve
from strategy import Strategy
from mt5handler import MT5Handler
import MetaTrader5 as mt5

logger = logger_setup.LoggerSingleton.get_logger()

class PositionSize:

    def calculate_position_size(self, lot_size, account_equity, strategy, stop_loss_price, eur_base_price, 
                    symbol_price):
        stopLossPips = round(abs(symbol_price - float(stop_loss_price)), 5)
        stopLossPipsEur = stopLossPips / eur_base_price
        logger.info(f'Stop Losses:\nstoploss: {round(stopLossPips, 5)}\nstoploss in EUR: {round(stopLossPipsEur, 5)}')

        if strategy.useFixedRiskAmount:
            riskLevelAmount = round(strategy.fixedRiskAmount / stopLossPipsEur / lot_size, 2)
        else:
            riskLevelAmount = round((account_equity * strategy.risklevel) / stopLossPipsEur / lot_size, 2)
        
        return riskLevelAmount

class ProcessTradeSignal:
    log_width = 30

    def __init__(self, mt5):
        self.mt5handler = MT5Handler(mt5)
        self.positionSizer = PositionSize()

    def adjust_positions(self, position_attribute_type):
        """
        Based on the position attribute (SL or TP), adjust
        the corresponding attribute.
        """
        pass

    def start_order_entry_process(self, tradeSignal, strategy):
        logger.info("Starting the order entry process.")

        baseCurrency = tradeSignal.forexSymbol[-3:]
        bidEURBase = self.get_bid_eur_base(baseCurrency)
        if bidEURBase is None:
            return

        price = self.get_trade_price(tradeSignal)
        if price is None:
            return

        accountInfo = self.mt5handler.get_account_info()
        lot_size = self.mt5handler.get_contract_size(tradeSignal.forexSymbol)
        min_volume_size = self.mt5handler.get_minimal_volume_size(tradeSignal.forexSymbol) 

        positionSize = self.calculate_position_size(lot_size, accountInfo, tradeSignal, strategy, bidEURBase, price)
        logger.info(f'Original position size: {positionSize}')

        if strategy.splitPositionSize:
            # we can only split if the position size is 'splittable'
            # e.g. we can't split a position size of 0.03 if there are 4 target profit levels
            if ((positionSize / min_volume_size)  / len(tradeSignal.target_profits) )>= 1:
                positionSize = self.split_position_size(positionSize, len(tradeSignal.target_profits))
            else:
                # still splitting position size but every trade size is equal to the minimum volume size
                positionSize = [min_volume_size] * len(tradeSignal.target_profits)

        if not isinstance(positionSize, list):
            positionSize = [positionSize]

        if self.can_place_order(strategy, len(positionSize)):
            is_single_position_size = len(positionSize) == 1
            tpLevel = tradeSignal.target_profits[-1]
            refNumber = tradeSignal.ref_number
            orderResults = []
            orderResultsDict = []

            for index, size in enumerate(positionSize):
                # Check for more than 1 position size
                # if true, modify tpLevel and ref number
                if not is_single_position_size:
                    tradeSignal.ref_number = f"{refNumber}_{index + 1}"
                    tpLevel = tradeSignal.target_profits[index]

                placeOrderResult = self.place_order(tradeSignal, price, size, strategy, tpLevel)
                time.sleep(0.4)  # Wacht om overbelasting van de server te voorkomen

                if placeOrderResult:
                    order_dict = placeOrderResult._asdict()
                    order_dict['request'] = placeOrderResult.request._asdict()
                    orderResults.append(placeOrderResult)
                    orderResultsDict.append(order_dict)
                    # save the order result somewhere

            self.log_order_summary(orderResults, tradeSignal, accountInfo, strategy, bidEURBase, lot_size)

            # store the placed orders for future reference
            key = int(time.time()) # epoch time
            manage_shelve.store_data(manage_shelve.TRADES_POSITIONS_DB, str(key), orderResultsDict)

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

    def calculate_position_size(self, lot_size, accountInfo, tradeSignal, strategy, bidEURBase, price) -> float:
        """Calculates the position size of a new position
        """
        return self.positionSizer.calculate_position_size(
            lot_size, accountInfo.equity, strategy, 
            tradeSignal.stop_loss, bidEURBase, price
        )

    def can_place_order(self, strategy: Strategy, multiplier: int=1) -> bool:
        """Checks if portfolio is too hot, i.e. no more positions allowed

        IMPORTANT: this function return True by default until a sufficient
        enough portfolioheat checking mechanism is implemented.

        Parameters
        ----------
        strategy: Strategy
            The strategy that is used on the account. Is read from config.json
            at app startup

        multiplier: int, optional
            If position size is split into sub-position sizes we have to
            multiply the number of allowed position in the portfolio
            by the number of parts the position size was divided into.
        """

        return True

        # as for the reason why the lines below are commented out
        # please refer to the documentation of the function itself
        # nrOpenPositions = self.mt5handler.get_open_positions()
        # return (nrOpenPositions * strategy.risklevel) < multiplier * strategy.portfolioheat

    def place_order(self, tradeSignal, price, positionSize, strategy, tp_level):
        """Places the order at the broker
        """

        return self.mt5handler.place_trade_order(
            tradeSignal.forexSymbol, price, tradeSignal.stop_loss, 
            tp_level, positionSize, tradeSignal.tradeDirection, 
            tradeSignal.ref_number
        )

    def split_position_size(self, number, parts_count=3, largest_at_end=False):
        """
        Verdeelt een getal met twee decimalen in een willekeurig aantal delen, 
        waarbij de som gelijk blijft aan het originele getal.

        Parameters:
            number (float): Het getal om te verdelen.
            parts_count (int): Het aantal delen waarin het getal verdeeld moet worden.
            largest_at_end (bool): Plaats de grootste waarde aan het eind als True, anders aan het begin.

        Returns:
            list: Delen waarvan de som gelijk is aan het originele getal.
        """
        try:
            # Type-checks
            if not isinstance(number, (int, float)):
                raise ValueError(f"Invalid type for number: {type(number)}. Must be int or float.")
            if not isinstance(parts_count, int) or parts_count <= 0:
                raise ValueError(f"Invalid parts_count: {parts_count}. Must be a positive integer.")

            # Zorg dat het getal twee decimalen heeft
            number = round(number, 2)

            # Verdeel het getal in gelijke delen
            base = round(number / parts_count, 2)

            # Bereken de som van de basisdelen en de afwijking
            parts = [base] * parts_count
            difference = round(number - sum(parts), 2)

            # Wijs de afwijking toe aan delen
            for i in range(abs(int(difference * 100))):
                index = -1 if largest_at_end else 0
                parts[index] += 0.01 if difference > 0 else -0.01
                if not largest_at_end:
                    parts.sort(reverse=True)

            # Controleer of de som correct is
            if round(sum(parts), 2) != number:
                raise ValueError("Rounding error: Sum of parts does not match original number.")

            # Sorteer de delen indien nodig
            if largest_at_end:
                parts.sort()

            return parts

        except Exception as e:
            print(f"Error in split_position_size: {e}")
            return []

    def log_order_summary(self, orderResults, tradeSignal, accountInfo, strategy, bidEURBase, lot_size):
        if not orderResults:
            logger.info("No orders received, skip logging output.")
            return
        averagePrice = sum(result.price for result in orderResults) / len(orderResults)
        prices = [result.price for result in orderResults]
        volumes = [result.volume for result in orderResults]
        
        weighted_sum_price = sum(prices * volumes for prices, volumes in zip(prices, volumes))
        total_volume = sum(volumes)

        if total_volume > 0:  # Controleer of de totale gewichten niet nul zijn
            weighted_average_price = weighted_sum_price / total_volume

        netAbsStoploss = round(abs(averagePrice - tradeSignal.stop_loss), 5)
        netAbsStoplossEUR = netAbsStoploss / bidEURBase
        realPositionsRisk = [100 * (lot_size * result.volume * netAbsStoplossEUR / accountInfo.equity) for result in orderResults]
        
        netTargetProfits = [abs(t - averagePrice) for t in tradeSignal.target_profits]
        netRR = [round((net_t / netAbsStoploss), 3) for net_t in netTargetProfits]
        averageRR = sum(netRR) / len(netRR) if netRR else 0

        logger.info(
            'SUMMARY:\n'
            f'Successfully placed {volumes} units of {tradeSignal.forexSymbol}.\n'
            f'Account Balance: {accountInfo.balance}\n'
            f'Account Equity: {accountInfo.equity}\n'
            f'Average price: {averagePrice:.5f}\n'
            f"Weighted average price: {weighted_average_price:.5f}\n"
            f'Net positions risk: {", ".join(f"{positionRisk:.2f}%" for positionRisk in realPositionsRisk)}\n'
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
    exTradeSignal =  TradeSignal("EURCAD", "Long", open_price=1.5752, stop_loss=1.5722, target_profits=[1.5792, 1.5840, 1.5890], 
                    ref_number='EURCAD1.5018', tp_level_hit=3)

    exTradeSignal2 = TradeSignal('XAUUSD', 'Buy', open_price=3228.00, stop_loss=3200.00, target_profits=[3242.00, 3250.00, 3261.00, 3275.00], 
                    ref_number='GS', tp_level_hit=4)

    from strategy import Strategy
    exStrategy = Strategy(0.015, 0.1, 3, '', True, True, 50)

    pts = ProcessTradeSignal(mt5)
    pts.start_order_entry_process(exTradeSignal2, exStrategy)
