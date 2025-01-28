# core/database.py

import sqlite3
import datetime
import shutil
from pathlib import Path
from decimal import Decimal
import logging
import config.config as cfg
from sqlalchemy import create_engine, Column, String, Float, Integer, DateTime, Boolean, JSON
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from sqlalchemy.sql import text
from typing import Optional, Dict

logger = logging.getLogger(__name__)

Base = declarative_base()

class Signal(Base):
    __tablename__ = 'signals'
    id = Column(Integer, primary_key=True)
    symbol = Column(String, nullable=False)
    signal_type = Column(String, nullable=False)  # 'BUY' or 'SELL'
    rsi_value = Column(Float, nullable=True)
    signal_strength = Column(Float, nullable=True)
    gap_percent = Column(Float, nullable=True)
    timestamp = Column(DateTime, default=datetime.datetime.utcnow)

class Gap(Base):
    __tablename__ = 'gaps'
    id = Column(Integer, primary_key=True)
    symbol = Column(String, nullable=False)
    gap_percent = Column(Float, nullable=False)
    previous_close = Column(Float, nullable=False)
    current_open = Column(Float, nullable=False)
    gap_type = Column(String, nullable=False)  # 'UP' or 'DOWN'
    timestamp = Column(DateTime, default=datetime.datetime.utcnow)

class RiskState(Base):
    __tablename__ = 'risk_states'
    id = Column(Integer, primary_key=True)
    symbol = Column(String, nullable=False)
    state = Column(String, nullable=False)
    reason = Column(String, nullable=False)
    weekly_rsi = Column(Float)
    daily_rsi = Column(Float)
    current_rsi = Column(Float)
    timestamp = Column(DateTime, default=datetime.datetime.utcnow)

class PriceMilestone(Base):
    __tablename__ = 'price_milestones'
    id = Column(Integer, primary_key=True)
    symbol = Column(String, nullable=False)
    milestone_type = Column(String, nullable=False)
    price = Column(Float, nullable=False)
    timestamp = Column(DateTime, default=datetime.datetime.utcnow)

class CorePosition(Base):
    __tablename__ = 'core_positions'
    id = Column(Integer, primary_key=True)
    symbol = Column(String, nullable=False)
    lot_id = Column(String, nullable=False)
    quantity = Column(Integer, nullable=False)
    price = Column(Float, nullable=False)
    timestamp = Column(DateTime, default=datetime.datetime.utcnow)

class UnwindCycle(Base):
    __tablename__ = 'unwind_cycles'
    id = Column(Integer, primary_key=True)
    symbol = Column(String, nullable=False)
    base_price = Column(Float, nullable=False)
    cycle_count = Column(Integer, nullable=False)
    timestamp = Column(DateTime, default=datetime.datetime.utcnow)

class CoreProgress(Base):
    __tablename__ = 'core_progress'
    id = Column(Integer, primary_key=True)
    symbol = Column(String, nullable=False)
    current_percentage = Column(Float, nullable=False)
    target_percentage = Column(Float, nullable=False)
    cycles_completed = Column(Integer, nullable=False)
    cycles_remaining = Column(Integer, nullable=False)
    timestamp = Column(DateTime, default=datetime.datetime.utcnow)

class PositionCategory(Base):
    __tablename__ = 'position_categories'
    id = Column(Integer, primary_key=True)
    symbol = Column(String, nullable=False)
    total_size = Column(Integer, nullable=False)
    core_size = Column(Integer, nullable=False)
    trading_size = Column(Integer, nullable=False)
    timestamp = Column(DateTime, default=datetime.datetime.utcnow)

class TradePerformance(Base):
    __tablename__ = 'trade_performance'
    id = Column(Integer, primary_key=True)
    symbol = Column(String, nullable=False)
    entry_price = Column(Float, nullable=False)
    exit_price = Column(Float, nullable=False)
    quantity = Column(Integer, nullable=False)
    entry_time = Column(DateTime, nullable=False)
    exit_time = Column(DateTime, nullable=False)
    profit_loss = Column(Float, nullable=False)
    profit_loss_percent = Column(Float, nullable=False)
    trade_type = Column(String, nullable=False)  # 'core_build', 'core_unwind', 'trading'
    risk_state = Column(String, nullable=False)
    rsi_entry = Column(Float)
    rsi_exit = Column(Float)
    gap_present = Column(Boolean, default=False)
    gap_size = Column(Float)

