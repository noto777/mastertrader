import yfinance as yf
import pandas as pd
from datetime import datetime, timedelta
from typing import Dict, List, Optional
import logging
import numpy as np

logger = logging.getLogger(__name__)

class DataLoader:
    def __init__(self):
        """Initialize DataLoader."""
        self.data_cache = {}  # Cache data to avoid repeated downloads
        
    def load_historical_data(self, symbols: List[str], 
                           start_date: datetime,
                           end_date: datetime = None,
                           timeframes: List[str] = ['1d', '1wk']) -> Dict[str, Dict[str, pd.DataFrame]]:
        """
        Load historical data for multiple symbols and timeframes.
        Removed 15m timeframe as it's limited to 60 days
        """
        try:
            if end_date is None:
                end_date = datetime.now()
                
            data = {}
            for symbol in symbols:
                data[symbol] = {}
                for timeframe in timeframes:
                    print(f"Loading {symbol} {timeframe} data...")
                    df = yf.download(
                        symbol,
                        start=start_date,
                        end=end_date,
                        interval=timeframe
                    )
                    
                    if df.empty:
                        logger.warning(f"No data found for {symbol} at {timeframe} timeframe")
                        continue
                        
                    df = self._add_indicators(df)
                    data[symbol][timeframe] = df
                    
            return data
            
        except Exception as e:
            logger.error(f"Error loading historical data: {e}")
            return {}
            
    def _adjust_start_date(self, start_date: datetime, timeframe: str) -> datetime:
        """Adjust start date based on timeframe to ensure enough data for indicators."""
        if timeframe == '1d':
            return start_date - timedelta(days=100)
        else:  # '1wk'
            return start_date - timedelta(days=365)
            
    def _add_indicators(self, df: pd.DataFrame) -> pd.DataFrame:
        """Add technical indicators needed for backtesting."""
        try:
            # Calculate 7-period RSI
            delta = df['Close'].diff()
            gain = (delta.where(delta > 0, 0)).rolling(window=7).mean()
            loss = (-delta.where(delta < 0, 0)).rolling(window=7).mean()
            rs = gain / loss
            df['RSI'] = 100 - (100 / (1 + rs))
            
            # Calculate gaps using numpy for better performance
            df['Gap'] = df['Open'] - df['Close'].shift(1)
            df['GapPercent'] = np.where(
                df['Close'].shift(1) != 0,
                (df['Gap'] / df['Close'].shift(1)) * 100,
                0
            )
            
            # Fill NaN values
            df.fillna(0, inplace=True)
            
            return df
            
        except Exception as e:
            logger.error(f"Error adding indicators: {e}")
            return df 