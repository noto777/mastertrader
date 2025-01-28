# master_trader/main.py

import asyncio
import sys
import signal
from datetime import datetime, time, timedelta
import config.config as cfg
import utils.logger as logger_utils
from core.database import Database
from core.portfolio_manager import PortfolioManager
from core.order_manager import OrderManager
from core.signal_generator import SignalGenerator
from core.connection import IBConnection

logger_utils.setup_logging()
logger = logger_utils.get_logger(__name__)

class TradingSystem:
    def __init__(self):
        """Initialize trading system components."""
        self.connection = IBConnection()
        self.db = Database()
        self.order_manager = OrderManager(self.connection, self.db)
        self.portfolio_manager = PortfolioManager(self.connection, self.db, self.order_manager)
        self.signal_generator = SignalGenerator(self.db)
        self.shutdown_event = asyncio.Event()

    async def connect(self):
        """Connect to Interactive Brokers."""
        try:
            connected = await self.connection.connect()
            if connected:
                logger.info("Connected to Interactive Brokers")
                return True
            return False
        except Exception as e:
            logger.error(f"Failed to connect to IB: {e}")
            return False

    async def check_trading_hours(self) -> bool:
        """Check if current time is within trading hours."""
        now = datetime.now().time()
        return (cfg.MARKET_OPEN <= now <= cfg.MARKET_CLOSE or 
                cfg.PREMARKET_OPEN <= now < cfg.MARKET_OPEN or
                cfg.MARKET_CLOSE < now <= cfg.AFTERMARKET_CLOSE)

    async def run_task(self, task_name, coro, interval):
        """Run a periodic async task with trading hours check."""
        while not self.shutdown_event.is_set():
            try:
                if await self.check_trading_hours():
                    logger.info(f"Running task: {task_name}")
                    await coro()
                else:
                    logger.info(f"Outside trading hours. {task_name} sleeping...")
                    await asyncio.sleep(300)  # Sleep for 5 minutes outside trading hours
                    continue
            except Exception as e:
                logger.error(f"Error in task {task_name}: {str(e)}", exc_info=True)
            await asyncio.sleep(interval)

    async def monitor_risk_state(self):
        """Monitor and update risk state for all symbols."""
        while not self.shutdown_event.is_set():
            try:
                if await self.check_trading_hours():
                    for symbol in cfg.CORE_POSITIONS:
                        current_state = self.db.get_latest_risk_state(symbol)
                        if current_state == 'RISK_OFF':
                            await self.portfolio_manager.handle_risk_off_core(symbol)
            except Exception as e:
                logger.error(f"Error monitoring risk state: {e}", exc_info=True)
            await asyncio.sleep(cfg.RISK_CHECK_INTERVAL)

    async def manage_sessions(self):
        """Manage trading sessions and order transitions."""
        while not self.shutdown_event.is_set():
            try:
                now = datetime.now().time()
                
                # Pre-market to Regular Hours transition
                if now >= cfg.MARKET_OPEN and now < (datetime.combine(datetime.today(), cfg.MARKET_OPEN) + 
                            timedelta(seconds=60)).time():
                    await self.order_manager.handle_session_transition('PRE', 'RTH')
                    
                # Regular Hours to After Hours transition
                elif now >= cfg.MARKET_CLOSE and now < (datetime.combine(datetime.today(), cfg.MARKET_CLOSE) + 
                            timedelta(seconds=60)).time():
                    await self.order_manager.handle_session_transition('RTH', 'AFTER')
                    
            except Exception as e:
                logger.error(f"Error managing sessions: {e}", exc_info=True)
            await asyncio.sleep(30)  # Check every 30 seconds

    async def track_performance(self):
        """Track and record system performance."""
        while not self.shutdown_event.is_set():
            try:
                if await self.check_trading_hours():
                    await self.portfolio_manager.track_performance()
                await asyncio.sleep(cfg.PERFORMANCE_UPDATE_INTERVAL)
            except Exception as e:
                logger.error(f"Error tracking performance: {e}", exc_info=True)
                await asyncio.sleep(10)

    def setup_shutdown_handlers(self):
        """Setup shutdown signal handlers."""
        def shutdown_handler(sig, frame):
            logger.info("Shutdown signal received")
            self.shutdown_event.set()
            
        signal.signal(signal.SIGINT, shutdown_handler)
        signal.signal(signal.SIGTERM, shutdown_handler)

    async def shutdown(self):
        """Clean shutdown of the trading system."""
        logger.info("Initiating trading system shutdown...")
        
        try:
            # Cancel all pending orders
            await self.order_manager.cancel_all_orders()
            
            # Disconnect from IB
            await self.connection.disconnect()
            
            # Close database connection
            await self.db.close()
            
            logger.info("Trading system shutdown complete")
            
        except Exception as e:
            logger.error(f"Error during shutdown: {e}", exc_info=True)

    async def run(self):
        """Main run loop."""
        try:
            # Connect to IB
            if not await self.connect():
                return
                
            # Setup shutdown handlers
            self.setup_shutdown_handlers()
            
            # Create tasks
            tasks = [
                asyncio.create_task(self.run_task("Manage Core Positions", self.portfolio_manager.manage_core_position_all, cfg.TRADING_LOOP_INTERVAL)),
                asyncio.create_task(self.run_task("Signal Generator", self.signal_generator.generate_signals_all, cfg.SIGNAL_CHECK_INTERVAL)),
                asyncio.create_task(self.run_task("Gap Detector", self.signal_generator.detect_gaps_all, cfg.GAP_CHECK_INTERVAL)),
                asyncio.create_task(self.monitor_risk_state()),
                asyncio.create_task(self.manage_sessions()),
                asyncio.create_task(self.track_performance())
            ]
            
            logger.info("Trading system started")
            
            # Wait for shutdown signal
            await self.shutdown_event.wait()
            
            # Cancel all tasks
            for task in tasks:
                task.cancel()
                
            # Wait for tasks to complete
            await asyncio.gather(*tasks, return_exceptions=True)
            
            # Clean shutdown
            await self.shutdown()
            
        except Exception as e:
            logger.error(f"Critical error in trading system: {e}", exc_info=True)
            await self.shutdown()

async def main():
    """Main entry point."""
    trading_system = TradingSystem()
    await trading_system.run()

if __name__ == "__main__":
    asyncio.run(main())
