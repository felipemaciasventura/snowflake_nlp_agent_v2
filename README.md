# Snowflake NLP Agent v2

A Streamlit web app that lets you query Snowflake in plain English. It generates SQL via LangChain, runs it on Snowflake, and displays well-formatted results. Supports multiple LLM providers (Google Gemini, Groq/Llama, local Ollama, and SQLCoder) without changing app functionality.

---

## Key Features
- Natural language to Snowflake SQL (English)
- Multiple LLM providers with auto-detection (priority: SQLCoder > Ollama > Gemini > Groq)
- Secure Snowflake connection (connector + SQLAlchemy)
- Smart result formatting (readable column names, COUNT/metadata handling)
- Input validation and safety guardrails
- Logs panel with generated SQL for transparency

---

## Supported OS
- Windows (PowerShell)
- Linux (bash)
- macOS (zsh/bash)

---

## Installation
You can install dependencies using either requirements.txt or directly from pyproject.toml. Choose the method you prefer.

### Windows (PowerShell)
1) Create and activate a virtual environment
```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
```
2) Install dependencies (choose one)
- From requirements.txt:
```powershell
pip install -r requirements.txt
```
- From pyproject.toml (PEP 621):
```powershell
# Runtime only
pip install .
# Editable install for development (includes dev/test/docs extras)
pip install -e .[dev,test,docs]
```
3) Create .env and fill in credentials
```powershell
Copy-Item .env.example .env
# Edit .env with your SNOWFLAKE_* and one LLM provider
```
4) Run the app
```powershell
streamlit run streamlit_app.py
```

### Linux (bash)
1) Create and activate a virtual environment
```bash
python3 -m venv .venv
source .venv/bin/activate
```
2) Install dependencies (choose one)
- From requirements.txt:
```bash
pip install -r requirements.txt
```
- From pyproject.toml (PEP 621):
```bash
# Runtime only
pip install .
# Editable install for development (includes dev/test/docs extras)
pip install -e .[dev,test,docs]
```
3) Create .env and fill in credentials
```bash
cp .env.example .env
# Edit .env with your SNOWFLAKE_* and one LLM provider
```
4) Run the app
```bash
streamlit run streamlit_app.py
```

### macOS (zsh/bash)
1) Create and activate a virtual environment
```bash
python3 -m venv .venv
source .venv/bin/activate
```
2) Install dependencies (choose one)
- From requirements.txt:
```bash
pip install -r requirements.txt
```
- From pyproject.toml (PEP 621):
```bash
# Runtime only
pip install .
# Editable install for development (includes dev/test/docs extras)
pip install -e .[dev,test,docs]
```
3) Create .env and fill in credentials
```bash
cp .env.example .env
# Edit .env with your SNOWFLAKE_* and one LLM provider
```
4) Run the app
```bash
streamlit run streamlit_app.py
```

---

## Automation with Make (optional)
This project ships with a Makefile that automates common tasks. If make is available on your system:

```bash
make help         # Show available commands
make init         # Initialize dev environment (.env + pre-commit)
make install      # Install runtime dependencies (pip install -e .)
make install-dev  # Install dev/test/docs dependencies (pip install -e .[dev,test,docs])
make run          # Run the Streamlit app
make test         # Run tests
make quality      # Format + lint + type-check
```
Notes:
- Windows users can install GNU Make via Chocolatey (choco install make) or run the individual commands shown in this README.
- On macOS, you can install make with Homebrew (brew install make) if needed.

---

## Required Environment Variables (.env)
Snowflake:
```
SNOWFLAKE_ACCOUNT=...
SNOWFLAKE_USER=...
SNOWFLAKE_PASSWORD=...
SNOWFLAKE_WAREHOUSE=...
SNOWFLAKE_DATABASE=...
SNOWFLAKE_SCHEMA=PUBLIC
```
Choose a single LLM provider:
- Gemini:
```
LLM_PROVIDER=gemini
GOOGLE_API_KEY=...
GEMINI_MODEL=gemini-1.5-flash
```
- Groq/Llama:
```
LLM_PROVIDER=groq
GROQ_API_KEY=...
MODEL_NAME=llama-3.3-70b-versatile
```
- Ollama (local):
```
LLM_PROVIDER=ollama
OLLAMA_BASE_URL=http://localhost:11434
OLLAMA_MODEL=codellama:7b-instruct
```
- SQLCoder (SQL-specialized):
```
LLM_PROVIDER=sqlcoder
SQLCODER_BASE_URL=http://localhost:11434
SQLCODER_MODEL=sqlcoder-fp16:latest
```

---

## Usage
Ask in English, e.g.:
- "How many customers are there?"
- "Show the 10 highest-value orders"
- "Which database am I using?"
The app generates SQL, executes it, and displays a clean table with helpful formatting.

---

## Project Structure (high level)
```
src/
  agent/            # NLP logic (LangChain + LLM)
  database/         # Snowflake connection and helpers
  utils/            # Config, prompts, helpers, context system
streamlit_app.py     # Streamlit UI (chat + logs)
tests/               # Test suite
config/              # Optional prompt templates
```

---

## Security Notes
- Do not commit .env or credentials
- Use least-privilege Snowflake accounts
- Prefer local LLM (Ollama/SQLCoder) for maximum privacy

---

## License
MIT (see LICENSE)