class PortfolioPerformance(Base):
    __tablename__ = 'portfolio_performance'
    id = Column(Integer, primary_key=True)
    timestamp = Column(DateTime, default=datetime.datetime.utcnow)
    total_value = Column(Float, nullable=False)
    cash_balance = Column(Float, nullable=False)
    total_profit_loss = Column(Float, nullable=False)
    daily_profit_loss = Column(Float, nullable=False)
    total_trades = Column(Integer, nullable=False)
    winning_trades = Column(Integer, nullable=False)
    core_position_values = Column(JSON)  # Store as JSON
    risk_states = Column(JSON)  # Store as JSON

class CorePerformance(Base):
    __tablename__ = 'core_performance'
    id = Column(Integer, primary_key=True)
    symbol = Column(String, nullable=False)
    timestamp = Column(DateTime, default=datetime.datetime.utcnow)
    target_percentage = Column(Float, nullable=False)
    current_percentage = Column(Float, nullable=False)
    total_cost = Column(Float, nullable=False)
    market_value = Column(Float, nullable=False)
    unrealized_pl = Column(Float, nullable=False)
    build_cycles_completed = Column(Integer, nullable=False)
    unwind_cycles_completed = Column(Integer, nullable=False)

class DatabaseError(Exception):
    """Custom exception for database errors."""
    pass

