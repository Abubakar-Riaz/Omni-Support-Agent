from fastapi import FastAPI
from pydantic import BaseModel
#from bot import agent_executor,HumanMessage
from  bot import process_query

class UserRequest(BaseModel):
    query:str

app=FastAPI()

@app.get("/")
async def root():
    return {"message":"Server Running"}

@app.post('/chat')
async def chat_endpoint(request:UserRequest):
    """
    This function:
    1. Receives the JSON data (validated by UserRequest).
    2. Extracts the text.
    3. Runs the AI Agent.
    4. Returns the answer.
    """
    user_input=request.query

    print(f"Processing:{user_input}")

    #response= agent_executor.invoke({"messages":HumanMessage(content=user_input) })
    response=process_query(user_input)

    #ai_response=response['messages'][-1].content

    return {"response":response}