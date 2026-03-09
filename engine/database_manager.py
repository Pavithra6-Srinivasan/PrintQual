import pymysql
from pymysql.err import OperationalError, ProgrammingError
import urllib.parse
from sqlalchemy import text

class DatabaseManager:
    """
    Manages database connection and summary insertion for Life Test reports.
    """
    def __init__(self, host, database, username, password, db_type="mysql"):
        self.host = host
        self.database = database
        self.username = username
        self.password = urllib.parse.unquote_plus(password)
        self.db_type = db_type
        self.conn = None

        self.connect()

    def connect(self):
        try:
            self.conn = pymysql.connect(
                host=self.host,
                user=self.username,
                password=self.password,
                database=self.database,
                autocommit=True
            )
            print("✓ Database connection established")
        except OperationalError as e:
            raise ConnectionError(f"Database connection failed: {e}")

    def create_tables(self):
        """
        Creates the summary table if it does not exist.
        """
        with self.conn.cursor() as cursor:
            create_sql = """
            CREATE TABLE IF NOT EXISTS summary (
                id INT AUTO_INCREMENT PRIMARY KEY,
                category VARCHAR(100),
                media_type VARCHAR(100),
                overall_result VARCHAR(10),
                common_failure_factor TEXT,
                year INT,
                quarter INT
            );
            """
            cursor.execute(create_sql)
            print("✓ Summary table ready")

    def insert_summary(self, summary_data, year, quarter):
        """
        Inserts summary data into the database.
        summary_data should have the structure:
        summary_data['categories'][i]['media_summary'][j] -> dict with keys:
        'category', 'media_type', 'overall_result', 'common_failure_factor'
        """
        if not summary_data or "categories" not in summary_data:
            raise ValueError("Invalid summary_data format")

        with self.conn.cursor() as cursor:
            insert_sql = """
            INSERT INTO summary
            (category, media_type, overall_result, common_failure_factor, year, quarter)
            VALUES (%s, %s, %s, %s, %s, %s);
            """

            for cat in summary_data["categories"]:
                for media in cat.get("media_summary", []):
                    category = media.get("category", "Unknown")
                    media_type = media.get("media_type", "Unknown")
                    overall_result = media.get("overall_result", "NO DATA")
                    common_factor = "\n".join(media.get("failed_combinations", []))

                    cursor.execute(
                        insert_sql,
                        (category, media_type, overall_result, common_factor, year, quarter)
                    )

            print(f"✓ Inserted summary data for year={year}, quarter={quarter}")
    
    def get_all_quarters(self):
        """Get list of all quarters in database"""
        query = """
            SELECT DISTINCT year, quarter
            FROM summary
            ORDER BY year DESC, quarter DESC
        """
        
        with self.conn.cursor(pymysql.cursors.DictCursor) as cursor:
            cursor.execute(query)
            return cursor.fetchall()
    
    def get_quarter_summary(self, year, quarter):
        """Get summary for a specific quarter"""
        query = """
            SELECT category, media_type, overall_result, common_failure_factor
            FROM summary
            WHERE year = %s AND quarter = %s
            ORDER BY category, media_type
        """
        
        with self.conn.cursor(pymysql.cursors.DictCursor) as cursor:
            cursor.execute(query, (year, quarter))
            return cursor.fetchall()

    def get_quarter_trends(self):

        query = """
            SELECT
                year,
                quarter,
                category,
                media_type,
                overall_result
            FROM summary
            ORDER BY category, media_type, year, quarter
        """

        with self.conn.cursor(pymysql.cursors.DictCursor) as cursor:
            cursor.execute(query)
            rows = cursor.fetchall()

        trends = []
        grouped = {}

        for r in rows:
            key = (r["category"], r["media_type"])

            if key not in grouped:
                grouped[key] = []

            grouped[key].append((r["year"], r["quarter"], r["overall_result"]))

        for (category, media), values in grouped.items():

            if len(values) < 2:
                continue

            # Simple trend logic: check if latest result became FAIL
            prev_result = values[-2][2]
            latest_result = values[-1][2]

            if prev_result == "PASS" and latest_result == "FAIL":

                trends.append({
                    "category": category,
                    "media_type": media,
                    "trend_description":
                        f"Result changed from PASS to FAIL in latest quarter"
                })

        return trends

    def close(self):
        if self.conn:
            self.conn.close()
            print("✓ Database connection closed")