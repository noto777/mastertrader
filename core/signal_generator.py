import pandas as pd
import numpy as np
import datetime
import pytz
import yfinance as yf
import ib_insync
from decimal import Decimal
import config.config as cfg
from core.database import Database
from utils.logger import get_logger
from sqlalchemy import text

logger = get_logger(__name__)


class SignalGenerator:
    def __init__(self, db: Database, ib: ib_insync.IB):
        """Initialize SignalGenerator with database and Interactive Brokers connection."""
        self.db = db
        self.ib = ib
        self.et_tz = pytz.timezone('US/Eastern')
        # Add RSI periods for different timeframes
        self.RSI_PERIODS = {
            '15min': 7,    # Entry signals
            'daily': 7,   # Risk state
            'weekly': 7   # Risk state
        }

    def calculate_rsi(self, data: pd.DataFrame, period: int = 14) -> pd.Series:
        """Calculate RSI for the given data."""
        try:
            # Ensure we're working with the 'Close' column as a Series
            close_prices = data['Close']
            
            # Calculate price changes
            delta = close_prices.diff()
            
            # Separate gains and losses
            gains = delta.where(delta > 0, 0)
            losses = -delta.where(delta < 0, 0)
            
            # Calculate average gains and losses
            avg_gains = gains.rolling(window=period).mean()
            avg_losses = losses.rolling(window=period).mean()
            
            # Calculate RS and RSI
            rs = avg_gains / avg_losses
            rsi = 100 - (100 / (1 + rs))
            
            return rsi
            
        except Exception as e:
            logger.error(f"Error calculating RSI: {e}")
            return pd.Series(index=data.index)  # Return empty series with same index

    def detect_gaps(self, data: pd.DataFrame) -> pd.DataFrame:
        """Detect gaps in pre-market only."""
        try:
            if not self.is_premarket():
                return pd.DataFrame()  # Return empty if not pre-market
            
            if 'Close' not in data.columns or 'Open' not in data.columns:
                raise ValueError("Required columns 'Close' or 'Open' are missing.")
            
            data['GapPercent'] = (
                ((data['Open'] - data['Close'].shift(1)) / data['Close'].shift(1)) * 100
            ).fillna(0)  # Handle initial NaN
            data['GapType'] = data['GapPercent'].apply(
                lambda x: 'UP' if x > 0 else ('DOWN' if x < 0 else 'NONE')
            )

            # Ensure GapPercent and GapType are 1D
            data['GapPercent'] = data['GapPercent'].astype(float)
            return data
            
        except Exception as e:
            logger.error(f"Error detecting gaps: {e}")
            return pd.DataFrame()

    def is_premarket(self) -> bool:
        """Check if current time is in pre-market (first 15 minutes)."""
        now = datetime.datetime.now(self.et_tz)
        market_open = now.replace(hour=9, minute=30, second=0, microsecond=0)
        premarket_start = now.replace(hour=4, minute=0, second=0, microsecond=0)
        return premarket_start <= now < market_open and (now - premarket_start).seconds <= 900  # 15 minutes

    def get_rsi_state(self, symbol: str) -> dict:
        """Get RSI values for all timeframes."""
        try:
            # Get data for different timeframes
            end = datetime.datetime.now()
            weekly_start = end - datetime.timedelta(weeks=52)  # 1 year of weekly data
            daily_start = end - datetime.timedelta(days=100)   # 100 days of daily data
            
            weekly_data = yf.download(symbol, start=weekly_start, end=end, interval='1wk')
            daily_data = yf.download(symbol, start=daily_start, end=end, interval='1d')
            intraday_data = yf.download(symbol, start=end - datetime.timedelta(days=7), end=end, interval='15m')
            
            return {
                'weekly_rsi': float(self.calculate_rsi(weekly_data, self.RSI_PERIODS['weekly']).iloc[-1]),
                'daily_rsi': float(self.calculate_rsi(daily_data, self.RSI_PERIODS['daily']).iloc[-1]),
                'current_rsi': float(self.calculate_rsi(intraday_data, self.RSI_PERIODS['15min']).iloc[-1])
            }
        except Exception as e:
            logger.error(f"Error getting RSI state: {e}")
            return {}

    def check_entry_signal(self, data: pd.DataFrame) -> bool:
        """Check if we have a valid entry signal."""
        try:
            rsi = self.calculate_rsi(data, self.RSI_PERIODS['15min'])
            if len(rsi) < 3:  # Need at least 3 periods
                return False
            
            # Check if previous candle was <= 30 and current candle crossed above 30
            prev_2_rsi = float(rsi.iloc[-3])
            prev_rsi = float(rsi.iloc[-2])
            curr_rsi = float(rsi.iloc[-1])
            
            return prev_2_rsi <= 30 and prev_rsi > 30 and curr_rsi > 30
            
        except Exception as e:
            logger.error(f"Error checking entry signal: {e}")
            return False

    def get_all_time_high(self, symbol: str) -> float:
        """Get all-time high price for a symbol."""
        try:
            # Get max historical data from yfinance
            data = yf.download(symbol, start='1970-01-01')
            return float(data['High'].max())
        except Exception as e:
            logger.error(f"Error getting all-time high for {symbol}: {e}")
            return 0.0

    def calculate_price_increase(self, symbol: str, base_price: float) -> float:
        """Calculate percentage price increase from base price."""
        try:
            current_price = yf.download(symbol, period='1d')['Close'].iloc[-1]
            return ((current_price - base_price) / base_price) * 100
        except Exception as e:
            logger.error(f"Error calculating price increase for {symbol}: {e}")
            return 0.0

    def check_risk_state(self, symbol: str) -> str:
        """Check if we're in risk-on or risk-off state."""
        try:
            # Get RSI states
            rsi_state = self.get_rsi_state(symbol)
            if not rsi_state:
                self.log_risk_state_change(symbol, 'RISK_OFF', 'Unable to get RSI state')
                return 'RISK_OFF'
            
            # Get current price and highs
            current_price = yf.download(symbol, period='1d')['Close'].iloc[-1]
            year_high = yf.download(symbol, period='1y')['High'].max()
            all_time_high = self.get_all_time_high(symbol)
            
            # First check risk-off conditions
            if rsi_state['weekly_rsi'] > 70:
                self.log_risk_state_change(symbol, 'RISK_OFF', f"Weekly RSI {rsi_state['weekly_rsi']:.2f} > 70")
                return 'RISK_OFF'
            
            if current_price >= year_high:
                self.log_risk_state_change(symbol, 'RISK_OFF', f"52-week high ${current_price:.2f}")
                self.log_price_milestone(symbol, '52_WEEK_HIGH', current_price)
                return 'RISK_OFF'
            
            if current_price >= all_time_high:
                self.log_risk_state_change(symbol, 'RISK_OFF', f"All-time high ${current_price:.2f}")
                self.log_price_milestone(symbol, 'ALL_TIME_HIGH', current_price)
                return 'RISK_OFF'
            
            # Check if we've had a weekly RSI cross below 70
            previous_state = self.get_last_risk_state(symbol)
            if previous_state == 'RISK_OFF':
                # Only check daily RSI if we were previously in RISK_OFF
                if rsi_state['daily_rsi'] < 30:
                    self.log_risk_state_change(
                        symbol, 
                        'RISK_ON', 
                        f"Weekly RSI below 70 and Daily RSI crossed below 30"
                    )
                    return 'RISK_ON'
                return 'RISK_OFF'  # Stay in RISK_OFF until daily RSI < 30
            
            return previous_state or 'NEUTRAL'
            
        except Exception as e:
            logger.error(f"Error checking risk state for {symbol}: {e}")
            self.log_risk_state_change(symbol, 'RISK_OFF', f"Error: {str(e)}")
            return 'RISK_OFF'

    def get_last_risk_state(self, symbol: str) -> str:
        """Get the last recorded risk state for a symbol."""
        try:
            with self.db.engine.connect() as conn:
                result = conn.execute(
                    text("""
                        SELECT state 
                        FROM risk_states 
                        WHERE symbol = :symbol 
                        ORDER BY timestamp DESC 
                        LIMIT 1
                    """),
                    {'symbol': symbol}
                ).first()
                return result[0] if result else 'NEUTRAL'
        except Exception as e:
            logger.error(f"Error getting last risk state: {e}")
            return 'RISK_OFF'  # Default to risk-off on error

    def generate_signals(self, symbol: str):
        """Generate buy/sell signals based on strategy rules."""
        try:
            # First check risk state
            risk_state = self.check_risk_state(symbol)
            if risk_state == 'RISK_OFF':
                logger.info(f"Risk-off state for {symbol}, no new signals generated")
                return

            # Get 15-minute data for entry signals
            end_date = datetime.datetime.now()
            start_date = end_date - datetime.timedelta(days=7)
            data = yf.download(symbol, start=start_date, end=end_date, interval='15m')

            # Check for entry signal
            if self.check_entry_signal(data):
                # Check for pre-market gap
                if self.is_premarket():
                    gaps = self.detect_gaps(data)
                    if not gaps.empty:
                        gap_percent = float(gaps['GapPercent'].iloc[-1])
                        if gap_percent > 0:  # Gap up
                            logger.info(f"Gap up detected for {symbol}: {gap_percent:.2f}%")
                            # Signal will be handled by order manager for modified exit
                
                # Record entry signal
                self.db.record_signal(
                    symbol=symbol,
                    signal_type='BUY',
                    rsi_value=float(self.calculate_rsi(data, self.RSI_PERIODS['15min']).iloc[-1]),
                    signal_strength=1.0,
                    gap_percent=gap_percent if 'gap_percent' in locals() else 0.0
                )
                logger.info(f"Entry signal generated for {symbol}")

        except Exception as e:
            logger.error(f"Error generating signals for {symbol}: {e}")

    def fetch_signals(self, symbol: str = None, limit: int = 100):
        """Fetch recent signals."""
        return self.db.get_recent_signals(symbol, limit)

    def fetch_gaps(self, symbol: str = None, limit: int = 100):
        """Fetch recent gaps."""
        return self.db.get_recent_gaps(symbol, limit)

    def log_risk_state_change(self, symbol: str, new_state: str, reason: str):
        """Log risk state changes to database."""
        try:
            self.db.record_risk_state(
                symbol=symbol,
                state=new_state,
                reason=reason,
                rsi_values=self.get_rsi_state(symbol)
            )
            logger.info(f"Recorded risk state change for {symbol}: {new_state} due to {reason}")
        except Exception as e:
            logger.error(f"Error logging risk state change: {e}")

    def log_price_milestone(self, symbol: str, milestone_type: str, price: float):
        """Log price milestones (52-week high, all-time high) to database."""
        try:
            self.db.record_price_milestone(
                symbol=symbol,
                milestone_type=milestone_type,
                price=price
            )
            logger.info(f"Recorded {milestone_type} for {symbol} at ${price:.2f}")
        except Exception as e:
            logger.error(f"Error logging price milestone: {e}")
