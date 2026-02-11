import os
import psycopg2
from dotenv import load_dotenv

load_dotenv(dotenv_path="../.env")
DB_URL = os.getenv("DATABASE_URL")

def add_title_column():
    try:
        conn = psycopg2.connect(DB_URL, sslmode='require')
        cur = conn.cursor()

        cur.execute("""
            ALTER TABLE user_threads 
            ADD COLUMN IF NOT EXISTS title TEXT DEFAULT 'New Chat';
        """)
        
        conn.commit()
        print("Column 'title' added successfully!")
        conn.close()
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    add_title_column()