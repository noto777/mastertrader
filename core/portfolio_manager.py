import ib_insync
from decimal import Decimal
from core.database import Database
from core.order_manager import OrderManager
from utils.logger import setup_logger
import asyncio
from typing import Dict, List, Optional
import config.config as cfg


class PortfolioManager:
    def __init__(self, ib: ib_insync.IB, db: Database):
        """Initialize PortfolioManager with IB connection and database."""
        self.logger = setup_logger(__name__)
        self.ib = ib
        self.db = db
        self.order_manager = OrderManager(ib, db)
        # Use config values instead of hardcoded
        self.MIN_CASH_RESERVE = Decimal(str(cfg.MIN_CASH_RESERVE))
        self.MAX_TOTAL_INVESTED = Decimal(str(cfg.MAX_TOTAL_INVESTED))
        self.CORE_TARGET_PERCENT = Decimal('5')  # Max core exposure (5%)
        self.MAX_EXPOSURE_PERCENT = Decimal('10')  # Max exposure (10%)

    def calculate_portfolio_value(self) -> float:
        """Calculate total portfolio value (NetLiquidation)."""
        try:
            account_values = self.ib.accountValues()
            net_liquidation = next(
                (Decimal(av.value) for av in account_values if av.tag == 'NetLiquidation'), Decimal('0')
            )
            self.logger.info(f"Net Liquidation Value: {net_liquidation}")
            return float(net_liquidation)
        except Exception as e:
            self.logger.error(f"Error calculating portfolio value: {e}")
            return 0.0

    def get_positions(self) -> List[ib_insync.Position]:
        """Retrieve current IB account positions."""
        try:
            positions = self.ib.positions()
            self.logger.info(f"Retrieved {len(positions)} positions.")
            return positions
        except Exception as e:
            self.logger.error(f"Error retrieving positions: {e}")
            return []

    def get_current_price(self, symbol: str) -> Decimal:
        """Retrieve the current market price for a given symbol."""
        try:
            contract = ib_insync.Stock(symbol)
            ticker = self.ib.reqMktData(contract, '', False, False)
            self.ib.sleep(1)  # Allow data to update
            price = Decimal(ticker.bid if ticker.bid else ticker.last)
            self.logger.info(f"Current price for {symbol}: {price}")
            return price
        except Exception as e:
            self.logger.error(f"Error retrieving current price for {symbol}: {e}")
            return Decimal('0')

    def calculate_position_value(self, symbol: str) -> Decimal:
        """Calculate total value of a position for a given symbol."""
        try:
            positions = self.db.get_all_positions(symbol)
            current_price = self.get_current_price(symbol)
            total_quantity = sum(pos['quantity'] for pos in positions)
            return Decimal(total_quantity) * current_price
        except Exception as e:
            self.logger.error(f"Error calculating position value for {symbol}: {e}")
            return Decimal('0')

    def check_exposure_limit(self, symbol: str, lot_type: str) -> bool:
        """Check if position exposure is within allowable limits."""
        try:
            position_value = self.calculate_position_value(symbol)
            portfolio_value = Decimal(self.calculate_portfolio_value())

            max_limit = (self.CORE_TARGET_PERCENT if lot_type == 'CORE' else self.MAX_EXPOSURE_PERCENT) / 100
            allowed = position_value <= portfolio_value * max_limit

            if not allowed:
                self.logger.warning(f"Exposure limit exceeded for {symbol}. Allowed: {max_limit * portfolio_value}, "
                                    f"Current: {position_value}")
            return allowed
        except Exception as e:
            self.logger.error(f"Error checking exposure for {symbol}: {e}")
            return False

    async def handle_buy_signal(self, symbol: str, quantity: int, limit_price: float):
        """Handle buy signal by placing a limit order."""
        try:
            if not self.check_exposure_limit(symbol, 'TRADING'):
                self.logger.warning(f"Cannot increase position for {symbol}. Exposure limit reached.")
                return

            await self.order_manager.place_limit_order(symbol, 'BUY', quantity, limit_price)
            self.logger.info(f"Handled BUY signal for {symbol}.")
        except Exception as e:
            self.logger.error(f"Error handling BUY signal for {symbol}: {e}")

    async def handle_sell_signal(self, symbol: str, lot_id: int, sell_price: float):
        """Handle sell signal for a specific lot."""
        try:
            await self.order_manager.place_limit_order(symbol, 'SELL', lot_id, sell_price)
            self.logger.info(f"Handled SELL signal for {symbol}, Lot ID: {lot_id}.")
        except Exception as e:
            self.logger.error(f"Error handling SELL signal for {symbol}, Lot ID: {lot_id}: {e}")

    async def rebalance_portfolio(self):
        """Trim or adjust positions based on limits."""
        try:
            positions = self.get_positions()
            portfolio_value = Decimal(self.calculate_portfolio_value())

            for position in positions:
                symbol = position.contract.symbol
                quantity = Decimal(position.position)
                current_price = self.get_current_price(symbol)
                position_value = quantity * current_price

                max_allowed_value = portfolio_value * self.MAX_EXPOSURE_PERCENT / 100
                if position_value > max_allowed_value:
                    excess_value = position_value - max_allowed_value
                    excess_quantity = int(excess_value / current_price)
                    self.logger.info(f"Trimming {excess_quantity} shares of {symbol}.")
                    await self.order_manager.place_limit_order(symbol, 'SELL', excess_quantity, float(current_price))
        except Exception as e:
            self.logger.error(f"Error rebalancing portfolio: {e}")

    async def manage_core_position(self, symbol: str):
        """Manage core position building or unwinding based on risk state."""
        try:
            # Get current risk state
            risk_state = self.db.get_latest_risk_state(symbol)
            if not risk_state:
                return

            portfolio_value = Decimal(await self.calculate_portfolio_value())
            requirements = await self.order_manager.calculate_core_building_requirements(
                symbol, float(portfolio_value)
            )

            if risk_state == 'RISK_OFF':
                await self.handle_risk_off_core(symbol)
            elif risk_state == 'RISK_ON' and requirements['cycles_remaining'] > 0:
                await self.build_core_position(symbol)

        except Exception as e:
            self.logger.error(f"Error managing core position for {symbol}: {e}")

    async def handle_risk_off_core(self, symbol: str):
        """Handle core position unwinding in risk-off state."""
        try:
            current_position = await self.order_manager.get_position_size(symbol)
            if current_position > 0:
                self.logger.info(f"Unwinding core position for {symbol}")
                await self.order_manager.place_order_async(symbol, 'SELL', current_position)
                self.db.record_unwind_cycle(symbol, self.db.get_latest_price(symbol))
        except Exception as e:
            self.logger.error(f"Error handling risk-off core for {symbol}: {e}")

    async def build_core_position(self, symbol: str):
        """Build core position for a symbol."""
        try:
            target_percentage = Decimal(str(cfg.CORE_POSITIONS.get(symbol, 0)))
            portfolio_value = Decimal(await self.calculate_portfolio_value())
            order_size = (self.MAX_TOTAL_INVESTED * target_percentage).quantize(Decimal('0.01'))

            # Check available cash
            cash_balance = Decimal(await self.order_manager.get_cash_balance())
            if cash_balance < (order_size + self.MIN_CASH_RESERVE):
                self.logger.warning(f"Insufficient cash to build core position for {symbol}")
                return

            quantity = (order_size / Decimal(await self.order_manager.get_current_price(symbol))).to_integral_value()
            if quantity <= 0:
                self.logger.warning(f"Calculated quantity for {symbol} is non-positive.")
                return

            self.logger.info(f"Building core position for {symbol}: {quantity} shares")
            await self.order_manager.place_order_async(symbol, 'BUY', int(quantity))
            self.db.record_core_position(symbol, str(cfg.LOT_ID), int(quantity), float(order_size))
        except Exception as e:
            self.logger.error(f"Error building core position for {symbol}: {e}")

    def check_cash_reserves(self, required_percent: float) -> bool:
        """Check if we have enough cash reserves for a trade."""
        try:
            account_values = self.ib.accountValues()
            available_cash = Decimal(next(
                (av.value for av in account_values if av.tag == 'AvailableFunds'), 
                '0'
            ))
            portfolio_value = Decimal(self.calculate_portfolio_value())
            
            # Check if trade would violate minimum cash reserve
            trade_value = portfolio_value * Decimal(str(required_percent))
            remaining_ratio = (available_cash - trade_value) / portfolio_value
            
            return remaining_ratio >= self.MIN_CASH_RESERVE

        except Exception as e:
            self.logger.error(f"Error checking cash reserves: {e}")
            return False

    async def monitor_positions(self):
        """Monitor all positions for risk state changes and core management."""
        try:
            for symbol in cfg.CORE_POSITIONS:
                # Update risk state
                current_state = self.db.get_latest_risk_state(symbol)
                
                # Manage core position based on risk state
                await self.manage_core_position(symbol)
                
                # Track progress toward core target
                if current_state == 'RISK_ON':
                    progress = self.order_manager.track_core_progress(symbol)
                    if progress:
                        self.logger.info(
                            f"Core progress for {symbol}: {progress['progress_percentage']:.2f}%"
                        )

        except Exception as e:
            self.logger.error(f"Error monitoring positions: {e}")

    async def calculate_total_exposure(self) -> Decimal:
        """Calculate total portfolio exposure as percentage."""
        try:
            portfolio_value = Decimal(self.calculate_portfolio_value())
            positions = await self.ib.reqPositionsAsync()
            
            total_position_value = Decimal('0')
            for position in positions:
                ticker = await self.ib.reqMktDataAsync(position.contract)
                position_value = Decimal(str(position.position)) * Decimal(str(ticker.marketPrice()))
                total_position_value += position_value
            
            return total_position_value / portfolio_value
            
        except Exception as e:
            self.logger.error(f"Error calculating total exposure: {e}")
            return Decimal('0')

    async def verify_position_limits(self, symbol: str) -> bool:
        """Verify position is within core target + buffer limit."""
        try:
            core_target = Decimal(str(cfg.CORE_POSITIONS.get(symbol, 0)))
            max_allowed = core_target + Decimal(str(cfg.MAX_POSITION_BUFFER))
            
            current_value = Decimal(str(await self.get_position_value(symbol)))
            portfolio_value = Decimal(self.calculate_portfolio_value())
            
            current_percentage = current_value / portfolio_value
            
            return current_percentage <= max_allowed
            
        except Exception as e:
            self.logger.error(f"Error verifying position limits: {e}")
            return False

    def categorize_position(self, symbol: str) -> Dict:
        """Categorize position into core and trading components."""
        try:
            core_position = self.db.get_core_position(symbol)
            total_position = self.get_position_size(symbol)
            
            if not total_position:
                return {'core': 0, 'trading': 0}
                
            core_size = core_position['quantity'] if core_position else 0
            trading_size = total_position - core_size
            
            return {
                'core': core_size,
                'trading': trading_size if trading_size > 0 else 0
            }
            
        except Exception as e:
            self.logger.error(f"Error categorizing position: {e}")
            return {'core': 0, 'trading': 0}

    async def track_performance(self):
        """Track and record all performance metrics."""
        try:
            # Get portfolio-level performance
            portfolio_value = Decimal(await self.calculate_portfolio_value())
            cash_balance = await self.order_manager.get_cash_balance()
            
            # Calculate daily P&L
            yesterday_value = self.db.get_previous_portfolio_value()
            daily_pl = float(portfolio_value - yesterday_value) if yesterday_value else 0.0
            
            # Get trade statistics
            trades = self.db.get_todays_trades()
            winning_trades = sum(1 for t in trades if t.profit_loss > 0)
            
            # Get core positions status
            core_values = {}
            risk_states = {}
            for symbol in cfg.CORE_POSITIONS:
                core_pos = self.categorize_position(symbol)
                core_values[symbol] = await self.get_position_value(symbol)
                risk_states[symbol] = self.db.get_latest_risk_state(symbol)
                
                # Record core-specific performance
                await self.track_core_performance(symbol)
            
            # Record portfolio performance
            self.db.record_portfolio_performance({
                'total_value': float(portfolio_value),
                'cash_balance': float(cash_balance),
                'total_profit_loss': self.calculate_total_pl(),
                'daily_profit_loss': daily_pl,
                'total_trades': len(trades),
                'winning_trades': winning_trades,
                'core_position_values': core_values,
                'risk_states': risk_states
            })
            
        except Exception as e:
            self.logger.error(f"Error tracking performance: {e}")

    async def track_core_performance(self, symbol: str):
        """Track performance of core position building/unwinding."""
        try:
            position = self.categorize_position(symbol)
            core_progress = await self.order_manager.calculate_core_building_requirements(
                symbol, float(await self.calculate_portfolio_value())
            )
            
            current_value = await self.get_position_value(symbol)
            cost_basis = self.db.get_core_position_cost_basis(symbol)
            
            self.db.record_core_performance({
                'symbol': symbol,
                'target_percentage': cfg.CORE_POSITIONS[symbol],
                'current_percentage': core_progress['current_percentage'],
                'total_cost': cost_basis,
                'market_value': current_value,
                'unrealized_pl': current_value - cost_basis if cost_basis else 0,
                'build_cycles_completed': core_progress['cycles_completed'],
                'unwind_cycles_completed': self.db.get_unwind_cycles(symbol)
            })
            
        except Exception as e:
            self.logger.error(f"Error tracking core performance for {symbol}: {e}")
