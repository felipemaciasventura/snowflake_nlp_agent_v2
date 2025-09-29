# 🤖 Snowflake NLP Agent v2 - Complete Guide

An intelligent web application built with Streamlit that enables natural language queries (English) to Snowflake databases, using LangChain with **triple LLM support** for Groq/Llama, Google Gemini, and Ollama (local models).

![License](https://img.shields.io/badge/license-MIT-blue.svg)
![Python](https://img.shields.io/badge/python-3.8+-blue.svg)
![Streamlit](https://img.shields.io/badge/streamlit-1.28+-red.svg)
![Snowflake](https://img.shields.io/badge/snowflake-supported-blue.svg)

---

## 📋 Table of Contents

1. [🌟 Features & Overview](#-features--overview)
2. [🚀 Quick Start Guide](#-quick-start-guide)
3. [⚙️ Configuration & Setup](#️-configuration--setup)
4. [🤖 LLM Providers](#-llm-providers)
5. [💻 Usage Examples](#-usage-examples)
6. [🛠️ Development Workflow](#️-development-workflow)
7. [🏗️ Architecture Overview](#️-architecture-overview)
8. [🧪 Testing & Quality](#-testing--quality)
9. [🤝 Contributing](#-contributing)
10. [📚 Reference & Support](#-reference--support)

---

## 🌟 Features & Overview

### **Core Capabilities**
- **💬 Intuitive Chat Interface**: Natural conversation with your database
- **🧠 Hybrid NLP Processing**: Smart intent detection (DB vs. help vs. out-of-scope)
- **🔄 Triple LLM Support**: Works with Groq/Llama, Google Gemini, and Ollama (local) with auto-detection
- **📊 Smart Visualization**: Automatic result formatting with interactive tables
- **🔒 Secure Connection**: Robust Snowflake integration using encrypted credentials
- **🎯 Educational Answers**: Helpful guidance with examples and friendly redirection
- **🎨 Modern UI**: Responsive design with Streamlit and interactive components

### **Enhanced Context System**
- **🔍 Dynamic Schema Discovery**: Comprehensive table analysis with metadata
- **📚 Query Learning**: History tracking and success pattern analysis
- **🎯 Intelligent Context**: Multi-source integration with quality validation
- **⚡ Performance Optimization**: Query optimization hints and caching

### **Professional Development**
- **📦 Modern Python Packaging**: PEP 518/621 compliant with pyproject.toml
- **🛠️ Automated Workflows**: 15+ Make commands for development tasks
- **🧪 Testing Infrastructure**: pytest with fixtures and CI/CD pipeline
- **🔍 Code Quality**: Black, flake8, mypy, pre-commit hooks

---

## 🚀 Quick Start Guide

### **Prerequisites**
- Python 3.8+
- Snowflake account with access credentials
- At least one LLM provider configured:
  - **Groq API Key** (option 1) for Llama models
  - **Google Gemini API Key** (option 2) for Gemini models  
  - **Ollama server** (option 3) for local models

### **One-Command Setup (Recommended)**
```bash
# Clone and setup complete development environment
git clone https://github.com/your-username/snowflake_nlp_agent_v2.git
cd snowflake_nlp_agent_v2
make init
```

### **Manual Setup**
```bash
# Create virtual environment
python -m venv venv
source venv/bin/activate  # Linux/Mac
# venv\Scripts\activate   # Windows

# Install dependencies
make install-dev  # Development setup
# OR
pip install -e ".[dev]"  # Alternative

# Configure environment
cp .env.example .env
# Edit .env with your credentials

# Start application
make run
```

### **Quick Commands**
```bash
make help           # Show all available commands
make quality        # Run all quality checks
make test          # Run test suite
make run           # Start application
make run-debug     # Start with debug logging
```

---

## ⚙️ Configuration & Setup

### **Environment Configuration**

Create and edit `.env` file with your settings:

```env
# Snowflake Configuration
SNOWFLAKE_ACCOUNT=your-account.region.snowflakecomputing.com
SNOWFLAKE_USER=your-username
SNOWFLAKE_PASSWORD=your-password
SNOWFLAKE_WAREHOUSE=your-warehouse
SNOWFLAKE_DATABASE=your-database
SNOWFLAKE_SCHEMA=PUBLIC

# LLM Provider Selection (auto, groq, gemini, ollama)
LLM_PROVIDER=gemini

# Groq Configuration (Option 1)
GROQ_API_KEY=your-groq-api-key
MODEL_NAME=llama-3.3-70b-versatile

# Google Gemini Configuration (Option 2 - RECOMMENDED)
GOOGLE_API_KEY=your-google-api-key
GEMINI_MODEL=gemini-1.5-flash

# Ollama Configuration (Option 3 - Local)
OLLAMA_BASE_URL=http://localhost:11434
OLLAMA_MODEL=codellama:7b-instruct

# Optional Settings
DEBUG=False
SHOW_TABLE_LIMIT=100
SHOW_TABLE_SAMPLE_PERCENT=0.0
```

### **Security Best Practices**
- Never commit `.env` files to version control
- Use environment-specific configurations
- Rotate API keys regularly
- Use least-privilege Snowflake accounts

---

## 🤖 LLM Providers

### **Provider Comparison**

| Provider | Model | Location | Cost | Privacy | Speed | Best For |
|----------|-------|----------|------|---------|-------|----------|
| **🏠 Ollama** | CodeLlama 7B | Local | 💚 Free | 🔒 Maximum | ⚡ Fast | Privacy, Offline |
| **🟢 Gemini** | Gemini 1.5 Flash | Cloud | 💛 Economic | 🔄 Medium | ⚡ Very Fast | General Use |
| **🔵 Groq** | Llama 3.3 70B | Cloud | 🧡 Moderate | 🔄 Medium | 🚀 Ultra Fast | Complex Queries |

### **Setup Instructions**

#### **Option 1: Ollama (Local - Maximum Privacy)**
```bash
# Install Ollama
curl -fsSL https://ollama.com/install.sh | sh

# Download CodeLlama model
ollama pull codellama:7b-instruct

# Verify installation
ollama list

# Configure in .env
LLM_PROVIDER=ollama
OLLAMA_BASE_URL=http://localhost:11434
OLLAMA_MODEL=codellama:7b-instruct
```

**Advantages:**
- 🔒 Complete privacy - no data sent to internet
- 💰 Zero cost - no API charges
- 🛡️ Offline capability
- 🎯 SQL-specialized model

**Requirements:**
- 4GB+ RAM available
- Ollama server running
- CodeLlama model downloaded

#### **Option 2: Google Gemini (Cloud - Recommended)**
```bash
# Get API key from Google AI Studio
# https://aistudio.google.com/app/apikey

# Configure in .env
LLM_PROVIDER=gemini
GOOGLE_API_KEY=your-google-api-key
GEMINI_MODEL=gemini-1.5-flash
```

**Advantages:**
- 🚀 Excellent performance/cost ratio
- ⚡ Very fast response times
- 🧠 Strong reasoning capabilities
- 💛 Competitive pricing

#### **Option 3: Groq (Cloud - Ultra Fast)**
```bash
# Get API key from Groq Console
# https://console.groq.com/keys

# Configure in .env
LLM_PROVIDER=groq
GROQ_API_KEY=your-groq-api-key
MODEL_NAME=llama-3.3-70b-versatile
```

**Advantages:**
- 🚀 Ultra-fast inference
- 💪 Powerful 70B parameter model
- 🎯 Excellent for complex queries

---

## 💻 Usage Examples

### **Database Queries**
```
🔹 "What are the 10 highest-value orders?"
🔹 "Show me this month's sales"
🔹 "How many customers are there in total?"
🔹 "List the best-selling products"
🔹 "Which database am I using?"
🔹 "Show available tables"
🔹 "What is the average revenue by region?"
🔹 "Find customers with orders over $1000"
```

### **Help & Information**
```
🔹 "What can you help me with?"
🔹 "What can you do?"
🔹 "How does this app work?"
🔹 "Show me examples of what you can do"
```

### **Metadata Queries**
```
🔹 "What database am I connected to?"
🔹 "What schema am I using?"
🔹 "What is my current role?"
🔹 "Which warehouse am I using?"
🔹 "Show me the CUSTOMERS table"
```

### **Automatic Outputs**
The application automatically generates:
- ✅ **Optimized SQL queries** with validation
- 📊 **Formatted tables** with friendly column names
- 💰 **Currency formatting** for financial values
- 📈 **Record counters** and statistics
- 🔍 **Persistent conversation** history

---

## 🛠️ Development Workflow

### **Available Commands**

#### **Setup & Installation**
```bash
make install          # Production dependencies
make install-dev      # Development dependencies
make setup-dev        # Complete dev environment setup
make init            # One-command project initialization
```

#### **Development Tasks**
```bash
make run             # Start Streamlit application
make run-debug       # Start with debug logging
make format          # Format code with Black
make lint            # Check code style with flake8
make type-check      # Type checking with mypy
make quality         # Run all quality checks
```

#### **Testing**
```bash
make test            # Run full test suite with coverage
make test-fast       # Quick test run without coverage
```

#### **Project Management**
```bash
make clean           # Clean build artifacts
make build           # Build distribution package
make help            # Show all available commands
```

### **Quality Standards**
- **Code Formatting**: Black (88 character limit)
- **Linting**: flake8 with comprehensive rules
- **Type Checking**: mypy with strict settings
- **Testing**: pytest with fixtures and coverage
- **Pre-commit**: Automated quality checks

### **CI/CD Pipeline**
- **Matrix Testing**: Python 3.8-3.13
- **Quality Checks**: Automated linting, formatting, type checking
- **Security Scanning**: safety and bandit
- **Build Verification**: Package building and artifact generation

---

## 🏗️ Architecture Overview

### **System Architecture**

```
┌─────────────────────────────────────────────────────────────────┐
│                    🌐 STREAMLIT WEB APP                         │
│  ├─ 💬 Chat Interface    ├─ 📊 Data Display                    │
│  ├─ 🔧 Configuration     └─ 📋 Logs Panel                      │
└─────────────────────────────────────────────────────────────────┘
                              │ user_input
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                   🧠 NLP AGENT LAYER                           │
│  ├─ 🤖 LLM Integration    ├─ 🔍 Intent Detection               │
│  ├─ 📝 SQL Generation     └─ 🎯 Context Enhancement            │
└─────────────────────────────────────────────────────────────────┘
                              │ sql_query
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                  🗄️ DATABASE LAYER                              │
│  ├─ ❄️ Snowflake Connection ├─ 🔍 Schema Inspector              │
│  ├─ 📊 Query Execution      └─ 📚 Query Context Manager        │
└─────────────────────────────────────────────────────────────────┘
```

### **Project Structure**

```
snowflake_nlp_agent_v2/
├── 📦 Configuration & Build
│   ├── pyproject.toml              # Modern Python project config
│   ├── Makefile                    # Development automation
│   ├── requirements.txt            # Dependencies
│   └── .env.example               # Configuration template
│
├── 📁 Source Code
│   ├── streamlit_app.py           # Main Streamlit application
│   └── src/
│       ├── agent/                 # NLP processing logic
│       │   └── nlp_agent.py
│       ├── database/              # Database connections
│       │   ├── snowflake_conn.py
│       │   └── schema_inspector.py
│       ├── utils/                 # Utilities and configuration
│       │   ├── config.py
│       │   ├── helpers.py
│       │   ├── context_enhancer.py
│       │   └── prompt_loader.py
│       └── prompts/               # SQL prompt templates
│           └── sql_prompts.py
│
├── 🧪 Testing & Quality
│   ├── tests/                     # Test suite
│   │   ├── test_config.py
│   │   ├── conftest.py
│   │   └── __init__.py
│   ├── .github/workflows/         # CI/CD pipeline
│   │   └── ci.yml
│   ├── .pre-commit-config.yaml    # Code quality hooks
│   └── .flake8                    # Linting configuration
│
└── 📚 Documentation
    ├── README.md                  # This comprehensive guide
    └── TECHNICAL_REFERENCE.md     # Technical implementation details
```

### **Key Components**

#### **NLP Agent (`src/agent/nlp_agent.py`)**
- LLM provider abstraction (Groq, Gemini, Ollama)
- SQL generation with intelligent prompts
- Error handling and response cleaning
- Intent detection and classification

#### **Database Layer (`src/database/`)**
- Snowflake connection management
- Schema inspection and metadata extraction
- Query execution and result processing
- Connection pooling and optimization

#### **Enhanced Context System (`src/utils/`)**
- Dynamic schema discovery
- Query history tracking
- Context quality validation
- Performance optimization hints

---

## 🧪 Testing & Quality

### **Testing Framework**
- **pytest**: Primary testing framework
- **Coverage**: Maintain 80%+ test coverage
- **Fixtures**: Reusable test components in `conftest.py`
- **Mocking**: Mock external dependencies for unit tests

### **Test Organization**
```bash
tests/
├── conftest.py         # Shared fixtures and utilities
├── test_config.py      # Configuration module tests
├── test_nlp_agent.py   # NLP agent tests
├── test_database.py    # Database connection tests
└── integration/        # Integration tests
```

### **Running Tests**
```bash
# Full test suite with coverage
make test

# Quick tests without coverage
make test-fast

# Specific test file
pytest tests/test_config.py -v

# Coverage report
pytest --cov=src --cov-report=html
```

### **Quality Assurance**
```bash
# Complete quality check
make quality

# Individual checks
make format      # Black code formatting
make lint        # flake8 linting
make type-check  # mypy type checking
```

---

## 🤝 Contributing

### **Quick Start for Contributors**

1. **Fork and Setup**
   ```bash
   git clone https://github.com/your-username/snowflake_nlp_agent_v2.git
   cd snowflake_nlp_agent_v2
   make init  # Complete setup
   ```

2. **Development Workflow**
   ```bash
   git checkout -b feature/your-feature
   # Make your changes
   make quality  # Ensure quality standards
   make test     # Run tests
   git commit -m "feat: add your feature"
   git push origin feature/your-feature
   ```

### **Contribution Guidelines**

#### **Code Standards**
- **Language**: English documentation and comments
- **Style**: Black formatting (88 char limit)
- **Linting**: flake8 compliance
- **Types**: mypy type hints encouraged
- **Tests**: Unit tests for new features

#### **Pull Request Process**
- Clear description of changes
- All quality checks passing
- Test coverage maintained
- Documentation updated
- No breaking changes (unless discussed)

#### **Development Environment**
```bash
# Pre-commit hooks (automatic)
pre-commit install

# Manual quality checks
make quality

# Testing
make test
```

---

## 📚 Reference & Support

### **Documentation Structure**
- **README.md** (this file): Complete user guide and quick reference
- **[TECHNICAL_REFERENCE.md](TECHNICAL_REFERENCE.md)**: Advanced technical implementation details
- **[CHANGELOG.md](CHANGELOG.md)**: Version history and detailed changes

### **Version History**
- **v2.5**: Complete project modernization with CI/CD
- **v2.4**: Enhanced metadata queries and UI improvements  
- **v2.3**: Ollama integration and local model support
- **v2.2**: Hybrid intent detection and educational responses
- **v2.1**: Smart formatting and visualization improvements
- **v2.0**: Multi-LLM support and enhanced architecture

### **Getting Help**
- **🐛 Issues**: [GitHub Issues](https://github.com/your-username/snowflake_nlp_agent_v2/issues)
- **💬 Discussions**: [GitHub Discussions](https://github.com/your-username/snowflake_nlp_agent_v2/discussions)
- **📚 Documentation**: This guide and technical reference
- **📧 Email**: Support contact information

### **Useful Links**
- **Snowflake**: [Documentation](https://docs.snowflake.com/)
- **Streamlit**: [Documentation](https://docs.streamlit.io/)
- **LangChain**: [Documentation](https://docs.langchain.com/)
- **Groq**: [Console](https://console.groq.com/)
- **Google AI**: [Studio](https://aistudio.google.com/)
- **Ollama**: [Models](https://ollama.com/library)

### **License & Acknowledgments**
- **License**: MIT License - see [LICENSE](LICENSE) file
- **Dependencies**: See [pyproject.toml](pyproject.toml) for complete list
- **Contributors**: Thank you to all contributors and users

---

**Built with ❤️ using Python and modern AI technologies**

🚀 **Ready for production deployment with enterprise-grade quality!**