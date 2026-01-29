import os
from dotenv import load_dotenv
import sys
from langchain_core.messages import SystemMessage, HumanMessage
from langchain_groq import ChatGroq
from langgraph.prebuilt import create_react_agent

# Import your tools
from tools import query_sql_db, query_policy_rag

load_dotenv()

llm = ChatGroq(api_key=os.getenv("GROQ_API_KEY"),model="llama-3.1-8b-instant", temperature=0)

my_tools = [query_sql_db, query_policy_rag]

agent_executor = create_react_agent(llm, my_tools)

def process_query(user_input:str)->str:
    print(f"\nUser: {user_input}")
    
    system_instruction = """
You are a helpful assistant.
    You have access to two tools:
    1. query_sql_db: Use this for order numbers, counts, and statuses.
    2. query_policy_rag: Use this for returns, refunds, and rules.

    When you are asked a question:
    - Think about which tool to use.
    - Call the tool directly.
    - Once you get the result, answer the user in plain English.
    Note:Donot return in XML format
    """
    
    messages = [
        SystemMessage(content=system_instruction),
        HumanMessage(content=user_input)
    ]
    
    try:
        response = agent_executor.invoke({"messages": messages})
        
        #print(f"Agent: {response['messages'][-1].content}")
        return response['messages'][-1].content
    except Exception as e:
        #print(f"Error: {e}")
        return f"An error occured:{str(e)}"

if __name__ == "__main__":
    print(process_query("What is the return policy for sticker packs?"))