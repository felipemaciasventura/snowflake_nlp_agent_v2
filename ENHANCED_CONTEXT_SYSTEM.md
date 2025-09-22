# 🧠 Enhanced Context System for LLM SQL Generation

This document describes the comprehensive **Enhanced Context System** implemented to dramatically improve SQL query generation quality by providing rich, dynamic context to the LLM.

## 🎯 **Problem Solved**

The original system relied on basic static schema information, leading to:
- **Limited schema awareness** - Only basic table/column names
- **No learning from history** - Each query was independent 
- **Generic prompts** - No domain-specific context
- **Poor query optimization** - No performance insights
- **No context quality validation** - No way to assess context reliability

## ✨ **Enhanced Context System Architecture**

### 📊 **Core Components**

```
🏗️ Enhanced Context System
├── 🔍 Schema Inspector (Dynamic)
│   ├── Comprehensive table analysis
│   ├── Column metadata with samples
│   ├── Relationship detection
│   ├── Business domain inference
│   └── Performance characteristics
│
├── 📚 Query Context Manager (Learning)
│   ├── Query history tracking
│   ├── Success pattern analysis
│   ├── Similar query detection
│   ├── Performance metrics
│   └── Domain vocabulary building
│
├── 🧠 Context Enhancer (Integration)
│   ├── Multi-source context fusion
│   ├── Domain insights generation
│   ├── Quality assessment
│   ├── Adaptive prompt generation
│   └── Context-aware recommendations
│
└── ✅ Context Validator (Quality Assurance)
    ├── Schema context validation
    ├── Query history validation
    ├── Domain insights validation
    └── Overall quality scoring
```

## 🚀 **Key Features Implemented**

### 1. **Dynamic Schema Inspector** (`schema_inspector.py`)

**Advanced Schema Discovery:**
- ✅ **Complete table metadata** - Names, types, comments, row counts
- ✅ **Detailed column information** - Data types, nullability, constraints, sample values
- ✅ **Relationship detection** - Foreign keys + inferred relationships
- ✅ **Business domain inference** - Automatic domain classification
- ✅ **Performance analysis** - Large table detection, indexing info
- ✅ **Schema caching** - 24-hour TTL for performance

**Usage Example:**
```python
from src.database.schema_inspector import get_schema_inspector

inspector = get_schema_inspector(connection)
context = inspector.get_comprehensive_context(
    refresh_cache=False,
    include_samples=True,
    max_sample_size=10
)
```

### 2. **Query Context Manager** (`query_context.py`)

**Intelligent Learning System:**
- ✅ **Query pattern storage** - Success/failure tracking with scores
- ✅ **Similar query detection** - Text similarity + pattern matching
- ✅ **Success pattern analysis** - Common functions, patterns, structures
- ✅ **Performance tracking** - Execution times, result counts
- ✅ **Domain vocabulary building** - Learn from successful queries
- ✅ **Context-aware suggestions** - Table usage patterns

**Usage Example:**
```python
from src.utils.query_context import query_context_manager

# Record query execution
query_context_manager.record_query(
    user_question="Show me top customers",
    generated_sql="SELECT name, total FROM customers ORDER BY total DESC LIMIT 10",
    success=True,
    execution_time=1.2,
    result_count=10
)

# Get context for new query
context = query_context_manager.get_context_for_question("Who are the best customers?")
```

### 3. **Enhanced Context System** (`context_enhancer.py`)

**Comprehensive Context Integration:**
- ✅ **Multi-source fusion** - Combines schema + history + domain insights
- ✅ **Intent detection** - Understands what user wants to accomplish
- ✅ **Table/column suggestions** - Smart relevance matching
- ✅ **Complexity estimation** - Simple/medium/complex query classification
- ✅ **Performance optimization** - Hints based on table sizes and patterns
- ✅ **Quality scoring** - 0.0-1.0 context confidence score
- ✅ **Adaptive prompts** - Context-aware prompt generation

**Enhanced Context Structure:**
```python
@dataclass
class EnhancedContext:
    database_context: DatabaseContext       # Schema information
    query_context: QueryContext           # Historical patterns
    domain_insights: Dict[str, Any]       # Intent, suggestions, hints
    context_quality_score: float          # Quality assessment
    recommended_approach: str             # Generation strategy
    warning_messages: List[str]           # Context limitations
```

### 4. **Context Validator** (`context_validator.py`)

