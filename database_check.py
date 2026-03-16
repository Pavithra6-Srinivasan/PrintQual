"""
check_database.py - Check what's in the database
"""

from engine.database_manager import DatabaseManager

def main():
    print("\n" + "="*70)
    print("DATABASE CONTENTS CHECK")
    print("="*70)
    
    # Connect
    db = DatabaseManager(
        host="15.46.29.115",
        user="pavithra_030226",
        password="pavithra@030226",
        database="quality_sandbox"
    )
    
    try:
        conn = db.get_connection()
        cursor = conn.cursor(dictionary=True)
        
        # 1. Count total records
        cursor.execute("SELECT COUNT(*) as count FROM summary")
        total = cursor.fetchone()['count']
        print(f"\n📊 Total records: {total}")
        
        if total == 0:
            print("\n⚠ Database is empty - no data to analyze yet")
            print("  Generate some reports first!")
            cursor.close()
            conn.close()
            return
        
        # 2. Show unique quarters
        print("\n📅 Quarters in database:")
        cursor.execute("""
            SELECT DISTINCT year, quarter 
            FROM summary 
            ORDER BY year, quarter
        """)
        quarters = cursor.fetchall()
        for q in quarters:
            cursor.execute("""
                SELECT COUNT(*) as count 
                FROM summary 
                WHERE year = %s AND quarter = %s
            """, (q['year'], q['quarter']))
            count = cursor.fetchone()['count']
            print(f"  • Q{q['quarter']} {q['year']}: {count} records")
        
        # 3. Show categories
        print("\n📁 Categories:")
        cursor.execute("""
            SELECT DISTINCT category 
            FROM summary 
            ORDER BY category
        """)
        categories = cursor.fetchall()
        for cat in categories:
            print(f"  • {cat['category']}")
        
        # 4. Show sample records with enhanced fields
        print("\n📋 Sample Records (latest 5):")
        print("-" * 70)
        cursor.execute("""
            SELECT 
                category, media_type, overall_result,
                failed_units, failed_media_names, failed_error_types,
                year, quarter, generated_at
            FROM summary
            ORDER BY generated_at DESC
            LIMIT 5
        """)
        rows = cursor.fetchall()
        
        for i, row in enumerate(rows, 1):
            print(f"\n{i}. {row['category']} - {row['media_type']}")
            print(f"   Result: {row['overall_result']} | Q{row['quarter']} {row['year']}")
            
            if row['failed_units']:
                print(f"   Failed Units: {row['failed_units']}")
            if row['failed_media_names']:
                print(f"   Failed Media: {row['failed_media_names']}")
            if row['failed_error_types']:
                print(f"   Error Types: {row['failed_error_types']}")
        
        # 5. Test trend analysis
        print("\n" + "="*70)
        print("🔍 TREND ANALYSIS")
        print("="*70)
        
        trends = db.get_quarter_trends()
        
        if not trends:
            print("\n⚠ No trends detected yet (need at least 2 quarters of data)")
        else:
            print(f"\n✓ Found {len(trends)} trend(s):\n")
            
            for t in trends:
                print(f"📊 {t['category']} - {t['media_type']}")
                print(f"   Trend: {t['trend_type']}")
                print(f"   Data Points: {t['num_quarters']} quarters")
                
                earliest = t['earliest']
                latest = t['latest']
                
                print(f"   Earliest: Q{earliest['quarter']} {earliest['year']} - {earliest['overall_result']}")
                if earliest.get('failed_units'):
                    print(f"      Units: {earliest['failed_units']}")
                
                print(f"   Latest:   Q{latest['quarter']} {latest['year']} - {latest['overall_result']}")
                if latest.get('failed_units'):
                    print(f"      Units: {latest['failed_units']}")
                
                print()
        
        # 6. Summary statistics
        print("="*70)
        print("📈 STATISTICS")
        print("="*70)
        
        cursor.execute("""
            SELECT 
                COUNT(*) as total,
                SUM(CASE WHEN overall_result = 'Pass' THEN 1 ELSE 0 END) as pass_count,
                SUM(CASE WHEN overall_result = 'Fail' THEN 1 ELSE 0 END) as fail_count
            FROM summary
        """)
        stats = cursor.fetchone()
        
        pass_pct = (stats['pass_count'] / stats['total'] * 100) if stats['total'] > 0 else 0
        fail_pct = (stats['fail_count'] / stats['total'] * 100) if stats['total'] > 0 else 0
        
        print(f"\nTotal Tests: {stats['total']}")
        print(f"✓ Pass: {stats['pass_count']} ({pass_pct:.1f}%)")
        print(f"✗ Fail: {stats['fail_count']} ({fail_pct:.1f}%)")
        
        cursor.close()
        conn.close()
        
        print("\n" + "="*70)
        print("✓ Database check complete!")
        print("="*70 + "\n")
        
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()