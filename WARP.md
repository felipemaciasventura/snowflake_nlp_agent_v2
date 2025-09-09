# WARP.md

This file provides guidance to WARP (warp.dev) when working with code in this repository.

## Project Overview

This is a **Snowflake NLP Agent v2** - a Streamlit-based application that provides natural language processing capabilities for interacting with Snowflake databases. The application uses LangChain framework with Groq LLM services to enable natural language queries against Snowflake data warehouses.

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
# Edit .env with your Snowflake and Groq credentials
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
```

### Testing
```bash
# Run tests (when test files are implemented)
python -m pytest tests/

# Run specific test file
python -m pytest tests/test_specific.py

# Run tests with coverage
python -m pytest --cov=src tests/
```

### Environment Variables Required
- `SNOWFLAKE_ACCOUNT`: Your Snowflake account URL
- `SNOWFLAKE_USER`: Snowflake username
- `SNOWFLAKE_PASSWORD`: Snowflake password  
- `SNOWFLAKE_WAREHOUSE`: Snowflake warehouse name
- `SNOWFLAKE_DATABASE`: Snowflake database name
- `SNOWFLAKE_SCHEMA`: Snowflake schema (defaults to PUBLIC)
- `GROQ_API_KEY`: Groq API key for LLM services
- `MODEL_NAME`: LLM model name (defaults to llama-3.3-70b-versatile)
- `DEBUG`: Enable debug mode (defaults to False)

## Usage Examples

### Sample Natural Language Queries (Spanish)
The application accepts Spanish natural language queries that are converted to SQL:

```
"Muéstrame las ventas de este mes"
"¿Cuáles son los 10 clientes con más compras?"
"Lista todos los productos de la categoría electrónicos"
"¿Cuál es el promedio de ingresos por región?"
"Muestra los pedidos de los últimos 30 días"
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
│   ├── database/       # Snowflake connection and schema inspection
│   ├── ui/            # Additional UI components (if needed)
│   └── utils/         # Configuration and utility functions
├── tests/             # Test suite
├── requirements.txt   # Python dependencies
├── .env.example      # Environment variables template
└── WARP.md           # This file
```

### Core Components

#### Database Layer (`src/database/`)
- **`SnowflakeConnection`** (`snowflake_conn.py`): Manages Snowflake connections with both raw connector and SQLAlchemy engine support. Includes connection pooling, validation, and query execution methods.
- **`SchemaInspector`** (`schema_inspector.py`): Provides comprehensive database schema inspection including table discovery, column analysis, data sampling, statistics, and relationship mapping.

#### Utility Layer (`src/utils/`)
- **`Config`** (`config.py`): Centralized configuration management with environment variable loading and validation.
- **`LogManager`** (`helpers.py`): Application-wide logging system with Streamlit integration and categorized log levels.
- **`ErrorHandler`** (`helpers.py`): Robust error handling with context-aware exception management and connection validation.

#### Agent Layer (`src/agent/`)
- **`SnowflakeNLPAgent`** (`nlp_agent.py`): Complete LLM integration using LangChain and Groq for natural language to SQL conversion. Features custom Spanish prompts, SQLDatabaseChain for query generation, and comprehensive error handling with step-by-step logging.

#### UI Layer (`streamlit_app.py` + `src/ui/`)
- **Main Application** (`streamlit_app.py`): Complete Streamlit web interface with chat functionality, real-time query processing, connection management, and interactive data visualization.
- **UI Components**: Chat interface, sidebar configuration, connection status, processing logs panel, and data display with pandas DataFrames.

### Key Technology Stack
- **Streamlit**: Web application framework
- **LangChain**: LLM framework and orchestration
- **Groq**: LLM API service (Llama models)
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
- **LLM Configuration**: Uses Llama 3.3 70B Versatile model with temperature=0.1 for consistent SQL generation
- **Session Persistence**: Chat history and connection state maintained across user interactions
- **Real-time Logging**: Step-by-step query processing logs displayed in UI for transparency

### Key Features Implemented
- **Natural Language Processing**: Complete Spanish-to-SQL conversion using Llama 3.3 70B via Groq
- **Interactive Chat Interface**: Real-time conversation with database using Streamlit chat components
- **Smart Result Formatting**: Intelligent DataFrame formatting with monetary values and user-friendly column names
- **Robust SQL Parsing**: Advanced parsing of SQL result strings with Decimal support
- **Connection Management**: Robust Snowflake connection handling with status monitoring
- **Direct SQL Execution**: Direct execution of generated SQL against Snowflake for real data retrieval
- **Data Visualization**: Interactive pandas DataFrames with full-width tables and record counters
- **Error Handling**: Comprehensive error management with user-friendly messages
- **Session Management**: Persistent chat history and connection state
- **Production Ready**: Clean codebase without debug statements, optimized for deployment

### Recent Updates (v2.1)
✅ **Latest Improvements**:
- **Smart Result Formatting**: Implemented intelligent DataFrame formatting with monetary values
- **Robust Data Parsing**: Added parsing of SQL result strings with Decimal object support
- **LLM Model Update**: Updated to llama-3.3-70b-versatile for better performance
- **Direct SQL Execution**: Enhanced SQL execution pipeline for real data retrieval
- **UI/UX Improvements**: Full-width tables, record counters, and cleaner interface
- **Production Optimization**: Removed debug statements and optimized for deployment
- **Method Updates**: Fixed deprecated __call__ method usage in LangChain

### Development Status
✅ **Completed Components**:
- Database layer (connection + schema inspection) with connection string support
- NLP agent (LangChain + Groq integration) with llama-3.3-70b-versatile
- Main Streamlit application interface with smart formatting
- Configuration management with updated model defaults
- Logging and error handling with production-ready optimization
- Result parsing and visualization with pandas DataFrames

🔄 **Areas for Enhancement**:
- Test implementations in `tests/`
- Additional UI components in `src/ui/`
- Data visualization charts and analytics beyond tables
- Query optimization and caching mechanisms
- Multi-language support beyond Spanish
