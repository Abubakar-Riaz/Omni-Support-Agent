import os
from dotenv import load_dotenv
import psycopg2
from datetime import datetime,timedelta
from psycopg_pool import ConnectionPool
from langgraph.checkpoint.postgres import PostgresSaver
from psycopg.rows import dict_row

load_dotenv("../.env")
DB_URL=os.getenv("DATABASE_URL")

RESET_DB=True

def setup_database():
    if not DB_URL:
        print(f"Error:DATABASE URL Not Found")
        return
    try:
        print(f"Connecting to Database")

        conn=psycopg2.connect(DB_URL,sslmode='require')
        with conn:
            with conn.cursor() as cur:
                if RESET_DB:
                    print("RESET TRIGGERED: Dropping all tables")
                    cur.execute("DROP TABLE IF EXISTS return_labels CASCADE;")
                    cur.execute("DROP TABLE IF EXISTS tickets CASCADE;")
                    cur.execute("DROP TABLE IF EXISTS order_items CASCADE;")
                    cur.execute("DROP TABLE IF EXISTS orders CASCADE;")
                    cur.execute("DROP TABLE IF EXISTS items CASCADE;")
                    cur.execute("DROP TABLE IF EXISTS user_threads CASCADE;")
                    cur.execute("DROP TABLE IF EXISTS users CASCADE;")
                
                print("Creating user table")
                cur.execute("""
                    CREATE TABLE IF NOT EXISTS users (
                        id SERIAL PRIMARY KEY,
                        email TEXT UNIQUE NOT NULL,
                        google_sub TEXT UNIQUE,
                        full_name TEXT,
                        created_at TIMESTAMP DEFAULT NOW()
                    );
                """)

                print("Creating items table")
                cur.execute("""
                    CREATE TABLE IF NOT EXISTS items (
                        id SERIAL PRIMARY KEY,
                        name TEXT UNIQUE NOT NULL,
                        description TEXT,
                        current_price DECIMAL(10,2) NOT NULL,
                        category TEXT,
                        stock_quantity INTEGER DEFAULT 100
                    );
                """)

                print("Creating orders table")
                cur.execute("""
                CREATE TABLE IF NOT EXISTS orders (
                    order_id TEXT PRIMARY KEY,
                    user_id INTEGER REFERENCES users(id),
                    status TEXT NOT NULL CHECK (status IN ('Processing', 'Shipped', 'Delivered', 'Cancelled', 'Returned')),
                    total_amount DECIMAL(10,2) DEFAULT 0.00,
                    purchase_date DATE DEFAULT CURRENT_DATE 
                );
            """)
                
                print("Creating order_items")
                cur.execute("""
                    CREATE TABLE IF NOT EXISTS order_items (
                        id SERIAL PRIMARY KEY,
                        order_id TEXT REFERENCES orders(order_id),
                        item_id INTEGER REFERENCES items(id),  -- <--- THE LINK
                        quantity INTEGER DEFAULT 1,
                        unit_price DECIMAL(10,2) NOT NULL -- Price at time of purchase (Snapshot)
                    );
                """)
                
                print("Creating tickets")
                cur.execute("""
                    CREATE TABLE IF NOT EXISTS tickets (
                        id SERIAL PRIMARY KEY,
                        ticket_id TEXT UNIQUE NOT NULL,
                        user_id INTEGER REFERENCES users(id),
                        order_id TEXT REFERENCES orders(order_id),
                        issue TEXT NOT NULL,
                        status TEXT DEFAULT 'Open',
                        created_at TIMESTAMP DEFAULT NOW()
                    );
                """)

                print("Creating return_labels")
                cur.execute("""
                    CREATE TABLE IF NOT EXISTS return_labels (
                        id SERIAL PRIMARY KEY,
                        label_id TEXT UNIQUE NOT NULL,
                        ticket_id TEXT REFERENCES tickets(ticket_id),
                        status TEXT DEFAULT 'Generated',
                        created_at TIMESTAMP DEFAULT NOW()
                    );
                """)

                cur.execute("""
                    CREATE TABLE IF NOT EXISTS user_threads (
                        user_id INTEGER REFERENCES users(id),
                        thread_id TEXT NOT NULL,
                        title TEXT DEFAULT 'New Chat',
                        created_at TIMESTAMP DEFAULT NOW(),
                        PRIMARY KEY (user_id, thread_id)
                    );
                """)

                print("Seeding Professional Data...")
                
                cur.execute("INSERT INTO users (email, google_sub, full_name) VALUES (%s, %s, %s) ON CONFLICT (email) DO NOTHING RETURNING id;", 
                           ('test@developer.com', 'dev_master', 'Developer Account'))
                user_id = cur.fetchone()[0]

                products = [
                    ('Wireless Headphones', 'Noise cancelling over-ear headphones', 199.99, 'Electronics',100),
                    ('Protection Case', 'Hard shell case for headphones', 49.99, 'Accessories',0),
                    ('Gaming Laptop', 'RTX 4060, 16GB RAM, 1TB SSD', 1200.00, 'Computers',100),
                    ('Mechanical Keyboard', 'RGB Backlit, Blue Switches', 89.99, 'Electronics',100),
                    ('USB-C Cable', '2 Meter fast charging cable', 19.99, 'Accessories',0)
                ]
                item_map = {}
                for p in products:
                    cur.execute("""
                        INSERT INTO items (name, description, current_price, category,stock_quantity) 
                        VALUES (%s, %s, %s, %s,%s) 
                        ON CONFLICT (name) DO UPDATE SET current_price = EXCLUDED.current_price
                        RETURNING id, name;
                    """, p)
                    row = cur.fetchone()
                    item_map[row[1]] = row[0]

                old_date = datetime.now() - timedelta(days=45)
                cur.execute("INSERT INTO orders (order_id, user_id, status, total_amount, purchase_date) VALUES (%s, %s, 'Shipped', 249.98, %s) ON CONFLICT DO NOTHING;", ('ORD-001', user_id, old_date))
                
                cur.execute("INSERT INTO order_items (order_id, item_id, quantity, unit_price) VALUES (%s, %s, 1, 199.99);", 
                           ('ORD-001', item_map['Wireless Headphones']))
                cur.execute("INSERT INTO order_items (order_id, item_id, quantity, unit_price) VALUES (%s, %s, 1, 49.99);", 
                           ('ORD-001', item_map['Protection Case']))

                cur.execute("INSERT INTO orders (order_id, user_id, status, total_amount, purchase_date) VALUES (%s, %s, 'Processing', 1200.00, %s) ON CONFLICT DO NOTHING;", ('ORD-002', user_id, datetime.now()))
                cur.execute("INSERT INTO order_items (order_id, item_id, quantity, unit_price) VALUES (%s, %s, 1, 1200.00);", 
                           ('ORD-002', item_map['Gaming Laptop']))
                print("Database Ready")
            
    except Exception as e:
        print(f"Database Setup Error:{e}")
    finally:
        if 'conn' in locals() and conn: conn.close()

def setup_persistence():
    """Sets up the LangGraph Checkpoint tables"""

    try:
        print("Setting up AI Memory")
        pool=ConnectionPool(
            conninfo=DB_URL,
            kwargs={"autocommit":True,"row_factory":dict_row}
        )   
        checkpointer=PostgresSaver(pool)
        checkpointer.setup()
        print("AI Memory table ready")
    except Exception as e:
        print(f"Persistence Setup Error:{e}")

if __name__=="__main__":
    setup_database()
    setup_persistence()