import sqlite3
from datetime import datetime
import json

def init_db():
    conn = sqlite3.connect('finance.db')
    c = conn.cursor()
    
    # Create tables
    c.execute('''
        CREATE TABLE IF NOT EXISTS trial_balances (
            id INTEGER PRIMARY KEY,
            file_name TEXT,
            data TEXT,
            period TEXT,
            upload_date TIMESTAMP
        )
    ''')
    
    c.execute('''
        CREATE TABLE IF NOT EXISTS financial_statements (
            id INTEGER PRIMARY KEY,
            trial_balance_id INTEGER,
            balance_sheet TEXT,
            income_statement TEXT,
            cash_flow TEXT,
            generation_date TIMESTAMP,
            FOREIGN KEY (trial_balance_id) REFERENCES trial_balances(id)
        )
    ''')
    
    # Add period column if it doesn't exist
    try:
        c.execute('ALTER TABLE trial_balances ADD COLUMN period TEXT')
    except sqlite3.OperationalError:
        pass  # Column already exists
    
    conn.commit()
    return conn

def save_trial_balance(file_name: str, data: str, period: str) -> int:
    conn = init_db()
    c = conn.cursor()
    c.execute(
        'INSERT INTO trial_balances (file_name, data, period, upload_date) VALUES (?, ?, ?, ?)',
        (file_name, data, period, datetime.now())
    )
    conn.commit()
    return c.lastrowid

def save_statements(trial_balance_id: int, statements: dict):
    conn = init_db()
    c = conn.cursor()
    c.execute(
        '''INSERT INTO financial_statements 
           (trial_balance_id, balance_sheet, income_statement, cash_flow, generation_date)
           VALUES (?, ?, ?, ?, ?)''',
        (
            trial_balance_id,
            json.dumps(statements['balance_sheet']),
            json.dumps(statements['income_statement']),
            json.dumps(statements['cash_flow']),
            datetime.now()
        )
    )
    conn.commit()

def get_historical_statements():
    conn = init_db()
    c = conn.cursor()
    c.execute('''
        SELECT 
            t.file_name,
            f.balance_sheet,
            f.income_statement,
            f.cash_flow,
            f.generation_date,
            t.period
        FROM financial_statements f
        JOIN trial_balances t ON f.trial_balance_id = t.id
        ORDER BY f.generation_date DESC
    ''')
    return c.fetchall()

def get_statements_by_period(period: str):
    conn = init_db()
    c = conn.cursor()
    c.execute('''
        SELECT 
            t.file_name,
            f.balance_sheet,
            f.income_statement,
            f.cash_flow,
            f.generation_date
        FROM financial_statements f
        JOIN trial_balances t ON f.trial_balance_id = t.id
        WHERE t.period = ?
        ORDER BY f.generation_date DESC
        LIMIT 1
    ''', (period,))
    return c.fetchone()
