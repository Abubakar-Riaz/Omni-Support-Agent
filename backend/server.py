import uuid
from fastapi import FastAPI,HTTPException
from bot import graph
from pydantic import BaseModel
from typing import List, Optional, Dict, Any

app=FastAPI(
    title="Omni-Support Agent API",
    description="Industry Standard RAG Agent for Order Management and Policy Queries.",
    version="1.0"
)

class ChatRequest(BaseModel):
    query:str
    thread_id:Optional[str]=None
class ChatResponse(BaseModel):
    response:str
    thread_id:str
    action_taken:List[str]

@app.get("/health")
def health_check():
    return {"status":"running","service":"Omni-Support Agent"}

@app.post("/chat")
def chat_endpoint(req:ChatRequest):
    try:
        thread_id=req.thread_id or str(uuid.uuid4())

        config={"configurable":{"thread_id":thread_id}}

        input_message={"messages":[("user",req.query)]}

        output_state=graph.invoke(input_message,config=config)

        messages=output_state.get("messages",[])
        ai_response=messages[-1].content

        actions=[]

        for msg in reversed(messages):
            if msg.type=="human":
                break
            if msg.type=="ai" and hasattr(msg,"tool_calls") and msg.tool_calls:
                for tool in msg.tool_calls:
                    actions.append(f"Called Tools: {tool['name']}")
                    
                actions.reverse()

                return {
                    "response":ai_response,
                    "thread_id":thread_id,
                    "actions_taken":actions,
                }
    except Exception as e:
        raise HTTPException(status_code=500,detail=str(e))