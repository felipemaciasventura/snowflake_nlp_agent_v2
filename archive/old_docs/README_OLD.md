# 🤖 Snowflake NLP Agent v2

An intelligent web application built with Streamlit that enables natural language queries (English) to Snowflake databases, using LangChain with **triple support** for Groq/Llama, Google Gemini, and Ollama (local models) for automatic text-to-SQL conversion with hybrid intent detection.

![License](https://img.shields.io/badge/license-MIT-blue.svg)
![Python](https://img.shields.io/badge/python-3.8+-blue.svg)
![Streamlit](https://img.shields.io/badge/streamlit-1.28+-red.svg)
![Snowflake](https://img.shields.io/badge/snowflake-supported-blue.svg)

## 🌟 Key Features

- **💬 Intuitive Chat Interface**: Natural conversation with your database
- **🧠 Hybrid NLP Processing**: Smart intent detection (DB vs. help vs. out-of-scope)
- **🔄 Triple LLM Support**: Works with Groq/Llama, Google Gemini, and Ollama (local) with auto-detection
- **📊 Smart Visualization**: Automatic result formatting with interactive tables
- **🔒 Secure Connection**: Robust Snowflake integration using encrypted credentials
- **🎯 Educational Answers**: Helpful guidance with examples and friendly redirection
- **🎨 Modern UI**: Responsive design with Streamlit and interactive components

## 🚀 Quick Start

### Prerequisites

- Python 3.8+
- Cuenta de Snowflake con credenciales de acceso
- Groq **API Key** (option 1) for Llama models
- Google Gemini **API Key** (option 2) for Gemini models  
- Ollama **server** (option 3) for local models
- At least one of the three LLM providers configured

### 1. Installation

#### Quick Start (Recommended)

```bash
# Clone the repository
git clone https://github.com/tu-usuario/snowflake_nlp_agent_v2.git
cd snowflake_nlp_agent_v2

# Complete development setup with one command
make init
```

#### Manual Installation

```bash
# Create and activate a virtual environment
python -m venv venv
source venv/bin/activate  # Linux/Mac
# venv\Scripts\activate   # Windows

# Install dependencies (choose one)
make install          # Production dependencies only
make install-dev      # Development dependencies (recommended)
pip install -e .      # Alternative: pip installation
```

### 2. Configuration

```bash
# Copy configuration template
cp .env.example .env

# Edit .env with your credentials
nano .env
```

Set the following variables in `.env`:

```env
# Snowflake credentials
SNOWFLAKE_ACCOUNT=your-account-url
SNOWFLAKE_USER=your-username
SNOWFLAKE_PASSWORD=your-password
SNOWFLAKE_WAREHOUSE=your-warehouse
SNOWFLAKE_DATABASE=your-database
SNOWFLAKE_SCHEMA=PUBLIC

# LLM Providers - Configure at least one
# Groq (option 1)
GROQ_API_KEY=your-groq-api-key
MODEL_NAME=llama-3.3-70b-versatile

# Google Gemini (option 2) - RECOMMENDED
GOOGLE_API_KEY=your-google-api-key
GEMINI_MODEL=gemini-1.5-flash

# Ollama (option 3 - local model)
OLLAMA_BASE_URL=http://localhost:11434
OLLAMA_MODEL=codellama:7b-instruct

# Provider selection (auto, groq, gemini, ollama)
LLM_PROVIDER=gemini

# Optional
DEBUG=False

# Table preview (only for intents like "show <table>")
# Maximum number of rows to display in the preview
SHOW_TABLE_LIMIT=100
# Probabilistic sampling percentage (0.0 = disabled). E.g., 0.1 -> 0.1%
SHOW_TABLE_SAMPLE_PERCENT=0.0
```

### 3. Run the App

```bash
# Activate virtual environment
source venv/bin/activate

# Run application
streamlit run streamlit_app.py
```

The app will be available at `http://localhost:8501`

## 💻 Usage Examples

### 🔍 Database Queries

```
🔹 "What are the 10 highest-value orders?"
🔹 "Show me this month's sales"
🔹 "How many customers are there in total?"
🔹 "List the best-selling products"
🔹 "Which database am I using?"
🔹 "Show available tables"
🔹 "What is the average revenue by region?"
```

### 🎯 Help Queries (Educational Response)

```
🔹 "What can you help me with?"
🔹 "What can you do?"
🔹 "How does this app work?"
🔹 "Show me examples of what you can do"
```

### 🚫 Out-of-Scope Queries (Friendly Redirection)

```
🔹 "How's the weather?"
🔹 "Tell me a joke"
🔹 "What movies do you recommend?"
→ Friendly redirection to database-related capabilities
```

### Automatic Outputs

The application automatically generates:
- ✅ **Optimized and validated SQL queries**
- 📊 **Formatted tables** with friendly column names
- 💰 **Currency formatting** for financial values
- 📈 **Record counters** and statistics
- 🔍 **Persistent conversation history**

## 🏗️ Architecture

### Project Structure

```
snowflake_nlp_agent_v2/
├── 📄 streamlit_app.py         # Main application
├── 📁 src/
│   ├── 🤖 agent/              # NLP and LangChain logic
│   │   └── nlp_agent.py
│   ├── 🗄️  database/           # Snowflake connection
│   │   └── snowflake_conn.py
│   ├── 📝 prompts/            # SQL prompt templates
│   └── ⚙️  utils/              # Configuration and helpers
│       ├── config.py
│       ├── helpers.py
│       ├── context_enhancer.py
│       └── prompt_loader.py
├── 🧪 tests/                  # Test suite
│   ├── test_config.py
│   ├── conftest.py
│   └── __init__.py
├── 📁 .github/workflows/      # CI/CD pipeline
│   └── ci.yml
├── 📦 pyproject.toml          # Modern Python project config
├── 📋 requirements.txt        # Legacy dependencies
├── 🔧 .env.example           # Configuration template
├── 🛠️  Makefile               # Development automation
├── 📜 LICENSE                 # MIT License
├── 🔍 .pre-commit-config.yaml # Code quality hooks
└── 📚 docs/                   # Documentation
    ├── ARCHITECTURE.md
    ├── CHANGELOG.md
    └── PROJECT_MODERNIZATION.md
```

### Key Technologies

| Technology | Purpose | Version |
|------------|---------|---------|
| **Streamlit** | Web framework | 1.28+ |
| **LangChain** | LLM orchestration | 0.1+ |
| **Groq** | LLM API (Llama 3.3) ✅ | Latest |
| **Google Gemini** | LLM API (Gemini 1.5) ✅ | Latest |
| **Ollama** | Local models (CodeLlama) ✅ | 0.6+ |
| **Snowflake** | Data Warehouse | Connector 3.0+ |
| **Pandas** | Data manipulation | 1.5+ |
| **SQLAlchemy** | ORM and connections | 2.0+ |

## 🔧 Advanced Configuration

### Environment Variables

| Variable | Description | Required | Example |
|----------|-------------|----------|---------|
| `SNOWFLAKE_ACCOUNT` | Snowflake account URL | ✅ | `your-org-account` |
| `SNOWFLAKE_USER` | Snowflake user | ✅ | `user@company.com` |
| `SNOWFLAKE_PASSWORD` | User password | ✅ | `password123` |
| `SNOWFLAKE_WAREHOUSE` | Warehouse to use | ✅ | `COMPUTE_WH` |
| `SNOWFLAKE_DATABASE` | Database | ✅ | `PROD_DB` |
| `SNOWFLAKE_SCHEMA` | Default schema | ❌ | `PUBLIC` |
| `GROQ_API_KEY` | Groq API Key (option 1) | 🔄 | `gsk_...` |
| `GOOGLE_API_KEY` | Google Gemini API Key (option 2) | 🔄 | `AIza...` |
| `OLLAMA_BASE_URL` | Ollama server URL (option 3) | 🔄 | `http://localhost:11434` |
| `OLLAMA_MODEL` | Ollama model | ❌ | `codellama:7b-instruct` |
| `MODEL_NAME` | Groq model | ❌ | `llama-3.3-70b-versatile` |
| `GEMINI_MODEL` | Gemini model | ❌ | `gemini-1.5-flash` |
| `LLM_PROVIDER` | Provider selection | ❌ | `auto`, `groq`, `gemini`, `ollama` |
| `SHOW_TABLE_LIMIT` | Table preview row limit | ❌ | `100` |
| `SHOW_TABLE_SAMPLE_PERCENT` | Probabilistic sampling percent for preview (0.0 disables) | ❌ | `0.0` |

**Note:** 🔄 = At least one of the three LLM providers must be configured

### Development Commands

#### 🚀 Quick Commands (New!)

```bash
# Start the application
make run              # Standard mode
make run-debug        # Debug mode with detailed logs

# Development workflow
make quality          # Run all quality checks (format + lint + type-check)
make test             # Run test suite with coverage
make format           # Format code with Black
make lint             # Check code style with flake8
make type-check       # Type checking with mypy

# Project management
make clean            # Clean build artifacts
make build            # Build distribution package
make help             # Show all available commands
```

#### 🔧 Traditional Commands (Still Available)

```bash
# Run with custom configuration
streamlit run streamlit_app.py --server.port 8080
DEBUG=True streamlit run streamlit_app.py

# Manual quality checks
python -m py_compile streamlit_app.py
flake8 src/ streamlit_app.py
black src/ streamlit_app.py
mypy src/ streamlit_app.py
pytest tests/
```

## 🔬 Detailed Flow Example

To understand how the magic works behind the scenes, let’s follow the journey of a simple question through the system.

**User question:** `Which are the top 10 customers by spending?`

---

#### **Step 1: User Interface (Streamlit)**

1.  **User Input**: The user types the question in the web app chat (`streamlit_app.py`).
2.  **Input Processing**: The app immediately stores and displays the user’s message in the interface.
3.  **Agent Call**: The system core is invoked: `agent.process_query(...)`.

---

#### **Step 2: NLP Agent Layer (LangChain + Groq)**

4.  **Processing Start**: The `SnowflakeNLPAgent` (`src/agent/nlp_agent.py`) receives the query.
5.  **Prompt Construction**: LangChain’s `SQLDatabaseChain` combines the user question with the database schema and a Spanish prompt template.
6.  **LLM Invocation**: The complete prompt is sent to the Groq API using the `llama-3.3-70b-versatile` model.
7.  **SQL Generation**: Guided by the prompt, the LLM generates the corresponding SQL query.
    ```sql
    SELECT c.c_name, SUM(o.o_totalprice) AS total_gastado
    FROM CUSTOMER c
    JOIN ORDERS o ON c.c_custkey = o.o_custkey
    GROUP BY c.c_name
    ORDER BY total_gastado DESC
    LIMIT 10
    ```
8.  **SQL Extraction**: The agent extracts the generated SQL from the LangChain response.

---

#### **Step 3: Data Access Layer (Snowflake)**

9.  **Query Execution**: The agent runs the SQL through the database connection layer (`src/database/snowflake_conn.py`).
10. **Processing in Snowflake**: Snowflake receives the query, executes it in its compute engine, and returns the results. For example:
    ```
    [('Customer#0001', Decimal('555285.16')), ('Customer#0002', Decimal('544089.09')), ...]
    ```
11. **Results Reception**: The application receives these results (a list of tuples).

---

#### **Step 4: Formatting and Visualization (Streamlit)**

12. **Smart Formatting**: A utility function (`format_sql_result_to_dataframe`) converts the list of tuples into a Pandas DataFrame, applying currency formatting and friendly column names.
13. **Final Visualization**:
    *   The app shows the formatted DataFrame in an interactive table.
    *   It displays a counter below the table: `📊 10 records found`.
    *   The full response is saved in the chat history.

---

#### **Step 5: Traceability (Logs in UI)**

14. **Logs Panel**: Throughout the process, detailed logs are recorded and shown in the sidebar, providing full transparency from the generated SQL to the obtained results.

## 🔄 Recent Updates (v2.5) - Project Modernization 🚀

### ✅ **New in v2.5 - Complete Project Modernization**

- **📦 Modern Python Packaging**: Added `pyproject.toml` with PEP 518/621 compliance
- **🛠️ Development Automation**: Added comprehensive Makefile with all development commands
- **🧪 Testing Infrastructure**: Complete test suite setup with pytest, fixtures, and examples
- **🔄 CI/CD Pipeline**: GitHub Actions workflow with matrix testing (Python 3.8-3.13)
- **🔍 Code Quality**: Pre-commit hooks, enhanced linting, formatting, and type checking
- **📜 Licensing**: Added MIT License file
- **🧹 Cleanup**: Removed artifact files and modernized .gitignore
- **📚 Documentation**: Updated README, added PROJECT_MODERNIZATION.md
- **🔐 Security**: Enhanced gitignore patterns to prevent credential leakage

### 🛠️ **Developer Experience Improvements**
- **One-command setup**: `make init` for complete environment setup
- **Quality automation**: `make quality` runs all code quality checks
- **Easy testing**: `make test` with coverage reporting
- **Simple deployment**: `make run` and `make run-debug`
- **Build tools**: `make build` and `make clean` for distribution

---

## 🔄 Previous Updates (v2.4)

### ✅ What's New in v2.4

- **🔎 Expanded metadata intents**: direct answers (no LLM) for:
  - Current database (`CURRENT_DATABASE()`)
  - Current schema (`CURRENT_SCHEMA()`)
  - Current role (`CURRENT_ROLE()`)
  - Current warehouse (`CURRENT_WAREHOUSE()`)
  - Supports variants/typos: "which/what/wich/current ..."
- **📄 Intent-based table preview**: for phrases like "show me agents table" or "show agents" a safe preview is executed directly:
  - Configurable limit via `.env` with `SHOW_TABLE_LIMIT` (default `100`).
  - Optional probabilistic sampling with `SHOW_TABLE_SAMPLE_PERCENT` (default `0.0`, disabled). If enabled, uses `SAMPLE(<percent>) LIMIT <limit>`.
  - Detailed logs in the process panel.
- **🧱 Robust UI**: fixes for when the backend returns results as text (list of tuples/string) and dates like `datetime.date(...)`.
  - Parsed and normalized to display a correct DataFrame.
- **📋 Persistent "Show all columns" checkbox**: state now persists, and you can toggle between key columns and all columns for both new results and chat history.

---

## 🔄 Recent Updates (v2.3)

### ✅ New Main Features

- **🛠️ Ollama Support**: Integrated full support for local models (CodeLlama 7B-Instruct)
- **🔄 Triple LLM Support**: Groq/Llama + Google Gemini + Ollama with auto-detection and local-first preference
- **📝 Advanced SQL Cleaning**: Robust system to handle CodeLlama markdown output
- **🏠 Local Processing**: Full privacy option with local model and zero API cost

### ✅ Updates in v2.2

- **🧠 Hybrid Detection**: Smart classification of queries (DB vs. help vs. out-of-scope)
- **🎯 Educational Responses**: Comprehensive guidance with examples for new users
- **🚀 Friendly Redirection**: Helpful responses for out-of-scope queries
- **📊 Dynamic Info**: Sidebar shows the active LLM model in real time

### ✅ Earlier Improvements (v2.1)

- **🎯 Smart Formatting**: Automatic recognition of query types
- **💹 Currency Formatting**: Automatic display of financial values
- **🔧 Robust Parsing**: Advanced handling of Snowflake Decimal objects
- **⚡ Updated Models**: Llama 3.3 70B Versatile + Gemini 1.5 Flash
- **🖥️ Improved UI**: Full-width tables and record counters

### 🐛 Fixes

- ✅ Deprecated `__call__` method replaced with `invoke`
- ✅ Robust handling of DataFrame constructor errors
- ✅ Parsing of strings with complex SQL results
- ✅ Dynamic configuration of LLM providers
- ✅ Automatic detection of available models

## 🤝 Contributing

### Quick Start for Contributors

```bash
# 1. Fork and clone the repository
git clone https://github.com/your-username/snowflake_nlp_agent_v2.git
cd snowflake_nlp_agent_v2

# 2. Set up development environment
make init

# 3. Create a feature branch
git checkout -b feature/AmazingFeature

# 4. Make your changes and ensure quality
make quality          # Format, lint, and type-check
make test            # Run tests
```

### Development Workflow

1. **Code Quality**: All PRs must pass quality checks
   - Code formatting with Black
   - Linting with flake8
   - Type checking with mypy
   - Test coverage maintenance

2. **Testing**: Add tests for new features
   - Unit tests in `tests/`
   - Integration tests welcome
   - Maintain coverage above 80%

3. **CI/CD**: All checks run automatically
   - Matrix testing across Python 3.8-3.13
   - Security scanning
   - Build verification

4. **Submit PR**:
   ```bash
   git commit -m 'feat: add amazing feature'
   git push origin feature/AmazingFeature
   # Open Pull Request on GitHub
   ```

### Code Standards

- **Python**: 3.8+ compatibility required
- **Style**: Black formatting (88 char limit)
- **Linting**: flake8 compliance
- **Types**: mypy type hints encouraged
- **Tests**: pytest with fixtures
- **Commits**: Conventional commit messages preferred

## 📚 Documentation

- 📖 **[README.md](README.md)** - Main project documentation
- 🏗️ **[ARCHITECTURE.md](ARCHITECTURE.md)** - System architecture details
- 📝 **[CHANGELOG.md](CHANGELOG.md)** - Version history and changes
- 🤝 **[CONTRIBUTING.md](CONTRIBUTING.md)** - Contribution guidelines
- 🚀 **[PROJECT_MODERNIZATION.md](PROJECT_MODERNIZATION.md)** - v2.5 modernization details
- 🔧 **[LLM_SETUP.md](LLM_SETUP.md)** - LLM provider configuration
- 📊 **[ENHANCED_CONTEXT_SYSTEM.md](ENHANCED_CONTEXT_SYSTEM.md)** - Context enhancement features

## 📝 License

This project is licensed under the MIT License. See [LICENSE](LICENSE) for details.

## 🆘 Support

Issues or questions?

- 🐛 **Issues**: [GitHub Issues](https://github.com/tu-usuario/snowflake_nlp_agent_v2/issues)
- 🤝 **Contributing**: See [CONTRIBUTING.md](CONTRIBUTING.md) for guidelines
- 📚 **Documentation**: See [PROJECT_MODERNIZATION.md](PROJECT_MODERNIZATION.md) for v2.5 changes
- 💬 **Discussions**: [GitHub Discussions](https://github.com/tu-usuario/snowflake_nlp_agent_v2/discussions)
- 📧 **Email**: soporte@empresa.com

## 🙏 Acknowledgments

- **Streamlit** for the amazing web framework
- **LangChain** for LLM orchestration
- **Groq** for fast LLM services with Llama models
- **Google** for Gemini API access
- **Ollama** for local model support
- **Snowflake** for the robust data platform
- **Open Source Community** for the amazing tools and libraries

## 🌟 Contributors

Special thanks to all contributors who help make this project better:

- **Felipe Macias** - Project creator and maintainer
- **Community Contributors** - Bug reports, feature requests, and code contributions

---

**Built with ❤️ using Python and modern AI technologies**

🚀 **Ready for production deployment with v2.5 modernization!**
