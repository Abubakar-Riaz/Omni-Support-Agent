import sqlite3
from langchain_community.embeddings import FastEmbedEmbeddings
from langchain_chroma import Chroma
from langchain_core.tools import tool

@tool
def query_sql_db(query: str):

    """
    Execute a SQL query on the 'orders.db' database. 
    Use this ONLY when the user asks about specific order numbers, status, customer counts, or refund calculations. 
    Do not use for general policy questions.
    """
    try:
        with sqlite3.connect('../data/orders.db') as db_con:
            cursor=db_con.cursor()

            cursor.execute(query)

            res=cursor.fetchall()
            #print(res)
            return res
    except Exception as e:
        print(f"Error:{e}")
        return []

@tool
def query_policy_rag(query: str):

    """
    Search the company policy document. 
    Use this for questions about return windows, conditions, restocking fees, shipping rules, or cancellation policies.
    """

    embeddings=FastEmbedEmbeddings()

    vector_store=Chroma(
        persist_directory='../data/vector_store',
        embedding_function=embeddings
    )

    results=vector_store.similarity_search(query,k=3)
    context_text = "\n\n".join([doc.page_content for doc in results])
    #print(context_text)
    return context_text

if __name__=="__main__":
    #query_sql_db("Select * from orders")
    query_policy_rag("For how long can i return my item")