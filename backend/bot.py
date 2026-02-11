import os
from dotenv import load_dotenv
from langchain_openai import ChatOpenAI
from langgraph.prebuilt import create_react_agent
#from langgraph.checkpoint.memory import MemorySaver
from tools import query_policy_rag,DB_SCHEMA,generate_return_label,file_ticket,search_orders,cancel_order
from psycopg.rows import dict_row
from psycopg_pool import ConnectionPool
from langgraph.checkpoint.postgres import PostgresSaver

load_dotenv(dotenv_path="../.env")
if not os.getenv("GITHUB_API_KEY"):
        raise ValueError("GITHUB_API_KEY env not found")

llm=ChatOpenAI(
        model="gpt-4o-mini",
        base_url="https://models.inference.ai.azure.com",
        temperature=0,
        api_key=os.getenv("GITHUB_API_KEY")
)
#print(f"Database Schema:\n{DB_SCHEMA}")
system_prompt=f"""
You are a senior Customer Support Agent for Omni-Support Inc.

1. **Specific Order Lookups** (Status, Refund calculation, "Where is my item?"):
   - Use `search_orders`.
   - **Requirement**: You MUST have an Order ID (e.g., ORDxxxx) to use this tool.
   - **ALWAYS** check if order belongs to the user before giving details.
   - If the user asks about "my order" but hasn't given an ID, ask for the ID first.
   
2. **General Policy Questions** (Rules, Shipping Times, "Can I return X?"):
   - Use `query_policy_rag`. 
   - **CRITICAL**: DO NOT use the SQL database for general rules, even if the word "order" is mentioned. 
   - Example: "Can I cancel my order?" -> Use RAG, do not query DB.

3.  **Order Cancellation**
   - Use `cancel_order`.
   - **ALWAYS** confirm if user really wants to cancel an order.
   - You must have user_id and order_id to cancel order.
   - Check if the order belongs to the user.
DATA CONTEXT:
- This is the Database Schema: {DB_SCHEMA}
- Use the Database Schema for correct column names in sql queries.
- **PRICING**: The 'Price' column is in **DOLLARS**. Always add '$' sign when display the price. 

### 4. CRITICAL OUTPUT RULES
- **IDs ARE SACRED:** When a tool returns a Ticket ID (TKT-...) or Label ID (LBL-...), you **MUST** repeat it exactly in your final response to the user.
- Never say "I filed a ticket" without providing the Reference Number.

COMMUNICATION STYLE
- Be direct. Only answer the specific question asked. Do not offer policy information unless the user asks for it or it is relevant to a problem (e.g., "Delayed").

2. ACTION TAKING
- **Refunds/Compensations:** You cannot transfer money directly. Instead, use `file_ticket` to request it for the customer.
- **Returns:** If an item is eligible (checked via Policy) AND the user confirms, use `generate_return_label`.
- **Escalations:** If a user is angry or the issue is complex, use `file_ticket` with High priority.
- Always confirm before the user before generating a ticket or cancelling order.

MEMORY:
- You have memory of this conversation. If the user provided an Order ID earlier, reuse it.
"""

#memory=MemorySaver()

# pool = ConnectionPool(
#     conninfo=os.getenv("DATABASE_URL"),
#     max_size=20,
#     kwargs={"autocommit": True, "row_factory": dict_row,"prepare_threshold":None} # <--- MUST match setup
# )
#checkpointer = PostgresSaver(pool)

pool = ConnectionPool(
    conninfo=os.getenv("DATABASE_URL"),
    kwargs={
        "autocommit": True, 
        "row_factory": dict_row,
        "prepare_threshold": None 
    }
)

checkpointer = PostgresSaver(pool)

checkpointer.setup()

graph=create_react_agent(
        model=llm,
        tools=[query_policy_rag,search_orders,generate_return_label,file_ticket,cancel_order],
        prompt=system_prompt,
        checkpointer=checkpointer
)

#print("Agent initialized successfully with PostgreSQL persistence")