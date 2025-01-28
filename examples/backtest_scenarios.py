from backtesting.backtest_engine import BacktestEngine
from datetime import datetime
import matplotlib.pyplot as plt
import seaborn as sns
import pandas as pd

def run_scenario_tests():
    engine = BacktestEngine()
    
    # Scenario 1: Bull Market Period
    bull_results = engine.run_backtest(
        start_date=datetime(2023, 1, 1),
        end_date=datetime(2023, 8, 1),
        symbols=['SOXL', 'NVDL']  # Test subset of symbols
    )
    
    # Scenario 2: High Volatility Period
    volatile_results = engine.run_backtest(
        start_date=datetime(2022, 9, 1),
        end_date=datetime(2023, 3, 1)
    )
    
    # Scenario 3: Different Position Sizes
    engine.config['ORDER_SIZE_PERCENT'] = 0.02  # Test with 2% positions
    size_test_results = engine.run_backtest(
        start_date=datetime(2023, 1, 1),
        end_date=datetime(2024, 1, 1)
    )
    
    # Scenario 4: Different RSI Settings
    engine.config['RSI_OVERSOLD'] = 25  # More conservative entry
    rsi_test_results = engine.run_backtest(
        start_date=datetime(2023, 1, 1),
        end_date=datetime(2024, 1, 1)
    )
    
    return {
        'bull_market': bull_results,
        'high_volatility': volatile_results,
        'position_size_test': size_test_results,
        'rsi_settings_test': rsi_test_results
    }

def create_visualizations(results):
    # Create output directory
    Path('backtest_visuals').mkdir(exist_ok=True)
    
    # 1. Equity Curves Comparison
    plt.figure(figsize=(15, 8))
    for scenario, result in results.items():
        equity_curve = pd.Series(result['test_results']['equity_curve'])
        plt.plot(equity_curve.index, equity_curve.values, label=scenario)
    plt.title('Equity Curves Across Scenarios')
    plt.legend()
    plt.grid(True)
    plt.savefig('backtest_visuals/equity_curves_comparison.png')
    plt.close()
    
    # 2. Drawdown Analysis
    plt.figure(figsize=(15, 8))
    for scenario, result in results.items():
        drawdown = pd.Series(result['test_results']['drawdowns'])
        plt.plot(drawdown.index, drawdown.values, label=scenario)
    plt.title('Drawdown Comparison')
    plt.legend()
    plt.grid(True)
    plt.savefig('backtest_visuals/drawdown_comparison.png')
    plt.close()
    
    # 3. Core Position Building Progress
    plt.figure(figsize=(15, 8))
    for symbol in engine.config['CORE_POSITIONS']:
        progress_data = []
        for scenario, result in results.items():
            core_progress = result['test_results']['core_progress'][symbol]
            progress_data.append({
                'scenario': scenario,
                'final_percentage': core_progress[-1]['current_percentage']
            })
        progress_df = pd.DataFrame(progress_data)
        plt.bar(progress_df['scenario'], progress_df['final_percentage'])
    plt.title('Core Position Building Progress by Scenario')
    plt.xticks(rotation=45)
    plt.savefig('backtest_visuals/core_progress.png')
    plt.close()
    
    # 4. Risk State Transitions
    plt.figure(figsize=(15, 8))
    for scenario, result in results.items():
        risk_states = pd.Series(result['test_results']['risk_states']['SOXL'])  # Example for SOXL
        plt.plot(risk_states.index, risk_states.values, label=scenario)
    plt.title('Risk State Transitions (SOXL)')
    plt.legend()
    plt.grid(True)
    plt.savefig('backtest_visuals/risk_states.png')
    plt.close()
    
    # 5. Performance Metrics Heatmap
    metrics_data = {}
    for scenario, result in results.items():
        metrics = result['performance_report']['overall_metrics']
        metrics_data[scenario] = metrics
    
    metrics_df = pd.DataFrame(metrics_data).T
    plt.figure(figsize=(12, 8))
    sns.heatmap(metrics_df, annot=True, fmt='.2f', cmap='RdYlGn')
    plt.title('Performance Metrics Comparison')
    plt.savefig('backtest_visuals/metrics_heatmap.png')
    plt.close()

def main():
    # Run all scenarios
    results = run_scenario_tests()
    
    # Create visualizations
    create_visualizations(results)
    
    # Print summary
    print("\nBacktest Scenarios Summary:")
    for scenario, result in results.items():
        metrics = result['performance_report']['overall_metrics']
        print(f"\n{scenario.upper()}:")
        print(f"Total Return: {metrics['total_return']:.2f}%")
        print(f"Sharpe Ratio: {metrics['sharpe_ratio']:.2f}")
        print(f"Max Drawdown: {metrics['max_drawdown']:.2f}%")
        print(f"Win Rate: {metrics['win_rate']:.2f}%")

if __name__ == "__main__":
    main() 