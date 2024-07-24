import backtrader as bt
import csv

class DualListedArbitrage(bt.Strategy):
    params = (
        ('long_term_average', 100),
        ('short_term_average', 20),
        ('take_profit', 0.0025),     # 0.25% take profit
        ('quantity', 5)
    )

    def __init__(self):
        self.data0 = self.datas[0]
        self.data1 = self.datas[1]
        
        # Calculate the spread and indicators
        self.spread = self.data0.close - self.data1.close
        self.spread = self.spread / self.data1.close
        self.long_term_sma = bt.indicators.SimpleMovingAverage(self.spread, period=self.params.long_term_average)
        self.short_term_sma = bt.indicators.SimpleMovingAverage(self.spread, period=self.params.short_term_average)
        
        # Store entry prices
        self.entry_prices = {self.datas[0]: None, self.datas[1]: None}
        
        # Initialize the trade log
        self.trade_log = []

    def log(self, txt, dt=None):
        ''' Logging function for this strategy'''
        dt = dt or self.datas[0].datetime.date(0)
        print(f'{dt.isoformat()}, {txt}')

    def notify_order(self, order):
        if order.status in [order.Submitted, order.Accepted]:
            return

        if order.status in [order.Completed]:
            if order.isbuy():
                self.log(f'BUY EXECUTED, {order.executed.price}')
                self.trade_log.append(['BUY', order.data._name, self.datas[0].datetime.datetime(0).isoformat(), order.executed.price])
            elif order.issell():
                self.log(f'SELL EXECUTED, {order.executed.price}')
                self.trade_log.append(['SELL', order.data._name, self.datas[0].datetime.datetime(0).isoformat(), order.executed.price])
        
        elif order.status in [order.Canceled, order.Margin, order.Rejected]:
            self.log(f'Order Canceled/Margin/Rejected')
        
        self.order = None

    def next(self):
        if len(self.data0) < self.params.long_term_average or len(self.data1) < self.params.long_term_average:
            return

        # Entry conditions
        if self.short_term_sma[0] > self.long_term_sma[0] and self.short_term_sma[-1] <= self.long_term_sma[-1]:
            self.buy(data=self.datas[0], size=self.params.quantity)
            self.sell(data=self.datas[1], size=self.params.quantity)
            self.entry_prices[self.datas[0]] = self.data0.close[0]
            self.entry_prices[self.datas[1]] = self.data1.close[0]
        elif self.short_term_sma[0] < self.long_term_sma[0] and self.short_term_sma[-1] >= self.long_term_sma[-1]:
            self.sell(data=self.datas[0], size=self.params.quantity)
            self.buy(data=self.datas[1], size=self.params.quantity)
            self.entry_prices[self.datas[0]] = self.data0.close[0]
            self.entry_prices[self.datas[1]] = self.data1.close[0]
        # else:
        #     # Take profit logic
        #     for data in [self.datas[0], self.datas[1]]:
        #         position = self.getposition(data)
        #         if position.size != 0 and self.entry_prices[data] is not None:
        #             current_price = data.close[0]
        #             entry_price = self.entry_prices[data]
        #             #print(f'Position in {data._name}: Entry Price: {entry_price}, Current Price: {current_price}')
        #             if position.size > 0:  # Long position
        #                 if current_price >= entry_price * (1 + self.params.take_profit):
        #                     print(f'Closing Long Position in {data._name}')
        #                     self.close(data)
        #                     self.entry_prices[data] = None
        #             elif position.size < 0:  # Short position
        #                 if current_price <= entry_price * (1 - self.params.take_profit):
        #                     print(f'Closing Short Position in {data._name}')
        #                     self.close(data)
        #                     self.entry_prices[data] = None

    def stop(self):
        with open('trade_log.csv', 'w', newline='') as csvfile:
            fieldnames = ['Type', 'Stock', 'Date', 'Price']
            writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
            writer.writeheader()
            for log_entry in self.trade_log:
                writer.writerow({'Type': log_entry[0], 'Stock': log_entry[1], 'Date': log_entry[2], 'Price': log_entry[3]})
        print("Trade log saved to trade_log.csv")

