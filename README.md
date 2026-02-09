# PROJECT CONTEXT: Omni-Support Agent (RAG + SQL + Persistence)

## 1. Project Overview
I am building an "Omni-Support Agent" for an E-commerce platform. 
It is a **Microservice** built with Python that uses **LangGraph** to handle customer support queries.
It connects to a **PostgreSQL (Supabase)** database for both Business Data (Orders) and Agent Memory (Chat Persistence).

## 2. Tech Stack
- **Framework:** LangGraph (State Management), LangChain.
- **API:** FastAPI (server.py).
- **Database:** PostgreSQL (Supabase) via `psycopg-pool` and `psycopg2`.
- **LLM:** GPT-4o-mini (or Gemini 1.5 Flash).
- **Hosting:** Currently local (localhost:8000), utilizing Cloud DB.

## 3. Current Status
- ✅ **Migration Complete:** Moved from SQLite/Memory to PostgreSQL for both Data and Persistence.
- ✅ **Persistence Verified:** Agent remembers users across server restarts via `thread_id`.
- ✅ **API Live:** `server.py` successfully handles POST requests with `thread_id`.
- ✅ **Schema Fixed:** `orders` table is live, and Schema is hardcoded in `tools.py` to prevent hallucinations.

---

## 4. File Structure & Responsibilities

### `backend/server.py` (The API Layer)
- **Role:** Entry point. FastAPI app.
- **Key Logic:** - Receives `POST /chat` with `{"query": "...", "thread_id": "..."}`.
  - If `thread_id` is missing, generates a new UUID.
  - Invokes `graph.invoke(..., config={"configurable": {"thread_id": ...}})` to trigger the agent.
  - Returns JSON with `response`, `thread_id`, and `actions_taken` (metadata).

### `backend/agent.py` (The Brain)
- **Role:** Defines the LangGraph State Graph.
- **Key Configuration (CRITICAL):**
  - Uses `PostgresSaver` for persistence.
  - **Connection Pool:** MUST use `kwargs={"autocommit": True, "row_factory": dict_row}` to match the setup script and prevent Transaction errors.
- **Prompt:** Includes strict rules: "Table name is `orders`, Primary Key is `id` (NOT `order_id`)."

### `backend/tools.py` (The Limbs)
- **Role:** Contains `@tool` definitions.
- **Tools:**
  - `query_sql_db`: Connects to Supabase. Uses **Hardcoded Schema** docstring to guide LLM.
  - `query_policy_rag`: Vector search (ChromaDB) for policy docs.
  - `file_ticket` & `generate_return_label`: Write to a local log file.
- **Fix Applied:** `load_dotenv()` is called at the very top to ensure `DATABASE_URL` is found.

### `backend/setup_persistence.py` (Run Once)
- **Role:** Creates `checkpoints` and `checkpoint_writes` tables in Postgres.
- **Status:** Already ran successfully.

### `backend/setup_cloud_db.py` (Run Once)
- **Role:** Creates and populates the `orders` table in Postgres.
- **Schema:** `id` (PK), `cust_name`, `item_name`, `status`, `price` (in cents).
- **Status:** Already ran successfully.

---

## 5. Known Constraints & Rules
1.  **Connection Settings:** The `ConnectionPool` in `agent.py` MUST match `autocommit=True` and `row_factory=dict_row` or the agent crashes with a 500 error.
2.  **Schema Hallucination:** The LLM loves to guess `order_id`. We explicitly forbid this in the System Prompt and Tool Docstring.
3.  **Authentication:** Currently using `sslmode='require'` for Supabase.

## 6. My Goal / Next Task
[INSERT YOUR NEXT QUESTION HERE, e.g., "I want to deploy this to Render" or "I want to build a React Frontend"]