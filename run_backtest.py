from datetime import datetime
from backtesting.backtest_engine import BacktestEngine
from examples.backtest_scenarios import run_scenario_tests, create_visualizations
from pathlib import Path
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def main():
    try:
        print("Starting backtest...")
        
        # Simple single run
        engine = BacktestEngine()
        
        # Use a shorter timeframe for initial testing
        results = engine.run_backtest(
            start_date=datetime(2023, 6, 1),  # Last 6 months
            end_date=datetime(2024, 1, 1)
        )
        
        if results:
            print("\nBasic Results:")
            metrics = results.get('performance_report', {}).get('overall_metrics', {})
            print(f"Total Return: {metrics.get('total_return', 0):.2f}%")
            print(f"Sharpe Ratio: {metrics.get('sharpe_ratio', 0):.2f}")
            
            # Run scenarios and create visualizations
            print("\nRunning scenario tests...")
            scenario_results = run_scenario_tests()
            create_visualizations(scenario_results)
            
            print("\nBacktest complete! Check 'backtest_visuals' directory for charts.")
        else:
            print("No results returned from backtest.")
            
    except Exception as e:
        logger.error(f"Error in main: {e}", exc_info=True)

if __name__ == "__main__":
    main() 