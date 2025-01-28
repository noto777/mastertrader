import pandas as pd
import numpy as np
from typing import Dict, List
import matplotlib.pyplot as plt
import seaborn as sns
from datetime import datetime
import logging

logger = logging.getLogger(__name__)

class PerformanceAnalyzer:
    def __init__(self, trades: List[Dict], daily_performance: pd.DataFrame):
        """Initialize with trade history and daily performance data."""
        self.trades = pd.DataFrame(trades)
        self.daily_perf = daily_performance
        
    def generate_report(self, output_dir: str = 'reports'):
        """Generate comprehensive performance report."""
        try:
            report = {
                'overall_metrics': self._calculate_overall_metrics(),
                'monthly_metrics': self._calculate_monthly_metrics(),
                'risk_metrics': self._calculate_risk_metrics(),
                'core_metrics': self._calculate_core_metrics()
            }
            
            self._generate_charts(output_dir)
            self._save_report(report, output_dir)
            
            return report
            
        except Exception as e:
            logger.error(f"Error generating performance report: {e}")
            return {}
            
    def _calculate_overall_metrics(self) -> Dict:
        """Calculate overall performance metrics."""
        return {
            'total_return': self.daily_perf['total_value'].pct_change().sum(),
            'annualized_return': self._calculate_annualized_return(),
            'sharpe_ratio': self._calculate_sharpe_ratio(),
            'sortino_ratio': self._calculate_sortino_ratio(),
            'max_drawdown': self._calculate_max_drawdown(),
            'win_rate': len(self.trades[self.trades['profit'] > 0]) / len(self.trades),
            'profit_factor': self._calculate_profit_factor()
        }
        
    def _calculate_risk_metrics(self) -> Dict:
        """Calculate risk-related metrics."""
        return {
            'value_at_risk': self._calculate_var(),
            'expected_shortfall': self._calculate_expected_shortfall(),
            'beta': self._calculate_beta(),
            'correlation_matrix': self._calculate_correlation_matrix()
        }
        
    def _generate_charts(self, output_dir: str):
        """Generate performance visualization charts."""
        try:
            # Equity curve
            plt.figure(figsize=(12, 6))
            self.daily_perf['total_value'].plot()
            plt.title('Equity Curve')
            plt.savefig(f'{output_dir}/equity_curve.png')
            
            # Drawdown chart
            plt.figure(figsize=(12, 6))
            self._calculate_drawdown_series().plot()
            plt.title('Drawdown')
            plt.savefig(f'{output_dir}/drawdown.png')
            
            # Monthly returns heatmap
            plt.figure(figsize=(12, 8))
            monthly_returns = self._calculate_monthly_returns()
            sns.heatmap(monthly_returns.pivot_table(index=monthly_returns.index.year,
                                                  columns=monthly_returns.index.month,
                                                  values='returns'),
                       annot=True, fmt='.2%')
            plt.title('Monthly Returns Heatmap')
            plt.savefig(f'{output_dir}/monthly_heatmap.png')
            
        except Exception as e:
            logger.error(f"Error generating charts: {e}") 