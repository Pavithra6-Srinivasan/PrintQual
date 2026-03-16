"""
reset_database.py - Drop and recreate the summary table
"""

from engine.database_manager import DatabaseManager

def main():
    print("Resetting database (DROP + CREATE)...")
    print("-" * 50)
    
    # Connect to database
    db = DatabaseManager(
        host="15.46.29.115",
        user="pavithra_030226",
        password="pavithra@030226",
        database="quality_sandbox"
    )
    
    try:
        conn = db.get_connection()
        cursor = conn.cursor()
        
        # Ask for confirmation
        response = input("\n⚠ WARNING: This will DELETE the entire summary table and recreate it.\nAre you sure? (yes/no): ")
        
        if response.lower() != 'yes':
            print("Operation cancelled.")
            cursor.close()
            conn.close()
            return
        
        # Drop table
        print("\n1. Dropping existing table...")
        cursor.execute("DROP TABLE IF EXISTS summary")
        conn.commit()
        print("✓ Table dropped")
        
        # Close this connection
        cursor.close()
        conn.close()
        
        # Recreate table using create_tables method
        print("\n2. Creating fresh table...")
        db.create_tables()
        
        print("\n" + "=" * 50)
        print("✓ Database reset complete!")
        print("=" * 50)
        
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()