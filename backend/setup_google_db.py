import os
import psycopg2
from dotenv import load_dotenv

load_dotenv(dotenv_path="../.env")
DB_URL = os.getenv("DATABASE_URL")

def reset_users_table():
    try:
        conn = psycopg2.connect(DB_URL, sslmode='require')
        cur = conn.cursor()
        
        cur.execute("DROP TABLE IF EXISTS user_threads;")
        cur.execute("DROP TABLE IF EXISTS users;")
        
        cur.execute("""
            CREATE TABLE users (
                id SERIAL PRIMARY KEY,
                email TEXT UNIQUE NOT NULL,
                google_sub TEXT UNIQUE NOT NULL, -- The Unique ID from Google
                full_name TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
        """)

        cur.execute("""
            CREATE TABLE user_threads (
                user_id INTEGER REFERENCES users(id),
                thread_id TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                PRIMARY KEY (user_id, thread_id)
            );
        """)
        
        conn.commit()
        print("Database ready for Google Auth!")
        conn.close()
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    reset_users_table()