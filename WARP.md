# WARP.md

This file provides guidance to WARP (warp.dev) when working with code in this repository.

## Project Overview

This is a **Snowflake NLP Agent v2** - a Streamlit-based application that provides natural language processing capabilities for interacting with Snowflake databases. The application uses LangChain framework with **triple LLM support** (Groq/Llama + Google Gemini + Ollama local models) and **hybrid query detection** to enable intelligent natural language queries against Snowflake data warehouses.

## Development Commands

### Environment Setup
```bash
# Create and activate virtual environment
python -m venv venv
source venv/bin/activate  # On Linux/Mac
# venv\Scripts\activate   # On Windows

# Install dependencies
pip install -r requirements.txt
```

### Configuration
```bash
# Copy environment template and configure
cp .env.example .env
# Edit .env with your Snowflake and LLM provider credentials
```

### Running the Application
```bash
# Activate virtual environment first
source venv/bin/activate  # On Linux/Mac
# venv\Scripts\activate   # On Windows

# Run the main Streamlit application (recommended)
streamlit run streamlit_app.py

# Run with specific port
streamlit run streamlit_app.py --server.port 8501

# For production deployment
streamlit run streamlit_app.py --server.port 8080 --server.address 0.0.0.0

# Personal
source venv/bin/activate && streamlit run streamlit_app.py --server.port 8502
```


### Environment Variables Required
**Snowflake Configuration:**
- `SNOWFLAKE_ACCOUNT`: Your Snowflake account URL
- `SNOWFLAKE_USER`: Snowflake username
- `SNOWFLAKE_PASSWORD`: Snowflake password  
- `SNOWFLAKE_WAREHOUSE`: Snowflake warehouse name
- `SNOWFLAKE_DATABASE`: Snowflake database name
- `SNOWFLAKE_SCHEMA`: Snowflake schema (defaults to PUBLIC)

**LLM Providers (configure at least one):**
- `GROQ_API_KEY`: Groq API key for Llama models (option 1)
- `GOOGLE_API_KEY`: Google API key for Gemini models (option 2)
- `OLLAMA_BASE_URL`: Ollama server URL for local models (option 3)
- `OLLAMA_MODEL`: Ollama model name for local inference
- `MODEL_NAME`: Groq model name (defaults to llama-3.3-70b-versatile)
- `GEMINI_MODEL`: Gemini model name (defaults to gemini-1.5-flash)
- `LLM_PROVIDER`: Provider selection - auto, groq, gemini, ollama (defaults to gemini)

**Optional:**
- `DEBUG`: Enable debug mode (defaults to False)

## Usage Examples

### Sample Queries with Hybrid Detection
The application intelligently detects and responds to different types of queries:

**Database Queries (converted to SQL):**
```
"Muéstrame las ventas de este mes"
"?¿Cuáles son los 10 clientes con más compras?"
"Lista todos los productos de la categoría electrónicos"
"?¿Cuál es el promedio de ingresos por región?"
"Muestra los pedidos de los últimos 30 días"
```

**Help Queries (educational responses):**
```
"?¿En qué me puedes ayudar?"
"?¿Qué puedes hacer?"
"?¿Cómo funciona esta aplicación?"
```

**Off-topic Queries (friendly redirection):**
```
"?¿Cómo está el clima?"
"Cuéntame un chiste"
"?¿Qué películas recomiendas?"
```

### Expected Database Schema
The application works best with properly structured Snowflake databases that include:
- Table and column comments in Spanish or English
- Consistent naming conventions
- Appropriate data types and constraints

## Architecture

### High-Level Structure
The project follows a modular architecture with clear separation of concerns:

```
snowflake_nlp_agent_v2/
├── streamlit_app.py    # Main Streamlit application entry point
├── src/
│   ├── agent/          # NLP agent logic (LangChain + Groq integration)
│   ├── database/       # Snowflake connection
│   └── utils/         # Configuration and utility functions
├── requirements.txt   # Python dependencies
├── .env.example      # Environment variables template
└── WARP.md           # This file
```

### Core Components

#### Database Layer (`src/database/`)
- **`SnowflakeConnection`** (`snowflake_conn.py`): Manages Snowflake connections with both raw connector and SQLAlchemy engine support. Includes connection pooling, validation, and query execution methods.

#### Utility Layer (`src/utils/`)
- **`Config`** (`config.py`): Centralized configuration management with environment variable loading and validation.
- **`LogManager`** (`helpers.py`): Application-wide logging system with Streamlit integration and categorized log levels.
- **`ErrorHandler`** (`helpers.py`): Robust error handling with context-aware exception management and connection validation.

#### Agent Layer (`src/agent/`)
- **`SnowflakeNLPAgent`** (`nlp_agent.py`): Complete LLM integration using LangChain with triple provider support (Groq + Gemini + Ollama) for natural language to SQL conversion. Features custom Spanish prompts optimized for each model, SQLDatabaseChain for query generation, advanced SQL cleaning for CodeLlama markdown format, and comprehensive error handling with step-by-step logging.

#### UI Layer (`streamlit_app.py`)
- **Main Application** (`streamlit_app.py`): Complete Streamlit web interface with chat functionality, real-time query processing, connection management, and interactive data visualization including chat interface, sidebar configuration, connection status, processing logs panel, and data display with pandas DataFrames.

