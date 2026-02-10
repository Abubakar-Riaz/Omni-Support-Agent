import streamlit as st
import requests
import uuid

API_URL = "http://127.0.0.1:8000/chat"
st.set_page_config(page_title="Omni-Support Agent", page_icon="🤖")

if "thread_id" not in st.session_state:
    st.session_state.thread_id = str(uuid.uuid4())

if "messages" not in st.session_state:
    st.session_state.messages = []

st.sidebar.title("🔧 Settings")
st.sidebar.markdown(f"**Session ID:** `{st.session_state.thread_id}`")

# ... inside frontend.py sidebar ...

new_id = st.sidebar.text_input("Paste Thread ID to Resume Chat:")

if st.sidebar.button("Load Chat"):
    if new_id:
        st.session_state.thread_id = new_id
        st.session_state.messages = [] # Clear current UI
        
        # --- NEW CODE: FETCH OLD HISTORY ---
        try:
            # Call the new endpoint
            res = requests.get(f"http://127.0.0.1:8000/history/{new_id}")
            if res.status_code == 200:
                data = res.json()
                history = data.get("history", [])
                
                # Load them into Session State
                for msg in history:
                    st.session_state.messages.append(msg)
                
                st.success("Chat history loaded!")
                st.rerun()
            else:
                st.error("No history found for this ID.")
        except Exception as e:
            st.error(f"Could not connect to backend: {e}")

            
if st.sidebar.button("New Chat"):
    st.session_state.thread_id = str(uuid.uuid4())
    st.session_state.messages = []
    st.rerun()

st.title("🤖 Omni-Support Agent")
st.caption("Powered by LangGraph & PostgreSQL")

for msg in st.session_state.messages:
    role = "user" if msg["role"] == "user" else "assistant"
    with st.chat_message(role):
        st.markdown(msg["content"])

if user_input := st.chat_input("Type your message..."):
    with st.chat_message("user"):
        st.markdown(user_input)
    st.session_state.messages.append({"role": "user", "content": user_input})

    with st.chat_message("assistant"):
        message_placeholder = st.empty()
        message_placeholder.markdown("Thinking...")
        
        try:
            payload = {
                "query": user_input,
                "thread_id": st.session_state.thread_id
            }
            
            # Call your FASTAPI Server
            response = requests.post(API_URL, json=payload)
            response.raise_for_status() # Check for 500 errors
            data = response.json()
            
            ai_text = data["response"]
            actions = data.get("actions_taken", [])

            # Formatting: If tools were used, show them in a dropdown
            final_display_text = ai_text
            if actions:
                with st.expander("Actions Taken"):
                    for action in actions:
                        st.write(f"- {action}")
            
            message_placeholder.markdown(final_display_text)
            
            # Save AI response to session state
            st.session_state.messages.append({"role": "assistant", "content": final_display_text})

        except Exception as e:
            message_placeholder.error(f"Connection Error: {str(e)}")
            st.error("Is your backend server running on port 8000?")