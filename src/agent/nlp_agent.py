from langchain_google_genai import \
    ChatGoogleGenerativeAI  # For use with Gemini
from langchain_groq import ChatGroq  # For use with Groq (code preserved)

# Import ChatOllama - prefer langchain-ollama package (non-deprecated)
try:
    from langchain_ollama import ChatOllama  # Preferred: non-deprecated package
except ImportError:
    try:
        from langchain_community.chat_models import ChatOllama  # Fallback: deprecated but functional
        import warnings
        warnings.warn(
            "Using deprecated ChatOllama from langchain_community. "
            "Install langchain-ollama package for better compatibility: pip install langchain-ollama",
            DeprecationWarning,
            stacklevel=2
        )
    except ImportError:
        ChatOllama = None  # Will raise error if Ollama is selected but not available

import logging
import math
import time
from typing import Any, Dict, Optional
from decimal import Decimal

import pandas as pd
import streamlit as st
from langchain.prompts import PromptTemplate
from langchain_community.utilities import SQLDatabase
from langchain_experimental.sql import SQLDatabaseChain
from sqlalchemy.exc import SQLAlchemyError, OperationalError, ProgrammingError

from src.database.schema_inspector import validate_table_name
from src.utils.config import config
from src.utils.context_enhancer import get_context_enhancer
from src.utils.helpers import log_manager
from src.utils.prompt_loader import prompt_loader
from src.utils.query_cache import get_query_cache
from src.utils.query_paginator import QueryPaginator
from src.utils.sql_validator import get_sql_validator
from src.utils.query_explainer import get_query_explainer
from src.utils.confidence_scorer import get_confidence_scorer
from src.utils.query_corrector import get_query_corrector

logger = logging.getLogger(__name__)


