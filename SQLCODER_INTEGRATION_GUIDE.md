# SQLCoder Integration Guide

## 🎯 SQLCoder-fp16 LLM Integration

This document describes the integration of SQLCoder-fp16, a specialized SQL generation model, into the Snowflake NLP Agent.

### 🔧 Configuration

#### Environment Variables
Add these variables to your `.env` file:

```bash
# SQLCoder (specialized SQL model)
SQLCODER_BASE_URL=http://192.168.0.145:11434
SQLCODER_MODEL=sqlcoder-fp16:latest

# Set as primary provider
LLM_PROVIDER=sqlcoder
```

#### Provider Priority
When `LLM_PROVIDER=auto`, the detection priority is:
1. **SQLCoder** (specialized first)
2. **Ollama** (local general)
3. **Gemini** (cloud)
4. **Groq** (cloud)

### 🎯 Benefits of SQLCoder

#### Why SQLCoder?
- **🎯 SQL Specialized**: Trained specifically for SQL generation
- **🏠 Local Privacy**: Runs on your local network (192.168.0.145)
- **⚡ High Performance**: Optimized for SQL accuracy and speed
- **🔒 Zero Cost**: No API charges or token limits
- **📚 Context Aware**: Better understanding of database schemas

#### Optimized Features
- **Temperature 0.0**: More deterministic SQL generation
- **Specialized Prompts**: Tailored for SQL-specific instructions
- **Enhanced Validation**: Better SQL syntax and structure
- **Schema Understanding**: Improved table and column recognition

### 🚀 Usage

#### Automatic Detection
The system will automatically detect and use SQLCoder if:
- SQLCoder server is running on 192.168.0.145:11434
- Model `sqlcoder-fp16:latest` is available
- `LLM_PROVIDER=auto` or `LLM_PROVIDER=sqlcoder`

#### Manual Selection
You can force SQLCoder usage by setting:
```bash
LLM_PROVIDER=sqlcoder
```

#### UI Indicators
When SQLCoder is active, you'll see:
- 🎯 "SQL Specialized Model Active" in sidebar
- "LLM in use: SQLCoder (sqlcoder-fp16:latest) - SQL Specialized" message
- Server information showing 192.168.0.145:11434

### 🔧 Technical Details

#### Network Configuration
- **Server IP**: 192.168.0.145
- **Port**: 11434 (Ollama API compatible)
- **Protocol**: HTTP REST API
- **Timeout**: 3 seconds for availability check

#### Model Specifications
- **Model**: sqlcoder-fp16:latest
- **Type**: Specialized SQL generation
- **Format**: FP16 for optimized performance
- **API**: Ollama-compatible interface

#### Integration Method
SQLCoder integrates through the existing Ollama interface:
```python
self.llm = ChatOllama(
    base_url=config.SQLCODER_BASE_URL,
    model=config.SQLCODER_MODEL,
    temperature=0.0,  # Deterministic for SQL
)
```

### 🧪 Testing

#### Verify Connection
1. Check that SQLCoder appears in LLM selector
2. Verify "SQL Specialized Model Active" status
3. Test with simple query: "Show me all tables"
4. Confirm SQL generation and execution

#### Expected Improvements
- **Better SQL Syntax**: More accurate Snowflake SQL
- **Improved Schema Understanding**: Better table/column recognition
- **Reduced Errors**: Fewer syntax and semantic mistakes
- **Faster Processing**: Optimized for SQL generation speed

### 🔍 Troubleshooting

#### Common Issues
1. **"sqlcoder" not in provider list**
   - Check SQLCoder server is running on 192.168.0.145:11434
   - Verify network connectivity
   - Confirm model is loaded

2. **Connection timeout**
   - Check firewall settings
   - Verify IP address and port
   - Test with `curl http://192.168.0.145:11434/api/tags`

3. **Model not found**
   - Confirm model name: `sqlcoder-fp16:latest`
   - Check model is pulled and available
   - Verify Ollama server status

#### Debugging Commands
```bash
# Test connectivity
curl http://192.168.0.145:11434/api/tags

# Check model availability
curl http://192.168.0.145:11434/api/show -d '{"name": "sqlcoder-fp16:latest"}'
```

### 📊 Performance Comparison

| Model | Specialization | Location | SQL Accuracy | Response Time |
|-------|---------------|----------|--------------|---------------|
| **SQLCoder** | 🎯 SQL Expert | Local | ⭐⭐⭐⭐⭐ | ⚡ Fast |
| Ollama | 🏠 General | Local | ⭐⭐⭐ | ⚡ Fast |
| Gemini | ☁️ General | Cloud | ⭐⭐⭐⭐ | 🚀 Very Fast |
| Groq | ☁️ General | Cloud | ⭐⭐⭐⭐ | 🚀 Ultra Fast |

### 🎯 Best Practices

#### When to Use SQLCoder
- **Complex SQL queries** requiring high accuracy
- **Schema-heavy operations** with multiple joins
- **Production environments** requiring consistent results
- **Privacy-sensitive** data processing

#### Configuration Tips
- Set `LLM_PROVIDER=sqlcoder` for guaranteed usage
- Use `temperature=0.0` for maximum determinism
- Monitor server resources for optimal performance
- Keep model updated for best results

---

**SQLCoder integration provides specialized SQL generation capabilities while maintaining the flexibility of the existing multi-LLM architecture.**