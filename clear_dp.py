"""
clear_db.py - Clear all data from summary table
"""

import urllib.parse
from engine.database_manager import DatabaseManager

# Connect to database
db = DatabaseManager(
    host="15.46.29.115",
    database="quality_sandbox",
    username="pavithra_030226",
    password=urllib.parse.quote_plus("pavithra@030226"),
    db_type="mysql"
)

try:
    # Clear all data
    with db.conn.cursor() as cursor:
        cursor.execute("DELETE FROM summary")
        rows_deleted = cursor.rowcount
        print(f"✓ Deleted {rows_deleted} rows from summary table")
    
    # Verify
    with db.conn.cursor() as cursor:
        cursor.execute("SELECT COUNT(*) FROM summary")
        count = cursor.fetchone()[0]
        print(f"✓ Table now has {count} rows")

finally:
    db.close()