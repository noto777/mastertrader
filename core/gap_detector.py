import asyncio
import datetime
import pytz
from ib_insync import util
from core.database import Database
from utils.logger import get_logger
from decimal import Decimal

logger = get_logger(__name__)

class GapDetector:
    def __init__(self, ib, db, portfolio_manager):
        self.ib = ib
        self.db = db
        self.portfolio_manager = portfolio_manager
        self.et_tz = pytz.timezone('US/Eastern')
        self.check_times = [
            datetime.time(4, 0),    # Pre-market open
            datetime.time(16, 30)   # 30 minutes after market close
        ]

    async def monitor_gaps(self):
        """Monitor for gap-ups at specified times."""
        while True:
            now = datetime.datetime.now(self.et_tz).time()
            if now in self.check_times:
                logger.info(f"Checking for gap-ups at {now}")
                symbols = self.db.get_all_symbols()
                for symbol in symbols:
                    await self.handle_gap_up(symbol)
                await asyncio.sleep(60)  # Prevent multiple checks within the same minute
            await asyncio.sleep(30)  # Check every 30 seconds

    async def handle_gap_up(self, symbol: str):
        """Handle gap-up logic for a specific symbol."""
        try:
            current_price = self.portfolio_manager.get_current_price(symbol)
            active_lots = self.db.get_active_lots(symbol=symbol, lot_type='TRADING')
            for lot in active_lots:
                entry_price = Decimal(str(lot['entry_price']))
                profit_target = entry_price * Decimal('1.01')  # 1% profit target

                if current_price >= profit_target:
                    logger.info(f"Gap-up detected for {symbol}. Current price: {current_price} >= Target: {profit_target}")
                    # Adjust sell order
                    await self.adjust_sell_order(symbol, lot, current_price)

        except Exception as e:
            logger.error(f"Error handling gap-up for {symbol}: {str(e)}")

    async def adjust_sell_order(self, symbol: str, lot, current_price: Decimal):
        """Cancel existing sell orders and place new ones at the current price."""
        try:
            # Cancel existing sell orders for this lot
            sell_orders = self.db.get_open_sell_orders(lot_id=lot['lot_id'])
            for order_id in sell_orders:
                self.ib.cancelOrder(order_id)
                logger.info(f"Cancelled existing sell order {order_id} for lot {lot['lot_id']}")

            # Place a new sell order slightly below the current price to ensure quick execution
            new_limit_price = float(current_price * Decimal('0.995'))  # 0.5% below current price
            quantity = lot['quantity']
            logger.info(f"Placing new limit sell order for {quantity} shares of {symbol} at {new_limit_price}")
            trade = self.portfolio_manager.order_manager.place_limit_order(symbol, 'SELL', quantity, new_limit_price)
            asyncio.create_task(trade)

        except Exception as e:
            logger.error(f"Error adjusting sell order for {symbol}: {str(e)}") 