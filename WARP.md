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
# Run Streamlit application (main entry point not yet implemented)
# The project structure suggests running via streamlit command targeting the main module
streamlit run src/main.py  # When main.py is created

# Development mode with debug enabled
DEBUG=True streamlit run src/main.py
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
- `MODEL_NAME`: LLM model name (defaults to llama3-70b-8192)
- `DEBUG`: Enable debug mode (defaults to False)

## Architecture

### High-Level Structure
The project follows a modular architecture with clear separation of concerns:

```
src/
├── agent/          # NLP agent logic (LangChain integration)
├── database/       # Snowflake connection and schema inspection
├── ui/            # Streamlit user interface components
└── utils/         # Configuration and utility functions
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
- **LLM Integration**: Designed to integrate LangChain with Groq LLM for natural language processing (implementation pending).

#### UI Layer (`src/ui/`)
- **Streamlit Components**: User interface components for the web application (implementation pending).

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

### Development Notes
- The application uses Spanish language for comments and error messages
- Global instances are used for shared resources (config, snowflake_conn, log_manager)
- SQLAlchemy NullPool is used to avoid connection pool issues with Snowflake
- Comprehensive error handling with both logging and Streamlit UI feedback
- Schema inspection supports both specific schema queries and cross-schema discovery

### Missing Components
The following components appear to be planned but not yet implemented:
- Main application entry point (likely `src/main.py` or similar)
- Actual NLP agent implementation in `src/agent/`
- Streamlit UI components in `src/ui/`
- Test implementations in `tests/`
