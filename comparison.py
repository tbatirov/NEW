"""Comparison functionality for financial statements"""
from typing import Dict, Any
import plotly.graph_objects as go
from plotly.subplots import make_subplots

def calculate_variances(period1: dict, period2: dict) -> dict:
    """Calculate absolute and percentage changes between two periods"""
    
    def calculate_diff(val1, val2):
        if isinstance(val1, dict) and isinstance(val2, dict):
            return {k: calculate_diff(val1.get(k, 0), val2.get(k, 0)) 
                   for k in set(val1.keys()) | set(val2.keys())}
        try:
            val1_float = float(val1 or 0)
            val2_float = float(val2 or 0)
            abs_change = val2_float - val1_float
            pct_change = (abs_change / val1_float * 100) if val1_float != 0 else None
            return {
                'absolute_change': abs_change,
                'percentage_change': pct_change
            }
        except (TypeError, ValueError):
            return {'absolute_change': 0, 'percentage_change': None}
    
    return {
        'balance_sheet': calculate_diff(period1.get('balance_sheet', {}), 
                                      period2.get('balance_sheet', {})),
        'income_statement': calculate_diff(period1.get('income_statement', {}),
                                         period2.get('income_statement', {})),
        'cash_flow': calculate_diff(period1.get('cash_flow', {}),
                                  period2.get('cash_flow', {}))
    }

def generate_comparison_charts(periods: list) -> Dict[str, Any]:
    """Generate trend charts for key metrics across periods"""
    
    def extract_key_metrics(statement):
        if not statement:
            return {}
            
        bs = statement.get('balance_sheet', {})
        is_stmt = statement.get('income_statement', {})
        
        return {
            'Total Assets': sum(float(val) for val in bs.get('assets', {}).values() if isinstance(val, (int, float))),
            'Total Liabilities': sum(float(val) for val in bs.get('liabilities', {}).values() if isinstance(val, (int, float))),
            'Revenue': sum(float(val) for val in is_stmt.get('revenue', {}).values() if isinstance(val, (int, float))),
            'Net Income': sum(float(val) for val in is_stmt.get('net_income', {}).values() if isinstance(val, (int, float)))
        }
    
    # Extract data for plotting
    metrics_data = {period['period']: extract_key_metrics(period['statements']) 
                   for period in periods}
    
    # Create subplot figure
    fig = make_subplots(rows=2, cols=2,
                       subplot_titles=('Total Assets', 'Total Liabilities', 
                                     'Revenue', 'Net Income'))
    
    # Add traces for each metric
    metrics = ['Total Assets', 'Total Liabilities', 'Revenue', 'Net Income']
    positions = [(1, 1), (1, 2), (2, 1), (2, 2)]
    
    for metric, (row, col) in zip(metrics, positions):
        values = [data.get(metric, 0) for data in metrics_data.values()]
        periods_list = list(metrics_data.keys())
        
        fig.add_trace(
            go.Scatter(x=periods_list, y=values, name=metric),
            row=row, col=col
        )
    
    fig.update_layout(height=800, showlegend=False)
    
    return {
        'trend_chart': fig,
        'metrics_data': metrics_data
    }
