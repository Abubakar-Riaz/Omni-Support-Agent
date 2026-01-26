import sqlite3
from langchain_community.embeddings import FastEmbedEmbeddings
from langchain_chroma import Chroma

def query_sql_db(query: str):

    try:
        with sqlite3.connect('../data/orders.db') as db_con:
            cursor=db_con.cursor()

            cursor.execute(query)

            res=cursor.fetchall()
            print(res)
            return res
    except Exception as e:
        print(f"Error:{e}")
        return []

def query_policy_rag(query: str):
    embeddings=FastEmbedEmbeddings()

    vector_store=Chroma(
        persist_directory='../data/vector_store',
        embedding_function=embeddings
    )

    results=vector_store.similarity_search(query,k=3)
    context_text = "\n\n".join([doc.page_content for doc in results])
    print(context_text)
    return context_text

if __name__=="__main__":
    #query_sql_db("Select * from orders")
    query_policy_rag("For how long can i return my item")