import sqlite3
from datetime import datetime
import logging

logger = logging.getLogger(__name__)

def check_update_status():
    """Check the status of automatic updates system"""
    try:
        # Connect to SQLite database
        conn = sqlite3.connect('finance.db')
        cursor = conn.cursor()
        
        # Get latest scraping logs
        cursor.execute("""
            SELECT timestamp, source, status, message 
            FROM scraping_log 
            ORDER BY timestamp DESC 
            LIMIT 5
        """)
        logs = cursor.fetchall()
        
        # Get standards content stats
        cursor.execute("""
            SELECT COUNT(*), MIN(last_updated), MAX(last_updated)
            FROM standards_content
            WHERE status = 'active'
        """)
        content_stats = cursor.fetchone()
        
        # Format results
        result = {
            'latest_logs': logs,
            'total_standards': content_stats[0] if content_stats else 0,
            'oldest_update': content_stats[1] if content_stats else None,
            'latest_update': content_stats[2] if content_stats else None
        }
        
        conn.close()
        return result
        
    except Exception as e:
        logger.error(f"Error checking update status: {str(e)}")
        return None
