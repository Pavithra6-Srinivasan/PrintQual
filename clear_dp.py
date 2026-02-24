from engine.database_manager import DatabaseManager
from sqlalchemy import text
import urllib.parse

db = DatabaseManager(
    host="15.46.29.115",
    database="quality_sandbox",
    username="pavithra_030226",
    password=urllib.parse.quote_plus("pavithra@030226"),
    db_type="mysql"
)

with db.engine.connect() as conn:

    # Disable foreign key checks
    conn.execute(text("SET FOREIGN_KEY_CHECKS = 0;"))

    # Get all tables
    result = conn.execute(text("SHOW TABLES;"))
    tables = [row[0] for row in result]

    for table in tables:
        print(f"Clearing {table}...")
        conn.execute(text(f"TRUNCATE TABLE `{table}`;"))

    # Enable foreign key checks
    conn.execute(text("SET FOREIGN_KEY_CHECKS = 1;"))

    conn.commit()

print("✅ Database cleared successfully!")