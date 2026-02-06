import sqlite3
import os
import uuid
from datetime import datetime
import random
from langchain_community.embeddings import FastEmbedEmbeddings
from langchain_chroma import Chroma
from langchain_core.tools import tool
from typing import List,Any

DB_PATH='../data/orders.db'
VECTOR_DB_PATH='../data/vector_store'
RECORDS_FILE='../data/records.log'
embeddings=FastEmbedEmbeddings()

if os.path.exists(VECTOR_DB_PATH):
    vector_store=Chroma(
        embedding_function=embeddings,
        persist_directory=VECTOR_DB_PATH
    )
else:
    print(f"WARNING: Vector store not found at {VECTOR_DB_PATH}. Please run setup_vector_db.py")
    vector_store=None

def get_db_Schema():
    """Helper:Dynamic schema extraction for LLM"""
    try:
        with sqlite3.connect(DB_PATH) as con:
            cursor=con.cursor()
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
            tables=cursor.fetchall()
            schema_str=[]
            for table in tables:
                table_name=table[0]
                cursor.execute(f"PRAGMA table_info({table_name})")
                columns=cursor.fetchall()
                col_names=[col[1] for col in columns]
                schema_str.append(f"{table_name}({', '.join(col_names)})")
            return "\n".join(schema_str)
    except Exception as e:
        print(f"Error getting schema: {str(e)}")
        return f"Error getting schema: {str(e)}"
    
DB_SCHEMA=get_db_Schema()

@tool
def query_sql_db(query: str)->List[Any]:

    """
    Execute a read-only SQL query on the 'orders.db' database. 
    Input must be valid SQLite syntax.
    Do not use for general policy questions.
    """
    try:
        with sqlite3.connect('../data/orders.db') as db_con:
            cursor=db_con.cursor()

            cursor.execute(query)

            res=cursor.fetchall()
            #print(res)
            return res if res else ["No results found"]
    except Exception as e:
        print(f"SQL Error:{str(e)}")
        return [f"SQL Error:{str(e)}"]

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
def file_ticket(order_id:str,issue:str,priority:str="Normal"):
    """
    Files a formal support ticket for issues the Agent cannot resolve immediately
    (e.g., compensation requests, lost items, angry customers).
    Returns the Ticket ID.
    """
    ticket_id=f"TKT-{uuid.uuid4().hex[:6].upper()}"
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    log_entry = f"[{timestamp}] TICKET: {ticket_id} | Order: {order_id} | Issue: {issue} | Priority: {priority}\n"
    
    try:
        with open(RECORDS_FILE, "a") as f:
            f.write(log_entry)
        return f"Ticket {ticket_id} created successfully. A human agent will review it within 24 hours."
    except Exception as e:
        return f"Error filing ticket: {str(e)}"

@tool
def generate_return_label(order_id:str,reason:str="Customer Request"):
    """
    Generates a return shipping label ID.
    ONLY use this if:
    1. You have confirmed the order exists.
    2. You have confirmed the item is eligible for return according to Policy.
    3. The user has explicitly confirmed they want to return it.
    """
    label_id=f"LBL-{random.randint(10000,99999)}"
    timestamp=datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    log_entry=f"[{timestamp}] LABEL: {label_id} | Order: {order_id} | Reason: {reason}\n"

    try:
        with open(RECORDS_FILE,"a") as f:
            f.write(log_entry)
        return f"Success! Return Label generated: {label_id}. Sent to customer email."
    except Exception as e:
        return f"Error generating label: {str(e)}"
    
if __name__=="__main__":
    #query_sql_db("Select * from orders")
    query_policy_rag("For how long can i return my item")