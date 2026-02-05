import sqlite3

db_connection=sqlite3.connect("../data/orders.db")
cursor=db_connection.cursor()

cursor.execute("DROP TABLE IF EXISTS orders;")
db_connection.commit()

table_creation_query="""
    CREATE TABLE orders(
    ID VARCHAR(10) PRIMARY KEY,
    Cust_Name TEXT NOT NULL,
    Item_Name TEXT NOT NULL,
    Status TEXT NOT NULL CHECK(Status IN('Shipped', 'Pending', 'Delayed', 'Cancelled')),
    Price FLOAT NOT NULL
    );
"""
cursor.execute(table_creation_query)

db_connection.commit()

print("Table is ready")

table_insertion_query="""
INSERT INTO orders (ID, Cust_Name, Item_Name, Status, Price) VALUES
('ORD0001', 'Alice Johnson', 'Wireless Mouse', 'Delayed', 25.99),
('ORD0002', 'Bob Smith', 'Mechanical Keyboard', 'Shipped', 89.99),
('ORD0003', 'Carlos Rivera', 'USB-C Charger', 'Pending', 19.99),
('ORD0004', 'Diana Lee', 'Noise Cancelling Headphones', 'Cancelled', 12.999),
('ORD0005', 'Ethan Brown', 'Sticker Pack', 'Shipped', 1.99),
('ORD0006', 'Fiona Green', '4K Monitor', 'Pending', 349.99),
('ORD0007', 'Alice Johnson', 'Laptop Stand', 'Shipped', 45.99),
('ORD0008', 'George White', 'External Hard Drive', 'Delayed', 74.99);
"""

cursor.execute(table_insertion_query)

db_connection.commit()

cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='orders';")
table=cursor.fetchone()

if table:
    print("Table has been created")

    cursor.execute("SELECT * FROM orders")
    rows=cursor.fetchall()
    print("Row inserted ",len(rows))
    
    for row in rows:
        print(row)
else:
    print("Table not created")
db_connection.close()

rules = """
OMNI-SUPPORT INC. - COMPANY POLICY MANUAL (2025)

1. SHIPPING & DELIVERY
   - Standard Shipping: 5-7 business days. Free for orders over $50.
   - Express Shipping: 2 business days. Flat rate of $15.
   - We do not ship to PO Boxes.

2. RETURNS & REFUNDS
   - Return Window: Customers may return items within 30 days of delivery.
   - Condition: Items must be unopened. Opened items are subject to a 15% restocking fee.
   - Non-Refundable: "Sticker Pack" items are final sale and cannot be returned.

3. DELAY COMPENSATION (The "Apology" Clause)
   - Definition: An order is "Delayed" if it is still 'Pending' >7 days after purchase or marked 'Delayed'.
   - Compensation: If an order is marked 'Delayed', the customer is entitled to a 10% discount on that specific order.
   - Action: Support agents must apply this discount immediately upon customer request.

4. CANCELLATIONS
   - 'Pending' orders can be cancelled immediately for a full refund.
   - 'Shipped' orders cannot be cancelled; they must be treated as Returns.
"""

with open("../data/policy.txt",'w') as file:
    file.write(rules)