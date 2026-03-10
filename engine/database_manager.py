import pymysql
from pymysql.err import OperationalError
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

        self.ensure_connection()
        with self.conn.cursor() as cursor:
            create_sql = """
            CREATE TABLE IF NOT EXISTS summary (
                id INT AUTO_INCREMENT PRIMARY KEY,
                category VARCHAR(100),
                unit VARCHAR(50),
                media_type VARCHAR(100),
                overall_result VARCHAR(10),
                common_failure_factor TEXT,
                year INT,
                quarter INT
            );
            """
            cursor.execute(create_sql)
            print("✓ Summary table ready")

    def insert_test_result(self, category, unit, media_type, result, year, quarter):

        self.ensure_connection()

        query = """
        INSERT INTO test_results
        (category, unit, media_type, result, year, quarter)
        VALUES (%s, %s, %s, %s, %s, %s)
        """

        with self.conn.cursor() as cursor:
            cursor.execute(query, (
                category,
                unit,
                media_type,
                result,
                year,
                quarter
            ))

    def insert_summary(self, summary_data, year, quarter):
        """
        Inserts summary data into the database.
        """
        
        self.ensure_connection()
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
                    category = cat.get("category", "Unknown")
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
        
        self.ensure_connection()
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
        
        self.ensure_connection()
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
        """
        Get trends comparing ALL quarters for each category/media combination.
        Shows overall trend from earliest to latest.
        """
        
        self.ensure_connection()

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

        if not rows:
            return []

        trends = []
        grouped = {}

        # Group by (category, media_type)
        for r in rows:
            key = (r["category"], r["media_type"])
            if key not in grouped:
                grouped[key] = []
            grouped[key].append((r["year"], r["quarter"], r["overall_result"]))

        # Analyze trends for each category/media
        for (category, media), values in grouped.items():
            if len(values) < 2:
                continue  # Need at least 2 quarters to compare

            # Sort chronologically
            values.sort(key=lambda x: (x[0], x[1]))

            # Get earliest and latest
            earliest = values[0]
            latest = values[-1]
            
            earliest_label = f"Q{earliest[1]} {earliest[0]}"
            latest_label = f"Q{latest[1]} {latest[0]}"
            earliest_result = earliest[2].lower()
            latest_result = latest[2].lower()

            # Count pass/fail across all quarters
            pass_count = sum(1 for v in values if v[2].lower() == "pass")
            fail_count = sum(1 for v in values if v[2].lower() == "fail")
            total = len(values)

            # Build trend description
            trend_desc = None

            # Case 1: Degraded (was pass, now fail)
            if earliest_result == "pass" and latest_result == "fail":
                trend_desc = f"⚠ DEGRADED: {earliest_label} PASS → {latest_label} FAIL"
                if total > 2:
                    trend_desc += f" (across {total} quarters)"

            # Case 2: Improved (was fail, now pass)
            elif earliest_result == "fail" and latest_result == "pass":
                trend_desc = f"✓ IMPROVED: {earliest_label} FAIL → {latest_label} PASS"
                if total > 2:
                    trend_desc += f" (across {total} quarters)"

            # Case 3: Persistent failure
            elif fail_count == total:
                trend_desc = f"⚠ PERSISTENT FAILURE: All {total} quarters FAIL ({earliest_label} to {latest_label})"

            # Case 4: Consistent pass (good, no alert needed)
            elif pass_count == total:
                pass

            # Case 5: Unstable (mixed results)
            elif fail_count > 0 and pass_count > 0:
                trend_desc = f"⚠ UNSTABLE: {fail_count}/{total} quarters failed between {earliest_label} and {latest_label}"

            # Add to trends if noteworthy
            if trend_desc:
                trends.append({
                    "category": category,
                    "media_type": media,
                    "trend_description": trend_desc,
                    "quarters": total,
                    "pass_count": pass_count,
                    "fail_count": fail_count
                })

        return trends

    def ensure_connection(self):
        """
        Reconnect if the database connection was closed.
        """
        try:
            self.conn.ping(reconnect=True)
        except:
            self.connect()

    def close(self):
        if self.conn:
            self.conn.close()
            print("✓ Database connection closed")