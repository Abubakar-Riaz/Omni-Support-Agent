import os
from dotenv import load_dotenv
from psycopg_pool import ConnectionPool
from langgraph.checkpoint.postgres import PostgresSaver
from psycopg.rows import dict_row

load_dotenv()
DB_URL = os.getenv("DATABASE_URL")

#print("Setting up LangGraph Persistence Tables...")

pool = ConnectionPool(
    conninfo=DB_URL,
    kwargs={"autocommit": True, "row_factory": dict_row}
)

checkpointer = PostgresSaver(pool)

checkpointer.setup() 

#print("SUCCESS: Persistence tables created! Your agent can now remember things forever.")