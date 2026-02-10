import uuid
import uvicorn
from fastapi import FastAPI,HTTPException
from bot import graph
from pydantic import BaseModel
from typing import List, Optional
from langchain_core.messages import HumanMessage, AIMessage

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

# --- ADD ToolMessage TO IMPORTS ---
from langchain_core.messages import HumanMessage, AIMessage, ToolMessage

# ... (inside your server.py) ...

@app.get("/history/{thread_id}")
def get_history(thread_id: str):
    try:
        config = {"configurable": {"thread_id": thread_id}}
        
        # 1. Get the latest state snapshot
        state_snapshot = graph.get_state(config)
        
        # 2. Extract messages
        messages = state_snapshot.values.get("messages", [])
        
        formatted_history = []
        for msg in messages:
            # FILTER 1: Skip Raw Tool Outputs (The ugly lists/JSON)
            if isinstance(msg, ToolMessage):
                continue
            
            # FILTER 2: Skip AI "Thinking" messages (Empty content, just tool calls)
            if isinstance(msg, AIMessage) and not msg.content:
                continue
            
            # Determine Role
            role = "user" if isinstance(msg, HumanMessage) else "ai"
            content = msg.content
            
            formatted_history.append({"role": role, "content": content})
            
        return {"history": formatted_history}

    except Exception as e:
        raise HTTPException(status_code=404, detail="History not found")
       
@app.post("/chat")
def chat_endpoint(req:ChatRequest):
    try:
        thread_id=req.thread_id or str(uuid.uuid4())

        #print(f"DEBUG:Processing request for Thread ID: {thread_id}")
        config={"configurable":{"thread_id":thread_id}}

        input_message={"messages":[("user",req.query)]}

        output_state=graph.invoke(input_message,config=config)

        messages=output_state.get("messages",[])
        if not messages:
            return {"response": "Error: No response from Agent", "thread_id": thread_id, "actions_taken": []}
        
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
        print(f"Server Error:{e}")
        raise HTTPException(status_code=500,detail=str(e))
    
if __name__=="__main__":
    uvicorn.run(app,host="127.0.0.1",port=8000)