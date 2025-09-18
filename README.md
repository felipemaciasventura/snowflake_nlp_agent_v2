# 🤖 Snowflake NLP Agent v2

An intelligent web application built with Streamlit that enables natural
language (English) queries to Snowflake databases, using LangChain with
**triple support** for Groq/Llama, Google Gemini, and Ollama (local
model) for automatic text-to-SQL conversion with hybrid query detection.

![License](https://img.shields.io/badge/license-MIT-blue.svg)
![Python](https://img.shields.io/badge/python-3.8+-blue.svg)
![Streamlit](https://img.shields.io/badge/streamlit-1.28+-red.svg)
![Snowflake](https://img.shields.io/badge/snowflake-supported-blue.svg)

## 🌟 Key Features

-   **💬 Intuitive Chat Interface**: Natural conversation with your
    database\
-   **🧠 Hybrid NLP Processing**: Intelligent query detection (DB vs
    help vs off-topic)\
-   **🔄 Triple LLM Support**: Compatible with Groq/Llama, Google
    Gemini, and Ollama (local) with auto-detection\
-   **📊 Smart Visualization**: Automatic result formatting with
    interactive tables\
-   **🔒 Secure Connection**: Robust integration with Snowflake using
    encrypted credentials\
-   **🎯 Educational Responses**: Intelligent guidance for users with
    examples and friendly redirection\
-   **🎨 Modern Interface**: Responsive design with Streamlit and
    interactive components

## 🚀 Quick Start

### Prerequisites

-   Python 3.8+\
-   Snowflake account with access credentials\
-   **Groq API Key** (option 1) for Llama models\
-   **Google Gemini API Key** (option 2) for Gemini models\
-   **Ollama Server** (option 3) for local models\
-   At least one of the three LLM providers configured

### 1. Installation

``` bash
# Clone repository
git clone https://github.com/your-user/snowflake_nlp_agent_v2.git
cd snowflake_nlp_agent_v2

# Create and activate virtual environment
python -m venv venv
source venv/bin/activate  # Linux/Mac
# venv\Scriptsctivate   # Windows

# Install dependencies
pip install -r requirements.txt
```

### 2. Configuration

``` bash
# Copy configuration template
cp .env.example .env

# Edit .env with your credentials
nano .env
```

Configure the following variables in `.env`:

``` env
# Snowflake Credentials
SNOWFLAKE_ACCOUNT=your-account-url
SNOWFLAKE_USER=your-user
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
```

### 3. Run Application

``` bash
# Activate virtual environment
source venv/bin/activate

# Run application
streamlit run streamlit_app.py
```

The application will be available at `http://localhost:8501`

## 💻 Usage Examples

### 🔍 Database Queries

    🔹 "What are the 10 orders with the highest value?"
    🔹 "Show me sales for this month"
    🔹 "How many customers are there in total?"
    🔹 "List the best-selling products"
    🔹 "What database am I using?"
    🔹 "Show available tables"
    🔹 "What is the average revenue per region?"

### 🎯 Help Queries (Educational Response)

    🔹 "How can you help me?"
    🔹 "What can you do?"
    🔹 "How does this application work?"
    🔹 "Show me examples of what you can do"

### 🚫 Off-Topic Queries (Friendly Redirection)

    🔹 "How's the weather?"
    🔹 "Tell me a joke"
    🔹 "What movies do you recommend?"
    → Friendly redirection to DB functionalities

### Automatic Results

The application automatically generates: - ✅ **Optimized and validated
SQL queries**\
- 📊 **Formatted tables** with user-friendly column names\
- 💰 **Currency formatting** for financial values\
- 📈 **Record counters** and statistics\
- 🔍 **Persistent conversation history**

## 🏗️ Architecture

### Project Structure

    snowflake_nlp_agent_v2/
    ├── 📄 streamlit_app.py         # Main application
    ├── 📁 src/
    │   ├── 🤖 agent/              # NLP logic and LangChain
    │   │   └── nlp_agent.py
    │   ├── 🗄️  database/           # Snowflake connection
    │   │   └── snowflake_conn.py
    │   └── ⚙️  utils/              # Configuration and helpers
    │       ├── config.py
    │       └── helpers.py
    ├── 📋 requirements.txt        # Python dependencies
    ├── 🔧 .env.example           # Configuration template
    └── 📚 WARP.md                # Development documentation

### Key Technologies

  Technology          Purpose                       Version
  ------------------- ----------------------------- ----------------
  **Streamlit**       Web framework                 1.28+
  **LangChain**       LLM orchestration             0.1+
  **Groq**            LLM API (Llama 3.3) ✅        Latest
  **Google Gemini**   LLM API (Gemini 1.5) ✅       Latest
  **Ollama**          Local models (CodeLlama) ✅   0.6+
  **Snowflake**       Data warehouse                Connector 3.0+
  **Pandas**          Data manipulation             1.5+
  **SQLAlchemy**      ORM and connections           2.0+

## 🔧 Advanced Configuration

### Environment Variables

  ------------------------------------------------------------------------------------------
  Variable                Description           Required         Example
  ----------------------- --------------------- ---------------- ---------------------------
  `SNOWFLAKE_ACCOUNT`     Snowflake account URL ✅               `your-org-account`

  `SNOWFLAKE_USER`        Snowflake user        ✅               `user@company.com`

  `SNOWFLAKE_PASSWORD`    User password         ✅               `password123`

  `SNOWFLAKE_WAREHOUSE`   Warehouse to use      ✅               `COMPUTE_WH`

  `SNOWFLAKE_DATABASE`    Database              ✅               `PROD_DB`

  `SNOWFLAKE_SCHEMA`      Default schema        ❌               `PUBLIC`

  `GROQ_API_KEY`          Groq API key (option  🔄               `gsk_...`
                          1)                                     

  `GOOGLE_API_KEY`        Google Gemini API key 🔄               `AIza...`
                          (option 2)                             

  `OLLAMA_BASE_URL`       Ollama server URL     🔄               `http://localhost:11434`
                          (option 3)                             

  `OLLAMA_MODEL`          Ollama model          ❌               `codellama:7b-instruct`

  `MODEL_NAME`            Groq model            ❌               `llama-3.3-70b-versatile`

  `GEMINI_MODEL`          Gemini model          ❌               `gemini-1.5-flash`

  `LLM_PROVIDER`          Provider selection    ❌               `auto`, `groq`, `gemini`,
                                                                 `ollama`
  ------------------------------------------------------------------------------------------

**Note:** 🔄 = At least one of the three LLM providers must be
configured

### Development Commands

``` bash
# Run with specific port
streamlit run streamlit_app.py --server.port 8080

# Development mode with detailed logs
DEBUG=True streamlit run streamlit_app.py

# Production (public server)
streamlit run streamlit_app.py --server.port 8080 --server.address 0.0.0.0

# Syntax check
python -m py_compile streamlit_app.py

# Linting
flake8 src/ streamlit_app.py
```

## 🔬 Detailed Workflow Example

To understand how the magic works behind the scenes, let's follow the
journey of a simple question through the system.

**User Question:** `Which are the 10 customers who have spent the most?`

------------------------------------------------------------------------

#### **Step 1: User Interface (Streamlit)**

1.  **User Input**: The user types the question into the web app chat
    (`streamlit_app.py`).\
2.  **Input Processing**: The app immediately saves and displays the
    user's message in the interface.\
3.  **Agent Call**: The system's core is invoked:
    `agent.process_query(...)`.

------------------------------------------------------------------------

#### **Step 2: NLP Agent Layer (LangChain + Groq)**

4.  **Start of Processing**: The `SnowflakeNLPAgent`
    (`src/agent/nlp_agent.py`) receives the query.\
5.  **Prompt Construction**: LangChain's `SQLDatabaseChain` combines the
    user's question with the database schema and a prompt template.\
6.  **LLM Invocation**: The full prompt is sent to the Groq API, using
    the `llama-3.3-70b-versatile` model.\
7.  **SQL Generation**: Guided by the prompt, the LLM generates the
    corresponding SQL query.\
    `sql     SELECT c.c_name, SUM(o.o_totalprice) AS total_spent     FROM CUSTOMER c     JOIN ORDERS o ON c.c_custkey = o.o_custkey     GROUP BY c.c_name     ORDER BY total_spent DESC     LIMIT 10`
8.  **SQL Extraction**: The agent extracts the generated SQL from
    LangChain's response.

------------------------------------------------------------------------

#### **Step 3: Data Access Layer (Snowflake)**

9.  **Query Execution**: The agent executes the SQL query via the
    database connection layer (`src/database/snowflake_conn.py`).\
10. **Snowflake Processing**: Snowflake executes the query in its
    compute engine and returns results. Example:\
    `[('Customer#0001', Decimal('555285.16')), ('Customer#0002', Decimal('544089.09')), ...]`
11. **Result Reception**: The application receives these results (a list
    of tuples).

------------------------------------------------------------------------

#### **Step 4: Formatting and Visualization (Streamlit)**

12. **Smart Formatting**: A utility function
    (`format_sql_result_to_dataframe`) converts the tuple list into a
    Pandas DataFrame, applying currency formatting and user-friendly
    column names.\
13. **Final Visualization**:\

-   Displays the formatted DataFrame in an interactive table\
-   Shows a counter below the table: `📊 10 records found`\
-   Saves the full response in the chat history

------------------------------------------------------------------------

#### **Step 5: Traceability (Logs in UI)**

14. **Logs Panel**: Throughout the process, detailed logs are recorded
    and shown in the sidebar, providing full transparency---from the SQL
    that was generated to the results obtained.

## 🔄 Recent Updates (v2.3)

### ✅ New Key Features

-   **🛠️ Ollama Support**: Full integration for local models (CodeLlama
    7B-Instruct)\
-   **🔄 Triple LLM Support**: Groq/Llama + Google Gemini + Ollama with
    auto-detection and local priority\
-   **📝 Advanced SQL Cleaning**: Robust system to handle CodeLlama
    markdown formatting\
-   **🏠 Local Processing**: Full privacy option with a local model, no
    API costs

### ✅ Updates v2.2

-   **🧠 Hybrid Detection**: Smart classification of queries (DB vs help
    vs off-topic)\
-   **🎯 Educational Responses**: Complete guidance with examples for
    new users\
-   **🚀 Friendly Redirection**: Polite responses for off-topic queries\
-   **📊 Dynamic Info**: Sidebar shows active LLM model in real time

### ✅ Previous Improvements (v2.1)

-   **🎯 Smart Formatting**: Automatic recognition of query types\
-   **💹 Currency Formatting**: Automatic display of financial values\
-   **🔧 Robust Parsing**: Advanced handling of Snowflake Decimal
    objects\
-   **⚡ Updated Models**: Llama 3.3 70B Versatile + Gemini 1.5 Flash\
-   **🖥️ Improved UI**: Full-width tables and record counters

### 🐛 Bug Fixes

-   ✅ Deprecated `__call__` replaced by `invoke`\
-   ✅ Robust error handling in DataFrame constructor\
-   ✅ Parsing of strings with complex SQL results\
-   ✅ Dynamic LLM provider configuration\
-   ✅ Automatic detection of available models

## 🤝 Contribution

1.  **Fork** the project\
2.  Create a feature branch (`git checkout -b feature/AmazingFeature`)\
3.  Commit changes (`git commit -m 'Add AmazingFeature'`)\
4.  Push to branch (`git push origin feature/AmazingFeature`)\
5.  Open a **Pull Request**

## 📝 License

This project is licensed under the MIT License. See `LICENSE` for
details.

## 🆘 Support

Problems or questions?

-   📧 **Email**: support@company.com\
-   🐛 **Issues**: [GitHub
    Issues](https://github.com/your-user/snowflake_nlp_agent_v2/issues)\
-   📚 **Documentation**: See `WARP.md` for technical details

## 🙏 Acknowledgments

-   **Streamlit** for the amazing web framework\
-   **LangChain** for LLM orchestration\
-   **Groq** for fast LLM services\
-   **Snowflake** for the robust data platform

------------------------------------------------------------------------

**Built with ❤️ using Python and modern AI technologies**
