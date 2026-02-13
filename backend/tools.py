import psycopg2
from psycopg2 import pool
import os
import uuid
from dotenv import load_dotenv
from datetime import datetime
import random
from langchain_community.embeddings import FastEmbedEmbeddings
from langchain_chroma import Chroma
from langchain_core.tools import tool
from typing import List,Any

load_dotenv(dotenv_path="../.env")
DB_URL = os.getenv("DATABASE_URL")
VECTOR_DB_PATH='../data/vector_store'

try:
    db_pool=psycopg2.pool.SimpleConnectionPool(1,10,dsn=DB_URL,sslmode='require')
    print("Tools Connection Pool created successfully")
except Exception as e:
    print("Error creating pool in tools.py")
    db_pool=None

def get_db_connection():

    if not db_pool:
        raise Exception("Tool DB Pool not ready")
    return db_pool.getconn()

def release_db_connection(conn):
    if db_pool and conn:
        db_pool.putconn(conn)
        
embeddings=FastEmbedEmbeddings()

print("="*50)
print(f"DEBUG:Tools.py")
print(f"DEBUG: DB_URL Preview:{DB_URL}...")
print("="*50)

if os.path.exists(VECTOR_DB_PATH):
    vector_store=Chroma(
        embedding_function=embeddings,
        persist_directory=VECTOR_DB_PATH
    )
else:
    print(f"WARNING: Vector store not found at {VECTOR_DB_PATH}. Please run setup_vector_db.py")
    vector_store=None

