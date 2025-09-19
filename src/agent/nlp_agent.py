from langchain_groq import ChatGroq  # For use with Groq (code preserved)
from langchain_google_genai import ChatGoogleGenerativeAI  # For use with Gemini

# Import ChatOllama with compatibility for different versions
try:
    from langchain_ollama import ChatOllama  # Latest version
except ImportError:
    from langchain_community.chat_models import ChatOllama  # Legacy version
from langchain_community.utilities import SQLDatabase
from langchain_experimental.sql import SQLDatabaseChain
from langchain.prompts import PromptTemplate
import streamlit as st
from typing import Dict, Any, Optional

import pandas as pd
from src.utils.config import config
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

    def __init__(self, db_connection: str, groq_api_key: Optional[str] = None, google_api_key: Optional[str] = None):
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
            raise RuntimeError("No LLM provider available. Configure GOOGLE_API_KEY, GROQ_API_KEY or OLLAMA_BASE_URL.")

        self.db = SQLDatabase.from_uri(db_connection)

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
    
    def clean_sql_response(self, sql_text: str) -> str:
        """Clean SQL response by removing markdown and extra formatting - Optimized for CodeLlama"""
        if not isinstance(sql_text, str):
            return ""
        
        import re
        
        # Remove leading and trailing spaces
        cleaned = sql_text.strip()
        
        # STEP 1: Remove multiline markdown code blocks
        # Pattern for ```\nSELECT...\n```
        multiline_pattern = r'^```\s*\n(.*?)\n```$'
        match = re.search(multiline_pattern, cleaned, re.DOTALL | re.IGNORECASE)
        if match:
            cleaned = match.group(1).strip()
        else:
            # STEP 2: Remove inline code blocks ```sql...```
            inline_pattern = r'^```(?:sql)?\s*\n?(.*?)\n?```$'
            match = re.search(inline_pattern, cleaned, re.DOTALL | re.IGNORECASE)
            if match:
                cleaned = match.group(1).strip()
        
        # STEP 3: Remove loose backticks at beginning or end (multiple iterations)
        while cleaned.startswith('`') or cleaned.endswith('`'):
            cleaned = cleaned.strip('`').strip()
        
        # STEP 4: If there are still backticks at line beginnings, remove them
        lines = cleaned.split('\n')
        cleaned_lines = []
        for line in lines:
            line = line.strip()
            # Remove backticks at line beginning
            while line.startswith('`'):
                line = line[1:].strip()
            if line:  # Only add non-empty lines
                cleaned_lines.append(line)
        
        # STEP 5: Filter only valid SQL lines
        sql_lines = []
        for line in cleaned_lines:
            # Keep lines that look like SQL
            if (line.upper().startswith(('SELECT', 'INSERT', 'UPDATE', 'DELETE', 'WITH', 'FROM', 'WHERE', 'GROUP', 'ORDER', 'HAVING', 'LIMIT', 'SHOW', 'DESCRIBE', 'EXPLAIN')) or
                any(keyword in line.upper() for keyword in ['FROM', 'WHERE', 'AND', 'OR', 'ORDER BY', 'GROUP BY', 'HAVING', 'INNER JOIN', 'LEFT JOIN', 'RIGHT JOIN'])):
                sql_lines.append(line)
        
        # STEP 6: Join SQL lines
        result = ' '.join(sql_lines).strip()  # Use space instead of \n for one line
        
        # STEP 7: Clean multiple spaces
        result = re.sub(r'\s+', ' ', result)
        
        return result
    
    def _handle_metadata_query(self, user_question: str) -> Dict[str, Any]:
        """Handle metadata queries directly without LLM processing.
        
        Returns None if not a metadata query, or result dict if handled.
        """
        user_lower = user_question.lower().strip()
        
        # Check for table listing queries
        table_queries = [
            "show tables", "show me tables", "show all tables", "show me all tables",
            "list tables", "list all tables", "what tables", "which tables",
            "tables available", "available tables", "table names", "all tables"
        ]
        
        # Check for database info queries
        database_queries = [
            "what database", "which database", "current database", "database name",
            "what db", "which db", "current db", "db name", "database we are using",
            "database are we using", "what database we are use", "what database we use",
            "database we use now", "what database are we using now"
        ]
        
        # Check for schema info queries
        schema_queries = [
            "what schema", "which schema", "current schema", "schema name",
            "what schema are we using", "schema we are using"
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
                    "query_type": "metadata"
                }
            except Exception as e:
                self.log_step("⚠️ Metadata Error", str(e))
                return None
        
        elif any(query in user_lower for query in database_queries):
            try:
                # Get current database name
                sql = "SELECT CURRENT_DATABASE() AS database_name"
                self.log_step("🗂️ Database Query", "Getting current database name")
                result = self.db.run(sql)
                return {
                    "success": True,
                    "result": result,
                    "sql_query": sql,
                    "query_type": "metadata"
                }
            except Exception as e:
                self.log_step("⚠️ Database Query Error", str(e))
                return None
        
        elif any(query in user_lower for query in schema_queries):
            try:
                # Get current schema name
                sql = "SELECT CURRENT_SCHEMA() AS schema_name"
                self.log_step("📋 Schema Query", "Getting current schema name")
                result = self.db.run(sql)
                return {
                    "success": True,
                    "result": result,
                    "sql_query": sql,
                    "query_type": "metadata"
                }
            except Exception as e:
                self.log_step("⚠️ Schema Query Error", str(e))
                return None
        
        return None  # Not a metadata query

    def process_query(self, user_question: str) -> Dict[str, Any]:
        """Process user query and return data ready for the UI.

        Flow:
        1) Invoke SQL chain to get SQL from natural language
        2) Extract generated SQL from LangChain intermediate_steps
        3) Normalize/remove markdown format if it exists
        4) Execute SQL directly against Snowflake (via SQLDatabase)
        5) If no clear SQL, try alternatives (intermediate_steps, LLM response)
        6) Log each step for traceability in Streamlit
        """
        try:
            # Log processing start
            self.log_step("🔍 Processing query", user_question)
            
            # Check for metadata queries first (direct handling)
            metadata_result = self._handle_metadata_query(user_question)
            if metadata_result is not None:
                return metadata_result

            # Execute SQL chain using invoke method
            result = self.sql_chain.invoke(user_question)

            # Log generated query
            sql_query = "N/A"
            if "intermediate_steps" in result and result["intermediate_steps"]:
                try:
                    # Try different possible structures
                    step = result["intermediate_steps"][0]
                    if isinstance(step, dict):
                        # Check different possible keys
                        sql_query = (
                            step.get("sql_cmd")
                            or step.get("query")
                            or step.get("sql")
                            or str(step)
                        )
                    else:
                        sql_query = str(step)
                    self.log_step("📝 Generated SQL query", sql_query)
                except (KeyError, IndexError, TypeError):
                    self.log_step(
                        "⚠️ Could not extract SQL",
                        f"Structure: {result.get('intermediate_steps', 'N/A')}",
                    )

            # If we have clear SQL, execute it directly to get real data
            actual_result = None
            if isinstance(sql_query, str):
                # Normalize SQL (remove possible backticks/markdown) - Enhanced for CodeLlama
                cleaned_sql = self.clean_sql_response(sql_query)
                if cleaned_sql and cleaned_sql.upper().startswith(("SELECT", "SHOW", "DESCRIBE")):
                    try:
                        self.log_step("🚀 Executing detected SQL", cleaned_sql)
                        actual_result = self.db.run(cleaned_sql)
                        self.log_step(
                            "✅ Results obtained",
                            f"{len(actual_result) if hasattr(actual_result, '__len__') else 'N/A'} rows",  # noqa: E501
                        )
                    except Exception as e:
                        self.log_step(
                            "⚠️ Error executing generated SQL", f"Error: {str(e)}"
                        )
                        actual_result = None

            # If we couldn't execute the previous SQL, try extracting data from
            # intermediate_steps
            if (
                actual_result is None
                and "intermediate_steps" in result
                and result["intermediate_steps"]
            ):
                for step in result["intermediate_steps"]:
                    if isinstance(step, dict):
                        for key in ["sql_result", "result", "data", "query_result"]:
                            if (
                                key in step
                                and step[key]
                                and step[key] != result.get("result")
                            ):
                                actual_result = step[key]
                                self.log_step(
                                    "✅ Data found in intermediate_steps",
                                    f"Field: {key}, "
                                    f"Data: {str(actual_result)[:100]}...",
                                )
                                break
                    if actual_result:
                        break

            # Last resort: if the final result is SQL, execute it
            if actual_result is None:
                final_answer = result.get("result")
                if isinstance(final_answer, str):
                    # Clean the final response too
                    cleaned_final = self.clean_sql_response(final_answer)
                    if cleaned_final and cleaned_final.upper().startswith(
                        ("SELECT", "SHOW", "DESCRIBE")
                    ):
                        try:
                            self.log_step(
                                "🚀 Executing LLM response as SQL", cleaned_final
                            )
                            actual_result = self.db.run(cleaned_final)
                        except Exception as e:
                            self.log_step(
                                "⚠️ Error executing LLM response", f"Error: {str(e)}"
                            )
                            actual_result = final_answer
                    else:
                        actual_result = final_answer
                else:
                    actual_result = final_answer

            return {
                "success": True,
                "result": actual_result,
                "sql_query": (
                    sql_query if isinstance(sql_query, str) else str(sql_query)
                ),
                "intermediate_steps": result.get("intermediate_steps", []),
            }

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
