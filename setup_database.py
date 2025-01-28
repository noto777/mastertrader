import sys
import os

# Adjust the Python path to include the project root
current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.abspath(os.path.join(current_dir))
sys.path.append(project_root)

from core.database import Database
from utils.logger import setup_logger

def main():
    # Initialize Logger with the module name
    logger = setup_logger(__name__)

    # Initialize Database
    db = Database()
    
    # Define table creation queries
    signals_table = """
    CREATE TABLE IF NOT EXISTS signals (
        signal_id INTEGER PRIMARY KEY AUTOINCREMENT,
        symbol TEXT NOT NULL,
        signal_type TEXT NOT NULL,  -- 'BUY' or 'SELL'
        rsi_value REAL,
        signal_strength REAL,
        gap_percent REAL,
        processed INTEGER DEFAULT 0,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    """
    db.execute_query(signals_table)
    logger.info("Ensured 'signals' table exists.")

    orders_table = """
    CREATE TABLE IF NOT EXISTS orders (
        order_id INTEGER PRIMARY KEY AUTOINCREMENT,
        symbol TEXT NOT NULL,
        order_type TEXT NOT NULL,  -- 'BUY' or 'SELL'
        quantity REAL NOT NULL,
        price REAL NOT NULL,
        stop_loss REAL,
        take_profit REAL,
        status TEXT NOT NULL,  -- 'PENDING', 'FILLED', etc.
        filled REAL DEFAULT 0.0,
        avg_fill_price REAL,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    """
    db.execute_query(orders_table)
    logger.info("Ensured 'orders' table exists.")

    # Add other table creation queries as needed

if __name__ == "__main__":
    main()