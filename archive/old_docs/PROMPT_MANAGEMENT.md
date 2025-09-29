# 🎯 Prompt Management Guide

## 📋 **Overview**

The Snowflake NLP Agent now supports multiple ways to manage AI prompts without exposing them directly in the code. This provides better maintainability, security, and customization options.

---

## 🛠️ **Available Options**

### **Option 1: External Files (Recommended)**
```
config/sql_prompt_template.txt    # Main prompt template
config/gemini_sql_prompt.txt      # Gemini-specific prompt
config/groq_sql_prompt.txt        # Groq-specific prompt  
config/ollama_sql_prompt.txt      # Ollama-specific prompt
```

### **Option 2: Python Modules**
```python
# src/prompts/sql_prompts.py
from src.prompts.sql_prompts import get_prompt_for_provider
prompt = get_prompt_for_provider("gemini")
```

### **Option 3: Environment Variables**
```bash
# .env file
SQL_PROMPT_FILE=my_custom_prompt.txt
DOMAIN_CONTEXT=real_estate
PROMPT_STYLE=detailed
```

---

## 🔧 **How to Use**

### **Method 1: Create Custom Prompt File**

1. **Create prompt file:**
```bash
# Create config directory
mkdir -p config

# Create your custom prompt
nano config/my_custom_prompt.txt
```

2. **Write your prompt:**
```text
You are a SQL expert for {domain}.

DATABASE INFORMATION:
{table_info}

Question: {input}

Rules:
1. Generate SQL only
2. No explanations
3. Use LIMIT 10

SQL:
```

3. **Use in environment:**
```bash
# .env
SQL_PROMPT_FILE=my_custom_prompt.txt
```

### **Method 2: Provider-Specific Prompts**

Create different prompts for different AI models:

```bash
# For Gemini (detailed)
config/gemini_sql_prompt.txt

# For Groq (concise) 
config/groq_sql_prompt.txt

# For Ollama (simple)
config/ollama_sql_prompt.txt
```

The system automatically selects the right prompt based on your `LLM_PROVIDER` setting.

### **Method 3: Programmatic Usage**

```python
from src.utils.prompt_loader import prompt_loader

# Load specific prompt
prompt = prompt_loader.get_sql_prompt("gemini")

# Load from specific file
custom_prompt = prompt_loader.load_prompt_from_file("my_prompt.txt")

# List available prompts
available = prompt_loader.list_available_prompts()
```

---

## 📁 **File Structure**

```
project/
├── config/                          # External prompt files
│   ├── sql_prompt_template.txt     # Default template
│   ├── gemini_sql_prompt.txt       # Gemini-specific
│   └── custom_domain_prompt.txt    # Your custom prompts
├── src/
│   ├── prompts/
│   │   └── sql_prompts.py          # Python prompt definitions
│   └── utils/
│       └── prompt_loader.py        # Prompt loading utility
└── .env                            # Environment configuration
```

---

## ⚙️ **Configuration Options**

### **Environment Variables**

| Variable | Description | Default |
|----------|-------------|---------|
| `SQL_PROMPT_FILE` | Custom prompt filename | `sql_prompt_template.txt` |
| `DOMAIN_CONTEXT` | Domain for prompts | `real_estate` |
| `PROMPT_STYLE` | Style: detailed/concise/minimal | `detailed` |

### **Domain Contexts**

| Domain | Description | Key Tables |
|--------|-------------|------------|
| `real_estate` | Real estate database | Properties, Agents, Transactions |
| `sales` | Sales/CRM database | Customers, Orders, Products |
| `generic` | Any database | Auto-detected tables |

---

## 🎨 **Prompt Templates**

### **Template Variables**
- `{table_info}` - Database schema information
- `{input}` - User's natural language question

### **Example Minimal Prompt:**
```text
You are a SQL expert. Generate clean SQL queries.

DATABASE INFORMATION:
{table_info}

Question: {input}

Generate SQL only, no explanations.
```

### **Example Detailed Prompt:**
```text
You are a Snowflake SQL expert specialized in real estate.

DATABASE INFORMATION:
{table_info}

CONTEXT: Real estate database with properties, agents, and transactions.

Question: {input}

RULES:
1. Generate ONLY pure SQL
2. No markdown or explanations
3. Use LIMIT 10 for SELECT queries
4. Use CURRENT_DATABASE() for database info

SQL:
```

---

## 🚀 **Benefits**

### **✅ Code Cleanliness**
- Prompts separated from business logic
- Easier code reviews and maintenance
- Cleaner git diffs

### **✅ Security**
- No sensitive prompts in code
- External file management
- Environment-based configuration

### **✅ Flexibility**
- Easy prompt updates without code changes
- Provider-specific optimizations
- Domain-specific customization

### **✅ Maintainability**
- Version control for prompts
- A/B testing capabilities
- Easy rollbacks

---

## 🧪 **Testing Different Prompts**

### **Quick Test:**
```bash
# Test with custom prompt
SQL_PROMPT_FILE=test_prompt.txt streamlit run streamlit_app.py

# Test with different domain
DOMAIN_CONTEXT=sales streamlit run streamlit_app.py

# Test with minimal style
PROMPT_STYLE=minimal streamlit run streamlit_app.py
```

### **Compare Results:**
1. Create different prompt versions
2. Test with same queries
3. Compare AI response quality
4. Choose best performing prompt

---

## 📊 **Migration Guide**

### **From Inline Prompts:**

**Before:**
```python
sql_prompt = """Long prompt text here..."""
```

**After:**
```python
sql_prompt = prompt_loader.get_sql_prompt(provider)
```

### **Steps:**
1. Move existing prompt to `config/sql_prompt_template.txt`
2. Update agent code to use `prompt_loader`
3. Test functionality
4. Customize as needed

---

## 🎯 **Best Practices**

1. **Version Control**: Keep prompt files in git
2. **Testing**: Test prompts with various query types
3. **Documentation**: Document prompt changes
4. **Backup**: Keep working prompts as backups
5. **Monitoring**: Monitor AI response quality

---

*This approach provides professional prompt management while maintaining code cleanliness and security.*