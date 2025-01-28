import ib_insync
import pandas
import numpy
import asyncio
import typing
import datetime
import ta  # Import the ta library for technical analysis
import config.config as cfg  # Import the config module
import utils.logger as logger_utils  # Import the logger utility

class DataFetcher:
    def __init__(self, connection, symbol: str = None):
        self.connection = connection
        # Use the first core symbol as default if no symbol is provided
        self.symbol = symbol if symbol else cfg.CORE_SYMBOLS[0]
        self.ib = connection.ib
        self.logger = logger_utils.get_logger(__name__)  # Use the new logger

    async def get_historical_data(
        self, 
        symbol: str = None,  # Use the provided symbol or default
        duration: str = cfg.DURATION,
        bar_size: str = cfg.BAR_SIZE
    ) -> typing.Optional[pandas.DataFrame]:
        """Fetch historical data from IB"""
        try:
            # Use the provided symbol or the default one
            symbol = symbol if symbol else self.symbol
            contract = ib_insync.Contract(symbol=symbol, secType='STK', exchange='SMART', currency='USD')
            bars: typing.List[ib_insync.BarData] = await self.ib.reqHistoricalDataAsync(
                contract,
                endDateTime='',
                durationStr=duration,
                barSizeSetting=bar_size,
                whatToShow='TRADES',
                useRTH=False
            )
            
            if not bars:
                return None
                
            df = ib_insync.util.df(bars)
            return df
            
        except Exception as e:
            self.logger.error(f"Error fetching historical data: {str(e)}")
            return None

    def calculate_rsi(self, data: pandas.DataFrame, periods: int = 7) -> pandas.DataFrame:
        """Calculate RSI using the ta library"""
        try:
            # Calculate RSI using the ta library
            data['RSI'] = ta.momentum.RSIIndicator(data['close'], window=periods).rsi()
            return data
        except Exception as e:
            self.logger.error(f"Error calculating RSI: {str(e)}")
            return data