def get_simple_schema():
    """Simplified schema extraction"""
    if not DB_URL:
        return "Error: DATABASE_URL not found"
    conn=None
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT 
                t.table_name,
                c.column_name,
                c.data_type,
                c.is_nullable
            FROM information_schema.tables t
            JOIN information_schema.columns c 
                ON t.table_name = c.table_name
                AND t.table_schema = c.table_schema
            WHERE t.table_schema = 'public'
                AND t.table_type = 'BASE TABLE'
            ORDER BY t.table_name, c.ordinal_position;
        """)
        
        rows = cursor.fetchall()
        
        schema_dict = {}
        for table, column, data_type, nullable in rows:
            if table not in schema_dict:
                schema_dict[table] = []
            null_str = " NOT NULL" if nullable == 'NO' else ""
            schema_dict[table].append(f"{column} {data_type}{null_str}")
        
        schema_lines = []
        for table, columns in schema_dict.items():
            schema_lines.append(f"Table: {table}")
            schema_lines.append(f"  Columns: {', '.join(columns)}")
            schema_lines.append("")
        
        cursor.close()
        conn.close()
        
        return "\n".join(schema_lines) if schema_lines else "No tables found"
        
    except Exception as e:
        return f"Error: {str(e)}"
    finally:
        release_db_connection(conn)

DB_SCHEMA=get_simple_schema()

@tool
def search_item_details(item_name_query:str):
    """
    Search the GLOBAL PRODUCT CATALOG.
    - Use this when user asks "How much is X?" or "Do you have X?"
    - Returns Item Name, Current Price, and Description.
    """
    if not DB_URL:
        print(f"Search Item Error:DB URL missing")
        return "Error DB_URL missing"
    conn=None
    try:
        conn=get_db_connection()
        with conn.cursor() as cursor:
            
            query = """
                SELECT name, current_price, description, category,stock_quantity
                FROM items
                WHERE name ILIKE %s
                LIMIT 5
            """
            search_term = f"%{item_name_query}%"
            
            cursor.execute(query, (search_term,))
            rows = cursor.fetchall()
            
            if not rows:
                return f"We do not have any items matching '{item_name_query}'. Please try a different keyword."

            
            results = []
            for r in rows:
                name = r[0]
                price = r[1]
                desc = r[2]
                category = r[3]
                stock = r[4]

                stock_msg = ""
                if stock == 0:
                    stock_msg = " [OUT OF STOCK]"
                
                results.append(
                    f"🔹 {name} (${price}){stock_msg}\n"
                    f"   Category: {category}\n"
                    f"   Info: {desc}"
                )
            
            return "\n\n".join(results)

    except Exception as e:
        print(f"Search Item Error:{e}")
        return f"Database Error: {e}"
    finally:
        release_db_connection(conn)
@tool
def search_orders(user_id:int,order_id:str=None):
    """
    Search for orders belonging to current user.
    - Joins Orders -> Order Items -> Items to get names.
    - To see ALL orders, leave order_id as None.
    - To check a SPECIFIC order, provide the order_id (e.g. ORD0001).
   """
    print("\n\n")
    print("="*50)
    print(f"[TOOL START] search_order started for userid:{user_id}")
    print(f"DB_URL:{DB_URL}")
    print("="*50)
    conn=None
    try:
        conn=get_db_connection()
        #with psycopg2.connect(DB_URL,sslmode='require') as conn:
        print("[TOOL] Connection Successful!")
        with conn.cursor() as cursor:
            query="""
                SELECT o.order_id, o.status, o.total_amount, o.purchase_date,
                           string_agg(cat.name || ' ($' || i.unit_price || ') x' || i.quantity, ', ') as items
                    FROM orders o
                    JOIN order_items i ON o.order_id = i.order_id
                    JOIN items cat ON i.item_id = cat.id  -- <--- JOIN TO CATALOG
                    WHERE o.user_id = %s
                """
            params=[user_id]
                
            if order_id:
               query+=" AND o.order_id=%s"
               params.append(order_id)
                
            query += " GROUP BY o.order_id ORDER BY o.purchase_date DESC"

            print(f"Query to execute:{query} and params:{params}")
            cursor.execute(query,tuple(params))
            rows=cursor.fetchall()
            if not rows:
               print("Issue found")
               if order_id:
                   return f"Order {order_id} not found or you donot have access to view it."
               return "You have no active orders."
            results=[]

            for r in rows:
               results.append(f"Order: {r[0]} [{r[3]}]: {r[4]} - Total: ${r[2]} ({r[1]})")
            print(f"Result to return\n{results}")
            return "\n".join(results)
    except Exception as e:
        print(f"DATABASE ERROR:{str(e)}")
        return f"Database Error:{str(e)}"
    finally:
        release_db_connection(conn)

@tool
def cancel_order(order_id:str,user_id:int):
    """
    Cancel an order ONLY if it belongs to the user and is not already shipped.
    """
    print("\n")
    print("="*50)
    print("Cancel Query Called")
    conn=None
    try:
        conn=get_db_connection()
        with conn.cursor() as cursor:
            print(f"[TOOL USE]  Executing Query")
            cursor.execute("SELECT status FROM orders WHERE order_id = %s AND user_id = %s", (order_id, user_id))
            result=cursor.fetchone()

            print("Query Executed")
            print(f"Result:{result}")
            if not result:
                print("ID not found or permission denied")
                return f"Error:Order {order_id} not found or permission denied."
            status=result[0]
            if status in ['Shipped', 'Delivered']:
                print(f"Cant cancel Order status = {status}")
                return f"Cannot cancel order {order_id} because it is '{status}'."
            if status=='Cancelled':
                return f"Order with ID {order_id} has already been cancelled."
            
            cursor.execute("UPDATE orders SET status = 'Cancelled' WHERE order_id = %s", (order_id,))
            conn.commit()
            print("Cancelled successfully")
            return f"Success: Order {order_id} has been cancelled."
    except Exception as e:
        print(f"DB ERROR:{e}")
        return f"Database Error: {str(e)}"
    finally:
        release_db_connection(conn)

# def query_sql_db(query: str)->List[Any]:

#     """
#     Execute a read-only SQL query on the 'orders.db' database. 
#     Input must be valid SQLite syntax.
#     Do not use for general policy questions.
#     """
#     if not query.strip().upper().startswith("SELECT"):
#         return ["Error: Only SELECT queries are allowed for security reasons."]

