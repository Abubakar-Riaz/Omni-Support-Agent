import os
import psycopg2
from dotenv import load_dotenv

load_dotenv(dotenv_path="../.env")

DB_URL = os.getenv("DATABASE_URL")

if not DB_URL:
    print("ERROR: DATABASE_URL not found in .env file.")
    exit()

#print(f"Connecting to Cloud Database...")

try:
    conn = psycopg2.connect(DB_URL, sslmode='require')
    cursor = conn.cursor()

    #print("Dropping old tables (if any)...")
    cursor.execute("DROP TABLE IF EXISTS orders;")
    
    #print("Creating 'orders' table...")
    table_creation_query = """
        CREATE TABLE orders(
        ID VARCHAR(10) PRIMARY KEY,
        Cust_Name TEXT NOT NULL,
        Item_Name TEXT NOT NULL,
        Status TEXT NOT NULL CHECK(Status IN('Shipped', 'Pending', 'Delayed', 'Cancelled')),
        Price FLOAT NOT NULL
    );
    """
    cursor.execute(table_creation_query)

    #print("Inserting sample data...")
    table_insertion_query = """
    INSERT INTO orders (id, cust_name, item_name, status, price) VALUES
    ('ORD0001', 'Alice Johnson', 'Wireless Mouse', 'Delayed', 25.99),
    ('ORD0002', 'Bob Smith', 'Mechanical Keyboard', 'Shipped', 89.99),
    ('ORD0003', 'Carlos Rivera', 'USB-C Charger', 'Pending', 19.99),
    ('ORD0004', 'Diana Lee', 'Noise Cancelling Headphones', 'Cancelled', 129.99),
    ('ORD0005', 'Ethan Brown', 'Sticker Pack', 'Shipped', 1.99),
    ('ORD0006', 'Fiona Green', '4K Monitor', 'Pending', 349.99),
    ('ORD0007', 'Alice Johnson', 'Laptop Stand', 'Shipped', 45.99),
    ('ORD0008', 'George White', 'External Hard Drive', 'Delayed', 74.99);
    """
    cursor.execute(table_insertion_query)

    conn.commit()
    #print("SUCCESS: Cloud Database is ready and populated!")

    cursor.execute("SELECT count(*) FROM orders;")
    count = cursor.fetchone()[0]
    #print(f"Verified: {count} rows found in the cloud.")

    cursor.close()
    conn.close()

except Exception as e:
    print(f"FAILED: {e}")