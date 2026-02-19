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
            fail_rate FLOAT,
            worst_column VARCHAR(255)
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
            worst_col = (
                category["worst_columns"][0][0]
                if category["worst_columns"]
                else None
            )

            insert_query = text("""
                INSERT INTO pivot_summary
                (run_timestamp, category, total_pass, total_fail, fail_rate, worst_column)
                VALUES
                (:timestamp, :category, :pass, :fail, :rate, :worst)
            """)

            with self.engine.connect() as conn:
                conn.execute(insert_query, {
                    "timestamp": timestamp,
                    "category": category["category"],
                    "pass": category["total_pass"],
                    "fail": category["total_fail"],
                    "rate": category["fail_rate"],
                    "worst": worst_col
                })
                conn.commit()