#     try:
#         # Use a fresh connection for each query (stateless)
#         with psycopg2.connect(DB_URL, sslmode='require') as conn:
#             with conn.cursor() as cursor:

#                 cursor.execute(query)

#                 res=cursor.fetchall()
#                 #print(res)
#                 return res if res else ["No results found"]
#     except Exception as e:
#         print(f"SQL Error:{str(e)}")
#         return [f"SQL Error:{str(e)}"]

@tool
def query_policy_rag(query: str):

    """
    Search the company policy document. 
    Use this for questions about return windows, conditions, restocking fees, shipping rules, or cancellation policies.
    Return relevant text chunks.
    """

    if not vector_store:
        return "System Error:Vector Store not found"
    try:
        results=vector_store.similarity_search(query,k=3)
        context_text = "\n\n".join([doc.page_content for doc in results])
        #print(context_text)
        return context_text if context_text else "No relevant policy found"
    except Exception as e:
        print(f"Policy Error:{str(e)}")
        return [f"Policy Error:{str(e)}"]
    
@tool
def file_ticket(user_id:int,order_id:str,issue:str):
    """
    Files a SINGLE support ticket for an order.
    - AUTO-CALCULATES compensation (if applicable) and adds it to the ticket.
    - REJECTS if there is already an OPEN ticket.
    - User should combine all issues (e.g., "Wrong color + Late delivery") into 'issue_description'."""
    conn=None
    try:
        conn=get_db_connection()
        with conn.cursor() as cursor:
            cursor.execute("SELECT ticket_id, status FROM tickets WHERE order_id = %s AND status != 'Closed'", (order_id,))
            existing=cursor.fetchone()
            if existing:
                return f"Ticket ({existing[0]}) already exists for this order. Please wait for support."
            
            cursor.execute("SELECT total_amount, purchase_date FROM orders WHERE order_id = %s AND user_id = %s", (order_id, user_id))
            row=cursor.fetchone()

            if not row:
                return f"Order not found or you donot have access to the order."
            
            amount,p_date=row
            
            final_issue = issue
            
            new_ticket_id = f"TKT-{uuid.uuid4().hex[:6].upper()}"
            
            cursor.execute("""
                INSERT INTO tickets (ticket_id, user_id, order_id, issue, status)
                VALUES (%s, %s, %s, %s, 'Open')
            """, (new_ticket_id, user_id, order_id, final_issue))
            
            conn.commit()

            response = f"Ticket {new_ticket_id} filed successfully!"
            response += f"\nIssue Logged: {issue}"
            response+="Support will review it in 24 hours."
            return response
    
    except Exception as e:
        return f"Error filling ticket: {str(e)}"
    finally:
        release_db_connection(conn)
@tool
def generate_return_label(user_id:int,order_id:str,reason:str="Customer Request"):
    """
    Generates a return shipping label ID.
    ONLY use this if:
    1. You have confirmed the order exists.
    2. You have confirmed the item is eligible for return according to Policy.
    3. The user has explicitly confirmed they want to return it.
    """
    conn=None
    try:
        conn=get_db_connection()
        with conn.cursor() as cursor:
            cursor.execute("SELECT status FROM orders WHERE order_id = %s AND user_id = %s", (order_id, user_id))
            if not cursor.fetchone():
                return "Order not found."

            label_id = f"LBL-{random.randint(10000,99999)}"
            
            cursor.execute("""
                INSERT INTO return_labels (label_id, status)
                VALUES (%s, 'Generated')
            """, (label_id,))
            conn.commit()
            
            return f"Return Label {label_id} generated. Write this number to your package."
    except Exception as e:
        return f"Database Error: {e}"
    finally:
        release_db_connection(conn)
