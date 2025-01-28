import backtrader as bt
import datetime
from core.backtrader_strategy import CoreBuildingStrategy

class CustomCSVData(bt.feeds.GenericCSVData):
    params = (
        ('dtformat', '%Y-%m-%d'),  # Adjust this if your date format is different
        ('datetime', 0),
        ('open', 4),
        ('high', 2),
        ('low', 3),
        ('close', 1),
        ('volume', 5),
        ('openinterest', -1),
        ('headers', True),  # Indicate that there is a header row
        ('fromdate', datetime.datetime(2020, 1, 2)),  # Start date of your data
        ('todate', datetime.datetime(2021, 1, 1)),  # End date of your data
        ('nullvalue', 0.0),
        ('reverse', False),
        ('delimiter', ','),  # CSV delimiter
        ('skiprows', 2),  # Skip the first two rows
    )

def run_backtest():
    # Create a cerebro instance
    cerebro = bt.Cerebro()

    # Add a strategy
    cerebro.addstrategy(CoreBuildingStrategy)

    # Load data from the CSV file
    data = CustomCSVData(dataname='AAPL.csv')
    cerebro.adddata(data)

    # Set initial capital
    cerebro.broker.setcash(10000.0)

    # Run the backtest
    print('Starting Portfolio Value: %.2f' % cerebro.broker.getvalue())
    cerebro.run()
    print('Final Portfolio Value: %.2f' % cerebro.broker.getvalue())

    # Plot the results
    cerebro.plot()

if __name__ == "__main__":
    run_backtest()