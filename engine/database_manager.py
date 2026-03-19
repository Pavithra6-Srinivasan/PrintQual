import mysql.connector
from datetime import datetime

class DatabaseManager:
    
    def __init__(self, host, user, password, database):
        self.config = {
            'host': host,
            'user': user,
            'password': password,
            'database': database
        }
    
    def get_connection(self):
        return mysql.connector.connect(**self.config)
    
    def insert_summary_result(self, category, media_type, overall_result, 
                             failed_units, failed_media_names, failed_error_types,
                             failed_conditions, remarks, year, quarter):
        """Insert or update summary result in database."""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        query = """
        INSERT INTO summary (
            category, media_type, overall_result,
            failed_units, failed_media_names, failed_error_types, failed_conditions,
            remarks, year, quarter, generated_at
        ) VALUES (
            %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, NOW()
        )
        ON DUPLICATE KEY UPDATE
            overall_result = VALUES(overall_result),
            failed_units = VALUES(failed_units),
            failed_media_names = VALUES(failed_media_names),
            failed_error_types = VALUES(failed_error_types),
            failed_conditions = VALUES(failed_conditions),
            remarks = VALUES(remarks),
            generated_at = NOW()
        """
        
        cursor.execute(query, (
            category, media_type, overall_result,
            failed_units, failed_media_names, failed_error_types, failed_conditions,
            remarks, year, quarter
        ))
        
        conn.commit()
        cursor.close()
        conn.close()
    
    def get_quarter_trends(self):
        """Get historical trends with detailed failure analysis."""
        conn = self.get_connection()
        cursor = conn.cursor(dictionary=True)
        
        query = """
        SELECT 
            category, media_type, year, quarter,
            overall_result, failed_units, failed_media_names,
            failed_error_types, failed_conditions,
            remarks, generated_at
        FROM summary
        ORDER BY category, media_type, year, quarter
        """
        
        cursor.execute(query)
        results = cursor.fetchall()
        cursor.close()
        conn.close()
        
        # Group by category and media_type
        trends = {}
        for row in results:
            key = (row['category'], row['media_type'])
            if key not in trends:
                trends[key] = []
            trends[key].append(row)
        
        # Analyze trends
        trend_summaries = []
        for (category, media_type), history in trends.items():
            if len(history) < 2:
                continue
            
            history.sort(key=lambda x: (x['year'], x['quarter']))
            
            earliest = history[0]
            latest = history[-1]
            trend_type = self._detect_trend(history)
            
            summary = {
                'category': category,
                'media_type': media_type,
                'trend_type': trend_type,
                'num_quarters': len(history),
                'earliest': earliest,
                'latest': latest,
                'history': history
            }
            
            trend_summaries.append(summary)
        
        return trend_summaries
    
    def _detect_trend(self, history):
        """Detect trend pattern in historical data."""
        results = [str(h['overall_result']).strip().upper() for h in history]
        
        earliest_result = results[0]
        latest_result = results[-1]
        
        fail_count = sum(1 for r in results if r == 'FAIL')
        total = len(results)
        
        if earliest_result == 'PASS' and latest_result == 'FAIL':
            return 'DEGRADED'
        elif earliest_result == 'FAIL' and latest_result == 'PASS':
            return 'IMPROVED'
        elif fail_count == total and total >= 2:
            return 'PERSISTENT_FAILURE'
        elif fail_count > 0 and fail_count < total:
            return 'UNSTABLE'
        else:
            return 'STABLE_PASS'
    
    def create_tables(self):
        """
        Create database tables from scratch.
        FIXED: Properly creates table with all required columns.
        """
        conn = self.get_connection()
        cursor = conn.cursor()
        
        try:
            # Drop table if you want fresh start (optional - comment out if not needed)
            # cursor.execute("DROP TABLE IF EXISTS summary")
            
            # Create summary table with all enhanced columns
            cursor.execute("""
            CREATE TABLE IF NOT EXISTS summary (
                id INT AUTO_INCREMENT PRIMARY KEY,
                category VARCHAR(100) NOT NULL,
                media_type VARCHAR(100) NOT NULL,
                overall_result VARCHAR(50) NOT NULL,
                failed_units TEXT DEFAULT NULL,
                failed_media_names TEXT DEFAULT NULL,
                failed_error_types TEXT DEFAULT NULL,
                failed_conditions TEXT DEFAULT NULL,
                remarks TEXT DEFAULT NULL,
                year INT NOT NULL,
                quarter INT NOT NULL,
                generated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                UNIQUE KEY unique_entry (category, media_type, year, quarter),
                INDEX idx_year_quarter (year, quarter),
                INDEX idx_category_media (category, media_type),
                INDEX idx_result (overall_result)
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
            """)
            
            conn.commit()
            print("✓ Database table 'summary' created successfully")
            
            # Verify table structure
            cursor.execute("DESCRIBE summary")
            columns = cursor.fetchall()
            print("\nTable structure:")
            for col in columns:
                print(f"  - {col[0]}: {col[1]}")
            
        except Exception as e:
            print(f"❌ Error creating table: {e}")
            conn.rollback()
            raise
        finally:
            cursor.close()
            conn.close()
    
    def verify_connection(self):
        """Test database connection."""
        try:
            conn = self.get_connection()
            cursor = conn.cursor()
            cursor.execute("SELECT 1")
            result = cursor.fetchone()
            cursor.close()
            conn.close()
            print("✓ Database connection successful")
            return True
        except Exception as e:
            print(f"❌ Database connection failed: {e}")
            return False