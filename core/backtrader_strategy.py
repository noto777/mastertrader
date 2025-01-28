import backtrader as bt

class CoreBuildingStrategy(bt.Strategy):
    params = (
        ('rsi_period', 7),
        ('rsi_oversold', 30),
        ('profit_target', 0.01),
        ('core_target', 0.05),
        ('order_size_percent', 0.01),
    )

    def __init__(self):
        self.rsi = bt.indicators.RSI(self.data.close, period=self.params.rsi_period)
        self.core_position = 0
        self.core_repeats = 0

    def next(self):
        if self.rsi < self.params.rsi_oversold and not self.position:
            self.buy(size=self.calculate_order_size())
            self.core_repeats += 1
        elif self.position and self.data.close[0] >= self.position.price * (1 + self.params.profit_target):
            self.sell(size=self.position.size * 0.75)

    def calculate_order_size(self):
        return int(self.broker.getvalue() * self.params.order_size_percent / self.data.close[0]) 