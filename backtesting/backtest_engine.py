from .data_loader import DataLoader
from .strategy_tester import StrategyTester
from .performance_analyzer import PerformanceAnalyzer
from typing import Dict, List
from datetime import datetime
import logging
import json
from pathlib import Path
import importlib.util

logger = logging.getLogger(__name__)

class BacktestEngine:
    def __init__(self, config_path: str = 'config/config.py'):
        """Initialize backtest engine with configuration."""
        self.config = self._load_config(config_path)
        self.data_loader = DataLoader()
        self.strategy_tester = StrategyTester(
            initial_capital=self.config.get('INITIAL_CAPITAL', 100000.0)
        )
        
    def run_backtest(self, 
                    start_date: datetime,
                    end_date: datetime = None,
                    symbols: List[str] = None) -> Dict:
        """
        Run complete backtest and generate results.
        """
        try:
            # Use symbols from config if none provided
            if symbols is None:
                symbols = list(self.config['CORE_POSITIONS'].keys())
                
            # Load historical data
            data = self.data_loader.load_historical_data(
                symbols=symbols,
                start_date=start_date,
                end_date=end_date
            )
            
            # Run strategy test
            results = self.strategy_tester.test_strategy(
                data=data,
                core_targets=self.config['CORE_POSITIONS']
            )
            
            # Analyze performance
            analyzer = PerformanceAnalyzer(
                trades=self.strategy_tester.trades,
                daily_performance=self.strategy_tester.daily_performance
            )
            
            performance_report = analyzer.generate_report()
            
            # Save results
            self._save_results(results, performance_report)
            
            return {
                'test_results': results,
                'performance_report': performance_report
            }
            
        except Exception as e:
            logger.error(f"Error running backtest: {e}")
            return {}
            
    def _load_config(self, config_path: str) -> Dict:
        """Load configuration from config.py."""
        try:
            import sys
            from pathlib import Path
            
            # Add the project root to Python path
            root_dir = Path(config_path).parent.parent
            sys.path.append(str(root_dir))
            
            # Import config as module
            from config.config import (
                CORE_POSITIONS, INITIAL_CAPITAL, RSI_OVERSOLD, 
                RSI_OVERBOUGHT, ORDER_SIZE_PERCENT
            )
            
            return {
                'CORE_POSITIONS': CORE_POSITIONS,
                'INITIAL_CAPITAL': INITIAL_CAPITAL,
                'RSI_OVERSOLD': RSI_OVERSOLD,
                'RSI_OVERBOUGHT': RSI_OVERBOUGHT,
                'ORDER_SIZE_PERCENT': ORDER_SIZE_PERCENT
            }
        except Exception as e:
            logger.error(f"Error loading config: {e}")
            return {}
            
    def _save_results(self, results: Dict, performance_report: Dict):
        """Save backtest results and performance report."""
        try:
            output_dir = Path('backtest_results')
            output_dir.mkdir(exist_ok=True)
            
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            
            # Save results
            with open(output_dir / f'results_{timestamp}.json', 'w') as f:
                json.dump(results, f, indent=4)
                
            # Save performance report
            with open(output_dir / f'performance_{timestamp}.json', 'w') as f:
                json.dump(performance_report, f, indent=4)
                
        except Exception as e:
            logger.error(f"Error saving results: {e}") 