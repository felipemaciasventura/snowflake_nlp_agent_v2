# 🔧 Technical Reference - Snowflake NLP Agent v2

This document provides detailed technical implementation information, advanced configuration options, and architectural deep-dive for developers and system administrators.

---

## 📋 Table of Contents

1. [🏗️ System Architecture](#️-system-architecture)
2. [🔧 Advanced Configuration](#-advanced-configuration)
3. [🧠 Enhanced Context System](#-enhanced-context-system)
4. [🤖 LLM Integration Details](#-llm-integration-details)
5. [🗄️ Database Layer](#️-database-layer)
6. [⚡ Performance & Optimization](#-performance--optimization)
7. [🔐 Security Implementation](#-security-implementation)
8. [🐛 Debugging & Troubleshooting](#-debugging--troubleshooting)
9. [📊 Monitoring & Logging](#-monitoring--logging)
10. [🚀 Deployment Guide](#-deployment-guide)

---

## 🏗️ System Architecture

### **Detailed Component Flow**

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                         🌐 STREAMLIT WEB APP                                │
│                          (streamlit_app.py)                                │
├─────────────────────────────────────────────────────────────────────────────┤
│  🎨 UI Components:                                                          │
│  ├─ 💬 Chat Interface (messages, history)                                  │
│  ├─ 📊 Data Display (DataFrames, formatted tables)                         │
│  ├─ 🔧 Sidebar (configuration, connection status)                          │
│  └─ 📋 Logs Panel (process traceability)                                   │
└─────────────────────────────────────────────────────────────────────────────┘
                                    │ user_input
                                    ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                      🧠 NLP AGENT LAYER                                     │
│                   (src/agent/nlp_agent.py)                                 │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  ┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐         │
│  │  🤖 LLM Providers│    │  🔗 LangChain   │    │  📝 SQL Prompts │         │
│  │ (Multi-provider) │◄──►│ SQLDatabaseChain│◄──►│   (English)     │         │
│  └─────────────────┘    └─────────────────┘    └─────────────────┘         │
│                                                                             │
│  Process Flow:                                                              │
│  1️⃣ Receives question in English                                            │
│  2️⃣ Generates SQL using LLM + custom prompt                                │
│  3️⃣ Extracts SQL from intermediate_steps                                   │
│  4️⃣ Executes SQL directly in Snowflake                                     │
│  5️⃣ Logs steps for traceability                                            │
└─────────────────────────────────────────────────────────────────────────────┘
                                    │ sql_query
                                    ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                     🗄️ DATABASE LAYER                                       │
│                 (src/database/snowflake_conn.py)                           │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  ┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐         │
│  │ 🔌 Native       │    │ ⚙️ SQLAlchemy   │    │ 🔍 Schema       │         │
│  │ Connector       │    │    Engine       │    │ Inspector       │         │
│  │                 │    │ (NullPool)      │    │                 │         │
│  └─────────────────┘    └─────────────────┘    └─────────────────┘         │
│                                                                             │
│  Methods:                                                                   │
│  • connect() - Establish connection + validation                            │
│  • execute_query() - SQL → rows + columns                                  │
│  • get_connection_string() - For LangChain                                 │
│  • get_connection_info() - Session metadata                                │
└─────────────────────────────────────────────────────────────────────────────┘
```

### **Design Patterns Implementation**

| Pattern | Implementation | Location |
|---------|---------------|-----------|
| **🔄 Chain of Responsibility** | LangChain SQLDatabaseChain | `nlp_agent.py` |
| **🏭 Factory** | LLM provider selection | `nlp_agent.py` |
| **🔍 Observer** | Logging system integration | All modules |
| **📦 Singleton** | Global config, connection instances | `config.py`, `helpers.py` |
| **🎯 Strategy** | Intelligent formatting by query type | `streamlit_app.py` |
| **🔒 Context Manager** | Database connections (`with` statements) | `snowflake_conn.py` |

---

## 🔧 Advanced Configuration

### **Environment Variables Reference**

#### **Core Snowflake Configuration**
```env
# Required
SNOWFLAKE_ACCOUNT=your-account.region.snowflakecomputing.com
SNOWFLAKE_USER=your-username
SNOWFLAKE_PASSWORD=your-password
SNOWFLAKE_WAREHOUSE=your-warehouse
SNOWFLAKE_DATABASE=your-database

# Optional
SNOWFLAKE_SCHEMA=PUBLIC                    # Default schema
SNOWFLAKE_ROLE=your-role                   # Optional role
SNOWFLAKE_TIMEOUT=30                       # Connection timeout (seconds)
```

#### **LLM Provider Configuration**
```env
# Provider Selection
LLM_PROVIDER=auto                          # auto, groq, gemini, ollama

# Groq Configuration
GROQ_API_KEY=gsk_...
MODEL_NAME=llama-3.3-70b-versatile
GROQ_TIMEOUT=30
GROQ_MAX_RETRIES=3

# Google Gemini Configuration
GOOGLE_API_KEY=AIza...
GEMINI_MODEL=gemini-1.5-flash
GEMINI_TEMPERATURE=0.1
GEMINI_MAX_OUTPUT_TOKENS=4000

# Ollama Configuration
OLLAMA_BASE_URL=http://localhost:11434
OLLAMA_MODEL=codellama:7b-instruct
OLLAMA_TIMEOUT=60
OLLAMA_KEEP_ALIVE=5m
```

#### **Application Configuration**
```env
# Debug and Logging
DEBUG=False                                # Enable debug mode
LOG_LEVEL=INFO                            # DEBUG, INFO, WARNING, ERROR
LOG_FILE=snowflake_nlp.log               # Log file path

# UI Configuration
STREAMLIT_THEME=light                     # light, dark
SHOW_LOGS_PANEL=True                      # Show processing logs
MAX_CHAT_HISTORY=50                       # Maximum chat messages

# Query Configuration
SHOW_TABLE_LIMIT=100                      # Table preview row limit
SHOW_TABLE_SAMPLE_PERCENT=0.0             # Sampling percentage (0.0 = disabled)
MAX_QUERY_EXECUTION_TIME=300              # Maximum query time (seconds)
ENABLE_QUERY_CACHE=True                   # Enable query result caching
```

#### **Enhanced Context Configuration**
```env
# Context System
CONTEXT_CACHE_TTL=3600                    # Context cache TTL (seconds)
MAX_CONTEXT_LENGTH=8000                   # Maximum context tokens
ENABLE_QUERY_HISTORY=True                 # Track query history
MAX_QUERY_HISTORY=100                     # Maximum queries to track

# Schema Analysis
ENABLE_SCHEMA_CACHING=True                # Cache schema information
SCHEMA_CACHE_TTL=7200                     # Schema cache TTL (seconds)
ANALYZE_TABLE_SAMPLES=True                # Analyze table data samples
SAMPLE_SIZE=1000                          # Sample size for analysis
```

### **Custom Prompt Configuration**

#### **External Prompt Files**
```bash
# Place custom prompts in config/ directory
config/
├── sql_prompt_template.txt               # Main prompt template
├── enhanced_sql_prompt.txt               # Enhanced context prompt
├── gemini_sql_prompt.txt                 # Gemini-specific prompt
├── groq_sql_prompt.txt                   # Groq-specific prompt
└── ollama_sql_prompt.txt                 # Ollama-specific prompt
```

#### **Environment-based Prompt Selection**
```env
# Prompt Configuration
SQL_PROMPT_FILE=custom_prompt.txt         # Custom prompt file
DOMAIN_CONTEXT=real_estate                # Domain-specific context
PROMPT_STYLE=detailed                     # concise, detailed, educational
ENABLE_CONTEXT_ENHANCEMENT=True           # Use enhanced context system
```

---

## 🧠 Enhanced Context System

### **System Components**

#### **Schema Inspector (`src/database/schema_inspector.py`)**
```python
class SchemaInspector:
    """Comprehensive database schema analysis"""
    
    def analyze_database(self) -> Dict[str, Any]:
        """
        Analyzes complete database schema including:
        - Table structures and relationships
        - Column metadata and data types
        - Sample data for context
        - Business domain inference
        - Performance characteristics
        """
        
    def get_table_context(self, table_name: str) -> Dict[str, Any]:
        """Get detailed context for specific table"""
        
    def detect_relationships(self) -> List[Dict[str, Any]]:
        """Detect foreign key relationships"""
        
    def analyze_data_patterns(self) -> Dict[str, Any]:
        """Analyze data patterns and business logic"""
```

#### **Query Context Manager (`src/utils/query_context.py`)**
```python
class QueryContextManager:
    """Manages query history and learning"""
    
    def track_query(self, query: str, result: Any, success: bool):
        """Track query execution for learning"""
        
    def get_similar_queries(self, query: str) -> List[Dict[str, Any]]:
        """Find similar successful queries"""
        
    def analyze_query_patterns(self) -> Dict[str, Any]:
        """Analyze successful query patterns"""
        
    def get_optimization_hints(self, query: str) -> List[str]:
        """Get optimization suggestions"""
```

#### **Context Enhancer (`src/utils/context_enhancer.py`)**
```python
class ContextEnhancer:
    """Multi-source context integration"""
    
    def enhance_context(self, base_context: str) -> str:
        """
        Enhances base LangChain context with:
        - Dynamic schema information
        - Query history insights
        - Performance optimization hints
        - Domain-specific knowledge
        """
        
    def validate_context_quality(self, context: str) -> float:
        """Validate context quality score (0-1)"""
        
    def get_domain_insights(self) -> Dict[str, Any]:
        """Get domain-specific insights"""
```

### **Context Generation Flow**

```
🔍 Schema Inspector
    ├─ Analyze table structures
    ├─ Extract column metadata
    ├─ Sample data for context
    └─ Detect relationships
            │
            ▼
📚 Query Context Manager
    ├─ Track query history
    ├─ Analyze success patterns
    ├─ Find similar queries
    └─ Generate optimization hints
            │
            ▼
🎯 Context Enhancer
    ├─ Combine all sources
    ├─ Validate context quality
    ├─ Add domain insights
    └─ Generate final context
            │
            ▼
🤖 LLM with Enhanced Context
```

---

## 🤖 LLM Integration Details

### **Provider Abstraction**

#### **Auto-Detection Logic**
```python
def get_available_llm_provider(self) -> str:
    """
    Auto-detection priority:
    1. Ollama (local-first for privacy)
    2. Gemini (best performance/cost ratio)
    3. Groq (ultra-fast inference)
    """
    
    # Check Ollama availability
    if self._check_ollama_availability():
        return "ollama"
    
    # Check Gemini API key
    if self.GOOGLE_API_KEY:
        return "gemini"
    
    # Check Groq API key
    if self.GROQ_API_KEY:
        return "groq"
    
    raise ValueError("No LLM provider available")
```

#### **Provider-Specific Configurations**

##### **Ollama Configuration**
```python
def setup_ollama(self) -> ChatOllama:
    """Configure Ollama with optimized settings"""
    return ChatOllama(
        base_url=self.OLLAMA_BASE_URL,
        model=self.OLLAMA_MODEL,
        temperature=0.1,
        timeout=60,
        keep_alive="5m",
        # Optimize for SQL generation
        num_predict=1000,
        top_k=20,
        top_p=0.9
    )
```

##### **Gemini Configuration**
```python
def setup_gemini(self) -> ChatGoogleGenerativeAI:
    """Configure Gemini with optimized settings"""
    return ChatGoogleGenerativeAI(
        google_api_key=self.GOOGLE_API_KEY,
        model=self.GEMINI_MODEL,
        temperature=0.1,
        max_output_tokens=4000,
        # Safety settings for SQL
        safety_settings={
            HarmCategory.HARM_CATEGORY_DANGEROUS_CONTENT: HarmBlockThreshold.BLOCK_NONE
        }
    )
```

##### **Groq Configuration**
```python
def setup_groq(self) -> ChatGroq:
    """Configure Groq with optimized settings"""
    return ChatGroq(
        groq_api_key=self.GROQ_API_KEY,
        model_name=self.MODEL_NAME,
        temperature=0.1,
        max_tokens=4000,
        max_retries=3,
        request_timeout=30
    )
```

### **SQL Response Cleaning**

#### **Advanced Cleaning Pipeline**
```python
def clean_sql_response(self, response: str) -> str:
    """
    Comprehensive SQL cleaning for multiple LLM formats:
    - Remove markdown code blocks
    - Extract SQL from explanatory text
    - Normalize whitespace and formatting
    - Validate SQL syntax
    """
    
    # Remove markdown code blocks
    response = re.sub(r'```sql\s*\n', '', response, flags=re.IGNORECASE)
    response = re.sub(r'```\s*$', '', response, flags=re.MULTILINE)
    
    # Extract SQL from mixed content
    sql_patterns = [
        r'(?:SELECT|WITH|INSERT|UPDATE|DELETE|CREATE|DROP|ALTER)\b.*?(?=\n\n|\Z)',
        r'(?:select|with|insert|update|delete|create|drop|alter)\b.*?(?=\n\n|\Z)'
    ]
    
    for pattern in sql_patterns:
        matches = re.findall(pattern, response, re.DOTALL | re.IGNORECASE)
        if matches:
            response = matches[0].strip()
            break
    
    # Normalize and validate
    response = self._normalize_sql(response)
    response = self._validate_sql_syntax(response)
    
    return response
```

---

## 🗄️ Database Layer

### **Connection Management**

#### **Snowflake Connection Class**
```python
class SnowflakeConnection:
    """Enhanced Snowflake connection with pooling and optimization"""
    
    def __init__(self):
        self.connection = None
        self.engine = None
        self.is_connected = False
        self._connection_pool = None
        
    def connect(self) -> bool:
        """
        Establish optimized connection:
        - Validate configuration
        - Create SQLAlchemy engine with NullPool
        - Test connection with simple query
        - Initialize connection metadata
        """
        
    def execute_query(self, sql: str) -> Tuple[List[Any], List[str]]:
        """
        Execute SQL with error handling:
        - Parameter validation
        - Query timeout management
        - Result set optimization
        - Connection recovery
        """
        
    def get_connection_info(self) -> Dict[str, Any]:
        """Get comprehensive connection metadata"""
        return {
            'account': self.config.SNOWFLAKE_ACCOUNT,
            'database': self.current_database(),
            'schema': self.current_schema(),
            'warehouse': self.current_warehouse(),
            'role': self.current_role(),
            'session_id': self.session_id(),
            'connection_time': self.connection_time
        }
```

#### **Connection Optimization**
```python
def create_optimized_engine(self) -> Engine:
    """Create SQLAlchemy engine with optimization"""
    
    connection_params = {
        'account': self.config.SNOWFLAKE_ACCOUNT,
        'user': self.config.SNOWFLAKE_USER,
        'password': self.config.SNOWFLAKE_PASSWORD,
        'warehouse': self.config.SNOWFLAKE_WAREHOUSE,
        'database': self.config.SNOWFLAKE_DATABASE,
        'schema': self.config.SNOWFLAKE_SCHEMA,
        
        # Performance optimizations
        'paramstyle': 'qmark',
        'timezone': 'UTC',
        'client_session_keep_alive': True,
        'client_prefetch_threads': 4,
        'client_result_chunk_size': 1024,
        
        # Security settings
        'insecure_mode': False,
        'ocsp_response_cache_filename': None
    }
    
    return create_engine(
        URL(**connection_params),
        poolclass=NullPool,  # Avoid connection pooling issues
        echo=self.config.DEBUG,
        future=True
    )
```

### **Query Execution Pipeline**

#### **Query Validation**
```python
def validate_query(self, sql: str) -> Dict[str, Any]:
    """
    Comprehensive query validation:
    - SQL syntax validation
    - Security checks (injection prevention)
    - Performance analysis
    - Resource estimation
    """
    
    validation_result = {
        'is_valid': True,
        'errors': [],
        'warnings': [],
        'estimated_cost': None,
        'estimated_time': None
    }
    
    # Syntax validation
    try:
        parsed = sqlparse.parse(sql)[0]
        validation_result['parsed_tokens'] = len(parsed.tokens)
    except Exception as e:
        validation_result['is_valid'] = False
        validation_result['errors'].append(f"Syntax error: {e}")
    
    # Security checks
    if self._detect_sql_injection(sql):
        validation_result['is_valid'] = False
        validation_result['errors'].append("Potential SQL injection detected")
    
    # Performance analysis
    if self._analyze_query_complexity(sql) > 0.8:
        validation_result['warnings'].append("Complex query detected - may take time")
    
    return validation_result
```

---

## ⚡ Performance & Optimization

### **Query Optimization**

#### **Automatic Query Enhancement**
```python
def optimize_query(self, sql: str) -> str:
    """
    Automatic query optimization:
    - Add appropriate LIMIT clauses
    - Optimize JOIN conditions
    - Add performance hints
    - Cache-friendly modifications
    """
    
    # Parse SQL
    parsed = sqlparse.parse(sql)[0]
    
    # Add LIMIT if not present
    if not self._has_limit_clause(parsed):
        sql = self._add_smart_limit(sql)
    
    # Optimize JOINs
    sql = self._optimize_joins(sql)
    
    # Add query hints for Snowflake
    sql = self._add_snowflake_hints(sql)
    
    return sql

def _add_smart_limit(self, sql: str) -> str:
    """Add intelligent LIMIT based on query type"""
    
    # Different limits for different query types
    limits = {
        'exploratory': 100,
        'aggregation': 1000,
        'detailed': 50
    }
    
    query_type = self._classify_query_type(sql)
    limit = limits.get(query_type, 100)
    
    return f"{sql.rstrip(';')} LIMIT {limit};"
```

#### **Result Set Optimization**
```python
def optimize_result_processing(self, results: List[Any]) -> List[Any]:
    """
    Optimize result processing:
    - Efficient data type conversion
    - Memory-optimized iteration
    - Lazy loading for large results
    """
    
    if len(results) > 10000:
        # Use generator for large result sets
        return self._process_large_results(results)
    else:
        # Standard processing for small results
        return self._process_standard_results(results)
```

### **Caching Strategy**

#### **Multi-Level Caching**
```python
class CacheManager:
    """Multi-level caching for performance optimization"""
    
    def __init__(self):
        self.schema_cache = {}      # Schema information cache
        self.query_cache = {}       # Query result cache
        self.context_cache = {}     # Context cache
        
    def get_cached_schema(self, database: str) -> Optional[Dict]:
        """Get cached schema information"""
        
    def cache_query_result(self, sql_hash: str, result: Any, ttl: int = 3600):
        """Cache query results with TTL"""
        
    def get_cached_context(self, context_key: str) -> Optional[str]:
        """Get cached enhanced context"""
```

---

## 🔐 Security Implementation

### **Input Validation & Sanitization**

#### **SQL Injection Prevention**
```python
def validate_sql_security(self, sql: str) -> Dict[str, Any]:
    """
    Comprehensive SQL security validation:
    - SQL injection pattern detection
    - Dangerous function blocking
    - Schema access control
    - Query complexity limits
    """
    
    security_result = {
        'is_safe': True,
        'threats': [],
        'blocked_patterns': []
    }
    
    # Check for SQL injection patterns
    injection_patterns = [
        r"(?i)union\s+select",
        r"(?i)drop\s+table",
        r"(?i)delete\s+from",
        r"(?i)insert\s+into",
        r"(?i)update\s+\w+\s+set",
        r"(?i)exec\s*\(",
        r"(?i)xp_cmdshell",
        r"(?i)sp_executesql"
    ]
    
    for pattern in injection_patterns:
        if re.search(pattern, sql):
            security_result['is_safe'] = False
            security_result['threats'].append(f"Potential injection: {pattern}")
    
    return security_result
```

#### **Access Control**
```python
def validate_schema_access(self, sql: str) -> bool:
    """
    Validate schema access permissions:
    - Check table access rights
    - Validate schema boundaries
    - Enforce data access policies
    """
    
    # Extract table references
    tables = self._extract_table_references(sql)
    
    # Check access permissions
    for table in tables:
        if not self._has_table_access(table):
            return False
    
    return True
```

### **Credential Management**

#### **Environment Variable Security**
```python
def validate_credentials(self) -> Dict[str, bool]:
    """
    Validate all credential requirements:
    - Snowflake connection parameters
    - LLM API keys
    - Optional service credentials
    """
    
    validation = {
        'snowflake': self._validate_snowflake_creds(),
        'groq': self._validate_groq_creds(),
        'gemini': self._validate_gemini_creds(),
        'ollama': self._validate_ollama_creds()
    }
    
    return validation

def _validate_snowflake_creds(self) -> bool:
    """Validate Snowflake credentials without connecting"""
    required_fields = [
        'SNOWFLAKE_ACCOUNT',
        'SNOWFLAKE_USER',
        'SNOWFLAKE_PASSWORD',
        'SNOWFLAKE_WAREHOUSE',
        'SNOWFLAKE_DATABASE'
    ]
    
    return all(getattr(self, field) for field in required_fields)
```

---

## 🐛 Debugging & Troubleshooting

### **Debug Mode Configuration**

#### **Enhanced Logging**
```python
def setup_debug_logging(self):
    """Configure comprehensive debug logging"""
    
    if self.config.DEBUG:
        logging.basicConfig(
            level=logging.DEBUG,
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            handlers=[
                logging.FileHandler('debug.log'),
                logging.StreamHandler()
            ]
        )
        
        # Enable SQLAlchemy query logging
        logging.getLogger('sqlalchemy.engine').setLevel(logging.INFO)
        
        # Enable LangChain debugging
        os.environ['LANGCHAIN_VERBOSE'] = 'true'
```

#### **Error Tracking**
```python
def track_error(self, error: Exception, context: Dict[str, Any]):
    """
    Comprehensive error tracking:
    - Error classification
    - Context preservation
    - Stack trace analysis
    - Recovery suggestions
    """
    
    error_info = {
        'timestamp': datetime.utcnow().isoformat(),
        'error_type': type(error).__name__,
        'error_message': str(error),
        'context': context,
        'stack_trace': traceback.format_exc(),
        'recovery_suggestions': self._generate_recovery_suggestions(error)
    }
    
    self.error_log.append(error_info)
    
    if self.config.DEBUG:
        self._display_error_details(error_info)
```

### **Common Issues & Solutions**

#### **Connection Issues**
```python
def diagnose_connection_issues(self) -> Dict[str, Any]:
    """
    Diagnose common connection problems:
    - Network connectivity
    - Credential validation
    - Snowflake service status
    - Configuration errors
    """
    
    diagnosis = {
        'network': self._test_network_connectivity(),
        'credentials': self._validate_credentials(),
        'snowflake_status': self._check_snowflake_status(),
        'configuration': self._validate_configuration()
    }
    
    return diagnosis
```

#### **LLM Provider Issues**
```python
def diagnose_llm_issues(self) -> Dict[str, Any]:
    """
    Diagnose LLM provider problems:
    - API key validation
    - Service availability
    - Rate limiting
    - Model availability
    """
    
    diagnosis = {}
    
    for provider in ['groq', 'gemini', 'ollama']:
        diagnosis[provider] = {
            'available': self._check_provider_availability(provider),
            'api_key_valid': self._validate_provider_key(provider),
            'rate_limit_status': self._check_rate_limits(provider),
            'model_accessible': self._check_model_access(provider)
        }
    
    return diagnosis
```

---

## 📊 Monitoring & Logging

### **Application Metrics**

#### **Performance Metrics**
```python
class MetricsCollector:
    """Collect and track application performance metrics"""
    
    def __init__(self):
        self.query_times = []
        self.llm_response_times = []
        self.error_rates = {}
        self.usage_statistics = {}
    
    def track_query_performance(self, sql: str, execution_time: float):
        """Track query execution performance"""
        
    def track_llm_performance(self, provider: str, response_time: float):
        """Track LLM response performance"""
        
    def generate_performance_report(self) -> Dict[str, Any]:
        """Generate comprehensive performance report"""
```

#### **Usage Analytics**
```python
def track_usage_analytics(self):
    """
    Track application usage:
    - Query patterns
    - User interactions
    - Feature utilization
    - Error frequency
    """
    
    analytics = {
        'total_queries': len(self.query_history),
        'successful_queries': len([q for q in self.query_history if q['success']]),
        'average_response_time': self._calculate_avg_response_time(),
        'most_used_features': self._analyze_feature_usage(),
        'error_patterns': self._analyze_error_patterns()
    }
    
    return analytics
```

### **Log Management**

#### **Structured Logging**
```python
def setup_structured_logging(self):
    """Configure structured JSON logging"""
    
    formatter = StructuredFormatter()
    
    handlers = [
        RotatingFileHandler(
            'logs/application.log',
            maxBytes=10485760,  # 10MB
            backupCount=5
        ),
        StreamHandler()
    ]
    
    for handler in handlers:
        handler.setFormatter(formatter)
        self.logger.addHandler(handler)

class StructuredFormatter(logging.Formatter):
    """JSON formatter for structured logging"""
    
    def format(self, record):
        log_entry = {
            'timestamp': datetime.utcnow().isoformat(),
            'level': record.levelname,
            'module': record.module,
            'message': record.getMessage(),
            'extra': getattr(record, 'extra', {})
        }
        
        return json.dumps(log_entry)
```

---

## 🚀 Deployment Guide

### **Production Configuration**

#### **Environment Setup**
```bash
# Production environment variables
export ENVIRONMENT=production
export DEBUG=False
export LOG_LEVEL=WARNING

# Security configurations
export SSL_VERIFY=True
export SNOWFLAKE_SECURE_CONNECTION=True
export API_RATE_LIMIT=100

# Performance configurations
export CONNECTION_POOL_SIZE=10
export QUERY_TIMEOUT=300
export CACHE_TTL=3600
```

#### **Docker Deployment**
```dockerfile
# Dockerfile
FROM python:3.11-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    build-essential \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements and install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Create non-root user
RUN useradd -m -u 1000 appuser && chown -R appuser:appuser /app
USER appuser

# Expose port
EXPOSE 8501

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8501/_stcore/health || exit 1

# Start application
CMD ["streamlit", "run", "streamlit_app.py", "--server.port=8501", "--server.address=0.0.0.0"]
```

#### **Kubernetes Deployment**
```yaml
# k8s-deployment.yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: snowflake-nlp-agent
spec:
  replicas: 3
  selector:
    matchLabels:
      app: snowflake-nlp-agent
  template:
    metadata:
      labels:
        app: snowflake-nlp-agent
    spec:
      containers:
      - name: app
        image: snowflake-nlp-agent:latest
        ports:
        - containerPort: 8501
        env:
        - name: ENVIRONMENT
          value: "production"
        - name: SNOWFLAKE_ACCOUNT
          valueFrom:
            secretKeyRef:
              name: snowflake-credentials
              key: account
        resources:
          requests:
            memory: "512Mi"
            cpu: "250m"
          limits:
            memory: "1Gi"
            cpu: "500m"
        livenessProbe:
          httpGet:
            path: /_stcore/health
            port: 8501
          initialDelaySeconds: 30
          periodSeconds: 30
        readinessProbe:
          httpGet:
            path: /_stcore/health
            port: 8501
          initialDelaySeconds: 5
          periodSeconds: 10
```

### **Monitoring & Alerting**

#### **Health Checks**
```python
def health_check() -> Dict[str, Any]:
    """
    Comprehensive health check:
    - Database connectivity
    - LLM provider availability
    - System resources
    - Application status
    """
    
    health_status = {
        'timestamp': datetime.utcnow().isoformat(),
        'status': 'healthy',
        'checks': {}
    }
    
    # Database health
    try:
        self.db.execute_query("SELECT 1")
        health_status['checks']['database'] = 'healthy'
    except Exception as e:
        health_status['checks']['database'] = f'unhealthy: {e}'
        health_status['status'] = 'unhealthy'
    
    # LLM provider health
    for provider in ['groq', 'gemini', 'ollama']:
        health_status['checks'][f'llm_{provider}'] = self._check_llm_health(provider)
    
    # System resources
    health_status['checks']['memory'] = self._check_memory_usage()
    health_status['checks']['cpu'] = self._check_cpu_usage()
    
    return health_status
```

#### **Performance Monitoring**
```python
def setup_performance_monitoring(self):
    """
    Setup comprehensive performance monitoring:
    - Response time tracking
    - Error rate monitoring
    - Resource utilization
    - Custom metrics
    """
    
    # Prometheus metrics (if available)
    try:
        from prometheus_client import Counter, Histogram, Gauge
        
        self.query_counter = Counter('queries_total', 'Total queries', ['provider', 'status'])
        self.response_time = Histogram('response_time_seconds', 'Response time')
        self.active_connections = Gauge('active_connections', 'Active connections')
        
    except ImportError:
        self.logger.warning("Prometheus client not available - using basic metrics")
        self._setup_basic_metrics()
```

---

**This technical reference provides comprehensive implementation details for advanced users, system administrators, and developers working with the Snowflake NLP Agent v2 system.**