**Quality Assurance System:**
- ✅ **Schema validation** - Table/column completeness, relationships
- ✅ **History validation** - Query quality, recency, patterns
- ✅ **Domain validation** - Intent detection, suggestions quality
- ✅ **Overall scoring** - Weighted quality assessment
- ✅ **Warning generation** - Context limitations and issues
- ✅ **Recommendations** - Improvement suggestions

## 🔧 **Integration with NLP Agent**

The enhanced context system is integrated into the main NLP agent (`nlp_agent.py`) with backward compatibility:

```python
def process_query(self, user_question: str, use_enhanced_context: bool = True) -> Dict[str, Any]:
    # Enhanced flow:
    # 1. Get comprehensive context (schema + history + insights)
    # 2. Generate context-aware prompt
    # 3. Execute with enhanced LLM chain
    # 4. Record execution for learning
    # 5. Return enriched results
```

## 📈 **Context Quality Scoring**

The system provides a comprehensive **0.0-1.0 quality score** based on:

| Component | Weight | Factors |
|-----------|--------|---------|
| **Schema Context** | 40% | Table count, column details, relationships, domain detection |
| **Query History** | 30% | Similar queries, success patterns, recency |
| **Domain Insights** | 20% | Intent detection, table suggestions, performance hints |
| **Completeness** | 10% | Overall context availability and integration |

**Quality Levels:**
- **🌟 Excellent (0.9+)**: High-confidence generation with rich context
- **👍 Good (0.7-0.9)**: Solid context with some historical data
- **⚖️ Fair (0.5-0.7)**: Limited context, conservative approach
- **⚠️ Poor (0.3-0.5)**: Minimal context, basic structure only
- **❌ Inadequate (<0.3)**: Insufficient context for reliable generation

## 🎯 **Domain-Specific Features**

### **Intent Detection**
The system automatically detects query intent:
- **📊 Aggregation**: COUNT, SUM, AVG queries
- **🏆 Ranking**: TOP, HIGHEST, BEST queries  
- **🔍 Filtering**: WHERE, WITH conditions
- **📈 Comparison**: Comparative analysis
- **⏰ Temporal**: Time-based queries
- **📋 Listing**: Simple data retrieval
- **🔍 Exploration**: General investigation

### **Smart Table/Column Suggestions**
Uses multiple signals for relevance:
- **Direct name matching** - Question words ↔ table/column names
- **Data type relevance** - Price queries → DECIMAL columns
- **Comment analysis** - Table descriptions and metadata
- **Historical success** - Previously successful combinations
- **Domain vocabulary** - Learned terminology

### **Performance Optimization Hints**
Provides actionable recommendations:
- **Large table handling** - LIMIT clauses, WHERE conditions
- **Join optimization** - Proper join conditions, aliases
- **Query patterns** - Successful structural patterns
- **Index awareness** - Performance-optimized approaches

## 🏃‍♂️ **Usage Examples**

### **Basic Enhanced Query Processing**
```python
# Initialize agent with enhanced context
agent = SnowflakeNLPAgent(db_connection)

# Process query with full context enhancement  
result = agent.process_query(
    "What are the top 10 most expensive properties?",
    use_enhanced_context=True
)

# Check context quality
print(f"Context quality: {result.get('context_quality', 'N/A')}")
print(f"Suggested tables: {result.get('suggested_tables', [])}")
```

### **Manual Context Analysis**
```python
from src.utils.context_enhancer import get_context_enhancer

enhancer = get_context_enhancer(connection)

# Get enhanced context
context = enhancer.get_enhanced_context(
    user_question="Show me sales by region",
    refresh_schema=False,
    include_samples=True,
    include_history=True
)

# Generate enhanced prompt
prompt = enhancer.generate_enhanced_prompt(
    user_question="Show me sales by region",
    base_prompt=base_template,
    enhanced_context=context
)
```

### **Context Validation**
```python
from src.utils.context_validator import context_validator

# Validate context quality
validation = context_validator.validate_enhanced_context(context)

print(f"Valid: {validation.is_valid}")
print(f"Score: {validation.score:.2f}")
print(f"Warnings: {validation.warnings}")
print(f"Recommendations: {validation.recommendations}")

# Get detailed report
report = context_validator.generate_validation_report(validation)
print(report)
```

## 📊 **Performance Impact**

### **Benefits**
- ✅ **Improved accuracy** - Context-aware SQL generation
- ✅ **Better performance** - Optimized queries with hints
- ✅ **Learning capability** - Continuous improvement from history
- ✅ **Domain adaptation** - Automatic domain-specific optimization
- ✅ **Quality assurance** - Validation and confidence scoring