class SnowflakeNLPAgent:
    """NLP Agent that translates English questions to SQL for Snowflake.

    Executes the query.

    Main responsibilities:
    - Configure the LLM (Groq, Gemini or Ollama, according to configuration)
    - Set up an SQL chain (SQLDatabaseChain) with a English prompt
    - Invoke the chain with the user's question
    - Extract the generated SQL from intermediate_steps
    - Execute the SQL safely in the database and return real rows
    - Log process steps for UI visibility
    """
    
    # Stopwords that should NOT be treated as table names
    # These are common English words that appear in queries but are not table identifiers
    TABLE_NAME_STOPWORDS = {
        'all', 'the', 'a', 'an', 'each', 'every', 'some', 'any',
        'my', 'our', 'your', 'this', 'that', 'these', 'those',
        'me', 'you', 'it', 'he', 'she', 'we', 'they',
        'and', 'or', 'but', 'for', 'from', 'to', 'in', 'on', 'at',
        'by', 'with', 'about', 'as', 'of', 'is', 'are', 'was', 'were',
        'been', 'be', 'have', 'has', 'had', 'do', 'does', 'did',
        'can', 'could', 'will', 'would', 'should', 'may', 'might', 'must',
        'tables', 'table'  # 'tables' for metadata queries, 'table' to avoid capturing it as table name
    }

    def __init__(
        self,
        db_connection: str,
        groq_api_key: Optional[str] = None,
        google_api_key: Optional[str] = None,
    ):
        # Select available LLM provider
        provider = config.get_available_llm_provider()

        # Allow override from parameters if passed explicitly
        groq_key = groq_api_key or config.GROQ_API_KEY
        google_key = google_api_key or config.GOOGLE_API_KEY

        # Store provider info for UI display
        provider_info = config.get_active_provider_info()
        self.active_provider = provider_info
        
        # Initialize query cache and paginator
        self.query_cache = get_query_cache(ttl_minutes=60)
        self.query_paginator = QueryPaginator(default_page_size=100)
        
        # Initialize Phase 2 components
        self.sql_validator = get_sql_validator()
        self.query_explainer = get_query_explainer()
        self.confidence_scorer = get_confidence_scorer()
        self.query_corrector = get_query_corrector()
        
        if provider == "ollama":
            # Use Ollama (local model - maximum privacy priority)
            if ChatOllama is None:
                raise ImportError(
                    "ChatOllama is not available. Install langchain-ollama: "
                    "pip install langchain-ollama"
                )
            self.llm = ChatOllama(
                base_url=config.OLLAMA_BASE_URL,
                model=config.OLLAMA_MODEL,
                temperature=0.1,
            )
        elif provider == "sqlcoder":
            # Use SQLCoder (specialized SQL model - maximum SQL accuracy)
            if ChatOllama is None:
                raise ImportError(
                    "ChatOllama is not available. Install langchain-ollama: "
                    "pip install langchain-ollama"
                )
            self.llm = ChatOllama(
                base_url=config.SQLCODER_BASE_URL,
                model=config.SQLCODER_MODEL,
                temperature=0.0,  # Lower temperature for more deterministic SQL generation
            )
        elif provider == "gemini" and google_key:
            # Use Gemini (recommended if you have student plan)
            self.llm = ChatGoogleGenerativeAI(
                google_api_key=google_key,
                model=config.GEMINI_MODEL,
                temperature=0.1,
                max_output_tokens=4000,
            )
        elif provider == "groq" and groq_key:
            self.llm = ChatGroq(
                groq_api_key=groq_key,
                model_name=config.MODEL_NAME,
                temperature=0.1,
                max_tokens=4000,
            )
        else:
            # Get status of all providers for better error message
            providers_status = config.get_all_providers_status()
            available_providers = [p for p, status in providers_status.items() if status["available"]]
            enabled_providers = [p for p, status in providers_status.items() if status["enabled"]]
            
            error_msg = "No LLM provider available.\n\n"
            if enabled_providers:
                error_msg += f"Enabled providers: {', '.join(enabled_providers)}\n"
            if available_providers:
                error_msg += f"Available providers: {', '.join(available_providers)}\n"
            else:
                error_msg += "Please configure at least one LLM provider in .env:\n"
                error_msg += "- Set ENABLE_GROQ=true and GROQ_API_KEY=...\n"
                error_msg += "- Set ENABLE_GEMINI=true and GOOGLE_API_KEY=...\n"
                error_msg += "- Set ENABLE_OLLAMA=true and OLLAMA_BASE_URL=...\n"
                error_msg += "- Set ENABLE_SQLCODER=true and SQLCODER_BASE_URL=...\n"
            
            raise RuntimeError(error_msg)

        self.db = SQLDatabase.from_uri(db_connection)

        # Initialize enhanced context system
        self.context_enhancer = get_context_enhancer(self.db._engine)

        # Load prompt template from external source for cleaner code organization
        # This allows easy prompt updates without code changes
        sql_prompt = prompt_loader.get_sql_prompt(provider)

        self.sql_chain = SQLDatabaseChain.from_llm(
            self.llm,
            self.db,
            verbose=True,
            return_intermediate_steps=True,
            prompt=PromptTemplate(
                input_variables=["input", "table_info"], template=sql_prompt
            ),
        )

    def extract_sql_and_data_from_chain_result(
        self, result: Dict, user_question: str
    ) -> tuple:
        """Extract SQL and data from LangChain result, handling the Answer field problem.

        The issue: LangChain sometimes generates:
        1. SQLQuery: correct query
        2. SQLResult: correct data
        3. Answer: different incorrect query

        This method prioritizes the FIRST valid SQL/data pair and ignores subsequent ones.
        """
        sql_query = "N/A"
        chain_data = None

        self.log_step(
            "🔍 Extracting SQL and data from chain result",
            f"Keys: {list(result.keys())}",
        )

        # Method 1: Extract from intermediate_steps (most reliable)
        if "intermediate_steps" in result and result["intermediate_steps"]:
            logger.debug(
                f"EXTRACTOR: Found {len(result['intermediate_steps'])} intermediate steps"
            )
            self.log_step(
                "📋 Processing intermediate_steps",
                f"Found {len(result['intermediate_steps'])} steps",
            )

            for i, step in enumerate(result["intermediate_steps"]):
                logger.debug(
                    f"EXTRACTOR: Step {i+1} - Type: {type(step)}, Length: {len(step) if hasattr(step, '__len__') else 'N/A'}"
                )
                self.log_step(
                    f"📋 Step {i+1}",
                    f"Type: {type(step)}, Preview: {str(step)[:100]}...",
                )

                # NEW: Handle dict steps (LangChain stores SQL execution info in dicts)
                if isinstance(step, dict):
                    logger.debug(
                        f"EXTRACTOR: Step {i+1} DICT - Keys: {list(step.keys())}"
                    )

                    # Check for SQL in dict - but skip 'input' key as it contains user question
                    found_sql_in_dict = False
                    for key in ["sql_cmd", "query", "sql"]:  # Removed 'input' as it's user question
                        if key in step and isinstance(step[key], str):
                            potential_sql = step[key]
                            # Additional validation: make sure it's actual SQL, not user question
                            cleaned_potential = potential_sql.strip()
                            if (
                                ("SELECT" in potential_sql.upper() or "WITH" in potential_sql.upper()) and
                                (cleaned_potential.upper().startswith(("SELECT", "WITH")) and 
                                 ("FROM" in cleaned_potential.upper() or "(" in cleaned_potential))  # Basic SQL structure check
                            ):
                                logger.debug(
                                    f"EXTRACTOR: Found SQL in dict['{key}'] - {potential_sql[:60]}..."
                                )
                                if sql_query == "N/A":
                                    sql_query = potential_sql
                                    
                                    # Try to execute this SQL immediately to get data
                                    try:
                                        logger.debug(f"EXTRACTOR: Attempting immediate execution of SQL from dict['{key}']")
                                        cleaned_sql = self.clean_sql_response(potential_sql)
                                        if cleaned_sql and cleaned_sql.upper().startswith(("SELECT", "WITH", "SHOW", "DESCRIBE")):
                                            immediate_result = self.db.run(cleaned_sql)
                                            if immediate_result:
                                                chain_data = immediate_result
                                                logger.info(f"EXTRACTOR: Immediate execution successful - {len(immediate_result) if hasattr(immediate_result, '__len__') else 'N/A'} rows")
                                                found_sql_in_dict = True
                                                break
                                    except SQLAlchemyError as e:
                                        logger.warning(f"EXTRACTOR: Database error during immediate execution: {e}")
                                        # Continue to try other methods
                                    except Exception as e:
                                        logger.warning(f"EXTRACTOR: Unexpected error during immediate execution: {e}")
                                        # Continue to try other methods
                            elif "SELECT" in potential_sql.upper() or "WITH" in potential_sql.upper():
                                logger.warning(f"EXTRACTOR: Dict['{key}'] contains SELECT but doesn't look like valid SQL: {potential_sql[:100]}")
                    
                    if found_sql_in_dict and chain_data:
                        break

                    # Check for data in dict (only if we didn't already find it)
                    if not chain_data:
                        for key in ["sql_result", "result", "data", "output"]:
                            if key in step and step[key] is not None:
                                potential_data = step[key]
                                logger.debug(
                                    f"EXTRACTOR: Found data in dict['{key}'] - Type: {type(potential_data)}, Preview: {str(potential_data)[:60]}..."
                                )
                                if chain_data is None:
                                    chain_data = potential_data

                # Handle string steps (might contain SQL or DATA)
                elif isinstance(step, str):
                    logger.debug(
                        f"EXTRACTOR: Step {i+1} STRING - Preview: {step[:60]}..."
                    )

                    # Check for SQL in string - but validate it's actually SQL not user question
                    if (
                        "SELECT" in step.upper() or "WITH" in step.upper()
                    ) and sql_query == "N/A":
                        # Additional validation: make sure it's actual SQL, not user question
                        cleaned_step = step.strip()
                        if (cleaned_step.upper().startswith(("SELECT", "WITH")) and 
                            ("FROM" in cleaned_step.upper() or "(" in cleaned_step)):  # Basic SQL structure check
                            logger.debug(f"EXTRACTOR: Found SQL in string step")
                            sql_query = step
                            
                            # Try to execute this SQL immediately to get data
                            try:
                                logger.debug(f"EXTRACTOR: Attempting immediate execution of SQL from step {i+1}")
                                cleaned_sql = self.clean_sql_response(step)
                                if cleaned_sql and cleaned_sql.upper().startswith(("SELECT", "WITH", "SHOW", "DESCRIBE")):
                                    immediate_result = self.db.run(cleaned_sql)
                                    if immediate_result:
                                        chain_data = immediate_result
                                        logger.info(f"EXTRACTOR: Immediate execution successful - {len(immediate_result) if hasattr(immediate_result, '__len__') else 'N/A'} rows")
                                        # Break here to use the first working SQL
                                        break
                            except SQLAlchemyError as e:
                                logger.warning(f"EXTRACTOR: Database error during immediate execution: {e}")
                                # Continue to try other methods
                            except Exception as e:
                                logger.warning(f"EXTRACTOR: Unexpected error during immediate execution: {e}")
                                # Continue to try other methods
                        else:
                            logger.warning(f"EXTRACTOR: String contains SELECT but doesn't look like valid SQL: {step[:100]}")

                    # NEW: Check for DATA in string (list format) - only if we don't have data yet
                    elif step.strip().startswith("[") and ")]" in step and not chain_data:
                        logger.debug(
                            f"EXTRACTOR: Found data-like string in step {i+1}"
                        )
                        try:
                            import ast
                            import datetime
                            import re as _re

                            # First try with ast.literal_eval (safer)
                            try:
                                parsed_data = ast.literal_eval(step.strip())
                            except (ValueError, SyntaxError):
                                # If ast.literal_eval fails, try to handle datetime objects safely
                                # Replace datetime.date(Y, M, D) with 'YYYY-MM-DD' string
                                def _date_repl(match):
                                    y, m, d = match.group(1), match.group(2), match.group(3)
                                    try:
                                        y_i, m_i, d_i = int(y), int(m), int(d)
                                        return f"'{y_i:04d}-{m_i:02d}-{d_i:02d}'"
                                    except Exception:
                                        return match.group(0)
                                
                                sanitized = _re.sub(
                                    r"datetime\.date\(\s*(\d{1,4})\s*,\s*(\d{1,2})\s*,\s*(\d{1,2})\s*\)",
                                    _date_repl,
                                    step.strip(),
                                )
                                # Try again with sanitized string
                                parsed_data = ast.literal_eval(sanitized)
                            
                            if (
                                isinstance(parsed_data, list)
                                and parsed_data
                                and chain_data is None
                            ):
                                chain_data = parsed_data
                                logger.info(
                                    f"EXTRACTOR: Parsed data from string step {i+1} - Length: {len(parsed_data)}"
                                )
                        except Exception as e:
                            logger.warning(
                                f"EXTRACTOR: Failed to parse data string in step {i+1}: {e}"
                            )
                            logger.debug(f"EXTRACTOR: Data string preview: {step[:200]}...")

                # Original tuple handling (kept for compatibility)
                elif isinstance(step, tuple) and len(step) >= 2:
                    potential_sql, potential_data = step[0], step[1]

                    logger.debug(
                        f"EXTRACTOR: Step {i+1} TUPLE - SQL type: {type(potential_sql)}, Data type: {type(potential_data)}"
                    )
                    logger.debug(
                        f"EXTRACTOR: Step {i+1} TUPLE - SQL preview: {str(potential_sql)[:80]}"
                    )
                    logger.debug(
                        f"EXTRACTOR: Step {i+1} TUPLE - Data preview: {str(potential_data)[:80]}"
                    )

                    # Check if this looks like a SQL query with valid data
                    if (
                        isinstance(potential_sql, str)
                        and (
                            "SELECT" in potential_sql.upper()
                            or "WITH" in potential_sql.upper()
                        )
                        and potential_data is not None
                    ):
                        logger.debug(
                            f"EXTRACTOR: Found valid SQL/data pair in tuple step {i+1}"
                        )

                        # Use the FIRST valid SQL/data pair we find
                        if sql_query == "N/A":
                            sql_query = potential_sql
                            chain_data = potential_data

                            logger.info(
                                f"EXTRACTOR: Using tuple step {i+1} - Data length: {len(potential_data) if hasattr(potential_data, '__len__') else 'N/A'}"
                            )

                            self.log_step(
                                "✅ Found first valid SQL/data pair",
                                f"SQL: {sql_query[:80]}..., Data: {str(potential_data)[:100]}...",
                            )

                            # CRITICAL: Break here to prevent Answer field from overriding
                            break
                    else:
                        logger.debug(
                            f"EXTRACTOR: Tuple step {i+1} invalid - SQL check: {isinstance(potential_sql, str) and ('SELECT' in potential_sql.upper() or 'WITH' in potential_sql.upper())}, Data check: {potential_data is not None}"
                        )

                # If we found both SQL and data, we can break
                if sql_query != "N/A" and chain_data is not None:
                    logger.debug(
                        f"EXTRACTOR: Found both SQL and data, breaking at step {i+1}"
                    )
                    break

        # Method 2: If no data found in intermediate_steps, check result['result']
        if chain_data is None:
            logger.debug(
                f"EXTRACTOR: No data in intermediate_steps, checking result['result']"
            )
            possible_data = result.get("result", "")
            logger.debug(
                f"EXTRACTOR: result['result'] type: {type(possible_data)}, preview: {str(possible_data)[:100]}"
            )

            # If result contains a string representation of the data, try to parse it
            if isinstance(possible_data, str) and possible_data.strip():
                # Check if it looks like the SQLResult data we saw in console
                if "[(" in possible_data and ")]" in possible_data:
                    try:
                        import ast
                        import datetime
                        import re as _re
                        from decimal import Decimal

                        # First try with ast.literal_eval (safer)
                        try:
                            parsed_data = ast.literal_eval(possible_data)
                        except (ValueError, SyntaxError):
                            # If ast.literal_eval fails, try to handle datetime objects and Decimal safely
                            # Replace datetime.date(Y, M, D) with 'YYYY-MM-DD' string
                            def _date_repl(match):
                                y, m, d = match.group(1), match.group(2), match.group(3)
                                try:
                                    y_i, m_i, d_i = int(y), int(m), int(d)
                                    return f"'{y_i:04d}-{m_i:02d}-{d_i:02d}'"
                                except Exception:
                                    return match.group(0)
                            
                            # Replace Decimal('...') with float value
                            def _decimal_repl(match):
                                decimal_str = match.group(1)
                                try:
                                    return str(float(decimal_str))
                                except Exception:
                                    return match.group(0)
                            
                            sanitized = _re.sub(
                                r"datetime\.date\(\s*(\d{1,4})\s*,\s*(\d{1,2})\s*,\s*(\d{1,2})\s*\)",
                                _date_repl,
                                possible_data,
                            )
                            sanitized = _re.sub(
                                r"Decimal\('([^']+)'\)",
                                _decimal_repl,
                                sanitized,
                            )
                            # Try again with sanitized string
                            parsed_data = ast.literal_eval(sanitized)
                        
                        if isinstance(parsed_data, list) and parsed_data:
                            chain_data = parsed_data
                            logger.info(
                                f"EXTRACTOR: Parsed data from result['result'] - Length: {len(parsed_data)}"
                            )
                    except Exception as e:
                        logger.warning(
                            f"EXTRACTOR: Failed to parse result['result']: {e}"
                        )
                        logger.debug(f"EXTRACTOR: Result data preview: {possible_data[:200]}...")

            # If result contains the data directly
            elif isinstance(possible_data, list) and possible_data:
                chain_data = possible_data
                logger.info(
                    f"EXTRACTOR: Using direct data from result['result'] - Length: {len(possible_data)}"
                )

        # Method 3: If no intermediate_steps, try result['result'] for SQL (fallback only)
        if sql_query == "N/A":
            possible_sql = result.get("result", "")
            if isinstance(possible_sql, str) and (
                "SELECT" in possible_sql.upper() or "WITH" in possible_sql.upper()
            ):
                sql_query = self.clean_sql_response(possible_sql)
                self.log_step("📝 Using result as SQL (fallback)", sql_query[:80])

        self.log_step(
            "🎯 Final extraction result",
            f"SQL found: {sql_query != 'N/A'}, Data found: {chain_data is not None}, "
            f"Data type: {type(chain_data)}, Data length: {len(chain_data) if hasattr(chain_data, '__len__') else 'N/A'}",
        )

        return sql_query, chain_data

    def clean_sql_response(self, sql_text: str) -> str:
        """Clean SQL response by removing markdown and extra formatting while preserving SQL structure"""
        if not isinstance(sql_text, str):
            return ""

        import re

        # Remove leading and trailing spaces
        cleaned = sql_text.strip()

        # STEP 1: Remove multiline markdown code blocks
        # Pattern for ```\nSELECT...\n```
        multiline_pattern = r"^```\s*\n(.*?)\n```$"
        match = re.search(multiline_pattern, cleaned, re.DOTALL | re.IGNORECASE)
        if match:
            cleaned = match.group(1).strip()
        else:
            # STEP 2: Remove inline code blocks ```sql...```
            inline_pattern = r"^```(?:sql)?\s*\n?(.*?)\n?```$"
            match = re.search(inline_pattern, cleaned, re.DOTALL | re.IGNORECASE)
            if match:
                cleaned = match.group(1).strip()

        # STEP 3: Remove loose backticks at beginning or end (multiple iterations)
        while cleaned.startswith("`") or cleaned.endswith("`"):
            cleaned = cleaned.strip("`").strip()

        # STEP 4: If there are still backticks at line beginnings, remove them
        lines = cleaned.split("\n")
        cleaned_lines = []
        for line in lines:
            line = line.strip()
            # Remove backticks at line beginning
            while line.startswith("`"):
                line = line[1:].strip()
            if line:  # Only add non-empty lines
                cleaned_lines.append(line)

        # STEP 5: Join all lines back together (CRITICAL FIX: Don't filter individual lines)
        # The original filtering was destroying valid SQL structure
        result = "\n".join(cleaned_lines).strip()

        # STEP 6: Clean up excessive whitespace but preserve structure
        result = re.sub(r"\n\s*\n", "\n", result)  # Remove empty lines
        result = re.sub(r"[ \t]+", " ", result)    # Normalize spaces/tabs to single space

        return result

    def _handle_metadata_query(self, user_question: str) -> Dict[str, Any]:
        """Handle metadata queries directly without LLM processing.

        Returns None if not a metadata query, or result dict if handled.
        """
        user_lower = user_question.lower().strip()
        try:
            self.log_step("🔎 Metadata detector", user_lower)
        except Exception:
            pass

        # Check for table listing queries
        table_queries = [
            "show tables",
            "show me tables",
            "show all tables",
            "show me all tables",
            "list tables",
            "list all tables",
            "what tables",
            "which tables",
            "tables available",
            "available tables",
            "table names",
            "all tables",
        ]

        # Check for table count queries
        table_count_queries = [
            "how many tables",
            "how many tables are there",
            "how many tables do we have",
            "how many tables in the database",
            "how many tables in database",
            "count of tables",
            "number of tables",
            "total tables",
            "table count",
            "how many tables that we have",
            "how many tables we have",
        ]

        # Check for database info queries
        database_queries = [
            "what database",
            "which database",
            "wich database",
            "current database",
            "database name",
            "what db",
            "which db",
            "wich db",
            "current db",
            "db name",
            "database we are using",
            "database are we using",
            "what database we are use",
            "what database we use",
            "database we use now",
            "what database are we using now",
        ]

        # Check for schema info queries (include common typos and variants)
        schema_queries = [
            "what schema",
            "which schema",
            "wich schema",
            "current schema",
            "schema name",
            "what schema are we using",
            "schema we are using",
        ]

        # Check for role info queries (include common typos and variants)
        role_queries = [
            "what role",
            "which role",
            "wich role",
            "current role",
            "role name",
            "what role are we using",
            "role we are using",
        ]

        # Check for warehouse info queries (include common typos and variants)
        warehouse_queries = [
            "what warehouse",
            "which warehouse",
            "wich warehouse",
            "current warehouse",
            "warehouse name",
            "what warehouse are we using",
            "warehouse we are using",
        ]

        # Check for table count queries first (more specific)
        if any(query in user_lower for query in table_count_queries):
            try:
                # Count tables in current schema
                sql = "SELECT COUNT(*) AS table_count FROM INFORMATION_SCHEMA.TABLES WHERE TABLE_SCHEMA = CURRENT_SCHEMA() AND TABLE_TYPE IN ('BASE TABLE', 'VIEW')"
                self.log_step("📊 Table Count Query", "Counting tables in current schema")
                result = self.db.run(sql)
                return {
                    "success": True,
                    "result": result,
                    "sql_query": sql,
                    "query_type": "metadata",
                }
            except Exception as e:
                logger.error(f"Table count query error: {e}")
                self.log_step("⚠️ Table Count Error", str(e))
                return None

        elif any(query in user_lower for query in table_queries):
            try:
                # Use cleaner metadata query for tables
                sql = "SELECT TABLE_NAME, TABLE_TYPE FROM INFORMATION_SCHEMA.TABLES WHERE TABLE_SCHEMA = CURRENT_SCHEMA() ORDER BY TABLE_NAME"
                self.log_step("📋 Metadata Query", "Listing all tables")
                result = self.db.run(sql)
                return {
                    "success": True,
                    "result": result,
                    "sql_query": sql,
                    "query_type": "metadata",
                }
            except Exception as e:
                logger.error(f"Table listing query error: {e}")
                self.log_step("⚠️ Metadata Error", str(e))
                return None

        elif any(query in user_lower for query in database_queries) or __import__(
            "re"
        ).search(r"\b(what|which|wich|current)\b.*\b(database|db)\b", user_lower):
            try:
                # Get current database name
                sql = "SELECT CURRENT_DATABASE() AS database_name"
                self.log_step("🗂️ Database Query", "Getting current database name")
                result = self.db.run(sql)
                return {
                    "success": True,
                    "result": result,
                    "sql_query": sql,
                    "query_type": "metadata",
                }
            except Exception as e:
                self.log_step("⚠️ Database Query Error", str(e))
                return None

        elif any(query in user_lower for query in schema_queries) or __import__(
            "re"
        ).search(r"\b(what|which|wich|current)\b.*\b(schema)\b", user_lower):
            try:
                # Get current schema name
                sql = "SELECT CURRENT_SCHEMA() AS schema_name"
                self.log_step("📋 Schema Query", "Getting current schema name")
                result = self.db.run(sql)
                return {
                    "success": True,
                    "result": result,
                    "sql_query": sql,
                    "query_type": "metadata",
                }
            except Exception as e:
                self.log_step("⚠️ Schema Query Error", str(e))
                return None

        # Role query detection
        elif any(query in user_lower for query in role_queries) or __import__(
            "re"
        ).search(r"\b(what|which|wich|current)\b.*\b(role)\b", user_lower):
            try:
                sql = "SELECT CURRENT_ROLE() AS role_name"
                self.log_step("👤 Role Query", "Getting current role")
                result = self.db.run(sql)
                return {
                    "success": True,
                    "result": result,
                    "sql_query": sql,
                    "query_type": "metadata",
                }
            except Exception as e:
                self.log_step("⚠️ Role Query Error", str(e))
                return None

        # Warehouse query detection
        elif any(query in user_lower for query in warehouse_queries) or __import__(
            "re"
        ).search(r"\b(what|which|wich|current)\b.*\b(warehouse)\b", user_lower):
            try:
                sql = "SELECT CURRENT_WAREHOUSE() AS warehouse_name"
                self.log_step("🏭 Warehouse Query", "Getting current warehouse")
                result = self.db.run(sql)
                return {
                    "success": True,
                    "result": result,
                    "sql_query": sql,
                    "query_type": "metadata",
                }
            except Exception as e:
                self.log_step("⚠️ Warehouse Query Error", str(e))
                return None

        # Show specific table content: e.g., "show me agents table"
        else:
            import re

            # FIRST: Check if this is a complex query that should go to LLM
            # Indicators that this is NOT a simple table preview:
            complex_indicators = [
                r'\btop\s+\d+',           # "top 10", "top 5"
                r'\blimit\s+\d+',         # "limit 10"
                r'\bwhere\b',             # WHERE clause
                r'\bby\s+\w+\s+in\b',     # "by price in"
                r'\border\s+by\b',        # ORDER BY
                r'\bgroup\s+by\b',        # GROUP BY
                r'\bhaving\b',            # HAVING
                r'\bjoin\b',              # JOIN
                r'\bwith\s+\w+\s+\w+',    # "with X Y" (conditions)
                r'\bgreater\s+than\b',    # comparisons
                r'\bless\s+than\b',
                r'\bmore\s+than\b',
                r'\bequal\s+to\b',
                r'\bbetween\b',
                r'\bwhere\s+\w+\s*[><=]', # WHERE with operators
                r'\b(?:highest|lowest|most|least|best|worst)\b',  # superlatives
                r'\baverage\b',           # aggregations
                r'\bsum\b',
                r'\bcount\b',
                r'\bmax\b',
                r'\bmin\b',
            ]
            
            # Check if query contains complex patterns
            is_complex = False
            for pattern in complex_indicators:
                if re.search(pattern, user_lower):
                    is_complex = True
                    logger.info(f"Complex query detected (pattern: {pattern}) - will use LLM")
                    break
            
            # Check for location patterns "in [Multi-Word Location]"
            if not is_complex and re.search(r'\bin\s+[A-Z][a-z]+\s+[A-Z]', user_question, re.IGNORECASE):
                is_complex = True
                logger.info("Complex query detected (multi-word location) - will use LLM")
            
            # If complex query detected, return None to let LLM handle it
            if is_complex:
                return None
            
            # Pattern 1: show [me|the] <table> table (explicit "table" keyword)
            # This captures the word immediately before "table"
            m1 = re.search(
                r"\bshow\s+(?:me\s+)?(?:the\s+)?([a-zA-Z0-9_]+)\s+table\b",
                user_lower,
            )
            
            # Pattern 2: show [me] [stopwords...] <table> (implicit table name)
            # This finds the LAST word that is NOT a stopword
            # BUT only for SHORT, SIMPLE queries
            candidate = None
            
            if m1:
                candidate = m1.group(1)
                logger.info(f"Table name extracted via Pattern 1 (explicit): {candidate}")
            else:
                # Only try implicit pattern if query is short and simple
                words = user_lower.split()
                
                # If query is too long (>5 words), it's probably complex
                if len(words) > 5:
                    logger.info(f"Query too long ({len(words)} words) - assuming complex, will use LLM")
                    return None
                
                # Parse words after "show"
                if len(words) >= 2 and words[0] == 'show':
                    # Remove 'show' and find the last non-stopword
                    remaining = words[1:]
                    
                    # Find the last word that's not a stopword
                    for word in reversed(remaining):
                        # Clean punctuation
                        word_clean = re.sub(r'\W+', '', word)
                        if word_clean and word_clean not in self.TABLE_NAME_STOPWORDS:
                            candidate = word_clean
                            logger.info(f"Table name extracted via Pattern 2 (implicit): {candidate}")
                            break
            
            # Final validation: ensure candidate is not a stopword
            if candidate and candidate.lower() in self.TABLE_NAME_STOPWORDS:
                logger.warning(f"Rejected candidate '{candidate}' - it's a stopword")
                candidate = None

            if candidate:
                table = candidate
                self.log_step(
                    "🧭 Intent: Table Preview", f"Detected table name: {table}"
                )
                # Validate table name to prevent SQL injection
                try:
                    validated_table = validate_table_name(table)
                    
                    # Enhanced validation: verify table exists in schema
                    if not self.context_enhancer.schema_inspector.validate_table_exists(validated_table):
                        similar_tables = self.context_enhancer.schema_inspector.get_similar_table_names(validated_table)
                        error_msg = f"Table '{validated_table}' not found in current schema."
                        if similar_tables:
                            error_msg += f" Did you mean: {', '.join(similar_tables[:3])}?"
                        self.log_step("⚠️ Table Not Found", error_msg)
                        return {
                            "success": False,
                            "error": error_msg,
                            "query_type": "error",
                        }
                    
                    try:
                        # Build preview SQL using config-driven limit and optional sampling
                        limit_val = max(
                            1, int(getattr(config, "SHOW_TABLE_LIMIT", 100))
                        )
                        sample_pct = float(
                            getattr(config, "SHOW_TABLE_SAMPLE_PERCENT", 0.0)
                        )
                        if sample_pct > 0.0:
                            # Snowflake SAMPLE expects a percent value; we pass as-is
                            # Table name is validated, safe to use in f-string
                            sql = f"SELECT * FROM {validated_table} SAMPLE ({sample_pct}) LIMIT {limit_val}"
                            self.log_step(
                                "🎲 Sampling Enabled",
                                f"SAMPLE=({sample_pct}), LIMIT={limit_val}",
                            )
                        else:
                            sql = f"SELECT * FROM {validated_table} LIMIT {limit_val}"
                            self.log_step("🎚️ Sampling Disabled", f"LIMIT={limit_val}")
                        self.log_step(
                            "📄 Table Preview",
                            f"Fetching sample rows from table: {validated_table}",
                        )
                        result = self.db.run(sql)
                        return {
                            "success": True,
                            "result": result,
                            "sql_query": sql,
                            "query_type": "data_preview",
                        }
                    except OperationalError as e:
                        logger.error(f"Database connection error during table preview: {e}")
                        self.log_step("⚠️ Table Preview Error", f"Connection error: {str(e)}")
                        return None
                    except ProgrammingError as e:
                        logger.error(f"SQL error during table preview: {e}")
                        self.log_step("⚠️ Table Preview Error", f"SQL error: {str(e)}")
                        return None
                    except SQLAlchemyError as e:
                        logger.error(f"Database error during table preview: {e}")
                        self.log_step("⚠️ Table Preview Error", f"Database error: {str(e)}")
                        return None
                    except Exception as e:
                        logger.exception(f"Unexpected error during table preview: {e}")
                        self.log_step("⚠️ Table Preview Error", str(e))
                        return None
                except ValueError as e:
                    self.log_step(
                        "⚠️ Table Preview Skipped", f"Invalid table identifier: {e}"
                    )
                    return None

            # Fallback: try to detect a table name present in the schema and in the text
            # This helps when the phrase order confuses the regex
            try:
                # Fetch up to 200 table names from current schema
                tbls_sql = "SELECT TABLE_NAME FROM INFORMATION_SCHEMA.TABLES WHERE TABLE_SCHEMA = CURRENT_SCHEMA() LIMIT 200"
                tables_res = self.db.run(tbls_sql)
                schema_tables = set()
                for row in tables_res or []:
                    name = (
                        row[0]
                        if isinstance(row, (list, tuple))
                        else list(row.values())[0]
                    )
                    schema_tables.add(str(name).lower())
                # Find any table name as a whole word in user_lower
                for t in schema_tables:
                    if re.search(rf"\b{re.escape(t)}\b", user_lower):
                        table = t
                        self.log_step(
                            "🧭 Intent: Table Preview (fallback)",
                            f"Matched schema table: {table}",
                        )
                        # Validate table name to prevent SQL injection
                        try:
                            validated_table = validate_table_name(table)
                            limit_val = max(
                                1, int(getattr(config, "SHOW_TABLE_LIMIT", 100))
                            )
                            sample_pct = float(
                                getattr(config, "SHOW_TABLE_SAMPLE_PERCENT", 0.0)
                            )
                            if sample_pct > 0.0:
                                # Table name is validated, safe to use in f-string
                                sql = f"SELECT * FROM {validated_table} SAMPLE ({sample_pct}) LIMIT {limit_val}"
                                self.log_step(
                                    "🎲 Sampling Enabled",
                                    f"SAMPLE=({sample_pct}), LIMIT={limit_val}",
                                )
                            else:
                                sql = f"SELECT * FROM {validated_table} LIMIT {limit_val}"
                                self.log_step("🎚️ Sampling Disabled", f"LIMIT={limit_val}")
                            self.log_step(
                                "📄 Table Preview",
                                f"Fetching sample rows from table: {validated_table}",
                            )
                            result = self.db.run(sql)
                            return {
                                "success": True,
                                "result": result,
                                "sql_query": sql,
                                "query_type": "data_preview",
                            }
                        except ValueError as e:
                            self.log_step(
                                "⚠️ Table Preview Skipped (fallback)", f"Invalid table identifier: {e}"
                            )
                            continue  # Try next table
            except Exception as e:
                self.log_step("⚠️ Table Name Fallback Error", str(e))

        self.log_step("ℹ️ Metadata detector", "No metadata intent matched")
        return None  # Not a metadata query

    def _is_count_query(self, user_question: str) -> bool:
        """Check if the user question is asking for a count/total"""
        user_lower = user_question.lower().strip()
        count_indicators = [
            "how many",
            "how much",
            "count",
            "total",
            "number of",
            "cantidad",
            "cuantos",
            "cuantas",
            "total de",
            "numero de",
            "registers",
            "registros",
            "records",
            "rows",
            "filas",
        ]
        return any(indicator in user_lower for indicator in count_indicators)

    def _handle_count_queries(self, user_question: str) -> Dict[str, Any]:
        """Handle count/aggregation queries directly to avoid LLM confusion"""
        user_lower = user_question.lower().strip()

        # Extract table name from common patterns
        import re

        # Skip if this is a metadata query about tables (handled by _handle_metadata_query)
        # Check for "how many tables" patterns first to avoid false positives
        table_count_patterns = [
            "how many tables",
            "count of tables",
            "number of tables",
            "total tables",
            "table count"
        ]
        if any(pattern in user_lower for pattern in table_count_patterns):
            return None  # Let metadata query handler process this
        
        # Pattern 1: "how many X on/in Y table"
        match = re.search(
            r"how many.*(?:on|in|from)\s+([a-zA-Z0-9_]+)\s+table", user_lower
        )
        if not match:
            # Pattern 2: "how many Y" - but exclude "tables" keyword and stopwords
            match = re.search(r"how many\s+([a-zA-Z0-9_]+)", user_lower)
            # Skip if the matched word is a stopword or "tables"
            if match and (match.group(1).lower() == "tables" or match.group(1).lower() in self.TABLE_NAME_STOPWORDS):
                match = None
        if not match:
            # Pattern 3: "count of/from Y" - but exclude "tables" keyword and stopwords
            match = re.search(r"count.*(?:of|from)\s+([a-zA-Z0-9_]+)", user_lower)
            # Skip if the matched word is a stopword or "tables"
            if match and (match.group(1).lower() == "tables" or match.group(1).lower() in self.TABLE_NAME_STOPWORDS):
                match = None

        if match:
            table_name = match.group(1).strip()

            # Validate table name format and existence
            try:
                validated_table = validate_table_name(table_name)
                
                # Enhanced validation: verify table exists in schema
                if not self.context_enhancer.schema_inspector.validate_table_exists(validated_table):
                    similar_tables = self.context_enhancer.schema_inspector.get_similar_table_names(validated_table)
                    error_msg = f"Table '{validated_table}' not found in current schema."
                    if similar_tables:
                        error_msg += f" Did you mean: {', '.join(similar_tables[:3])}?"
                    logger.warning(f"Count query failed: {error_msg}")
                    self.log_step("⚠️ Table Not Found", error_msg)
                    return {
                        "success": False,
                        "error": error_msg,
                        "query_type": "error",
                    }
                
                # Generate simple COUNT query
                # Table name is validated, safe to use in f-string
                sql = f"SELECT COUNT(*) AS total_count FROM {validated_table}"
                self.log_step("🔢 Direct count query", f"Generated: {sql}")
                
                # Execute directly
                result = self.db.run(sql)
                logger.info(f"Count query executed successfully for table: {validated_table}")
                self.log_step("✅ Count query executed", f"Result: {result}")

                return {
                    "success": True,
                    "result": result,
                    "sql_query": sql,
                    "query_type": "count",
                }
            except ValueError as e:
                logger.warning(f"Count query failed: Invalid table name: {e}")
                self.log_step("⚠️ Direct count failed", f"Invalid table name: {e}")
                return None
            except OperationalError as e:
                logger.error(f"Database connection error during count query: {e}")
                self.log_step("⚠️ Direct count failed", f"Connection error: {str(e)}")
                return None
            except ProgrammingError as e:
                logger.error(f"SQL error during count query: {e}")
                self.log_step("⚠️ Direct count failed", f"SQL error: {str(e)}")
                return None
            except SQLAlchemyError as e:
                logger.error(f"Database error during count query: {e}")
                self.log_step("⚠️ Direct count failed", f"Database error: {str(e)}")
                return None
            except Exception as e:
                logger.exception(f"Unexpected error during count query: {e}")
                self.log_step("⚠️ Direct count failed", f"Error: {str(e)}")
                return None

        return None

    def process_query(
        self, user_question: str, use_enhanced_context: bool = True, 
        use_cache: bool = True, page: int = 1, page_size: Optional[int] = None
    ) -> Dict[str, Any]:
        """Process user query with enhanced context and return data ready for the UI.

        Enhanced Flow:
        1) Check for direct count queries first (to avoid LLM confusion)
        2) Check for metadata queries
        3) Get enhanced context (schema + query history + domain insights)
        4) Generate enhanced prompt with rich context
        5) Invoke SQL chain with enhanced prompt
        6) Extract generated SQL from LangChain intermediate_steps
        7) Record query execution for learning
        8) Return results with comprehensive logging

        Args:
            user_question: The user's natural language question
            use_enhanced_context: Whether to use the enhanced context system

        Returns:
            Dict with success, result, sql_query, and metadata
        """
        start_time = time.time()
        execution_success = False
        generated_sql = None
        result_count = None
        error_message = None
        total_count = None  # For pagination

        try:
            # Log processing start
            self.log_step("🔍 Processing query", user_question)
            
            # Check cache first (if enabled and not paginating)
            if use_cache and page == 1:
                # For cache lookup, we need the SQL first, but we'll check after SQL generation
                # For now, we'll check cache after SQL is generated
                pass

            # FIRST: Check for metadata queries (direct handling) - must be before count queries
            # This ensures "how many tables" is handled as metadata, not as count query
            metadata_result = self._handle_metadata_query(user_question)
            if metadata_result is not None:
                # Cache metadata results too
                if use_cache and "sql_query" in metadata_result:
                    self.query_cache.cache_result(
                        metadata_result["sql_query"], 
                        metadata_result.get("result")
                    )
                return metadata_result

            # SECOND: Check for count queries (direct handling to avoid LLM confusion)
            # Only process if not already handled as metadata query
            if self._is_count_query(user_question):
                count_result = self._handle_count_queries(user_question)
                if count_result is not None:
                    return count_result

            # Get enhanced context if enabled
            enhanced_context = None
            if use_enhanced_context:
                try:
                    self.log_step(
                        "🧠 Getting enhanced context",
                        "Analyzing schema and query history",
                    )
                    enhanced_context = self.context_enhancer.get_enhanced_context(
                        user_question=user_question,
                        refresh_schema=False,
                        include_samples=True,
                        include_history=True,
                    )

                    self.log_step(
                        "📊 Context quality",
                        f"Quality: {enhanced_context.context_quality_score:.2f}, "
                        f"Tables: {len(enhanced_context.database_context.tables)}, "
                        f"Similar queries: {len(enhanced_context.query_context.similar_successful_queries)}",
                    )

                    # Generate enhanced prompt
                    base_prompt = prompt_loader.get_sql_prompt("enhanced")
                    enhanced_prompt = self.context_enhancer.generate_enhanced_prompt(
                        user_question=user_question,
                        base_prompt=base_prompt,
                        enhanced_context=enhanced_context,
                    )

                    # Create a new chain with enhanced prompt for this query
                    from langchain.prompts import PromptTemplate

                    enhanced_chain = SQLDatabaseChain.from_llm(
                        self.llm,
                        self.db,
                        verbose=True,
                        return_intermediate_steps=True,
                        prompt=PromptTemplate(
                            input_variables=["input", "table_info"],
                            template=enhanced_prompt,
                        ),
                    )

                    self.log_step(
                        "✨ Enhanced context applied", "Using context-aware prompt"
                    )
                    result = enhanced_chain.invoke({"input": user_question})

                except Exception as e:
                    self.log_step(
                        "⚠️ Context enhancement failed",
                        f"Falling back to standard mode: {str(e)}",
                    )
                    result = self.sql_chain.invoke(user_question)
            else:
                # Standard processing without enhanced context
                self.log_step("🔧 Standard processing", "Using base SQL chain")
                result = self.sql_chain.invoke(user_question)

            # Extract SQL and data from LangChain result using our robust method
            sql_query, chain_data = self.extract_sql_and_data_from_chain_result(
                result, user_question
            )
            generated_sql = sql_query if sql_query != "N/A" else None
            
            # Debug log the initial extraction
            self.log_step(
                "🎯 Initial SQL Extraction",
                f"SQL extracted: {'Yes' if generated_sql else 'No'}, "
                f"SQL preview: {(generated_sql[:80] + '...') if generated_sql else 'None'}, "
                f"Data extracted: {'Yes' if chain_data else 'No'}"
            )

            if "intermediate_steps" in result and result["intermediate_steps"]:
                self.log_step(
                    "🔍 Analyzing intermediate_steps",
                    f"Steps found: {len(result['intermediate_steps'])}",
                )

                # Track if we found multiple SQL queries (which shouldn't happen for count queries)
                sql_queries_found = []

                for i, step in enumerate(result["intermediate_steps"]):
                    self.log_step(
                        f"📋 Step {i+1}",
                        f"Type: {type(step)}, Content preview: {str(step)[:100]}...",
                    )

                    # DETAILED LOGGING: Let's see exactly what's in each step
                    if isinstance(step, tuple):
                        self.log_step(
                            f"📋 Step {i+1} - Tuple Analysis",
                            f"Tuple length: {len(step)}, "
                            f"Item 0 type: {type(step[0]) if len(step) > 0 else 'N/A'}, "
                            f"Item 0 preview: {str(step[0])[:100] if len(step) > 0 else 'N/A'}..., "
                            f"Item 1 type: {type(step[1]) if len(step) > 1 else 'N/A'}, "
                            f"Item 1 preview: {str(step[1])[:100] if len(step) > 1 else 'N/A'}...",
                        )

                    # SQLDatabaseChain typically stores steps as tuples: (sql_query, sql_result)
                    if isinstance(step, tuple) and len(step) == 2:
                        potential_sql, potential_data = step
                        if (
                            isinstance(potential_sql, str)
                            and "SELECT" in potential_sql.upper()
                        ):
                            sql_queries_found.append(potential_sql)

                            # ONLY override if we don't already have extracted SQL
                            if not generated_sql and sql_query == "N/A":
                                sql_query = potential_sql
                                generated_sql = potential_sql
                                chain_data = potential_data
                                self.log_step(
                                    "✅ Found SQL and data in tuple (fallback)",
                                    f"SQL: {sql_query[:50]}..., Data preview: {str(potential_data)[:100]}...",
                                )

                                # For ANY query type, use the FIRST valid result and break
                                # This prevents LLM confusion from overriding correct results
                                self.log_step(
                                    "🎯 Using first valid SQL/data pair (fallback)",
                                    "Ignoring any additional SQL queries",
                                )
                                break

                    # Legacy format handling - only if we don't have SQL yet
                    elif isinstance(step, dict) and not generated_sql:
                        potential_sql = (
                            step.get("sql_cmd") or step.get("query") or step.get("sql")
                        )
                        potential_data = (
                            step.get("sql_result")
                            or step.get("result")
                            or step.get("data")
                        )

                        if potential_sql:
                            sql_queries_found.append(potential_sql)
                            if sql_query == "N/A":
                                sql_query = potential_sql
                                generated_sql = potential_sql
                                self.log_step("📝 Found SQL in dict (fallback)", sql_query)
                        if potential_data:
                            chain_data = potential_data
                            self.log_step(
                                "📊 Found data in dict (fallback)",
                                f"Data preview: {str(potential_data)[:100]}...",
                            )

                        if sql_query != "N/A" and chain_data:
                            break

                    # Some providers may pass SQL as a raw string step - only if we don't have SQL yet
                    elif isinstance(step, str) and "SELECT" in step.upper() and not generated_sql:
                        sql_queries_found.append(step)
                        if sql_query == "N/A":
                            sql_query = step
                            generated_sql = step
                            self.log_step(
                                "📝 Found SQL as raw string in steps (fallback)", sql_query[:120]
                            )

                # Log warning if multiple SQL queries were found
                if len(sql_queries_found) > 1:
                    self.log_step(
                        "⚠️ Multiple SQL queries detected",
                        f"Found {len(sql_queries_found)} queries, using the first one",
                    )
                    for i, sql in enumerate(sql_queries_found):
                        self.log_step(
                            f"📝 SQL {i+1}",
                            sql[:100] + "..." if len(sql) > 100 else sql,
                        )

            # If no SQL from steps and not from initial extraction, check if result['result'] itself holds SQL text
            # BUT ONLY if we haven't found a valid SQL from intermediate steps or initial extraction
            # AND we're not dealing with the problematic "Answer" field
            if not generated_sql and sql_query == "N/A" and "intermediate_steps" not in result:
                possible_sql = result.get("result")
                if isinstance(possible_sql, str) and "SELECT" in possible_sql.upper():
                    # This is a fallback for chains that don't produce intermediate steps
                    sql_query = self.clean_sql_response(possible_sql)
                    generated_sql = sql_query
                    self.log_step(
                        "📝 Found SQL in result['result'] (final fallback)", sql_query[:120]
                    )

            # IMPORTANT: If we have chain_data with results, DON'T use result['result']
            # as it often contains the problematic "Answer" SQL
            if chain_data is not None and generated_sql and sql_query != "N/A":
                self.log_step(
                    "🛡️ Preventing Answer field interference",
                    "Have valid chain_data and SQL, ignoring result['result']",
                )
            
            # Final SQL assignment - preserve what we already found
            if not generated_sql and sql_query != "N/A":
                generated_sql = sql_query

            # Process results
            actual_result = None

            # Debug logging for chain_data
            self.log_step(
                "🔍 Chain Data Analysis",
                f"chain_data type: {type(chain_data)}, "
                f"is None: {chain_data is None}, "
                f"has length: {hasattr(chain_data, '__len__')}, "
                f"length: {len(chain_data) if hasattr(chain_data, '__len__') else 'N/A'}, "
                f"preview: {str(chain_data)[:150]}...",
            )

            # Phase 2: Validate SQL before using intermediate_steps data
            if generated_sql:
                cleaned_sql_for_validation = self.clean_sql_response(generated_sql)
                validation_result_pre = self.sql_validator.validate_query(cleaned_sql_for_validation)
                if not validation_result_pre["valid"]:
                    # If validation fails, don't use intermediate_steps data
                    self.log_step(
                        "❌ SQL Validation Failed",
                        "Skipping intermediate_steps data due to validation errors"
                    )
                    chain_data = None  # Force manual execution with validation
            
            # If we found data in intermediate_steps and it looks like rows, use it; else fall back to manual exec
            looks_like_rows = False
            try:
                if isinstance(chain_data, list) and chain_data:
                    first = chain_data[0]
                    looks_like_rows = isinstance(first, (tuple, list, dict)) or hasattr(
                        first, "_mapping"
                    )
                    self.log_step(
                        "🔍 Row Validation",
                        f"First item type: {type(first)}, looks_like_rows: {looks_like_rows}",
                    )
            except Exception as e:
                looks_like_rows = False
                self.log_step("⚠️ Row validation error", str(e))

            if chain_data is not None and looks_like_rows:
                self.log_step(
                    "🎯 Using data from intermediate_steps",
                    f"Rows: {len(chain_data) if hasattr(chain_data, '__len__') else 'N/A'}",
                )
                actual_result = chain_data
                execution_success = True
                result_count = (
                    len(chain_data) if hasattr(chain_data, "__len__") else None
                )
                self.log_step(
                    "✅ Data successfully assigned to actual_result",
                    f"actual_result type: {type(actual_result)}, length: {len(actual_result) if hasattr(actual_result, '__len__') else 'N/A'}",
                )
            else:
                self.log_step(
                    "❌ Data from intermediate_steps not usable",
                    f"chain_data is None: {chain_data is None}, looks_like_rows: {looks_like_rows}",
                )

            # CRITICAL FIX: ALWAYS try manual execution if we have valid SQL
            # This ensures queries execute even when LangChain chain fails
            if generated_sql and not execution_success:
                self.log_step(
                    "🔄 Manual execution (LangChain fallback)",
                    "Executing SQL directly to ensure results",
                )

                # Clean SQL (remove markdown/backticks)
                cleaned_sql = self.clean_sql_response(generated_sql)
                self.log_step(
                    "🧹 SQL after cleaning",
                    f"Original: {generated_sql[:60]}... -> Cleaned: {cleaned_sql[:60]}...",
                )
                
                # Phase 2: Validate SQL before execution
                validation_result = self.sql_validator.validate_query(cleaned_sql)
                if not validation_result["valid"]:
                    error_msg = "SQL validation failed: " + "; ".join(validation_result["errors"])
                    self.log_step("❌ SQL Validation Failed", error_msg)
                    return {
                        "success": False,
                        "error": error_msg,
                        "result": None,
                        "sql_query": cleaned_sql,
                        "validation": validation_result,
                        "suggestions": self.query_corrector.suggest_corrections(
                            cleaned_sql, error_msg, 
                            schema={"tables": self.context_enhancer.schema_inspector._table_cache or []}
                        ) if hasattr(self, 'context_enhancer') else []
                    }
                
                # Log warnings if any
                if validation_result["warnings"]:
                    self.log_step(
                        "⚠️ SQL Validation Warnings",
                        "; ".join(validation_result["warnings"])
                    )
                
                # Calculate confidence score
                context_info = {}
                if hasattr(self, 'context_enhancer') and self.context_enhancer:
                    try:
                        enhanced_context = self.context_enhancer.get_enhanced_context(
                            user_question, refresh_schema=False, include_samples=False, include_history=False
                        )
                        context_info = {
                            "tables": [t.name for t in enhanced_context.database_context.tables] if enhanced_context.database_context.tables else []
                        }
                    except:
                        pass
                
                confidence = self.confidence_scorer.calculate_confidence(
                    cleaned_sql, user_question, context_info, validation_result
                )
                self.log_step(
                    "🎯 Confidence Score",
                    f"Overall: {confidence['overall']:.2f}, "
                    f"Syntax: {confidence['syntax']:.2f}, "
                    f"Semantic: {confidence['semantic']:.2f}"
                )
                
                # Generate query explanation
                explanation = self.query_explainer.explain_query(cleaned_sql, user_question)
                self.log_step("📖 Query Explanation", explanation)

                # Accept common starters, including CTEs (WITH ...)
                if cleaned_sql and cleaned_sql.upper().startswith(
                    ("SELECT", "SHOW", "DESCRIBE", "WITH")
                ):
                    try:
                        # Check cache before executing
                        if use_cache and page == 1:
                            cached_result = self.query_cache.get_cached_result(cleaned_sql)
                            if cached_result is not None:
                                self.log_step("⚡ Cache HIT", "Using cached results")
                                actual_result = cached_result
                                execution_success = True
                                result_count = (
                                    len(actual_result)
                                    if hasattr(actual_result, "__len__")
                                    else None
                                )
                                generated_sql = cleaned_sql
                                # Skip execution, use cached result
                            else:
                                self.log_step("🚀 Executing cleaned SQL", cleaned_sql)
                                # Apply pagination if needed
                                paginated_sql = cleaned_sql
                                count_sql = None
                                total_count = None
                                
                                # Check if pagination is needed
                                if page_size is not None or self.query_paginator.should_paginate(
                                    result_count or 0, threshold=100
                                ):
                                    if page_size is None:
                                        page_size = self.query_paginator.default_page_size
                                    paginated_sql, count_sql = self.query_paginator.paginate_sql(
                                        cleaned_sql, page=page, page_size=page_size
                                    )
                                    self.log_step(
                                        "📄 Pagination applied",
                                        f"Page {page}, Page size: {page_size}"
                                    )
                                
                                # Execute paginated query
                                manual_result = self.db.run(paginated_sql)
                                
                                # Get total count if pagination is used
                                if count_sql:
                                    try:
                                        count_result = self.db.run(count_sql)
                                        total_count = self.query_paginator.extract_count_from_result(count_result)
                                        self.log_step(
                                            "📊 Total count",
                                            f"Total rows: {total_count}"
                                        )
                                    except Exception as e:
                                        logger.warning(f"Failed to get total count: {e}")
                                
                                actual_result = manual_result
                                execution_success = True
                                result_count = (
                                    len(actual_result)
                                    if hasattr(actual_result, "__len__")
                                    else None
                                )
                                # Ensure the cleaned SQL is what's stored
                                generated_sql = cleaned_sql
                                
                                # Cache result (only for first page, non-paginated queries)
                                if use_cache and page == 1 and (page_size is None or total_count is None):
                                    self.query_cache.cache_result(cleaned_sql, actual_result)
                                    self.log_step("💾 Cached result", "Result saved to cache")

                                self.log_step(
                                    "✅ Manual execution successful",
                                    f"Got {result_count} rows. Data preview: {str(actual_result)[:100]}...",
                                )
                        else:
                            # No cache or pagination - execute directly
                            self.log_step("🚀 Executing cleaned SQL", cleaned_sql)
                            manual_result = self.db.run(cleaned_sql)
                            actual_result = manual_result
                            execution_success = True
                            result_count = (
                                len(actual_result)
                                if hasattr(actual_result, "__len__")
                                else None
                            )
                            generated_sql = cleaned_sql

                            self.log_step(
                                "✅ Manual execution successful",
                                f"Got {result_count} rows. Data preview: {str(actual_result)[:100]}...",
                            )
                    except Exception as e:
                        execution_success = False
                        error_message = str(e)
                        self.log_step("⚠️ Error executing SQL", error_message)
                        actual_result = []
                        
                        # Phase 2: Suggest corrections for errors
                        try:
                            context_info = {}
                            if hasattr(self, 'context_enhancer') and self.context_enhancer:
                                try:
                                    enhanced_context = self.context_enhancer.get_enhanced_context(
                                        user_question, refresh_schema=False, include_samples=False, include_history=False
                                    )
                                    context_info = {
                                        "tables": [t.name for t in enhanced_context.database_context.tables] if enhanced_context.database_context.tables else []
                                    }
                                except:
                                    pass
                            
                            suggestions = self.query_corrector.suggest_corrections(
                                cleaned_sql, error_message, context_info
                            )
                            if suggestions:
                                self.log_step(
                                    "💡 Correction Suggestions",
                                    f"Found {len(suggestions)} suggestions"
                                )
                                # Store suggestions in response
                                if 'suggestions' not in locals():
                                    suggestions_list = []
                                suggestions_list = suggestions
                        except Exception as sug_e:
                            logger.warning(f"Failed to generate suggestions: {sug_e}")
                            suggestions_list = []
                else:
                    execution_success = False
                    error_message = "Invalid or unrecognized SQL format after cleaning."
                    self.log_step(
                        "⚠️ SQL format invalid", f"Cleaned SQL: '{cleaned_sql}'"
                    )
                    actual_result = []
            elif not generated_sql:
                error_message = "No SQL query was generated by the LLM."
                self.log_step("⚠️ No SQL found", error_message)
                actual_result = []

            # Record query execution for learning (if enhanced context is enabled)
            if use_enhanced_context and generated_sql:
                try:
                    execution_time = time.time() - start_time
                    self.context_enhancer.record_query_execution(
                        user_question=user_question,
                        generated_sql=generated_sql,
                        success=execution_success,
                        execution_time=execution_time,
                        result_count=result_count,
                        error_message=error_message,
                    )
                    self.log_step(
                        "📚 Query recorded",
                        f"Learning from execution: success={execution_success}",
                    )
                except Exception as e:
                    self.log_step("⚠️ Failed to record query", str(e))

            # Prepare response with pagination info and Phase 2 metadata
            response = {
                "success": execution_success or (actual_result is not None),
                "result": actual_result,
                "sql_query": generated_sql or "N/A",
                "intermediate_steps": result.get("intermediate_steps", []),
            }
            
            # Add Phase 2 metadata if available
            if generated_sql:
                try:
                    cleaned_sql = self.clean_sql_response(generated_sql)
                    validation_result = self.sql_validator.validate_query(cleaned_sql)
                    response["validation"] = validation_result
                    
                    # Calculate confidence
                    context_info = {}
                    if hasattr(self, 'context_enhancer') and self.context_enhancer:
                        try:
                            enhanced_context = self.context_enhancer.get_enhanced_context(
                                user_question, refresh_schema=False, include_samples=False, include_history=False
                            )
                            context_info = {
                                "tables": [t.name for t in enhanced_context.database_context.tables] if enhanced_context.database_context.tables else []
                            }
                        except:
                            pass
                    
                    confidence = self.confidence_scorer.calculate_confidence(
                        cleaned_sql, user_question, context_info, validation_result
                    )
                    response["confidence"] = confidence
                    
                    # Generate explanation
                    explanation = self.query_explainer.explain_query(cleaned_sql, user_question)
                    response["explanation"] = explanation
                    
                    # Step-by-step explanation
                    steps = self.query_explainer.explain_step_by_step(cleaned_sql)
                    response["explanation_steps"] = steps
                except Exception as e:
                    logger.warning(f"Failed to add Phase 2 metadata: {e}")
            
            # Add pagination info if available
            if total_count is not None:
                page_size_used = page_size or self.query_paginator.default_page_size
                total_pages = math.ceil(total_count / page_size_used) if total_count > 0 else 1
                response["pagination"] = {
                    "page": page,
                    "page_size": page_size_used,
                    "total_count": total_count,
                    "total_pages": total_pages,
                    "has_next": page < total_pages,
                    "has_previous": page > 1,
                }

            # Debug logging for response
            self.log_step(
                "📤 Final Response Preparation",
                f"success: {response['success']}, "
                f"execution_success: {execution_success}, "
                f"actual_result type: {type(actual_result)}, "
                f"actual_result is None: {actual_result is None}, "
                f"actual_result length: {len(actual_result) if hasattr(actual_result, '__len__') else 'N/A'}, "
                f"sql_query: {generated_sql[:50] if generated_sql else 'None'}...",
            )

            # Add enhanced context metadata if available
            if enhanced_context:
                response["context_quality"] = enhanced_context.context_quality_score
                response["context_warnings"] = enhanced_context.warning_messages
                response["suggested_tables"] = enhanced_context.domain_insights.get(
                    "suggested_tables", []
                )

            return response

        except Exception as e:
            error_msg = str(e)
            self.log_step("❌ Error", error_msg)
            
            # Phase 2: Add suggestions if SQL was generated
            suggestions = []
            if generated_sql:
                try:
                    cleaned_sql = self.clean_sql_response(generated_sql)
                    context_info = {}
                    if hasattr(self, 'context_enhancer') and self.context_enhancer:
                        try:
                            enhanced_context = self.context_enhancer.get_enhanced_context(
                                user_question, refresh_schema=False, include_samples=False, include_history=False
                            )
                            context_info = {
                                "tables": [t.name for t in enhanced_context.database_context.tables] if enhanced_context.database_context.tables else []
                            }
                        except:
                            pass
                    suggestions = self.query_corrector.suggest_corrections(
                        cleaned_sql, error_msg, context_info
                    )
                except:
                    pass
            
            return {
                "success": False, 
                "error": error_msg, 
                "result": None,
                "sql_query": generated_sql or "N/A",
                "suggestions": suggestions
            }

    def log_step(self, step_name: str, content: str):
        """Log processing steps in Streamlit"""
        if "processing_logs" not in st.session_state:
            st.session_state.processing_logs = []

        log_entry = {
            "step": step_name,
            "content": content,
            "timestamp": pd.Timestamp.now().strftime("%H:%M:%S"),
        }

        st.session_state.processing_logs.append(log_entry)
