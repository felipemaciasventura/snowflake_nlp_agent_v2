from langchain_google_genai import \
    ChatGoogleGenerativeAI  # For use with Gemini
from langchain_groq import ChatGroq  # For use with Groq (code preserved)

# Import ChatOllama with compatibility for different versions
try:
    from langchain_ollama import ChatOllama  # Latest version
except ImportError:
    from langchain_community.chat_models import ChatOllama  # Legacy version

import time
from typing import Any, Dict, Optional

import pandas as pd
import streamlit as st
from langchain.prompts import PromptTemplate
from langchain_community.utilities import SQLDatabase
from langchain_experimental.sql import SQLDatabaseChain

from src.utils.config import config
from src.utils.context_enhancer import get_context_enhancer
from src.utils.helpers import log_manager
from src.utils.prompt_loader import prompt_loader


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

        if provider == "ollama":
            # Use Ollama (local model - maximum privacy priority)
            self.llm = ChatOllama(
                base_url=config.OLLAMA_BASE_URL,
                model=config.OLLAMA_MODEL,
                temperature=0.1,
            )
            st.sidebar.info(f"LLM in use: Ollama ({config.OLLAMA_MODEL}) - Local")
        elif provider == "gemini" and google_key:
            # Use Gemini (recommended if you have student plan)
            self.llm = ChatGoogleGenerativeAI(
                google_api_key=google_key,
                model=config.GEMINI_MODEL,
                temperature=0.1,
                max_output_tokens=4000,
            )
            st.sidebar.info("LLM in use: Gemini (Google)")
        elif provider == "groq" and groq_key:
            # USE WITH GROQ (code preserved):
            # self.llm = ChatGroq(
            #     groq_api_key=groq_key,
            #     model_name=config.MODEL_NAME,
            #     temperature=0.1,
            #     max_tokens=4000,
            # )
            # Groq functionality maintained active by default
            self.llm = ChatGroq(
                groq_api_key=groq_key,
                model_name=config.MODEL_NAME,
                temperature=0.1,
                max_tokens=4000,
            )
            st.sidebar.info("LLM in use: Groq (Llama)")
        else:
            raise RuntimeError(
                "No LLM provider available. Configure GOOGLE_API_KEY, GROQ_API_KEY or OLLAMA_BASE_URL."
            )

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
            print(
                f"🔍 EXTRACTOR: Found {len(result['intermediate_steps'])} intermediate steps"
            )  # Console log
            self.log_step(
                "📋 Processing intermediate_steps",
                f"Found {len(result['intermediate_steps'])} steps",
            )

            for i, step in enumerate(result["intermediate_steps"]):
                print(
                    f"📋 EXTRACTOR: Step {i+1} - Type: {type(step)}, Length: {len(step) if hasattr(step, '__len__') else 'N/A'}"
                )  # Console log
                self.log_step(
                    f"📋 Step {i+1}",
                    f"Type: {type(step)}, Preview: {str(step)[:100]}...",
                )

                # NEW: Handle dict steps (LangChain stores SQL execution info in dicts)
                if isinstance(step, dict):
                    print(
                        f"📋 EXTRACTOR: Step {i+1} DICT - Keys: {list(step.keys())}"
                    )  # Console log

                    # Check for SQL in dict
                    for key in ["sql_cmd", "query", "sql", "input"]:
                        if key in step and isinstance(step[key], str):
                            potential_sql = step[key]
                            if (
                                "SELECT" in potential_sql.upper()
                                or "WITH" in potential_sql.upper()
                            ):
                                print(
                                    f"✅ EXTRACTOR: Found SQL in dict['{key}'] - {potential_sql[:60]}..."
                                )  # Console log
                                if sql_query == "N/A":
                                    sql_query = potential_sql

                    # Check for data in dict
                    for key in ["sql_result", "result", "data", "output"]:
                        if key in step and step[key] is not None:
                            potential_data = step[key]
                            print(
                                f"✅ EXTRACTOR: Found data in dict['{key}'] - Type: {type(potential_data)}, Preview: {str(potential_data)[:60]}..."
                            )  # Console log
                            if chain_data is None:
                                chain_data = potential_data

                # Handle string steps (might contain SQL or DATA)
                elif isinstance(step, str):
                    print(
                        f"📋 EXTRACTOR: Step {i+1} STRING - Preview: {step[:60]}..."
                    )  # Console log

                    # Check for SQL in string
                    if (
                        "SELECT" in step.upper() or "WITH" in step.upper()
                    ) and sql_query == "N/A":
                        print(f"✅ EXTRACTOR: Found SQL in string step")  # Console log
                        sql_query = step

                    # NEW: Check for DATA in string (list format)
                    elif step.strip().startswith("[") and ")]" in step:
                        print(
                            f"✅ EXTRACTOR: Found data-like string in step {i+1}"
                        )  # Console log
                        try:
                            import ast
                            import datetime

                            # First try with ast.literal_eval (safer)
                            try:
                                parsed_data = ast.literal_eval(step.strip())
                            except Exception:
                                # If ast.literal_eval fails, try eval with safe namespace for datetime objects
                                safe_dict = {
                                    '__builtins__': {},
                                    'datetime': datetime,
                                    'date': datetime.date,
                                    'time': datetime.time,
                                    'timedelta': datetime.timedelta,
                                }
                                parsed_data = eval(step.strip(), safe_dict)
                            
                            if (
                                isinstance(parsed_data, list)
                                and parsed_data
                                and chain_data is None
                            ):
                                chain_data = parsed_data
                                print(
                                    f"✅ EXTRACTOR: Parsed data from string step {i+1} - Length: {len(parsed_data)}"
                                )  # Console log
                        except Exception as e:
                            print(
                                f"❌ EXTRACTOR: Failed to parse data string in step {i+1}: {e}"
                            )  # Console log
                            print(f"🔍 EXTRACTOR: Data string preview: {step[:200]}...")  # Debug info

                # Original tuple handling (kept for compatibility)
                elif isinstance(step, tuple) and len(step) >= 2:
                    potential_sql, potential_data = step[0], step[1]

                    print(
                        f"📋 EXTRACTOR: Step {i+1} TUPLE - SQL type: {type(potential_sql)}, Data type: {type(potential_data)}"
                    )  # Console log
                    print(
                        f"📋 EXTRACTOR: Step {i+1} TUPLE - SQL preview: {str(potential_sql)[:80]}"
                    )  # Console log
                    print(
                        f"📋 EXTRACTOR: Step {i+1} TUPLE - Data preview: {str(potential_data)[:80]}"
                    )  # Console log

                    # Check if this looks like a SQL query with valid data
                    if (
                        isinstance(potential_sql, str)
                        and (
                            "SELECT" in potential_sql.upper()
                            or "WITH" in potential_sql.upper()
                        )
                        and potential_data is not None
                    ):
                        print(
                            f"✅ EXTRACTOR: Found valid SQL/data pair in tuple step {i+1}"
                        )  # Console log

                        # Use the FIRST valid SQL/data pair we find
                        if sql_query == "N/A":
                            sql_query = potential_sql
                            chain_data = potential_data

                            print(
                                f"✅ EXTRACTOR: Using tuple step {i+1} - Data length: {len(potential_data) if hasattr(potential_data, '__len__') else 'N/A'}"
                            )  # Console log

                            self.log_step(
                                "✅ Found first valid SQL/data pair",
                                f"SQL: {sql_query[:80]}..., Data: {str(potential_data)[:100]}...",
                            )

                            # CRITICAL: Break here to prevent Answer field from overriding
                            break
                    else:
                        print(
                            f"❌ EXTRACTOR: Tuple step {i+1} invalid - SQL check: {isinstance(potential_sql, str) and ('SELECT' in potential_sql.upper() or 'WITH' in potential_sql.upper())}, Data check: {potential_data is not None}"
                        )  # Console log

                # If we found both SQL and data, we can break
                if sql_query != "N/A" and chain_data is not None:
                    print(
                        f"🎯 EXTRACTOR: Found both SQL and data, breaking at step {i+1}"
                    )  # Console log
                    break

        # Method 2: If no data found in intermediate_steps, check result['result']
        if chain_data is None:
            print(
                f"🔍 EXTRACTOR: No data in intermediate_steps, checking result['result']"
            )  # Console log
            possible_data = result.get("result", "")
            print(
                f"🔍 EXTRACTOR: result['result'] type: {type(possible_data)}, preview: {str(possible_data)[:100]}"
            )  # Console log

            # If result contains a string representation of the data, try to parse it
            if isinstance(possible_data, str) and possible_data.strip():
                # Check if it looks like the SQLResult data we saw in console
                if "[(" in possible_data and ")]" in possible_data:
                    try:
                        import ast
                        import datetime

                        # First try with ast.literal_eval (safer)
                        try:
                            parsed_data = ast.literal_eval(possible_data)
                        except Exception:
                            # If ast.literal_eval fails, try eval with safe namespace for datetime objects
                            safe_dict = {
                                '__builtins__': {},
                                'datetime': datetime,
                                'date': datetime.date,
                                'time': datetime.time,
                                'timedelta': datetime.timedelta,
                            }
                            parsed_data = eval(possible_data, safe_dict)
                        
                        if isinstance(parsed_data, list) and parsed_data:
                            chain_data = parsed_data
                            print(
                                f"✅ EXTRACTOR: Parsed data from result['result'] - Length: {len(parsed_data)}"
                            )  # Console log
                    except Exception as e:
                        print(
                            f"❌ EXTRACTOR: Failed to parse result['result']: {e}"
                        )  # Console log
                        print(f"🔍 EXTRACTOR: Result data preview: {possible_data[:200]}...")  # Debug info

            # If result contains the data directly
            elif isinstance(possible_data, list) and possible_data:
                chain_data = possible_data
                print(
                    f"✅ EXTRACTOR: Using direct data from result['result'] - Length: {len(possible_data)}"
                )  # Console log

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
        """Clean SQL response by removing markdown and extra formatting"""
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

        # STEP 5: Filter only valid SQL lines
        sql_lines = []
        for line in cleaned_lines:
            # Keep lines that look like SQL
            if line.upper().startswith(
                (
                    "SELECT",
                    "INSERT",
                    "UPDATE",
                    "DELETE",
                    "WITH",
                    "FROM",
                    "WHERE",
                    "GROUP",
                    "ORDER",
                    "HAVING",
                    "LIMIT",
                    "SHOW",
                    "DESCRIBE",
                    "EXPLAIN",
                )
            ) or any(
                keyword in line.upper()
                for keyword in [
                    "FROM",
                    "WHERE",
                    "AND",
                    "OR",
                    "ORDER BY",
                    "GROUP BY",
                    "HAVING",
                    "INNER JOIN",
                    "LEFT JOIN",
                    "RIGHT JOIN",
                ]
            ):
                sql_lines.append(line)

        # STEP 6: Join SQL lines
        result = " ".join(sql_lines).strip()  # Use space instead of \n for one line

        # STEP 7: Clean multiple spaces
        result = re.sub(r"\s+", " ", result)

        return result
        """Clean SQL response by removing markdown and extra formatting - Optimized for CodeLlama"""
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

        # STEP 5: Filter only valid SQL lines
        sql_lines = []
        for line in cleaned_lines:
            # Keep lines that look like SQL
            if line.upper().startswith(
                (
                    "SELECT",
                    "INSERT",
                    "UPDATE",
                    "DELETE",
                    "WITH",
                    "FROM",
                    "WHERE",
                    "GROUP",
                    "ORDER",
                    "HAVING",
                    "LIMIT",
                    "SHOW",
                    "DESCRIBE",
                    "EXPLAIN",
                )
            ) or any(
                keyword in line.upper()
                for keyword in [
                    "FROM",
                    "WHERE",
                    "AND",
                    "OR",
                    "ORDER BY",
                    "GROUP BY",
                    "HAVING",
                    "INNER JOIN",
                    "LEFT JOIN",
                    "RIGHT JOIN",
                ]
            ):
                sql_lines.append(line)

        # STEP 6: Join SQL lines
        result = " ".join(sql_lines).strip()  # Use space instead of \n for one line

        # STEP 7: Clean multiple spaces
        result = re.sub(r"\s+", " ", result)

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

        if any(query in user_lower for query in table_queries):
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

            # Pattern 1: show [me|the] <table> table (with optional trailing punctuation)
            m = re.search(
                r"\bshow\s+(?:me\s+|the\s+)?([a-zA-Z0-9_]+)\s+table\b(?:\W|$)",
                user_lower,
            )
            # Pattern 2: show <table> (no word 'table'), avoid matching 'tables'
            m2 = (
                None
                if m
                else re.search(
                    r"\bshow\s+(?:me\s+|the\s+)?([a-zA-Z0-9_]+)\b(?:\W|$)", user_lower
                )
            )
            candidate = None
            if m:
                candidate = m.group(1)
            elif m2 and m2.group(1) != "tables":
                candidate = m2.group(1)

            if candidate:
                table = candidate
                self.log_step(
                    "🧭 Intent: Table Preview", f"Detected table name: {table}"
                )
                # Basic validation to avoid injection (alphanumeric and underscore only)
                if re.fullmatch(r"[A-Za-z0-9_]+", table):
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
                            sql = f"SELECT * FROM {table} SAMPLE ({sample_pct}) LIMIT {limit_val}"
                            self.log_step(
                                "🎲 Sampling Enabled",
                                f"SAMPLE=({sample_pct}), LIMIT={limit_val}",
                            )
                        else:
                            sql = f"SELECT * FROM {table} LIMIT {limit_val}"
                            self.log_step("🎚️ Sampling Disabled", f"LIMIT={limit_val}")
                        self.log_step(
                            "📄 Table Preview",
                            f"Fetching sample rows from table: {table}",
                        )
                        result = self.db.run(sql)
                        return {
                            "success": True,
                            "result": result,
                            "sql_query": sql,
                            "query_type": "data_preview",
                        }
                    except Exception as e:
                        self.log_step("⚠️ Table Preview Error", str(e))
                        return None
                else:
                    self.log_step(
                        "⚠️ Table Preview Skipped", f"Invalid table identifier: {table}"
                    )

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
                        limit_val = max(
                            1, int(getattr(config, "SHOW_TABLE_LIMIT", 100))
                        )
                        sample_pct = float(
                            getattr(config, "SHOW_TABLE_SAMPLE_PERCENT", 0.0)
                        )
                        if sample_pct > 0.0:
                            sql = f"SELECT * FROM {table} SAMPLE ({sample_pct}) LIMIT {limit_val}"
                            self.log_step(
                                "🎲 Sampling Enabled",
                                f"SAMPLE=({sample_pct}), LIMIT={limit_val}",
                            )
                        else:
                            sql = f"SELECT * FROM {table} LIMIT {limit_val}"
                            self.log_step("🎚️ Sampling Disabled", f"LIMIT={limit_val}")
                        self.log_step(
                            "📄 Table Preview",
                            f"Fetching sample rows from table: {table}",
                        )
                        result = self.db.run(sql)
                        return {
                            "success": True,
                            "result": result,
                            "sql_query": sql,
                            "query_type": "data_preview",
                        }
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

        # Pattern 1: "how many X on/in Y table"
        match = re.search(
            r"how many.*(?:on|in|from)\s+([a-zA-Z0-9_]+)\s+table", user_lower
        )
        if not match:
            # Pattern 2: "how many Y"
            match = re.search(r"how many\s+([a-zA-Z0-9_]+)", user_lower)
        if not match:
            # Pattern 3: "count of/from Y"
            match = re.search(r"count.*(?:of|from)\s+([a-zA-Z0-9_]+)", user_lower)

        if match:
            table_name = match.group(1).strip()

            # Validate table exists in schema
            try:
                # Get table names from database
                tables_query = "SELECT TABLE_NAME FROM INFORMATION_SCHEMA.TABLES WHERE TABLE_SCHEMA = CURRENT_SCHEMA()"
                tables_result = self.db.run(tables_query)
                available_tables = [row[0].lower() for row in tables_result]

                if table_name.lower() in available_tables:
                    # Generate simple COUNT query
                    sql = f"SELECT COUNT(*) AS total_count FROM {table_name.upper()}"
                    self.log_step("🔢 Direct count query", f"Generated: {sql}")

                    # Execute directly
                    result = self.db.run(sql)
                    self.log_step("✅ Count query executed", f"Result: {result}")

                    return {
                        "success": True,
                        "result": result,
                        "sql_query": sql,
                        "query_type": "count",
                    }

            except Exception as e:
                self.log_step("⚠️ Direct count failed", f"Error: {str(e)}")

        return None

    def process_query(
        self, user_question: str, use_enhanced_context: bool = True
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

        try:
            # Log processing start
            self.log_step("🔍 Processing query", user_question)

            # FIRST: Check for count queries (direct handling to avoid LLM confusion)
            if self._is_count_query(user_question):
                count_result = self._handle_count_queries(user_question)
                if count_result is not None:
                    return count_result

            # SECOND: Check for metadata queries (direct handling)
            metadata_result = self._handle_metadata_query(user_question)
            if metadata_result is not None:
                return metadata_result

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

                            # CRITICAL FIX: Always use the FIRST valid SQL/data pair
                            # The first pair is usually the correct one; subsequent ones are often LLM confusion
                            if sql_query == "N/A":
                                sql_query = potential_sql
                                chain_data = potential_data
                                self.log_step(
                                    "✅ Found SQL and data in tuple",
                                    f"SQL: {sql_query[:50]}..., Data preview: {str(potential_data)[:100]}...",
                                )

                                # For ANY query type, use the FIRST valid result and break
                                # This prevents LLM confusion from overriding correct results
                                self.log_step(
                                    "🎯 Using first valid SQL/data pair",
                                    "Ignoring any additional SQL queries",
                                )
                                break

                    # Legacy format handling
                    elif isinstance(step, dict):
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
                                self.log_step("📝 Found SQL in dict", sql_query)
                        if potential_data:
                            chain_data = potential_data
                            self.log_step(
                                "📊 Found data in dict",
                                f"Data preview: {str(potential_data)[:100]}...",
                            )

                        if sql_query != "N/A" and chain_data:
                            break

                    # Some providers may pass SQL as a raw string step
                    elif isinstance(step, str) and "SELECT" in step.upper():
                        sql_queries_found.append(step)
                        if sql_query == "N/A":
                            sql_query = step
                            self.log_step(
                                "📝 Found SQL as raw string in steps", sql_query[:120]
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

            # If no SQL from steps, check if result['result'] itself holds SQL text
            # BUT ONLY if we haven't found a valid SQL from intermediate steps
            # AND we're not dealing with the problematic "Answer" field
            if sql_query == "N/A" and "intermediate_steps" not in result:
                possible_sql = result.get("result")
                if isinstance(possible_sql, str) and "SELECT" in possible_sql.upper():
                    # This is a fallback for chains that don't produce intermediate steps
                    sql_query = self.clean_sql_response(possible_sql)
                    self.log_step(
                        "📝 Found SQL in result['result'] (fallback)", sql_query[:120]
                    )

            # IMPORTANT: If we have chain_data with results, DON'T use result['result']
            # as it often contains the problematic "Answer" SQL
            if chain_data is not None and generated_sql and sql_query != "N/A":
                self.log_step(
                    "🛡️ Preventing Answer field interference",
                    "Have valid chain_data and SQL, ignoring result['result']",
                )
            # Store the generated SQL for learning
            generated_sql = sql_query if sql_query != "N/A" else None

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

            # If no usable rows found in intermediate_steps, but we have a valid SQL, do manual execution
            if not execution_success and generated_sql:
                # FALLBACK: Manual SQL execution
                self.log_step(
                    "🔄 Fallback: Manual execution",
                    "Data from chain was not usable, executing SQL directly.",
                )

                # Clean SQL (remove markdown/backticks)
                cleaned_sql = self.clean_sql_response(generated_sql)
                self.log_step(
                    "🧹 SQL after cleaning",
                    f"Original: {generated_sql[:60]}... -> Cleaned: {cleaned_sql[:60]}...",
                )

                # Accept common starters, including CTEs (WITH ...)
                if cleaned_sql and cleaned_sql.upper().startswith(
                    ("SELECT", "SHOW", "DESCRIBE", "WITH")
                ):
                    try:
                        self.log_step("🚀 Executing cleaned SQL", cleaned_sql)
                        manual_result = self.db.run(cleaned_sql)
                        actual_result = manual_result
                        execution_success = True
                        result_count = (
                            len(actual_result)
                            if hasattr(actual_result, "__len__")
                            else None
                        )
                        # Ensure the cleaned SQL is what's stored
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

            # Prepare response
            response = {
                "success": execution_success or (actual_result is not None),
                "result": actual_result,
                "sql_query": generated_sql or "N/A",
                "intermediate_steps": result.get("intermediate_steps", []),
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
            return {"success": False, "error": error_msg, "result": None}

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
