# .env Configuration Template

Copy this to `.env` and fill in your values.

```bash
# ===========================================
# Snowflake Configuration
# ===========================================
SNOWFLAKE_ACCOUNT=your_account
SNOWFLAKE_USER=your_user
SNOWFLAKE_PASSWORD=your_password
SNOWFLAKE_WAREHOUSE=your_warehouse
SNOWFLAKE_DATABASE=your_database
SNOWFLAKE_SCHEMA=PUBLIC

# ===========================================
# LLM Provider Configuration
# ===========================================
# Enable/Disable providers (true/false)
# Set to "true" to enable, "false" to disable
ENABLE_GROQ=true
ENABLE_GEMINI=true
ENABLE_OLLAMA=true
ENABLE_SQLCODER=true

# Provider Selection Mode
# Options: "auto", "groq", "gemini", "ollama", "sqlcoder"
# "auto" will use priority: SQLCoder > Ollama > Gemini > Groq
LLM_PROVIDER=auto

# ===========================================
# Groq Configuration (Cloud)
# ===========================================
# Get your API key from: https://console.groq.com/
GROQ_API_KEY=your_groq_api_key
MODEL_NAME=llama-3.3-70b-versatile

# ===========================================
# Google Gemini Configuration (Cloud)
# ===========================================
# Get your API key from: https://aistudio.google.com/app/apikey
GOOGLE_API_KEY=your_google_api_key
GEMINI_MODEL=gemini-1.5-flash

# ===========================================
# Ollama Configuration (Local)
# ===========================================
# Install Ollama from: https://ollama.ai/
# Run: ollama pull codellama:7b-instruct
OLLAMA_BASE_URL=http://localhost:11434
OLLAMA_MODEL=codellama:7b-instruct

# ===========================================
# SQLCoder Configuration (Local, SQL Specialized)
# ===========================================
# Install SQLCoder from: https://github.com/bigcode-project/starcoder
# Run: ollama pull sqlcoder-fp16:latest (if using Ollama)
SQLCODER_BASE_URL=http://localhost:11434
SQLCODER_MODEL=sqlcoder-fp16:latest

# ===========================================
# Application Configuration
# ===========================================
DEBUG=false
SHOW_TABLE_LIMIT=100
SHOW_TABLE_SAMPLE_PERCENT=0.0

# ===========================================
# Snowflake Connection Timeouts (Optional)
# ===========================================
SNOWFLAKE_NETWORK_TIMEOUT=60
SNOWFLAKE_LOGIN_TIMEOUT=30
```

## Configuration Examples

### Example 1: Use only Gemini (disable others)
```bash
ENABLE_GROQ=false
ENABLE_GEMINI=true
ENABLE_OLLAMA=false
ENABLE_SQLCODER=false
LLM_PROVIDER=gemini
GOOGLE_API_KEY=your_key
```

### Example 2: Use only local Ollama
```bash
ENABLE_GROQ=false
ENABLE_GEMINI=false
ENABLE_OLLAMA=true
ENABLE_SQLCODER=false
LLM_PROVIDER=ollama
OLLAMA_BASE_URL=http://localhost:11434
```

### Example 3: Auto-select (recommended)
```bash
ENABLE_GROQ=true
ENABLE_GEMINI=true
ENABLE_OLLAMA=true
ENABLE_SQLCODER=true
LLM_PROVIDER=auto
# Configure API keys for cloud providers
# Configure URLs for local providers
```

