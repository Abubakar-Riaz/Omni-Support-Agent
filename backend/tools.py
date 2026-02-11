import psycopg2
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
RECORDS_FILE='../data/records.log'
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
    
    try:
        conn = psycopg2.connect(DB_URL, sslmode='require')
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
    
DB_SCHEMA=get_simple_schema()

@tool
def search_orders(user_id:int,order_id:str=None):
    """
    Search for orders belonging to current user.
    - To see ALL orders, leave order_id as None.
    - To check a SPECIFIC order, provide the order_id (e.g. ORD0001).
   """
    print("\n\n")
    print("="*50)
    print(f"[TOOL START] search_order started for userid:{user_id}")
    print(f"DB_URL:{DB_URL}")
    print("="*50)
    try:
        with psycopg2.connect(DB_URL,sslmode='require') as conn:
            print("[TOOL] Connection Successful!")
            with conn.cursor() as cursor:
                query="""
                SELECT ID,Item_Name,Status,Price
                               FROM orders
                               WHERE user_id=%s
                """
                params=[user_id]
                
                if order_id:
                   query+=" AND ID=%s"
                   params.append(order_id)
                
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
                   results.append(f"Order {r[0]}: {r[1]} (${r[3]}) - Status: {r[2]}")
                print(f"Result to return\n{results}")
                return "\n".join(results)
    except Exception as e:
        print(f"DATABASE ERROR:{str(e)}")
        return f"Database Error:{str(e)}"
    
@tool
def cancel_order(order_id:str,user_id:int):
    """
    Cancel an order ONLY if it belongs to the user and is not already shipped.
    """
    print("\n")
    print("="*50)
    print("Cancel Query Called")
    try:
        with psycopg2.connect(DB_URL,sslmode='require') as conn:
            with conn.cursor() as cursor:
                print(f"[TOOL USE]  Executing Query")
                cursor.execute("SELECT Status FROM orders WHERE ID=%s AND user_id=%s",(order_id,user_id))
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
                cursor.execute("UPDATE orders SET status = 'Cancelled' WHERE ID = %s", (order_id,))
                conn.commit()
                print("Cancelled successfully")
                return f"Success: Order {order_id} has been cancelled."
    except Exception as e:
        print(f"DB ERROR:{e}")
        return f"Database Error: {str(e)}"
    
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
def file_ticket(user_id:int,order_id:str,issue:str,priority:str="Normal"):
    """
    Files a formal support ticket for issues the Agent cannot resolve immediately
    (e.g., compensation requests, lost items, angry customers).
    Returns the Ticket ID.
    """
    ticket_id=f"TKT-{uuid.uuid4().hex[:6].upper()}"
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    log_entry = f"[{timestamp}] TICKET: {ticket_id} | User:{user_id} | Order: {order_id} | Issue: {issue} | Priority: {priority}\n"
    
    try:
        with open(RECORDS_FILE, "a") as f:
            f.write(log_entry)
        return f"Ticket {ticket_id} created successfully. Support will review it within 24 hours."
    except Exception as e:
        return f"Error filing ticket: {str(e)}"

@tool
def generate_return_label(user_id:int,order_id:str,reason:str="Customer Request"):
    """
    Generates a return shipping label ID.
    ONLY use this if:
    1. You have confirmed the order exists.
    2. You have confirmed the item is eligible for return according to Policy.
    3. The user has explicitly confirmed they want to return it.
    """
    label_id=f"LBL-{random.randint(10000,99999)}"
    timestamp=datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    log_entry=f"[{timestamp}] LABEL: {label_id} | User: {user_id} | Order: {order_id} | Reason: {reason}\n"

    try:
        with open(RECORDS_FILE,"a") as f:
            f.write(log_entry)
        return f"Success! Return Label generated: {label_id}. Sent to customer email."
    except Exception as e:
        return f"Error generating label: {str(e)}"
    
if __name__=="__main__":
    #query_sql_db("Select * from orders")
    query_policy_rag("For how long can i return my item")