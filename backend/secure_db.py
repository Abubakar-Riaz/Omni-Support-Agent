import os
from dotenv import load_dotenv
import psycopg2

load_dotenv('../.env')

def add_security():
    try:
        conn=psycopg2.connect(os.getenv('DATABASE_URL'),sslmode='require')
        cur=conn.cursor()

        cur.execute("ALTER TABLE orders ADD COLUMN IF NOT EXISTS user_id INTEGER;")
        cur.execute("SELECT id FROM users WHERE email='test@developer.com'")
        user=cur.fetchone()

        if user:
            my_id=user[0]
            print(f"Setting all dummy orders to User ID:{my_id}")

            cur.execute("UPDATE orders SET user_id=%s WHERE user_id IS NULL",(my_id,))
            conn.commit()
            print("Security Update Completed!")
        else:
            print("User test@developer.com not found")
        conn.close()
    except Exception as e:
        print(f"Error:{e}")
if __name__=="__main__":
    add_security()