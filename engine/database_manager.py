"""
database_manager.py

Handles SQL connections and pivot summary storage.
"""

from sqlalchemy import create_engine, text
import pandas as pd
from datetime import datetime


class DatabaseManager:
    def __init__(self, host, database, username, password, db_type="mysql"):
        self.db_type = db_type

        connection_string = f"mysql+pymysql://{username}:{password}@{host}/{database}"

        self.engine = create_engine(connection_string)

    def create_tables(self):
        """
        Creates pivot_summary table if not exists.
        """

        query = """
        CREATE TABLE IF NOT EXISTS pivot_summary (
            id INT AUTO_INCREMENT PRIMARY KEY,
            run_timestamp DATETIME,
            category VARCHAR(255),
            total_pass INT,
            total_fail INT,
            fail_rate FLOAT
        )
        """

        with self.engine.connect() as conn:
            conn.execute(text(query))
            conn.commit()

    def insert_summary(self, summary_data):
        """
        Insert summary results into SQL.
        """
        timestamp = datetime.now()

        for category in summary_data["categories"]:

            insert_query = text("""
                INSERT INTO pivot_summary
                (run_timestamp, category, total_pass, total_fail, fail_rate)
                VALUES
                (:timestamp, :category, :pass, :fail, :rate)
            """)

            with self.engine.connect() as conn:
                conn.execute(insert_query, {
                    "timestamp": timestamp,
                    "category": category["category"],
                    "pass": category["total_pass"],
                    "fail": category["total_fail"],
                    "rate": category["fail_rate"],
                })
                conn.commit()
