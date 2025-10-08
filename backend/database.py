import psycopg2
from psycopg2.extras import RealDictCursor
import os
from dotenv import load_dotenv

load_dotenv()

class Database:
    def __init__(self):
        self.conn = None
        self.connect()
    
    def connect(self):
        try:
            self.conn = psycopg2.connect(
                host=os.getenv('DB_HOST', 'localhost'),
                port=os.getenv('DB_PORT', '5432'),
                database=os.getenv('DB_NAME', 'ai_dbms'),
                user=os.getenv('DB_USER', 'postgres'),
                password=os.getenv('DB_PASSWORD', '')
            )
        except Exception as e:
            raise Exception(f"Database connection failed: {str(e)}")
    
    def execute_query(self, query, params=None, fetch=True):
        try:
            with self.conn.cursor(cursor_factory=RealDictCursor) as cur:
                cur.execute(query, params)
                if fetch:
                    result = cur.fetchall()
                    self.conn.commit()
                    return result
                self.conn.commit()
                return None
        except Exception as e:
            self.conn.rollback()
            raise e
    
    def close(self):
        if self.conn:
            self.conn.close()
