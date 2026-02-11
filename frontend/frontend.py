import streamlit as st
from streamlit_oauth import OAuth2Component
import requests
import os
import uuid

API_URL = "http://127.0.0.1:8000"
st.set_page_config(page_title="Omni-Support Agent", page_icon="🤖")

CLIENT_ID = os.getenv("CLIENT_ID")
CLIENT_SECRET = os.getenv("CLIENT_SECRET")

AUTHORIZE_URL = "https://accounts.google.com/o/oauth2/v2/auth"
TOKEN_URL = "https://oauth2.googleapis.com/token"
REVOKE_URL = "https://oauth2.googleapis.com/revoke"
REDIRECT_URI = "http://localhost:8501/component/streamlit_oauth.authorize_button"
SCOPE = "openid email profile"

if "messages" not in st.session_state:
    st.session_state.messages = []
if "user_id" not in st.session_state:
    st.session_state.user_id = None
if "email" not in st.session_state:
    st.session_state.email = None
if "thread_id" not in st.session_state:
    st.session_state.thread_id = None
if "token" not in st.session_state:
    st.session_state.token = None

@st.experimental_dialog("Rename this chat")
def rename_dialog(thread_id, current_title):
    st.write(f"Enter a new name:")
    new_title = st.text_input("Name", value=current_title)
    
    col1, col2 = st.columns([1, 1])
    with col1:
        if st.button("Cancel"):
            st.rerun()
    with col2:
        if st.button("Rename", type="primary"):
            if new_title:
                try:
                    requests.put(f"{API_URL}/rename_thread", json={"thread_id": thread_id, "title": new_title})
                    st.rerun()
                except Exception as e:
                    st.error(f"Error: {e}")

# --- 2. LOGIN SCREEN ---
if not st.session_state.user_id:
    st.title("🔒 Sign in to Omni-Support")
    
    tab1, tab2 = st.tabs(["🔑 Developer Login", "G Google Login"])

    # --- TAB 1: DEV LOGIN ---
    with tab1:
        st.write("Use this to bypass the Google library error.")
        if st.button("Login as Developer (Bypass)", type="primary"):
            try:
                payload = {"email": "test@developer.com"}
                res = requests.post(f"{API_URL}/auth/dev", json=payload)
                if res.status_code == 200:
                    user_data = res.json()
                    st.session_state.user_id = user_data["user_id"]
                    st.session_state.email = user_data["email"]
                    st.rerun()
                else:
                    st.error("Server Error")
            except Exception as e:
                st.error(f"Connection Error: {e}")

    # --- TAB 2: GOOGLE LOGIN ---
    with tab2:
        try:
            oauth2 = OAuth2Component(CLIENT_ID, CLIENT_SECRET, AUTHORIZE_URL, TOKEN_URL, TOKEN_URL, REVOKE_URL)
            result = oauth2.authorize_button(
                name="Continue with Google",
                icon="https://www.google.com.tw/favicon.ico",
                redirect_uri=REDIRECT_URI,
                scope=SCOPE,
                key="google_auth",
            )
            if result:
                id_token = result.get("token", {}).get("id_token")
                try:
                    res = requests.post(f"{API_URL}/auth/google", json={"token": id_token})
                    if res.status_code == 200:
                        user_data = res.json()
                        st.session_state.user_id = user_data["user_id"]
                        st.session_state.email = user_data["email"]
                        st.rerun()
                except Exception as e:
                    st.error(f"Connection Error: {e}")
        except:
            st.error("Google Login not available.")

# --- 3. MAIN APPLICATION (LOGGED IN) ---
else:
    # --- SIDEBAR START ---
    st.sidebar.write(f"Logged in as: **{st.session_state.email}**")
    if st.sidebar.button("Logout"):
        st.session_state.user_id = None
        st.rerun()
    
    st.sidebar.divider()
    
    if st.sidebar.button("➕ Start New Chat", type="primary"):
        st.session_state.thread_id = None
        st.session_state.messages = []
        st.rerun()

    st.sidebar.subheader("History")

    threads_data = []
    try:
        threads_res = requests.get(f"{API_URL}/user/threads/{st.session_state.user_id}")
        if threads_res.status_code == 200:
            threads_data = threads_res.json().get("threads", [])
    except Exception as e:
        st.sidebar.error(f"Connection error")

    for t in threads_data:
        tid = t.get("thread_id")
        if not tid: continue
        
        label = t.get("title") or "New Chat"
        
        col1, col2 = st.sidebar.columns([0.85, 0.15])
        
        if col1.button(label, key=tid):
            st.session_state.thread_id = tid
            hist_res = requests.get(f"{API_URL}/history/{tid}")
            if hist_res.status_code == 200:
                st.session_state.messages = hist_res.json().get("history", [])
            st.rerun()
            
        if col2.button("✎", key=f"edit_{tid}", help="Rename this chat"):
            rename_dialog(tid, label)

    st.title("🤖 Omni-Support Agent")

    for msg in st.session_state.messages:
        role = "user" if msg["role"] == "user" else "assistant"
        with st.chat_message(role):
            st.write(msg["content"])

    if user_input := st.chat_input("Type here..."):
        with st.chat_message("user"):
            st.write(user_input)
        st.session_state.messages.append({"role": "user", "content": user_input})

        with st.chat_message("assistant"):
            placeholder = st.empty()
            placeholder.write("Thinking...")
            
            try:
                payload = {
                    "query": user_input, 
                    "thread_id": st.session_state.thread_id,
                    "user_id": st.session_state.user_id
                }
                res = requests.post(f"{API_URL}/chat", json=payload)
                
                if res.status_code == 200:
                    data = res.json()
                    ai_text = data["response"]
                    
                    st.session_state.messages.append({"role": "ai", "content": ai_text})
                    placeholder.write(ai_text)
                    
                    if data.get("actions_taken") and st.session_state.email == "test@developer.com":
                        with st.expander("🔧 Debug: Tools Used"):
                            for act in data["actions_taken"]:
                                st.write(f"- {act}")

                    if not st.session_state.thread_id:
                        st.session_state.thread_id = data["thread_id"]
                        st.rerun()
                else:
                    placeholder.error(f"Server Error: {res.status_code}")
                    
            except Exception as e:
                placeholder.error(f"Error: {e}")