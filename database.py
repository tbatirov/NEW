import sqlite3
from datetime import datetime
import json

def init_db():
    conn = sqlite3.connect('finance.db')
    c = conn.cursor()
    
    # Create companies table
    c.execute('''
        CREATE TABLE IF NOT EXISTS companies (
            id INTEGER PRIMARY KEY,
            name TEXT NOT NULL,
            tax_id TEXT UNIQUE,
            registration_date TIMESTAMP,
            address TEXT,
            contact_email TEXT,
            contact_phone TEXT
        )
    ''')
    
    # Create tables with company_id
    c.execute('''
        CREATE TABLE IF NOT EXISTS trial_balances (
            id INTEGER PRIMARY KEY,
            company_id INTEGER,
            file_name TEXT,
            data TEXT,
            period TEXT,
            upload_date TIMESTAMP,
            FOREIGN KEY (company_id) REFERENCES companies(id)
        )
    ''')
    
    c.execute('''
        CREATE TABLE IF NOT EXISTS financial_statements (
            id INTEGER PRIMARY KEY,
            company_id INTEGER,
            trial_balance_id INTEGER,
            balance_sheet TEXT,
            income_statement TEXT,
            cash_flow TEXT,
            generation_date TIMESTAMP,
            FOREIGN KEY (company_id) REFERENCES companies(id),
            FOREIGN KEY (trial_balance_id) REFERENCES trial_balances(id)
        )
    ''')
    
    # Add knowledge base tables
    c.execute('''
        CREATE TABLE IF NOT EXISTS standards_content (
            id INTEGER PRIMARY KEY,
            url TEXT UNIQUE,
            content TEXT,
            source TEXT,
            last_updated TIMESTAMP,
            last_checked TIMESTAMP,
            status TEXT
        )
    ''')
    
    c.execute('''
        CREATE TABLE IF NOT EXISTS scraping_log (
            id INTEGER PRIMARY KEY,
            timestamp TIMESTAMP,
            source TEXT,
            status TEXT,
            message TEXT
        )
    ''')
    
    # Add period column if it doesn't exist
    try:
        c.execute('ALTER TABLE trial_balances ADD COLUMN period TEXT')
    except sqlite3.OperationalError:
        pass  # Column already exists

    # Add company_id column to existing tables if they don't exist
    try:
        c.execute('ALTER TABLE trial_balances ADD COLUMN company_id INTEGER REFERENCES companies(id)')
    except sqlite3.OperationalError:
        pass

    try:
        c.execute('ALTER TABLE financial_statements ADD COLUMN company_id INTEGER REFERENCES companies(id)')
    except sqlite3.OperationalError:
        pass
    
    conn.commit()
    return conn

def save_company(name: str, tax_id: str, address: str = None, contact_email: str = None, contact_phone: str = None) -> int:
    """Save a new company to the database"""
    conn = init_db()
    c = conn.cursor()
    
    try:
        c.execute(
            '''INSERT INTO companies (name, tax_id, registration_date, address, contact_email, contact_phone)
               VALUES (?, ?, ?, ?, ?, ?)''',
            (name, tax_id, datetime.now(), address, contact_email, contact_phone)
        )
        conn.commit()
        return c.lastrowid
    except sqlite3.IntegrityError:
        raise ValueError("A company with this tax ID already exists")

def get_company(company_id: int):
    """Get company details by ID"""
    conn = init_db()
    c = conn.cursor()
    c.execute('SELECT * FROM companies WHERE id = ?', (company_id,))
    return c.fetchone()

def get_all_companies():
    """Get all companies"""
    conn = init_db()
    c = conn.cursor()
    c.execute('SELECT id, name, tax_id FROM companies ORDER BY name')
    return c.fetchall()

def save_trial_balance(file_name: str, data: str, period: str, company_id: int) -> int:
    conn = init_db()
    c = conn.cursor()
    c.execute(
        'INSERT INTO trial_balances (file_name, data, period, upload_date, company_id) VALUES (?, ?, ?, ?, ?)',
        (file_name, data, period, datetime.now(), company_id)
    )
    conn.commit()
    return c.lastrowid

def save_statements(trial_balance_id: int, statements: dict, company_id: int):
    conn = init_db()
    c = conn.cursor()
    c.execute(
        '''INSERT INTO financial_statements 
           (trial_balance_id, balance_sheet, income_statement, cash_flow, generation_date, company_id)
           VALUES (?, ?, ?, ?, ?, ?)''',
        (
            trial_balance_id,
            json.dumps(statements['balance_sheet']),
            json.dumps(statements['income_statement']),
            json.dumps(statements['cash_flow']),
            datetime.now(),
            company_id
        )
    )
    conn.commit()

def save_standard_content(url: str, content: str, source: str, status: str = 'active'):
    """Save or update standard content in the database"""
    conn = init_db()
    c = conn.cursor()
    now = datetime.now()
    
    c.execute('''
        INSERT INTO standards_content (url, content, source, last_updated, last_checked, status)
        VALUES (?, ?, ?, ?, ?, ?)
        ON CONFLICT(url) DO UPDATE SET
            content=excluded.content,
            last_updated=excluded.last_updated,
            last_checked=excluded.last_checked,
            status=excluded.status
    ''', (url, content, source, now, now, status))
    
    conn.commit()

def log_scraping_activity(source: str, status: str, message: str):
    """Log scraping activity for monitoring"""
    conn = init_db()
    c = conn.cursor()
    
    c.execute('''
        INSERT INTO scraping_log (timestamp, source, status, message)
        VALUES (?, ?, ?, ?)
    ''', (datetime.now(), source, status, message))
    
    conn.commit()

def get_historical_statements(company_id: int = None):
    conn = init_db()
    c = conn.cursor()
    
    query = '''
        SELECT 
            t.file_name,
            f.balance_sheet,
            f.income_statement,
            f.cash_flow,
            f.generation_date,
            t.period,
            c.name as company_name
        FROM financial_statements f
        JOIN trial_balances t ON f.trial_balance_id = t.id
        JOIN companies c ON f.company_id = c.id
    '''
    
    if company_id:
        query += ' WHERE f.company_id = ?'
        c.execute(query, (company_id,))
    else:
        c.execute(query)
    
    return c.fetchall()

def get_statements_by_period(period: str, company_id: int):
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
        WHERE t.period = ? AND f.company_id = ?
        ORDER BY f.generation_date DESC
        LIMIT 1
    ''', (period, company_id))
    return c.fetchone()

def get_all_standards():
    """Retrieve all standards content from database"""
    conn = init_db()
    c = conn.cursor()
    c.execute('''
        SELECT url, content, source, last_updated
        FROM standards_content
        WHERE status = 'active'
    ''')
    return c.fetchall()

def get_standards_last_update():
    """Get the timestamp of the last standards update"""
    conn = init_db()
    c = conn.cursor()
    c.execute('''
        SELECT MAX(last_updated) FROM standards_content
    ''')
    return c.fetchone()[0]
