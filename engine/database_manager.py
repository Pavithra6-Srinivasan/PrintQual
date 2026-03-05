import pymysql
from pymysql.err import OperationalError, ProgrammingError
import urllib.parse

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

    def close(self):
        if self.conn:
            self.conn.close()
            print("✓ Database connection closed")