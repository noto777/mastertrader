import sys
import os

# Adjust the Python path to include the project root
current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.abspath(os.path.join(current_dir))
sys.path.append(project_root)

from core.database import Database
from utils.logger import setup_logging, get_logger

def add_new_tables():
    setup_logging()
    logger = get_logger(__name__)
    db = Database()
    
    try:
        conn = db.get_connection()
        cursor = conn.cursor()

        # Create signals table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS signals (
                signal_id INTEGER PRIMARY KEY AUTOINCREMENT,
                symbol TEXT NOT NULL,
                signal_type TEXT NOT NULL CHECK (signal_type IN ('BUY', 'SELL')),
                signal_strength REAL,
                rsi_value REAL,
                gap_percent REAL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                processed BOOLEAN DEFAULT FALSE
            )
        ''')
        logger.info("Created signals table")

        # Create gaps table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS gaps (
                gap_id INTEGER PRIMARY KEY AUTOINCREMENT,
                symbol TEXT NOT NULL,
                gap_date TIMESTAMP NOT NULL,
                gap_percent REAL NOT NULL,
                pre_gap_price REAL NOT NULL,
                post_gap_price REAL NOT NULL,
                gap_type TEXT CHECK (gap_type IN ('UP', 'DOWN')),
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        logger.info("Created gaps table")

        # Create settings table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS settings (
                setting_id INTEGER PRIMARY KEY AUTOINCREMENT,
                setting_name TEXT NOT NULL UNIQUE,
                setting_value TEXT NOT NULL,
                description TEXT,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        logger.info("Created settings table")

        # Create errors table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS errors (
                error_id INTEGER PRIMARY KEY AUTOINCREMENT,
                error_type TEXT NOT NULL,
                error_message TEXT NOT NULL,
                stack_trace TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        logger.info("Created errors table")

        # Add indexes for new tables
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_signals_symbol ON signals (symbol)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_gaps_symbol ON gaps (symbol)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_settings_name ON settings (setting_name)')
        logger.info("Created indexes for new tables")

        # Insert default settings
        cursor.execute('''
            INSERT OR IGNORE INTO settings 
            (setting_name, setting_value, description) 
            VALUES 
            ('RSI_OVERSOLD', '30', 'RSI oversold threshold'),
            ('RSI_OVERBOUGHT', '70', 'RSI overbought threshold'),
            ('TRADING_LOOP_INTERVAL', '300', 'Trading loop interval in seconds'),
            ('GAP_THRESHOLD', '2.0', 'Minimum gap percentage to trigger signal')
        ''')
        logger.info("Inserted default settings")

        conn.commit()
        logger.info("Successfully added new tables and default settings")

    except Exception as e:
        logger.error(f"Error adding new tables: {str(e)}")
        if conn:
            conn.rollback()
    finally:
        if conn:
            conn.close()

if __name__ == "__main__":
    add_new_tables() 