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
- Schema cache for improved performance
- SQL injection prevention with table name validation

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
python3.12 -m venv .venv
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

### Snowflake Configuration
```bash
SNOWFLAKE_ACCOUNT=your_account
SNOWFLAKE_USER=your_user
SNOWFLAKE_PASSWORD=your_password
SNOWFLAKE_WAREHOUSE=your_warehouse
SNOWFLAKE_DATABASE=your_database
SNOWFLAKE_SCHEMA=PUBLIC
```

### LLM Provider Configuration

#### Enable/Disable Providers
Control which providers are enabled with simple switches:
```bash
# Enable/Disable providers (true/false)
ENABLE_GROQ=true
ENABLE_GEMINI=true
ENABLE_OLLAMA=true
ENABLE_SQLCODER=true
```

#### Provider Selection
```bash
# Options: "auto", "groq", "gemini", "ollama", "sqlcoder"
# "auto" uses priority: SQLCoder > Ollama > Gemini > Groq
LLM_PROVIDER=auto
```

#### Provider-Specific Configuration

**Groq (Cloud):**
```bash
ENABLE_GROQ=true
GROQ_API_KEY=your_groq_api_key
MODEL_NAME=llama-3.3-70b-versatile
```

**Google Gemini (Cloud):**
```bash
ENABLE_GEMINI=true
GOOGLE_API_KEY=your_google_api_key
GEMINI_MODEL=gemini-1.5-flash
```

**Ollama (Local):**
```bash
ENABLE_OLLAMA=true
OLLAMA_BASE_URL=http://localhost:11434
OLLAMA_MODEL=codellama:7b-instruct
```

**SQLCoder (Local, SQL Specialized):**
```bash
ENABLE_SQLCODER=true
SQLCODER_BASE_URL=http://localhost:11434
SQLCODER_MODEL=sqlcoder-fp16:latest
```

**Note:** For Ollama/SQLCoder, install `langchain-ollama` to avoid deprecation warnings:
```bash
pip install langchain-ollama>=0.2.0
```

### Quick Start Configuration

**Example 1: Use only Gemini (disable others)**
```bash
ENABLE_GROQ=false
ENABLE_GEMINI=true
ENABLE_OLLAMA=false
ENABLE_SQLCODER=false
LLM_PROVIDER=gemini
GOOGLE_API_KEY=your_key
```

**Example 2: Use only local Ollama**
```bash
ENABLE_GROQ=false
ENABLE_GEMINI=false
ENABLE_OLLAMA=true
ENABLE_SQLCODER=false
LLM_PROVIDER=ollama
OLLAMA_BASE_URL=http://localhost:11434
```

**Example 3: Auto-select (recommended)**
```bash
ENABLE_GROQ=true
ENABLE_GEMINI=true
ENABLE_OLLAMA=true
ENABLE_SQLCODER=true
LLM_PROVIDER=auto
# Configure API keys for cloud providers
# Configure URLs for local providers
```

See `.env.example` for a complete configuration template.

---

## Usage
Ask in English, e.g.:
- "How many customers are there?"
- "Show the 10 highest-value orders"
- "Which database am I using?"
- "Show me the customers table"
- "What tables are available?"

The app generates SQL, executes it, and displays a clean table with helpful formatting.

### 📖 Query Guide
For detailed information on supported query types and best practices, see **[QUERY_GUIDE.md](QUERY_GUIDE.md)**.

**Quick Examples:**
- **Metadata:** `show tables`, `what database are we using?`, `how many tables do we have?`
- **Count:** `how many customers are there?`
- **Ranking:** `top 10 most expensive properties`
- **Aggregation:** `average price per city`
- **Filtering:** `properties with more than 3 bedrooms`
- **Temporal:** `transactions from last month`

---

## ✨ Recent Improvements
- ✅ **SQL Injection Prevention:** Table name validation for secure dynamic queries
- ✅ **Schema Cache:** Persistent cache for faster subsequent queries (80-90% performance improvement)
- ✅ **Enhanced Context System:** Better SQL generation with schema analysis and query history
- ✅ **Improved Error Handling:** More specific error messages and better debugging

---

## 🔧 Troubleshooting

### Problem: "No tables found" or "Discovered 0 tables"
**Solutions:**
1. Verify Snowflake connection is active (check sidebar)
2. Verify the schema has tables: `SHOW TABLES` in Snowflake
3. Check logs for connection errors
4. Try refreshing the schema cache (restart the app)

### Problem: "Cache not working" or slow performance
**Solutions:**
1. Verify write permissions in `data/` directory
2. Check that `data/schema_cache.json` is created after first query
3. Verify cache file is valid JSON: `cat data/schema_cache.json | python3 -m json.tool`
4. Delete cache to force refresh: `rm data/schema_cache.json`

### Problem: "ChatOllama deprecation warning"
**Solution:**
```bash
pip install langchain-ollama>=0.2.0
```

### Problem: Connection errors or timeouts
**Solutions:**
1. Verify `SNOWFLAKE_ACCOUNT` format (should be like `xy12345` or `xy12345.us-east-1`)
2. Check internet connectivity
3. Verify account name doesn't have extra characters (#, @, /)
4. Check Snowflake service status

### Problem: "Invalid table identifier" error
**Solutions:**
1. Verify table name is correct (case-insensitive)
2. Check that table exists in current schema
3. Use exact table name from `SHOW TABLES` query
4. Avoid special characters in table names

### Problem: LLM not responding or slow
**Solutions:**
1. Check LLM provider status (Ollama server running, API keys valid)
2. Try switching LLM provider in sidebar
3. Check network connectivity for cloud providers (Gemini, Groq)
4. For Ollama: Verify server is accessible at configured URL

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
