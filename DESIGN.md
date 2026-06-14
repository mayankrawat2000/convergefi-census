# Design Documentation: Census Analytics Agent

This document explains the "why" behind the architectural and implementation decisions for the Document Q&A Chatbot.

---

## 1. Architectural Decisions

Our goal is to build a highly factual, computational, and conversational agent. A single LLM call is insufficient because:
- **Factual lookup** requires exact text parsing and search.
- **Quantitative calculations** (e.g. subtracting literacy rates, finding minimums/maximums) are prone to hallucinations if calculated in-context.
- **Artifact production** (e.g. Matplotlib charts, tables) requires writing and executing code dynamically.

We chose a **FastAPI backend** + **Streamlit frontend** decoupled model:
- **Decoupled Architecture**: FastAPI serves as the single source of truth for the Agent loop, database, executor, and storage. Streamlit provides a clean, premium user interface. This separation makes it easy to write automated backend tests, swap frontend interfaces, or deploy on container orchestration services.
- **Docker Compose Orchestration**: Both services are isolated, and the `data/` and `workspace/` directories are mounted as volumes. This gives the containers access to the host census PDFs/markdown files, and writes generated charts, code, and chat history back to the host filesystem.

---

## 2. File-based Working Memory and Workspace

We structure the local filesystem inside `workspace/` to serve as the agent's memory and scratchpad:
- `workspace/data/`: Holds parsed CSV tables.
- `workspace/code/`: Temporary scripts written by the agent. If a run fails, the agent can examine the script.
- `workspace/artifacts/`: Saved Matplotlib plots, markdown tables, or CSV sheets. The FastAPI server serves these files to Streamlit.
- `workspace/history/`: Saved JSON files named `session_<session_id>.json` representing conversation histories. On each message, the backend loads the history and appends the new turn, giving the agent memory across turns.

---

## 3. Data Engineering (Offline Pre-parsing)

Rather than forcing the LLM to write complex code to parse raw markdown tables at runtime:
1. We segment the markdown files into pages using the `<!-- page X -->` markers and store them in a **SQLite database (`pages` table)**. This is used for keyword search, page retrieval, and citation snippet matching.
2. We parse the 48 statement tables from the markdown files and output them as structured, clean **CSV files** inside `workspace/data/`.
3. We create a unified master table `census_master.csv` containing common variables (Population, Literacy, WPR, SC%, ST%, Sex Ratio, Cultivators%) for all 110 districts.

**Why?**
- Pre-parsing tables to CSV makes the Agent's code execution sandbox *immensely* robust. Instead of the LLM trying to parse irregular markdown pipes at runtime (which is highly error-prone), it can simply execute:
  `df = pd.read_csv('data/census_master.csv')`
  `bhopal_lit = df[df['district_name']=='Bhopal']['literacy_rate_total'].values[0]`
  This results in a 100% success rate for computations.

---

## 4. Agent Tool Architecture and Execution Loop

We implement a classic **Reasoning and Action (ReAct) loop** using DeepInfra's tool-calling:
- **Tool Selection**: The agent selects from `search_pages` (for text search), `read_page` (to inspect a table/page), `list_available_csvs` (to discover CSV structures), `execute_python` (to calculate/plot), and `save_artifact` (to output tables/reports).
- **Self-Correction Loop**: If the agent's Python code fails (e.g. `pandas KeyError` or `SyntaxError`), the standard error traceback is returned as the tool output. The agent reviews the error, modifies its Python script, and runs it again. It has up to 10 iterations to solve the query.
- **Citations and Refusals**: The agent is instructed via the system prompt to return a structured JSON response at the end of the loop. If a question is unanswerable from the context, it refuses it.

---

## 5. Citations

To prevent hallucinations, every factual claim must cite a page and snippet.
- The SQLite pages table maps each piece of text back to the source document and page number.
- When the agent searches or reads pages, it captures these details.
- In the final JSON response, the agent outputs a `citations` array with `source_document`, `page_number`, and `snippet`. Streamlit displays these citations in a clean expander below the answer bubble.

---

## 6. Pinned Dependencies and Dockerization

To guarantee identical behavior across machines, dependencies are pinned in `requirements.txt`.
The FastAPI backend runs Uvicorn on port 8000, and Streamlit runs on port 8501. The services communicate via a shared bridge network, with volume mounts mapping `./workspace` and `./data` to keep state persistent.
