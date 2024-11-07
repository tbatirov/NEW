"""Financial ratios calculation module"""
from typing import Dict, Any

def get_nested_value(data: dict, *keys, default=0) -> float:
    def sum_numeric_values(d):
        total = 0
        for k, v in d.items():
            if isinstance(v, (int, float)):
                total += float(v)
            elif isinstance(v, dict):
                total += sum_numeric_values(v)
        return total

    current = data
    for key in keys:
        if isinstance(current, dict):
            current = current.get(key, default)
        else:
            return default
    
    if isinstance(current, dict):
        return sum_numeric_values(current)
    return float(current) if current != default else default

def calculate_ratios(balance_sheet: dict, income_statement: dict) -> dict:
    # Get balance sheet items
    current_assets = get_nested_value(balance_sheet, 'assets', 'current_assets')
    inventory = get_nested_value(balance_sheet, 'assets', 'current_assets', 'inventory')
    accounts_receivable = get_nested_value(balance_sheet, 'assets', 'current_assets', 'accounts_receivable')
    cash = get_nested_value(balance_sheet, 'assets', 'current_assets', 'cash')
    
    current_liabilities = get_nested_value(balance_sheet, 'liabilities', 'current_liabilities')
    total_assets = get_nested_value(balance_sheet, 'assets')
    total_liabilities = get_nested_value(balance_sheet, 'liabilities')
    total_equity = get_nested_value(balance_sheet, 'equity')
    
    # Get income statement items
    revenue = get_nested_value(income_statement, 'revenue')
    cost_of_sales = get_nested_value(income_statement, 'cost_of_sales')
    operating_expenses = get_nested_value(income_statement, 'operating_expenses')
    
    # Calculate key metrics
    gross_profit = revenue - cost_of_sales
    operating_income = gross_profit - operating_expenses
    net_income = operating_income - get_nested_value(income_statement, 'income_tax')
    
    ratios = {
        'liquidity_ratios': {
            'current_ratio': current_assets / current_liabilities if current_liabilities else None,
            'quick_ratio': (current_assets - inventory) / current_liabilities if current_liabilities else None,
            'cash_ratio': cash / current_liabilities if current_liabilities else None,
            'working_capital': current_assets - current_liabilities
        },
        'profitability_ratios': {
            'gross_margin_ratio': (gross_profit / revenue * 100) if revenue else None,
            'operating_margin_ratio': (operating_income / revenue * 100) if revenue else None,
            'net_profit_ratio': (net_income / revenue * 100) if revenue else None,
            'return_on_assets': (net_income / total_assets * 100) if total_assets else None,
            'return_on_equity': (net_income / total_equity * 100) if total_equity else None
        },
        'efficiency_ratios': {
            'asset_turnover': revenue / total_assets if total_assets else None,
            'inventory_turnover': cost_of_sales / inventory if inventory else None,
            'receivables_turnover': revenue / accounts_receivable if accounts_receivable else None
        },
        'leverage_ratios': {
            'debt_ratio': (total_liabilities / total_assets * 100) if total_assets else None,
            'debt_to_equity': (total_liabilities / total_equity) if total_equity else None,
            'equity_ratio': (total_equity / total_assets * 100) if total_assets else None
        }
    }
    
    return {
        'ratios': ratios,
        'explanations': {
            'current_ratio': 'Measures the company\'s ability to pay short-term obligations',
            'quick_ratio': 'Measures ability to pay short-term obligations using highly liquid assets',
            'cash_ratio': 'Measures ability to pay short-term obligations using only cash',
            'working_capital': 'Amount of money available for day-to-day operations',
            'gross_margin_ratio': 'Gross Profit / Revenue * 100. Profitability after direct costs',
            'operating_margin_ratio': 'Operating Income / Revenue * 100. Core business profitability',
            'net_profit_ratio': 'Net Income / Revenue * 100. Overall profitability',
            'return_on_assets': 'Net Income / Total Assets * 100. Asset efficiency',
            'return_on_equity': 'Net Income / Total Equity * 100. Return for shareholders',
            'asset_turnover': 'Revenue / Total Assets. Asset efficiency',
            'inventory_turnover': 'Cost of Sales / Inventory. Inventory management',
            'receivables_turnover': 'Revenue / Accounts Receivable. Collection efficiency',
            'debt_ratio': 'Total Liabilities / Total Assets * 100. Leverage measure',
            'debt_to_equity': 'Total Liabilities / Total Equity. Capital structure',
            'equity_ratio': 'Total Equity / Total Assets * 100. Owner financing'
        }
    }