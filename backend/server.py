import uuid
import uvicorn
from fastapi import FastAPI,HTTPException
from bot import graph
from pydantic import BaseModel
from typing import List, Optional
from langchain_core.messages import HumanMessage, AIMessage, ToolMessage
from google.oauth2 import id_token
from google.auth.transport import requests as google_requests
import psycopg2
from dotenv import load_dotenv
import os

load_dotenv(dotenv_path="../.env")
GOOGLE_CLIENT_ID = os.getenv("CLIENT_ID")
DB_URL=os.getenv("DATABASE_URL")

app=FastAPI(
    title="Omni-Support Agent API",
    description="Industry Standard RAG Agent for Order Management and Policy Queries.",
    version="1.0"
)

class GoogleAuthRequest(BaseModel):
    token: str

class ChatRequest(BaseModel):
    query:str
    thread_id:Optional[str]=None
    user_id: Optional[int] = None

class ChatResponse(BaseModel):
    response:str
    thread_id:str
    action_taken:List[str]

class RenameRequest(BaseModel):
    thread_id: str
    title: str

@app.get("/health")
def health_check():
    return {"status":"running","service":"Omni-Support Agent"}

@app.post("/auth/google")
def google_login(req: GoogleAuthRequest):
    try:
        id_info = id_token.verify_oauth2_token(
            req.token, 
            google_requests.Request(), 
            GOOGLE_CLIENT_ID
        )
        email = id_info['email']
        google_sub = id_info['sub']
        name = id_info.get('name', '')

        conn = psycopg2.connect(DB_URL, sslmode='require')
        cur = conn.cursor()
        
        cur.execute("SELECT id FROM users WHERE email = %s", (email,))
        user = cur.fetchone()

        if not user:
            cur.execute(
                "INSERT INTO users (email, google_sub, full_name) VALUES (%s, %s, %s) RETURNING id",
                (email, google_sub, name)
            )
            user_id = cur.fetchone()[0]
            conn.commit()
        else:
            user_id = user[0]
        
        conn.close()

        return {"user_id": user_id, "email": email, "name": name}

    except ValueError:
        raise HTTPException(status_code=401, detail="Invalid Google Token")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/user/threads/{user_id}")
def get_user_threads(user_id: int):
    try:
        conn = psycopg2.connect(DB_URL, sslmode='require')
        cur = conn.cursor()
        cur.execute("SELECT thread_id, created_at, title FROM user_threads WHERE user_id = %s ORDER BY created_at DESC", (user_id,))
        threads = []
        for row in cur.fetchall():
            threads.append({
                "thread_id": row[0],
                "date": str(row[1]),
                "title": row[2] or "New Chat"
            })
        conn.close()
        return {"threads": threads}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    
@app.get("/history/{thread_id}")
def get_history(thread_id: str):
    try:
        config = {"configurable": {"thread_id": thread_id}}
        
        state_snapshot = graph.get_state(config)
        
        messages = state_snapshot.values.get("messages", [])
        
        formatted_history = []
        for msg in messages:
            if isinstance(msg, ToolMessage):
                continue
            
            if isinstance(msg, AIMessage) and not msg.content:
                continue
            
            role = "user" if isinstance(msg, HumanMessage) else "ai"
            content = msg.content
            
            formatted_history.append({"role": role, "content": content})
            
        return {"history": formatted_history}

    except Exception as e:
        raise HTTPException(status_code=404, detail="History not found")
       
@app.post("/chat")
def chat_endpoint(req: ChatRequest):
    try:
        thread_id = req.thread_id or str(uuid.uuid4())

        if req.user_id:
            try:
                conn = psycopg2.connect(DB_URL, sslmode='require')
                cur = conn.cursor()
                # We add 'title' to the INSERT
                cur.execute(
                    """
                    INSERT INTO user_threads (user_id, thread_id, title) 
                    VALUES (%s, %s, %s) 
                    ON CONFLICT (user_id, thread_id) DO NOTHING
                    """, 
                    (req.user_id, thread_id, "New Chat")
                )
                conn.commit()
                conn.close()
            except Exception as db_e:
                print(f"Database Link Error: {db_e}")
                
        config = {"configurable": {"thread_id": thread_id}}
        input_message = {"messages": [("user", req.query)]}
        output_state = graph.invoke(input_message, config=config)

        messages = output_state.get("messages", [])
        if not messages:
            return {"response": "Error: No response from Agent", "thread_id": thread_id, "actions_taken": []}
        
        ai_response = messages[-1].content

        actions = []
        for msg in reversed(messages):
            if msg.type == "human":
                break
            if msg.type == "ai" and hasattr(msg, "tool_calls") and msg.tool_calls:
                for tool in msg.tool_calls:
                    actions.append(f"Called Tools: {tool['name']}")
                    
        actions.reverse()

        return {
            "response": ai_response,
            "thread_id": thread_id,
            "actions_taken": actions,
        }

    except Exception as e:
        print(f"Server Error: {e}")
        raise HTTPException(status_code=500, detail=str(e))
    
class DevAuthRequest(BaseModel):
    email: str

@app.post("/auth/dev")
def dev_login(req: DevAuthRequest):
    try:
        conn = psycopg2.connect(DB_URL, sslmode='require')
        cur = conn.cursor()

        cur.execute("SELECT id FROM users WHERE email = %s", (req.email,))
        user = cur.fetchone()

        if not user:
            cur.execute(
                "INSERT INTO users (email, google_sub, full_name) VALUES (%s, %s, %s) RETURNING id",
                (req.email, "dev_user_sub", "Developer Account")
            )
            user_id = cur.fetchone()[0]
            conn.commit()
        else:
            user_id = user[0]
        
        conn.close()
        return {"user_id": user_id, "email": req.email, "name": "Developer"}

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    
@app.put("/rename_thread")
def rename_thread(req: RenameRequest):
    try:
        conn = psycopg2.connect(DB_URL, sslmode='require')
        cur = conn.cursor()
        cur.execute("UPDATE user_threads SET title = %s WHERE thread_id = %s", (req.title, req.thread_id))
        conn.commit()
        conn.close()
        return {"msg": "Renamed"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

if __name__=="__main__":
    uvicorn.run(app,host="127.0.0.1",port=8000)