class Database:
    _instance = None
    DB_PATH = Path("data/trading.db")

    def __new__(cls):
        """Singleton pattern to ensure one database connection."""
        if cls._instance is None:
            cls._instance = super(Database, cls).__new__(cls)
            cls._instance.engine = create_engine(cfg.DB_CONNECTION_STRING, echo=False)
            cls._instance.Session = sessionmaker(bind=cls._instance.engine)
            cls._instance.session = cls._instance.Session()
            cls._instance.setup_database()
            logger.info(f"Connected to database at {cls.DB_PATH}")
        return cls._instance

    def execute_query(self, query, params=None):
        """
        Execute an SQL query with optional parameters.
        Logs and raises DatabaseError on failure.
        """
        try:
            if params:
                self.cursor.execute(query, params)
            else:
                self.cursor.execute(query)
            self.conn.commit()
            return self.cursor
        except sqlite3.Error as e:
            logger.error(f"Database error: {e} | Query: {query} | Params: {params}")
            raise DatabaseError(f"Error executing query: {e}")

    def fetch_all(self, query, params=None):
        """
        Fetch all results for a query.
        """
        try:
            cursor = self.execute_query(query, params)
            return cursor.fetchall()
        except DatabaseError as e:
            logger.error(f"Error fetching data: {str(e)}")
            return []

    def fetch_one(self, query, params=None):
        """
        Fetch a single result for a query.
        """
        try:
            cursor = self.execute_query(query, params)
            return cursor.fetchone()
        except DatabaseError as e:
            logger.error(f"Error fetching single record: {str(e)}")
            return None

    def backup_database(self):
        """Backup the database with a timestamped filename."""
        try:
            timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
            backup_dir = Path("data/backups")
            backup_dir.mkdir(parents=True, exist_ok=True)
            backup_path = backup_dir / f"trading_backup_{timestamp}.db"
            shutil.copy2(self.DB_PATH, backup_path)
            logger.info(f"Database backed up successfully to {backup_path}")
            return True
        except Exception as e:
            logger.error(f"Error backing up database: {e}")
            return False

    def setup_database(self):
        """
        Create tables and indexes if they don't exist.
        """
        Base.metadata.create_all(self.engine)
        logger.info("Database tables created or verified successfully.")

    def record_signal(self, symbol, signal_type, rsi_value=None, signal_strength=None, gap_percent=None):
        """Insert a new signal into the database."""
        try:
            logger.debug(f"record_signal called with symbol={symbol}, signal_type={signal_type}, "
                         f"rsi_value={rsi_value}, signal_strength={signal_strength}, gap_percent={gap_percent}")
            signal = Signal(
                symbol=symbol,
                signal_type=signal_type,
                rsi_value=rsi_value,
                signal_strength=signal_strength,
                gap_percent=gap_percent
            )
            self.session.add(signal)
            self.session.commit()
            logger.info(f"Recorded signal: {signal_type} for {symbol}")
        except Exception as e:
            self.session.rollback()
            logger.error(f"Error recording signal for {symbol}: {e}")

    def record_gap(self, symbol, gap_percent, previous_close, current_open, gap_type):
        """Insert a new gap into the database."""
        try:
            logger.debug(f"record_gap called with symbol={symbol}, gap_percent={gap_percent}, "
                         f"previous_close={previous_close}, current_open={current_open}, gap_type={gap_type}")
            gap = Gap(
                symbol=symbol,
                gap_percent=gap_percent,
                previous_close=previous_close,
                current_open=current_open,
                gap_type=gap_type
            )
            self.session.add(gap)
            self.session.commit()
            logger.info(f"Recorded gap: {gap_type} for {symbol} ({gap_percent:.2f}%)")
        except Exception as e:
            self.session.rollback()
            logger.error(f"Error recording gap for {symbol}: {e}")

    def get_recent_signals(self, symbol: str = None, limit: int = 100):
        """
        Fetch recent signals from the database.
        """
        try:
            query = self.session.query(Signal)
            if symbol:
                query = query.filter(Signal.symbol == symbol)
            signals = query.order_by(Signal.timestamp.desc()).limit(limit).all()
            return [
                {
                    'symbol': signal.symbol,
                    'action': signal.signal_type,
                    'rsi_value': signal.rsi_value,
                    'signal_strength': signal.signal_strength,
                    'gap_percent': signal.gap_percent,
                    'timestamp': signal.timestamp
                }
                for signal in signals
            ]
        except Exception as e:
            logger.error(f"Error fetching recent signals: {e}")
            return []

    def get_recent_gaps(self, symbol: str = None, limit: int = 100):
        """
        Fetch recent gaps from the database.
        """
        try:
            query = self.session.query(Gap)
            if symbol:
                query = query.filter(Gap.symbol == symbol)
            gaps = query.order_by(Gap.timestamp.desc()).limit(limit).all()
            return [
                {
                    'symbol': gap.symbol,
                    'gap_percent': gap.gap_percent,
                    'gap_type': gap.gap_type,
                    'previous_close': gap.previous_close,
                    'current_open': gap.current_open,
                    'timestamp': gap.timestamp
                }
                for gap in gaps
            ]
        except Exception as e:
            logger.error(f"Error fetching recent gaps: {e}")
            return []

    def get_all_symbols(self):
        """
        Fetch all distinct symbols from signals and gaps tables.
        """
        try:
            signal_symbols = self.session.query(Signal.symbol).distinct()
            gap_symbols = self.session.query(Gap.symbol).distinct()
            symbols = set([s.symbol for s in signal_symbols] + [g.symbol for g in gap_symbols])
            logger.debug(f"All symbols fetched: {symbols}")
            return list(symbols)
        except Exception as e:
            logger.error(f"Error fetching all symbols: {e}")
            return []

    def create_tables(self):
        """Create necessary database tables."""
        try:
            with self.engine.connect() as conn:
                # Existing tables...

                # Risk State Table
                conn.execute(text("""
                    CREATE TABLE IF NOT EXISTS risk_states (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        symbol TEXT NOT NULL,
                        state TEXT NOT NULL,
                        reason TEXT NOT NULL,
                        weekly_rsi REAL,
                        daily_rsi REAL,
                        current_rsi REAL,
                        timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
                    )
                """))

                # Price Milestones Table
                conn.execute(text("""
                    CREATE TABLE IF NOT EXISTS price_milestones (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        symbol TEXT NOT NULL,
                        milestone_type TEXT NOT NULL,
                        price REAL NOT NULL,
                        timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
                    )
                """))

                # Order Status Table
                conn.execute(text("""
                    CREATE TABLE IF NOT EXISTS order_status (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        order_id INTEGER NOT NULL,
                        status TEXT NOT NULL,
                        filled INTEGER,
                        remaining INTEGER,
                        avg_fill_price REAL,
                        last_fill_price REAL,
                        why_held TEXT,
                        timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
                    )
                """))

        except Exception as e:
            logger.error(f"Error creating tables: {e}")
            raise

    def record_risk_state(self, symbol: str, state: str, reason: str, rsi_values: dict):
        """Record risk state changes to database."""
        try:
            with self.engine.connect() as conn:
                conn.execute(
                    text("""
                        INSERT INTO risk_states 
                        (symbol, state, reason, weekly_rsi, daily_rsi, current_rsi)
                        VALUES (:symbol, :state, :reason, :weekly_rsi, :daily_rsi, :current_rsi)
                    """),
                    {
                        'symbol': symbol,
                        'state': state,
                        'reason': reason,
                        'weekly_rsi': rsi_values.get('weekly_rsi', None),
                        'daily_rsi': rsi_values.get('daily_rsi', None),
                        'current_rsi': rsi_values.get('current_rsi', None)
                    }
                )

        except Exception as e:
            logger.error(f"Error recording risk state: {e}")

    def record_price_milestone(self, symbol: str, milestone_type: str, price: float):
        """Record price milestones to database."""
        try:
            with self.engine.connect() as conn:
                conn.execute(
                    text("""
                        INSERT INTO price_milestones 
                        (symbol, milestone_type, price)
                        VALUES (:symbol, :milestone_type, :price)
                    """),
                    {
                        'symbol': symbol,
                        'milestone_type': milestone_type,
                        'price': price
                    }
                )

        except Exception as e:
            logger.error(f"Error recording price milestone: {e}")

    def record_core_position(self, symbol: str, lot_id: str, quantity: int, price: float):
        """Record a core position."""
        try:
            core_position = CorePosition(
                symbol=symbol,
                lot_id=lot_id,
                quantity=quantity,
                price=price
            )
            self.session.add(core_position)
            self.session.commit()
            logger.info(f"Recorded core position for {symbol}: {quantity} shares")
        except Exception as e:
            self.session.rollback()
            logger.error(f"Error recording core position for {symbol}: {e}")

    def record_unwind_cycle(self, symbol: str, base_price: float):
        """Record a core unwinding cycle."""
        try:
            unwind = UnwindCycle(
                symbol=symbol,
                base_price=base_price,
                cycle_count=1
            )
            self.session.add(unwind)
            self.session.commit()
            logger.info(f"Recorded unwind cycle for {symbol}")
        except Exception as e:
            self.session.rollback()
            logger.error(f"Error recording unwind cycle for {symbol}: {e}")

    def record_core_progress(self, symbol: str, current_percentage: float, 
                            target_percentage: float, cycles_completed: int,
                            cycles_remaining: int):
        """Record core position building progress."""
        try:
            progress = CoreProgress(
                symbol=symbol,
                current_percentage=current_percentage,
                target_percentage=target_percentage,
                cycles_completed=cycles_completed,
                cycles_remaining=cycles_remaining
            )
            self.session.add(progress)
            self.session.commit()
            logger.info(f"Recorded core progress for {symbol}: {current_percentage:.2f}%")
        except Exception as e:
            self.session.rollback()
            logger.error(f"Error recording core progress for {symbol}: {e}")

    def record_position_category(self, symbol: str, total_size: int, 
                               core_size: int, trading_size: int):
        """Record position categorization."""
        try:
            category = PositionCategory(
                symbol=symbol,
                total_size=total_size,
                core_size=core_size,
                trading_size=trading_size
            )
            self.session.add(category)
            self.session.commit()
            logger.info(f"Recorded position category for {symbol}")
        except Exception as e:
            self.session.rollback()
            logger.error(f"Error recording position category: {e}")

    def get_latest_position_category(self, symbol: str) -> Optional[Dict]:
        """Get the latest position categorization."""
        try:
            category = self.session.query(PositionCategory)\
                .filter(PositionCategory.symbol == symbol)\
                .order_by(PositionCategory.timestamp.desc())\
                .first()
            
            if category:
                return {
                    'symbol': category.symbol,
                    'total_size': category.total_size,
                    'core_size': category.core_size,
                    'trading_size': category.trading_size,
                    'timestamp': category.timestamp
                }
            return None
        except Exception as e:
            logger.error(f"Error getting position category: {e}")
            return None

    def record_trade_performance(self, trade_data: Dict):
        """Record individual trade performance."""
        try:
            trade = TradePerformance(**trade_data)
            self.session.add(trade)
            self.session.commit()
        except Exception as e:
            self.session.rollback()
            logger.error(f"Error recording trade performance: {e}")

    def record_portfolio_performance(self, performance_data: Dict):
        """Record portfolio-level performance."""
        try:
            perf = PortfolioPerformance(**performance_data)
            self.session.add(perf)
            self.session.commit()
        except Exception as e:
            self.session.rollback()
            logger.error(f"Error recording portfolio performance: {e}")

    def record_core_performance(self, core_data: Dict):
        """Record core position performance."""
        try:
            perf = CorePerformance(**core_data)
            self.session.add(perf)
            self.session.commit()
        except Exception as e:
            self.session.rollback()
            logger.error(f"Error recording core performance: {e}")

if __name__ == "__main__":
    db = Database()
    db.setup_database()