### **Overhead**
- ⏱️ **Initial schema scan**: ~2-5 seconds (cached for 24 hours)
- ⏱️ **Context generation**: ~100-500ms per query
- ⏱️ **Query recording**: ~10-50ms per query
- 💾 **Storage**: ~1-10MB for query history and schema cache

## 🔧 **Configuration Options**

### **Environment Variables**
```bash
# Enhanced context system settings
ENHANCED_CONTEXT_ENABLED=true
SCHEMA_CACHE_TTL_HOURS=24
QUERY_HISTORY_MAX_SIZE=1000
CONTEXT_QUALITY_THRESHOLD=0.3
INCLUDE_SAMPLE_DATA=true
MAX_SAMPLE_SIZE=10
```

### **Programmatic Configuration**
```python
# Context enhancer settings
enhancer = ContextEnhancer(
    connection=connection,
    data_dir="data"
)

# Schema inspector settings
inspector = SchemaInspector(
    connection=connection,
    cache_ttl_hours=24
)

# Query context manager settings
manager = QueryContextManager(
    data_dir="data"
)
```

## 🚨 **Troubleshooting**

### **Common Issues**

**1. Low Context Quality Score**
```
Issue: Context quality < 0.5
Solution: 
- Refresh schema cache
- Check database connectivity
- Verify table permissions
- Build query history by using the system
```

**2. No Query History Context**
```
Issue: No similar queries found
Solution:
- Use the system more to build history
- Check question similarity matching
- Verify query recording is enabled
```

**3. Schema Inspector Errors**
```
Issue: Schema analysis fails
Solution:
- Check INFORMATION_SCHEMA permissions
- Verify connection string
- Check for complex table structures
- Review error logs
```

### **Debug Mode**
```python
# Enable detailed logging
import logging
logging.getLogger('src.utils.context_enhancer').setLevel(logging.DEBUG)
logging.getLogger('src.database.schema_inspector').setLevel(logging.DEBUG)

# Check system statistics
enhancer = get_context_enhancer(connection)
stats = enhancer.get_context_statistics()
print(json.dumps(stats, indent=2))
```

## 🔮 **Future Enhancements**

### **Planned Features**
- 🔄 **Cross-database learning** - Share patterns across databases
- 🎯 **User-specific contexts** - Personalized query patterns
- 📊 **Advanced analytics** - Context effectiveness metrics
- 🔍 **Semantic similarity** - Better query matching algorithms
- 🏗️ **Query plan analysis** - Execution plan optimization
- 🌐 **Multi-language support** - Enhanced prompts for different languages

### **Integration Opportunities**
- 📈 **Monitoring integration** - Context quality dashboards
- 🔔 **Alert system** - Context quality degradation alerts
- 📝 **Documentation generation** - Auto-generated schema docs
- 🤖 **ML model training** - Context-based model fine-tuning

## 📚 **API Reference**

### **Main Classes**

#### `SchemaInspector`
- `get_comprehensive_context()` - Full schema analysis
- `generate_context_summary()` - Human-readable schema summary

#### `QueryContextManager`
- `record_query()` - Record query execution for learning
- `get_context_for_question()` - Get historical context for question
- `get_statistics()` - Query history statistics

#### `ContextEnhancer`
- `get_enhanced_context()` - Complete context integration
- `generate_enhanced_prompt()` - Context-aware prompt generation
- `record_query_execution()` - Learning integration

#### `ContextValidator`
- `validate_enhanced_context()` - Context quality validation
- `generate_validation_report()` - Human-readable validation report

---

## 🎉 **Summary**

The Enhanced Context System represents a **major architectural improvement** that transforms the NLP agent from a basic text-to-SQL converter into an **intelligent, context-aware, learning system** that:

1. **🧠 Understands your database** - Complete schema analysis with relationships
2. **📚 Learns from experience** - Query history and success patterns  
3. **🎯 Provides smart suggestions** - Domain-aware table/column recommendations
4. **⚡ Optimizes performance** - Large table handling and query optimization
5. **✅ Ensures quality** - Comprehensive validation and confidence scoring
6. **🔄 Continuously improves** - Self-learning from each interaction

This system provides the foundation for **dramatically improved SQL generation accuracy** and **user experience** while maintaining full **backward compatibility** with existing code.