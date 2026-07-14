# AI-First CRM HCP Module - Log Interaction Screen

This project is a high-fidelity Healthcare Professional (HCP) Customer Relationship Management (CRM) module focused on the **"Log Interaction" screen**, built as a hiring assignment submission.

It provides a dual-input CRM interface where representatives can log, view, and edit visits manually through a **Structured Form** (left pane) or conversationally through an **AI Assistant Chat Interface** (right pane). The form and chat share state in real-time (via **Redux Toolkit**). When the assistant executes tools, it updates the database and synchronizes the form dynamically.

---

## 1. Technology Stack
* **Frontend**: React + Vite + TypeScript, Redux Toolkit, Axios, Lucide Icons
* **Styling**: Modern Vanilla CSS, Google Inter Font, Responsive split grid layout
* **Backend**: Python 3.12+ with FastAPI, SQLAlchemy ORM
* **Agent Framework**: LangGraph Python, LangChain Core
* **LLM Integration**: Groq Cloud API (Configurable via environment variables)
* **Database**: PostgreSQL (SQLAlchemy models and transactions)

---

## 2. Bounded Agent & Technical Design
The AI assistant is built as a **bounded deterministic graph** to ensure maximum reliability and speed:
1. **Router Node**: Analyzes intent and parses user input using the Groq LLM. If database mutation or queries are requested, it binds and calls the corresponding tool. If no tools are required, it routes to a direct summary node.
2. **Transactional Tool Nodes**: Catch execution states, run SQLAlchemy mutations, update inventory stock, and return structured output payloads.
3. **Response Generator Node**: Formulates a user-friendly conversational summary of what the agent performed.

### Double-Defensive Fallback Engine
If the Groq API key is missing or the API call fails, the backend automatically falls back to an offline rule-based parser engine that runs the **exact same transactional tools** against the database. This guarantees a **100% crash-proof demo** even when offline or without an active API key.

---

## 3. Concrete Database Tools (6 Tools)
* `log_interaction`: Extracts HCP name, products, brochures, sentiment, and sample packs to save a new record. Transactionally rolls back on stock check failures.
* `edit_interaction`: Modifies whitelisted fields (`topics_discussed`, `observed_sentiment`, `outcomes`, `follow_up_actions`) on the active interaction.
* `get_hcp_context`: Retrieves specialty, clinic details, last 3 interactions, preferred products, and pending follow-ups for a doctor.
* `search_interactions`: Searches meeting logs by keyword or doctor name.
* `suggest_follow_up`: Analyzes meeting topics and generates actionable next steps (e.g. follow-up emails, advisory nominations).
* `manage_samples_and_materials`: Lists active inventory stock levels.

---

## 4. Setup & Running the Application

### Prerequisites
* **Node.js** (v18+)
* **Python** (v3.12+)
* **PostgreSQL** running locally

### Database Initialization & Seeding
1. Open a terminal and copy the `.env` configuration template:
   ```bash
   cp backend/.env.example backend/.env
   ```
2. Configure your environment credentials in `backend/.env`. Note that on this machine, PostgreSQL is configured on port `9571` with the password `Utkarsh@9571` (the default `DATABASE_URL` is set accordingly).
3. Activate the virtual environment and initialize the database (creates tables, drops old, and seeds records):
   ```bash
   # Create virtualenv and install requirements (if not done)
   uv venv backend/.venv
   uv pip install -r backend/requirements.txt
   
   # Run the seed script
   backend/.venv/Scripts/python.exe backend/seed.py
   ```

### Running the Backend
Start the FastAPI server on port 8000:
```bash
cd backend
.venv/Scripts/uvicorn app.main:app --reload
```
You can verify the Swagger UI at `http://localhost:8000/docs` and the health check at `http://localhost:8000/api/health`.

### Running the Frontend
Start the React Vite server:
```bash
cd frontend
npm install
npm run dev
```
Open your browser at `http://localhost:5173/` to interact with the dashboard.

---

## 5. Running the Tests
We have created focused backend tests utilizing a temporary, isolated SQLite in-memory database to verify mutations without corrupting your active PostgreSQL instance.

To run the test suite:
```bash
cd backend
.venv/Scripts/pytest tests/test_backend.py
```
Tests assert:
* Successful transactional interaction logging.
* Whitelisted interactive editing.
* Sample stock deduction.
* Reversion and prevention of negative sample stock.

---

## 6. Demonstration Scenarios

* **Scenario 1: Conversational Logging**
  * Click on the **Log Meeting** chip under the chat window (or type: *"Met Dr. Sarah Jenkins today. We discussed OncoBoost 50mg. She was positive. Shared OncoBoost Phase III Trial Report and gave 3 samples. Follow up in two weeks."*)
  * **Visual Sync**: Notice the left-side form automatically fills with Dr. Sarah Jenkins, OncoBoost 50mg, OncoBoost Report, 3 samples, and the follow-up text. The sample inventory panel dynamically decreases the stock of OncoBoost from 50 to 47.
  * **Tracer**: Expand the `⚙️ log_interaction` badge in the chat window to view the parsed JSON arguments.
* **Scenario 2: Conversational Modification**
  * Click on **Change Sentiment** (or type: *"Actually, change the sentiment to neutral and follow up next Thursday."*)
  * **Visual Sync**: The sentiment radio button instantly shifts to Neutral, and the follow-up textarea updates.
* **Scenario 3: Profile Context & Inventory Check**
  * Click on **Check Profile** or **Check Stocks** to query history or print stock list without mutating tables.
