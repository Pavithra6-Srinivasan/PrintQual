"""
check_db_data.py - Check what's in the database
"""

import urllib.parse
from engine.database_manager import DatabaseManager

# Connect
db = DatabaseManager(
    host="15.46.29.115",
    database="quality_sandbox",
    username="pavithra_030226",
    password=urllib.parse.quote_plus("pavithra@030226"),
    db_type="mysql"
)

try:
    print("\n" + "="*60)
    print("DATABASE CONTENTS")
    print("="*60)
    
    # Count total records
    with db.conn.cursor() as cursor:
        cursor.execute("SELECT COUNT(*) FROM summary")
        total = cursor.fetchone()[0]
        print(f"\nTotal records: {total}")
    
    if total == 0:
        print("\n⚠ Database is empty - no data to analyze yet")
        print("  Generate some reports first!")
    else:
        # Show quarters available
        print("\nQuarters in database:")
        quarters = db.get_all_quarters()
        for q in quarters:
            print(f"  - Q{q['quarter']} {q['year']}")
        
        # Show sample data
        print("\nSample records:")
        with db.conn.cursor() as cursor:
            cursor.execute("""
                SELECT category, media_type, overall_result, year, quarter
                FROM summary
                LIMIT 10
            """)
            rows = cursor.fetchall()
            
            for row in rows:
                print(f"  {row[0]:20} | {row[1]:15} | {row[2]:4} | Q{row[4]} {row[3]}")
        
        # Test trends
        print("\nTrend Analysis:")
        trends = db.get_quarter_trends()
        
        if trends:
            print(f"  Found {len(trends)} trends:")
            for t in trends:
                print(f"  - {t['category']} / {t['media_type']}")
                print(f"    {t['trend_description']}")
        else:
            print("  No trends detected (need at least 2 quarters)")
    
    print("\n" + "="*60)

finally:
    db.close()