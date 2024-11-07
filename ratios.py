"""Financial ratios calculation module"""
from typing import Dict, Any


def calculate_ratios(balance_sheet: dict, income_statement: dict) -> dict:
    """Calculate financial ratios from balance sheet and income statement"""
    
    def get_nested_value(data: dict, *keys, default=0) -> float:
        """Helper function to safely get nested dictionary values"""
        current = data
        for key in keys:
            if isinstance(current, dict):
                current = current.get(key, {})
            else:
                return default
        return float(current) if current != {} else default

    # Extract common values used in multiple ratios
    current_assets = get_nested_value(balance_sheet, 'assets', 'current_assets')
    current_liabilities = get_nested_value(balance_sheet, 'liabilities', 'current_liabilities')
    total_assets = get_nested_value(balance_sheet, 'assets')
    total_liabilities = get_nested_value(balance_sheet, 'liabilities')
    equity = get_nested_value(balance_sheet, 'equity')
    revenue = get_nested_value(income_statement, 'revenue')
    cogs = get_nested_value(income_statement, 'cost_of_sales')
    operating_expenses = get_nested_value(income_statement, 'operating_expenses')
    
    # Calculate operating and net income
    gross_profit = revenue - cogs
    operating_income = gross_profit - operating_expenses
    net_income = operating_income - get_nested_value(income_statement, 'income_tax')

    ratios = {
        'liquidity_ratios': {
            'current_ratio': current_assets / current_liabilities if current_liabilities else None,
            'quick_ratio': (current_assets - get_nested_value(balance_sheet, 'assets', 'current_assets', 'inventory', default=0)) / current_liabilities if current_liabilities else None,
            'cash_ratio': get_nested_value(balance_sheet, 'assets', 'current_assets', 'cash', default=0) / current_liabilities if current_liabilities else None,
            'working_capital': current_assets - current_liabilities
        },
        'profitability_ratios': {
            'gross_margin': (gross_profit / revenue * 100) if revenue else None,
            'operating_margin': (operating_income / revenue * 100) if revenue else None,
            'net_profit_margin': (net_income / revenue * 100) if revenue else None,
            'return_on_assets': (net_income / total_assets * 100) if total_assets else None,
            'return_on_equity': (net_income / equity * 100) if equity else None,
            'return_on_capital_employed': (operating_income / (total_assets - current_liabilities) * 100) if (total_assets - current_liabilities) else None
        },
        'efficiency_ratios': {
            'asset_turnover': revenue / total_assets if total_assets else None,
            'inventory_turnover': cogs / get_nested_value(balance_sheet, 'assets', 'current_assets', 'inventory', default=0) if get_nested_value(balance_sheet, 'assets', 'current_assets', 'inventory', default=0) else None,
            'receivables_turnover': revenue / get_nested_value(balance_sheet, 'assets', 'current_assets', 'accounts_receivable', default=0) if get_nested_value(balance_sheet, 'assets', 'current_assets', 'accounts_receivable', default=0) else None,
            'payables_turnover': cogs / get_nested_value(balance_sheet, 'liabilities', 'current_liabilities', 'accounts_payable', default=0) if get_nested_value(balance_sheet, 'liabilities', 'current_liabilities', 'accounts_payable', default=0) else None,
        },
        'leverage_ratios': {
            'debt_ratio': (total_liabilities / total_assets * 100) if total_assets else None,
            'debt_to_equity': (total_liabilities / equity) if equity else None,
            'equity_ratio': (equity / total_assets * 100) if total_assets else None,
        }
    }
    
    # Add ratio explanations
    ratio_explanations = {
        'current_ratio': 'Measures the company\'s ability to pay short-term obligations',
        'quick_ratio': 'Measures ability to pay short-term obligations using highly liquid assets',
        'cash_ratio': 'Measures ability to pay short-term obligations using only cash',
        'working_capital': 'Amount of money available for day-to-day operations',
        'gross_margin': 'Percentage of revenue remaining after cost of goods sold',
        'operating_margin': 'Percentage of revenue remaining after operating expenses',
        'net_profit_margin': 'Percentage of revenue remaining after all expenses',
        'return_on_assets': 'How efficiently company uses assets to generate earnings',
        'return_on_equity': 'How efficiently company uses equity to generate earnings',
        'return_on_capital_employed': 'Profitability relative to capital employed',
        'asset_turnover': 'How efficiently company uses assets to generate sales',
        'inventory_turnover': 'How many times inventory is sold and replaced over a period',
        'receivables_turnover': 'How efficiently company collects debt',
        'payables_turnover': 'How quickly company pays its bills',
        'debt_ratio': 'Percentage of assets financed by debt',
        'debt_to_equity': 'Proportion of debt relative to equity',
        'equity_ratio': 'Percentage of assets financed by equity'
    }

    return {'ratios': ratios, 'explanations': ratio_explanations}
