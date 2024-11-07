"""File format handlers for financial data import"""
import pandas as pd
import json
import xml.etree.ElementTree as ET
import io
from typing import Dict, Any, Optional
import csv

def detect_format(file_obj: io.BytesIO) -> str:
    """Detect the format of the uploaded file"""
    content_start = file_obj.read(4096)  # Read first 4KB
    file_obj.seek(0)  # Reset file pointer
    
    # Try to decode as text
    try:
        content_str = content_start.decode('utf-8')
        
        # Check for JSON format
        if content_str.strip().startswith('{') or content_str.strip().startswith('['):
            try:
                json.loads(content_str.strip())
                return 'json'
            except json.JSONDecodeError:
                pass
        
        # Check for XML format
        if content_str.strip().startswith('<?xml') or content_str.strip().startswith('<'):
            try:
                ET.fromstring(content_str)
                return 'xml'
            except ET.ParseError:
                pass
        
        # Check for CSV format
        try:
            dialect = csv.Sniffer().sniff(content_str)
            if dialect:
                return 'csv'
        except:
            pass
            
    except UnicodeDecodeError:
        pass
    
    # Check for Excel format (binary)
    if content_start.startswith(b'PK\x03\x04') or content_start.startswith(b'\xd0\xcf\x11\xe0'):
        return 'excel'
    
    # Check for fixed-width format (assuming it has consistent spacing)
    try:
        lines = content_str.split('\n')[:5]  # Check first 5 lines
        if all(len(line) == len(lines[0]) for line in lines[1:] if line.strip()):
            return 'fixed-width'
    except:
        pass
    
    return 'unknown'

def validate_dataframe(df: pd.DataFrame) -> bool:
    """Validate if the DataFrame has the required columns and structure"""
    required_columns = {
        'Account_code', 'Account_name',
        'opening_balance_debit', 'opening_balance_credit',
        'current_turnover_debit', 'current_turnover_credit',
        'end_of_period_debit', 'end_of_period_credit'
    }
    
    # Check if required columns exist
    missing_columns = required_columns - set(df.columns)
    if missing_columns:
        raise ValueError(f"Missing required columns: {', '.join(missing_columns)}")
    
    # Validate numeric columns
    numeric_columns = [
        'opening_balance_debit', 'opening_balance_credit',
        'current_turnover_debit', 'current_turnover_credit',
        'end_of_period_debit', 'end_of_period_credit'
    ]
    
    for col in numeric_columns:
        if not pd.to_numeric(df[col], errors='coerce').notna().all():
            raise ValueError(f"Column {col} must contain only numeric values")
    
    # Validate account code and name
    if df['Account_code'].isna().any():
        raise ValueError("Account_code cannot contain empty values")
    if df['Account_name'].isna().any():
        raise ValueError("Account_name cannot contain empty values")
    
    return True

def parse_fixed_width(file_obj: io.BytesIO) -> pd.DataFrame:
    """Parse fixed-width format file"""
    # Define column widths for the new structure
    widths = [10, 30, 15, 15, 15, 15, 15, 15]  # Adjusted for new columns
    names = [
        'Account_code', 'Account_name',
        'opening_balance_debit', 'opening_balance_credit',
        'current_turnover_debit', 'current_turnover_credit',
        'end_of_period_debit', 'end_of_period_credit'
    ]
    
    try:
        df = pd.read_fwf(file_obj, widths=widths, names=names)
        df = df.fillna(0)  # Replace NaN with 0 for numeric columns
        return df
    except Exception as e:
        raise ValueError(f"Error parsing fixed-width file: {str(e)}")

def parse_xml(file_obj: io.BytesIO) -> pd.DataFrame:
    """Parse XML format file"""
    try:
        tree = ET.parse(file_obj)
        root = tree.getroot()
        
        data = []
        for entry in root.findall('.//entry'):
            row = {
                'Account_code': entry.find('account_code').text if entry.find('account_code') is not None else '',
                'Account_name': entry.find('account_name').text if entry.find('account_name') is not None else '',
                'opening_balance_debit': float(entry.find('opening_debit').text) if entry.find('opening_debit') is not None else 0,
                'opening_balance_credit': float(entry.find('opening_credit').text) if entry.find('opening_credit') is not None else 0,
                'current_turnover_debit': float(entry.find('turnover_debit').text) if entry.find('turnover_debit') is not None else 0,
                'current_turnover_credit': float(entry.find('turnover_credit').text) if entry.find('turnover_credit') is not None else 0,
                'end_of_period_debit': float(entry.find('ending_debit').text) if entry.find('ending_debit') is not None else 0,
                'end_of_period_credit': float(entry.find('ending_credit').text) if entry.find('ending_credit') is not None else 0
            }
            data.append(row)
        
        return pd.DataFrame(data)
    except Exception as e:
        raise ValueError(f"Error parsing XML file: {str(e)}")

def parse_json(file_obj: io.BytesIO) -> pd.DataFrame:
    """Parse JSON format file"""
    try:
        data = json.load(file_obj)
        if isinstance(data, list):
            df = pd.DataFrame(data)
        elif isinstance(data, dict) and 'entries' in data:
            df = pd.DataFrame(data['entries'])
        else:
            raise ValueError("Invalid JSON structure")
        
        # Ensure all required columns exist
        required_columns = [
            'Account_code', 'Account_name',
            'opening_balance_debit', 'opening_balance_credit',
            'current_turnover_debit', 'current_turnover_credit',
            'end_of_period_debit', 'end_of_period_credit'
        ]
        
        for col in required_columns:
            if col not in df.columns:
                df[col] = 0
                
        return df
    except Exception as e:
        raise ValueError(f"Error parsing JSON file: {str(e)}")

def read_financial_file(file_obj: io.BytesIO, filename: str) -> pd.DataFrame:
    """Read and parse financial data file in various formats"""
    # Detect format based on content and extension
    format_type = detect_format(file_obj)
    
    try:
        if format_type == 'csv':
            df = pd.read_csv(file_obj)
        elif format_type == 'excel':
            df = pd.read_excel(file_obj)
        elif format_type == 'json':
            df = parse_json(file_obj)
        elif format_type == 'xml':
            df = parse_xml(file_obj)
        elif format_type == 'fixed-width':
            df = parse_fixed_width(file_obj)
        else:
            raise ValueError(f"Unsupported file format: {format_type}")
        
        # Validate the DataFrame structure
        validate_dataframe(df)
        
        # Clean up the data - ensure numeric columns are proper type
        numeric_columns = [
            'opening_balance_debit', 'opening_balance_credit',
            'current_turnover_debit', 'current_turnover_credit',
            'end_of_period_debit', 'end_of_period_credit'
        ]
        
        for col in numeric_columns:
            df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0)
        
        return df
        
    except Exception as e:
        raise ValueError(f"Error processing file: {str(e)}")
