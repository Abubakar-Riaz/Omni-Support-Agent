import os
from dotenv import load_dotenv
from langchain_openai import ChatOpenAI
from langgraph.prebuilt import create_react_agent
from langgraph.checkpoint.memory import MemorySaver
from tools import query_policy_rag,query_sql_db,DB_SCHEMA

load_dotenv()
if not os.getenv("GITHUB_API_KEY"):
        raise ValueError("GITHUB_API_KEY env not found")

llm=ChatOpenAI(
        model="gpt-4o-mini",
        base_url="https://models.inference.ai.azure.com",
        temperature=0,
        api_key=os.getenv("GITHUB_API_KEY")
)

system_prompt=f"""
You are a senior Customer Support Agent for Omni-Support Inc.

1. **Specific Order Lookups** (Status, Refund calculation, "Where is my item?"):
   - Use `query_sql_db`.
   - **Requirement**: You MUST have an Order ID (e.g., ORDxxxx) to use this tool.
   - If the user asks about "my order" but hasn't given an ID, ask for the ID first.
   
2. **General Policy Questions** (Rules, Shipping Times, "Can I return X?"):
   - Use `query_policy_rag`. 
   - **CRITICAL**: DO NOT use the SQL database for general rules, even if the word "order" is mentioned. 
   - Example: "Can I cancel my order?" -> Use RAG, do not query DB.

DATA CONTEXT:
- Database Schema: {DB_SCHEMA}
- **PRICING**: The 'Price' column is in **CENTS**. (Example: 2599 = $25.99). 
- Always convert cents to dollars when displaying prices or calculating refunds.

MEMORY:
- You have memory of this conversation. If the user provided an Order ID earlier, reuse it.
"""

memory=MemorySaver()

graph=create_react_agent(
        model=llm,
        tools=[query_policy_rag,query_sql_db],
        prompt=system_prompt,
        checkpointer=memory
)
