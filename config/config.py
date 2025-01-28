from datetime import time

# Interactive Brokers Connection
IB_HOST = '127.0.0.1'
IB_PORT = 7497
IB_CLIENT_ID = 3

# RSI Parameters
RSI_PERIOD = 7  # Used for all timeframes (15min, daily, weekly)
RSI_OVERSOLD = 30  # Entry signal threshold
RSI_OVERBOUGHT = 70  # Risk-off threshold

# Position Management
ORDER_SIZE_PERCENT = 0.01  # 1% position size for initial orders
RETAIN_PERCENT = 0.25      # Keep 25% for core building
MAX_TOTAL_INVESTED = 0.80  # Maximum 80% invested
MIN_CASH_RESERVE = 0.20    # Minimum 20% cash
MAX_POSITION_BUFFER = 0.05  # Maximum 5% above core target

# Core Position Definitions
CORE_POSITIONS = {
    'SOXL': 0.05,  # 5% target
    'TQQQ': 0.03,  # 3% target - replacing NVDL
    'UPRO': 0.02,  # 2% target - replacing BITX
    'SPXL': 0.04   # 4% target - replacing AAPU
}

# Risk Management
PROFIT_TARGET_PERCENT = 0.01     # 1% profit target
CORE_UNWIND_PERCENT = 0.05       # Sell 5% of core
PRICE_INCREASE_TRIGGER = 0.02    # Every 2% price increase

# Gap Detection
GAP_THRESHOLD = 0.01  # 1% minimum gap size
PREMARKET_GAP_CHECK_MINUTES = 15  # Check first 15 minutes only

# Trading Sessions
PREMARKET_START = '04:00:00'
MARKET_OPEN = time(9, 30)
MARKET_CLOSE = time(16, 0)
AFTERMARKET_END = '20:00:00'

# Order Session Management
ORDER_SESSIONS = {
    'PREMARKET': {
        'start': '04:00:00',
        'end': '09:30:00',
        'cancel_at_end': True     # Cancel unfilled orders at session end
    },
    'RTH': {
        'start': '09:30:00',
        'end': '16:00:00',
        'cancel_at_end': True     # Cancel unfilled orders at session end
    },
    'AFTERHOURS': {
        'start': '16:00:00',
        'end': '20:00:00',
        'cancel_at_end': True     # Cancel unfilled orders at session end
    }
}

# Order Persistence
RESUBMIT_ORDERS_ACROSS_SESSIONS = True  # If True, resubmit canceled orders in next session
ORDER_RESUBMIT_DELAY = 5  # Seconds to wait before resubmitting order in new session

# Lot Management
USE_TAX_OPTIMIZER = True  # Use IB's tax optimizer for lot selection
TRACK_LOTS_INDIVIDUALLY = True  # Track each lot separately

# Market Data Parameters
BAR_SIZE = '15 mins'
DURATION = '2 D'

# Logging
LOG_FILE_PATH = 'logs/trading_system.log'
LOG_LEVEL = 'INFO'
LOG_FORMAT = '%(asctime)s - %(name)s - %(levelname)s - %(message)s'

# Database
DB_CONNECTION_STRING = 'sqlite:///data/trading.db'

# Trading Loop Interval
TRADING_LOOP_INTERVAL = 60

# Symbols
CORE_SYMBOLS = ['SOXL', 'TQQQ', 'UPRO', 'SPXL']
TRADING_SYMBOLS = ['TSLL', 'CURE', 'NAIL']

# Email Notifications
SMTP_SERVER = 'smtp.example.com'
SMTP_PORT = 587
EMAIL_USER = 'your_email@example.com'
EMAIL_PASSWORD = 'your_password'
ALERT_RECIPIENTS = ['alert_recipient@example.com']
EMAIL_ALERTS_ENABLED = True

# Trading Parameters
INITIAL_CAPITAL = 100000.0

# Trading Hours
PREMARKET_OPEN = time(4, 0)
AFTERMARKET_CLOSE = time(20, 0)

# Intervals (in seconds)
SIGNAL_CHECK_INTERVAL = 300  # 5 minutes
GAP_CHECK_INTERVAL = 60
RISK_CHECK_INTERVAL = 300
PERFORMANCE_UPDATE_INTERVAL = 300


