import ib_insync
import asyncio
import typing
from datetime import datetime
from ib_insync import LimitOrder, MarketOrder, util
from utils.logger import setup_logger
from core.database import Database
import tenacity  # For retry logic
from decimal import Decimal
from config.config import (
    ORDER_SESSIONS, RESUBMIT_ORDERS_ACROSS_SESSIONS, ORDER_RESUBMIT_DELAY,
    USE_TAX_OPTIMIZER, PROFIT_TARGET_PERCENT, ORDER_SIZE_PERCENT, RETAIN_PERCENT,
    CORE_POSITIONS, MAX_POSITION_BUFFER, MIN_CASH_RESERVE
)

class OrderManager:
    def __init__(self, ib, db: Database):
        self.logger = setup_logger(__name__)
        self.ib = ib
        self.db = db
        self.active_orders = {}  # Track active orders by session

    def disconnect(self):
        """Disconnect from IB."""
        try:
            if self.ib.isConnected():
                self.ib.disconnect()
                self.logger.info("Disconnected from Interactive Brokers (IB).")
        except Exception as e:
            self.logger.error(f"Error disconnecting from IB: {e}")

    @tenacity.retry(
        stop=tenacity.stop_after_attempt(3),
        wait=tenacity.wait_exponential(multiplier=1, min=2, max=10),
        reraise=True
    )
    async def _retryable_place_order(self, contract, order):
        """Place order with retry logic."""
        trade = self.ib.placeOrder(contract, order)
        self.record_order_status(trade)  # Initial status
        
        # Register callback for status updates
        trade.statusEvent += self.record_order_status
        
        return trade

    async def place_limit_order(self, symbol: str, action: str, quantity: int, limit_price: float) -> bool:
        """Place a limit order and track it in the database."""
        try:
            # Validate inputs
            if action not in ['BUY', 'SELL']:
                raise ValueError(f"Invalid action: {action}")
            if quantity <= 0 or limit_price <= 0:
                raise ValueError(f"Invalid quantity or price. Quantity: {quantity}, Price: {limit_price}")

            # Qualify contract
            contract = util.ib.qualifyContracts(symbol)[0]

            # Create and place the order
            order = LimitOrder(action, quantity, limit_price)
            trade = await self._retryable_place_order(contract, order)

            # Wait for trade to complete
            while not trade.isDone():
                await asyncio.sleep(0.1)

            # Handle order completion
            if trade.orderStatus.status in ['Filled', 'Submitted']:
                self.logger.info(f"Order placed: {action} {quantity} {symbol} at {limit_price}")
                return True
            else:
                self.logger.error(f"Order failed: {action} {quantity} {symbol} at {limit_price}")
                return False

        except Exception as e:
            self.logger.error(f"Error placing order for {symbol}: {e}")
            return False

    def get_order_status(self, order_id: int):
        """Retrieve the current status of an order."""
        try:
            order = self.db.get_order(order_id)
            if order:
                self.logger.info(f"Order ID {order_id} status: {order['status']}")
            return order
        except Exception as e:
            self.logger.error(f"Error getting order status for ID {order_id}: {e}")
            return None

    def cancel_order(self, order_id: int) -> bool:
        """Cancel an order."""
        try:
            order = self.db.get_order(order_id)
            if not order:
                self.logger.warning(f"Order ID {order_id} not found.")
                return False

            # Cancel via IB
            self.ib.cancelOrder(order_id)
            self.logger.info(f"Order ID {order_id} canceled.")

            # Update DB status
            self.db.update_order_status(order_id, 'CANCELLED')
            return True
        except Exception as e:
            self.logger.error(f"Error canceling order ID {order_id}: {e}")
            return False
    
    def get_active_orders(self, symbol: Optional[str] = None) -> list:
        """Retrieve all active orders, optionally filtered by symbol."""
        try:
            if symbol:
                return self.db.get_active_orders(symbol=symbol)
            return self.db.get_active_orders()
        except Exception as e:
            self.logger.error(f"Error retrieving active orders: {e}")
            return []

    def get_current_session(self) -> str:
        """Determine current trading session."""
        now = datetime.now().strftime('%H:%M:%S')
        for session, times in ORDER_SESSIONS.items():
            if times['start'] <= now < times['end']:
                return session
        return None

    def should_cancel_order(self, order_time: datetime) -> bool:
        """Check if order should be canceled based on session transition."""
        current_session = self.get_current_session()
        if not current_session:
            return True
        
        session_end = ORDER_SESSIONS[current_session]['end']
        return ORDER_SESSIONS[current_session]['cancel_at_end'] and \
               datetime.now().strftime('%H:%M:%S') >= session_end

    async def place_profit_target_order(self, symbol: str, quantity: int, entry_price: float, 
                                      lot_id: str = None) -> bool:
        """Place a limit order at profit target, specific to a lot."""
        try:
            target_price = entry_price * (1 + PROFIT_TARGET_PERCENT)
            
            # Create order with tax optimizer if enabled
            order = LimitOrder('SELL', quantity, target_price)
            if USE_TAX_OPTIMIZER and lot_id:
                order.account = self.ib.wrapper.accounts[0]  # Primary account
                order.faGroup = 'Tax Optimizer'
                order.faProfile = lot_id
            
            contract = self.ib.qualifyContracts(ib_insync.Stock(symbol))[0]
            trade = await self._retryable_place_order(contract, order)
            
            # Store order-lot relationship
            if trade.order.orderId:
                self.db.record_order_lot(trade.order.orderId, lot_id)
            
            return bool(trade.order.orderId)
            
        except Exception as e:
            self.logger.error(f"Error placing profit target order for {symbol}: {e}")
            return False

    async def handle_gap_up_exit(self, symbol: str, quantity: int, current_price: float,
                               lot_id: str = None) -> bool:
        """Handle gap up scenario with immediate sell order."""
        try:
            # Place limit order slightly below current price
            limit_price = current_price * 0.999  # 0.1% below current
            
            order = LimitOrder('SELL', quantity, limit_price)
            if USE_TAX_OPTIMIZER and lot_id:
                order.faGroup = 'Tax Optimizer'
                order.faProfile = lot_id
            
            contract = self.ib.qualifyContracts(ib_insync.Stock(symbol))[0]
            trade = await self._retryable_place_order(contract, order)
            
            # Wait for 10 seconds for fill
            for _ in range(10):
                await asyncio.sleep(1)
                if trade.orderStatus.status == 'Filled':
                    return True
                    
            # Cancel if not filled
            if trade.orderStatus.status != 'Filled':
                await self.cancel_order(trade.order.orderId)
                return False
                
        except Exception as e:
            self.logger.error(f"Error handling gap up exit for {symbol}: {e}")
            return False

    async def place_core_unwind_order(self, symbol: str, quantity: int, 
                                    lot_id: str = None) -> bool:
        """Place order to unwind core position (market order)."""
        try:
            order = MarketOrder('SELL', quantity)
            if USE_TAX_OPTIMIZER and lot_id:
                order.faGroup = 'Tax Optimizer'
                order.faProfile = lot_id
            
            contract = self.ib.qualifyContracts(ib_insync.Stock(symbol))[0]
            trade = await self._retryable_place_order(contract, order)
            
            return bool(trade.order.orderId)
            
        except Exception as e:
            self.logger.error(f"Error placing core unwind order for {symbol}: {e}")
            return False

    async def handle_session_transition(self):
        """Handle orders during session transitions."""
        try:
            current_session = self.get_current_session()
            
            # Cancel orders from previous session
            for order_id in list(self.active_orders.keys()):
                if self.should_cancel_order(self.active_orders[order_id]['time']):
                    await self.cancel_order(order_id)
                    
                    # Resubmit if configured
                    if RESUBMIT_ORDERS_ACROSS_SESSIONS:
                        order_info = self.active_orders[order_id]
                        await asyncio.sleep(ORDER_RESUBMIT_DELAY)
                        await self.place_limit_order(
                            order_info['symbol'],
                            order_info['action'],
                            order_info['quantity'],
                            order_info['price']
                        )
                        
        except Exception as e:
            self.logger.error(f"Error handling session transition: {e}")

    def calculate_core_building_requirements(self, symbol: str, account_value: float) -> dict:
        """
        Calculate how many core building cycles needed to reach target.
        Returns dict with cycles needed and progress tracking info.
        """
        try:
            core_target = CORE_POSITIONS.get(symbol, 0)
            target_value = account_value * core_target
            
            # Each cycle retains 0.25% (RETAIN_PERCENT of 1%)
            value_per_cycle = account_value * ORDER_SIZE_PERCENT * RETAIN_PERCENT
            
            # Calculate total cycles needed
            total_cycles = int(target_value / value_per_cycle)
            
            # Get current progress
            current_position = await self.get_position_size(symbol)
            current_value = current_position * await self.get_current_price(symbol)
            current_percentage = current_value / account_value
            cycles_completed = int(current_percentage / (ORDER_SIZE_PERCENT * RETAIN_PERCENT))
            
            return {
                'symbol': symbol,
                'total_cycles_needed': total_cycles,
                'cycles_completed': cycles_completed,
                'cycles_remaining': total_cycles - cycles_completed,
                'target_percentage': core_target,
                'current_percentage': current_percentage,
                'value_per_cycle': value_per_cycle
            }
            
        except Exception as e:
            self.logger.error(f"Error calculating core building requirements: {e}")
            return None

    async def place_core_building_orders(self, symbol: str, account_value: float) -> bool:
        """Enhanced with cycle verification"""
        try:
            # First check if we need more core building
            requirements = self.calculate_core_building_requirements(symbol, account_value)
            if not requirements or requirements['cycles_remaining'] <= 0:
                self.logger.info(f"Core target reached for {symbol}, no more building needed")
                return False
                
            # Rest of the existing core building code...
            
        except Exception as e:
            self.logger.error(f"Error in core building orders for {symbol}: {e}")
            return False

    async def verify_position_limits(self, symbol: str, quantity: int, 
                                   action: str) -> bool:
        """Verify that an order won't violate position limits."""
        try:
            # Get current position
            position = await self.get_position_size(symbol)
            account = await self.ib.accountSummaryAsync()
            total_value = float([x.value for x in account if x.tag == 'NetLiquidation'][0])
            
            # Calculate limits
            core_target = CORE_POSITIONS.get(symbol, 0)
            max_allowed = core_target + MAX_POSITION_BUFFER
            max_shares = int((total_value * max_allowed) / await self.get_current_price(symbol))
            
            if action == 'BUY':
                if position + quantity > max_shares:
                    self.logger.warning(f"Order would exceed position limit for {symbol}")
                    return False
                    
            # Verify cash reserve
            if action == 'BUY':
                order_value = quantity * await self.get_current_price(symbol)
                cash_ratio = (await self.get_cash_balance() - order_value) / total_value
                if cash_ratio < MIN_CASH_RESERVE:
                    self.logger.warning(f"Order would violate minimum cash reserve")
                    return False
                    
            return True
            
        except Exception as e:
            self.logger.error(f"Error verifying position limits: {e}")
            return False

    def record_order_status(self, trade: ib_insync.Trade):
        """Record order status changes to database."""
        try:
            self.db.record_order_status(
                order_id=trade.order.orderId,
                status=trade.orderStatus.status,
                filled=trade.orderStatus.filled,
                remaining=trade.orderStatus.remaining,
                avg_fill_price=trade.orderStatus.avgFillPrice,
                last_fill_price=trade.orderStatus.lastFillPrice,
                whyHeld=trade.orderStatus.whyHeld
            )
        except Exception as e:
            self.logger.error(f"Error recording order status: {e}")

    def track_core_progress(self, symbol: str) -> dict:
        """
        Track progress toward core position target.
        Returns dict with current status and progress.
        """
        try:
            account_value = float([x.value for x in await self.ib.accountSummaryAsync() 
                                 if x.tag == 'NetLiquidation'][0])
            
            requirements = self.calculate_core_building_requirements(symbol, account_value)
            if not requirements:
                return None
                
            # Calculate percentage complete
            progress_percentage = (requirements['cycles_completed'] / 
                                requirements['total_cycles_needed']) * 100
                                
            # Record progress to database
            self.db.record_core_progress(
                symbol=symbol,
                current_percentage=requirements['current_percentage'],
                target_percentage=requirements['target_percentage'],
                cycles_completed=requirements['cycles_completed'],
                cycles_remaining=requirements['cycles_remaining']
            )
            
            return {
                'symbol': symbol,
                'progress_percentage': progress_percentage,
                'cycles_remaining': requirements['cycles_remaining'],
                'estimated_completion_time': requirements['cycles_remaining'] * 
                                          (ORDER_RESUBMIT_DELAY + 60)  # Rough estimate in seconds
            }
            
        except Exception as e:
            self.logger.error(f"Error tracking core progress: {e}")
            return None

    async def get_position_size(self, symbol: str) -> int:
        """Get current position size for a symbol."""
        try:
            positions = await self.ib.reqPositionsAsync()
            for position in positions:
                if position.contract.symbol == symbol:
                    return position.position
            return 0
        except Exception as e:
            self.logger.error(f"Error getting position size for {symbol}: {e}")
            return 0

    async def get_current_price(self, symbol: str) -> float:
        """Get current market price for a symbol."""
        try:
            contract = self.ib.qualifyContracts(ib_insync.Stock(symbol))[0]
            ticker = await self.ib.reqMktDataAsync(contract)
            return ticker.marketPrice()
        except Exception as e:
            self.logger.error(f"Error getting current price for {symbol}: {e}")
            return 0.0

    async def get_cash_balance(self) -> float:
        """Get current cash balance."""
        try:
            account = await self.ib.accountSummaryAsync()
            return float([x.value for x in account if x.tag == 'AvailableFunds'][0])
        except Exception as e:
            self.logger.error(f"Error getting cash balance: {e}")
            return 0.0

    async def cancel_all_orders(self):
        """Cancel all open orders."""
        try:
            open_orders = self.ib.openOrders()
            for order in open_orders:
                self.ib.cancelOrder(order)
                self.logger.info(f"Cancelled order: {order}")
            await asyncio.sleep(1)  # Allow cancellation to process
        except Exception as e:
            self.logger.error(f"Error cancelling all orders: {e}")