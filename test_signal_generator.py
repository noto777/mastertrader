import pandas as pd
import numpy as np
from ib_insync import IB
from core.signal_generator import SignalGenerator
from core.database import Database
import config.config as cfg
import logging
import yfinance as yf
from datetime import datetime, timedelta

# Set up logging with more detailed format
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def test_calculate_rsi(signal_generator):
    """Test RSI calculation with real AAPL data."""
    try:
        logger.info("Testing calculate_rsi with real AAPL data...")
        # Fetch real data from yfinance
        symbol = 'AAPL'
        end_date = datetime.now()
        start_date = end_date - timedelta(days=7)
        data = yf.download(symbol, start=start_date, end=end_date, interval='1h')
        
        if data.empty:
            logger.error("Failed to fetch AAPL data for RSI test")
            return False
            
        rsi = signal_generator.calculate_rsi(data, period=cfg.RSI_PERIOD)
        logger.info(f"RSI calculation successful. Last 5 values: {rsi.tail().to_dict()}")
        return True
    except Exception as e:
        logger.error(f"Error in test_calculate_rsi: {str(e)}")
        return False

def test_detect_gaps(signal_generator):
    """Test gap detection with real AAPL data."""
    try:
        logger.info("Testing detect_gaps with real AAPL data...")
        # Fetch real data from yfinance
        symbol = 'AAPL'
        end_date = datetime.now()
        start_date = end_date - timedelta(days=7)
        data = yf.download(symbol, start=start_date, end=end_date, interval='1h')
        
        if data.empty:
            logger.error("Failed to fetch AAPL data for gap detection test")
            return False
            
        gaps = signal_generator.detect_gaps(data)
        logger.info(f"Gap detection successful. Last 5 gaps: {gaps[['GapPercent', 'GapType']].tail().to_dict('records')}")
        return True
    except Exception as e:
        logger.error(f"Error in test_detect_gaps: {str(e)}")
        return False

def test_generate_signals(signal_generator):
    """Test signal generation with real data."""
    try:
        logger.info("Testing generate_signals with real data...")
        # Test with multiple symbols
        test_symbols = ['AAPL', 'MSFT', 'GOOGL']
        
        for symbol in test_symbols:
            logger.info(f"Generating signals for {symbol}...")
            signal_generator.generate_signals(symbol)
            
            # Fetch and verify the results
            signals = signal_generator.fetch_signals(symbol)
            gaps = signal_generator.fetch_gaps(symbol)
            
            logger.info(f"Results for {symbol}:")
            logger.info(f"Generated signals: {signals}")
            logger.info(f"Detected gaps: {gaps}")
        
        return True
    except Exception as e:
        logger.error(f"Error in test_generate_signals: {str(e)}")
        return False

def main():
    """Main test execution function."""
    success = True
    try:
        # Initialize IB connection
        logger.info("Initializing IB connection...")
        ib = IB()
        try:
            ib.connect(cfg.IB_HOST, cfg.IB_PORT, cfg.IB_CLIENT_ID)
            logger.info("Successfully connected to Interactive Brokers.")
        except Exception as e:
            logger.error(f"Failed to connect to IB: {e}")
            return False

        # Initialize database and SignalGenerator
        logger.info("Initializing Database and SignalGenerator...")
        db = Database()
        signal_generator = SignalGenerator(db=db, ib=ib)

        # Run tests
        tests = [
            (test_calculate_rsi, "RSI Calculation"),
            (test_detect_gaps, "Gap Detection"),
            (test_generate_signals, "Signal Generation")
        ]

        for test_func, test_name in tests:
            logger.info(f"\n{'='*20} Testing {test_name} {'='*20}")
            if not test_func(signal_generator):
                success = False
                logger.error(f"{test_name} test failed!")
            else:
                logger.info(f"{test_name} test passed!")

    except Exception as e:
        logger.error(f"Unexpected error in main: {str(e)}")
        success = False
    finally:
        # Cleanup
        try:
            if 'ib' in locals() and ib.isConnected():
                ib.disconnect()
                logger.info("Disconnected from Interactive Brokers.")
        except Exception as e:
            logger.error(f"Error during cleanup: {str(e)}")

    # Final status
    status = "SUCCESS" if success else "FAILURE"
    logger.info(f"\n{'='*20} Test Suite Complete: {status} {'='*20}")
    return success

if __name__ == "__main__":
    main()