### Key Technology Stack
- **Streamlit**: Web application framework
- **LangChain**: LLM framework and orchestration
- **Groq**: LLM API service (Llama models) ✅
- **Google Gemini**: LLM API service (Gemini models) ✅
- **Ollama**: Local LLM inference (CodeLlama) ✅
- **Snowflake**: Data warehouse with native Python connector and SQLAlchemy
- **Pandas**: Data manipulation and analysis
- **Plotly**: Data visualization
- **SQLParse**: SQL parsing utilities
- **Pydantic**: Data validation

### Design Patterns
- **Singleton Pattern**: Global instances for configuration, database connection, and utility managers
- **Context Manager**: Database connections support `with` statement usage
- **Factory Pattern**: Connection string building and configuration validation
- **Observer Pattern**: Integrated logging system across all components
- **Chain of Responsibility**: LangChain's SQLDatabaseChain for processing natural language queries
- **Session State Management**: Streamlit session state for maintaining chat history and connections

### Development Notes
- **Language Support**: Application interface and NLP processing optimized for Spanish language
- **Global Instances**: Shared resources managed via singleton pattern (config, snowflake_conn, log_manager)
- **Connection Pooling**: SQLAlchemy NullPool prevents Snowflake connection pool conflicts
- **Error Handling**: Dual-layer error management (Python logging + Streamlit UI feedback)
- **Schema Inspection**: Supports both specific schema queries and cross-schema discovery
- **LLM Configuration**: Uses Gemini 1.5 Flash (default), Llama 3.3 70B Versatile, or CodeLlama 7B-Instruct with temperature=0.1 for consistent SQL generation
- **Session Persistence**: Chat history and connection state maintained across user interactions
- **Real-time Logging**: Step-by-step query processing logs displayed in UI for transparency

### Key Features Implemented
- **Triple LLM Support**: Groq/Llama 3.3 70B + Google Gemini 1.5 Flash + Ollama CodeLlama 7B with auto-detection and local-first priority
- **Hybrid Query Detection**: Intelligent classification of database vs help vs off-topic queries
- **Educational Responses**: Comprehensive user guidance with examples and capabilities
- **Friendly Redirection**: Amigable responses for off-topic queries with gentle redirection
- **Natural Language Processing**: Complete Spanish-to-SQL conversion with multiple LLM options
- **Interactive Chat Interface**: Real-time conversation with database using Streamlit chat components
- **Smart Result Formatting**: Intelligent DataFrame formatting with monetary values and user-friendly column names
- **Robust SQL Parsing**: Advanced parsing of SQL result strings with Decimal support
- **Dynamic System Info**: Real-time display of active LLM model and provider status
- **Connection Management**: Robust Snowflake connection handling with status monitoring
- **Direct SQL Execution**: Direct execution of generated SQL against Snowflake for real data retrieval
- **Data Visualization**: Interactive pandas DataFrames with full-width tables and record counters
- **Error Handling**: Comprehensive error management with user-friendly messages
- **Session Management**: Persistent chat history and connection state
- **Production Ready**: Clean codebase without debug statements, optimized for deployment

### Recent Updates (v2.3)
✅ **Latest Major Improvements**:
- **Ollama Integration**: Complete support for local models (CodeLlama 7B-Instruct) with privacy-first approach
- **Triple LLM Provider Support**: Groq/Llama + Google Gemini + Ollama with intelligent auto-detection (Ollama > Gemini > Groq)
- **Advanced SQL Cleaning**: Robust markdown format handling for CodeLlama responses with multi-pattern recognition
- **Local Model Optimization**: Specialized prompts and processing pipeline for CodeLlama SQL generation
- **Provider Priority System**: Local-first architecture prioritizing privacy and cost-effectiveness

### Recent Updates (v2.2)
✅ **Previous Major Improvements**:
- **Hybrid Query Detection**: Intelligent query classification (database/help/off-topic)
- **Educational Interface**: Comprehensive help responses with usage examples
- **Friendly User Experience**: Amigable redirection for off-topic queries
- **Dynamic System Display**: Real-time LLM provider and model information
- **Auto-detection Logic**: Automatic LLM provider selection based on available credentials
- **Robust Error Handling**: Enhanced DataFrame constructor error management

✅ **Previous Improvements (v2.1)**:
- **Smart Result Formatting**: Implemented intelligent DataFrame formatting with monetary values
- **Robust Data Parsing**: Added parsing of SQL result strings with Decimal object support
- **LLM Model Update**: Updated to llama-3.3-70b-versatile + gemini-1.5-flash
- **Direct SQL Execution**: Enhanced SQL execution pipeline for real data retrieval
- **UI/UX Improvements**: Full-width tables, record counters, and cleaner interface
- **Production Optimization**: Removed debug statements and optimized for deployment
- **Method Updates**: Fixed deprecated __call__ method usage in LangChain

### Development Status
✅ **Completed Components**:
- Database layer (connection + schema inspection) with connection string support
- NLP agent with triple LLM support (Groq + Gemini + Ollama) and auto-detection
- Hybrid query processing with intelligent detection and appropriate responses
- Main Streamlit application interface with smart formatting and dynamic info
- Configuration management with triple provider support and validation
- Logging and error handling with production-ready optimization
- Result parsing and visualization with pandas DataFrames
- Educational user interface with comprehensive help system
- Advanced SQL cleaning system for CodeLlama markdown format
- Local model integration with Ollama server connectivity

🔄 **Areas for Enhancement**:
- Test suite implementation with provider-specific testing
- Data visualization charts and analytics beyond tables
- Query optimization and caching mechanisms
- Multi-language support beyond Spanish (interface + NLP)
- Additional UI components and advanced analytics features
- Query history and favorites functionality
- Advanced security features and user management
