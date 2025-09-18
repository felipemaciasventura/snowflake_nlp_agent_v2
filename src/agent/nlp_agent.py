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
import re


class SnowflakeNLPAgent:
    """NLP Agent that translates natural language questions to SQL for Snowflake.

    Executes the query.

    Main responsibilities:
    - Configure the LLM (Groq, Gemini or Ollama, according to configuration)
    - Set up an SQL chain (SQLDatabaseChain) with an English prompt
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

        # Create custom prompt that explicitly uses real table names
        # First, let's discover what tables actually exist
        try:
            # Get actual table information from the database
            table_info = self.db.get_table_info()
            self.log_step("📋 Database Schema Discovered", f"Found {len(table_info.split('CREATE TABLE'))} tables")
        except Exception as e:
            table_info = "Unable to retrieve table information"
            self.log_step("⚠️ Schema Discovery Failed", str(e))
        
        sql_prompt = f"""You are a Snowflake SQL expert. Generate ONLY pure SQL query using the ACTUAL table names from the database.

IMPORTANT: Use ONLY the real table names that exist in the database. Never use fictional or obfuscated names.

📋 ACTUAL DATABASE SCHEMA:
{{table_info}}

Question: {{input}}

❗ MANDATORY RULES:
1. NEVER use ``` or backticks in your response
2. NEVER use markdown format or code blocks  
3. RESPOND ONLY WITH PURE SQL - NOTHING ELSE
4. Use ONLY the actual table names shown in the schema above
5. For count queries: use COUNT(*) without LIMIT
6. For other queries: add LIMIT 20 (increase for complex analytical queries)
7. For rankings: use RANK() OVER (ORDER BY ...) or ROW_NUMBER() OVER
8. CRITICAL: For schema references, ALWAYS use CURRENT_SCHEMA() - NEVER use literal schema names
9. For database info queries, use CURRENT_DATABASE() function
10. For complex analytical queries: use simpler approaches if possible to avoid timeouts
11. For window functions: consider performance impact and add appropriate LIMIT

📋 SPECIFIC QUERY EXAMPLES:
- "show me all tables" → SHOW TABLES
- "what tables are there" → SHOW TABLES  
- "list all tables" → SHOW TABLES
- "how many tables" → SELECT COUNT(*) FROM INFORMATION_SCHEMA.TABLES WHERE TABLE_SCHEMA = CURRENT_SCHEMA()
- "what database am I using" → SELECT CURRENT_DATABASE()

🚫 NEVER USE THESE FAKE NAMES:
- real_estate_items, geographic_areas, sales_representatives, commercial_events, property_holders
- Any obfuscated or fictional table names

✅ ALWAYS USE REAL NAMES:
- Use the actual table names from the schema information provided above

Generate PURE SQL using ONLY the real table names from the schema."""

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
            "display tables", "get tables", "tables list"
        ]
        
        if any(query in user_lower for query in table_queries):
            try:
                self.log_step("🏷️ Metadata Query Detected", "Handling table list directly")
                
                # Execute clean query to get table names only
                clean_sql = "SELECT TABLE_NAME, TABLE_TYPE FROM INFORMATION_SCHEMA.TABLES WHERE TABLE_SCHEMA = CURRENT_SCHEMA() ORDER BY TABLE_NAME"
                self.log_step("📝 Direct SQL", clean_sql)
                
                result = self.db.run(clean_sql)
                self.log_step("✅ Tables retrieved", f"{len(result) if result else 0} tables found")
                
                return {
                    "success": True,
                    "result": result,
                    "sql_query": clean_sql,
                    "query_type": "metadata",
                    "direct_handling": True
                }
                
            except Exception as e:
                self.log_step("❌ Error in direct metadata query", str(e))
                return {
                    "success": False,
                    "error": f"Error retrieving tables: {str(e)}",
                    "query_type": "metadata"
                }
        
        return None  # Not a metadata query
    
    def process_query(self, user_question: str) -> Dict[str, Any]:
        """Process user query and return data ready for the UI.

        Flow:
        1) Check if it's a metadata query (handle directly)
        2) Invoke SQL chain to get SQL from natural language
        3) Extract generated SQL from LangChain intermediate_steps
        4) Normalize/remove markdown format if it exists
        5) Execute SQL directly against Snowflake (via SQLDatabase)
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
                        # Log the SQL generated by LLM
                        self.log_step("📝 SQL generated", cleaned_sql)
                        
                        # Execute the SQL directly against Snowflake
                        self.log_step("🚀 Executing SQL", cleaned_sql)
                        actual_result = self.db.run(cleaned_sql)
                        self.log_step(
                            "✅ Results obtained",
                            f"{len(actual_result) if hasattr(actual_result, '__len__') else 'N/A'} rows",  # noqa: E501
                        )
                        
                    except Exception as e:
                        self.log_step(
                            "⚠️ Error executing SQL", f"Error: {str(e)}"
                        )
                        # Return user-friendly error instead of None
                        return self._handle_sql_error(e, cleaned_sql)

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
            
            # Special handling for SHOW TABLES results
            if actual_result is None and sql_query and "SHOW TABLES" in sql_query.upper():
                # Extract data from intermediate_steps for SHOW TABLES
                if "intermediate_steps" in result and result["intermediate_steps"]:
                    for step in result["intermediate_steps"]:
                        if isinstance(step, dict) and "sql_result" in step:
                            actual_result = step["sql_result"]
                            self.log_step("📋 SHOW TABLES data extracted", f"Found {len(actual_result) if actual_result else 0} tables")
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
                            # Return user-friendly error for final SQL execution too
                            return self._handle_sql_error(e, cleaned_final)
                    else:
                        actual_result = final_answer
                else:
                    actual_result = final_answer

            # Prepare final result
            final_sql_query = sql_query if isinstance(sql_query, str) else str(sql_query)
            
            # Check if we have actual data or just a SQL query
            if actual_result is None or (isinstance(actual_result, str) and 
                any(keyword in actual_result.upper() for keyword in ['SELECT', 'WITH', 'FROM', 'WHERE'])):
                # We only have a SQL query, not actual results
                self.log_step("⚠️ No data results", "Query generated but no data obtained")
                return {
                    "success": False,
                    "error": "Query was generated successfully but couldn't retrieve data. This might be due to:"
                           "\n• Database connection issues"
                           "\n• Query complexity or timeout"
                           "\n• Data availability"
                           "\n• Column or table access permissions",
                    "sql_query": final_sql_query,
                    "user_friendly": True
                }
            
            return {
                "success": True,
                "result": actual_result,
                "sql_query": final_sql_query,
                "intermediate_steps": result.get("intermediate_steps", []),
            }

        except Exception as e:
            error_msg = str(e)
            self.log_step("❌ Error in query processing", error_msg)
            
            # Enhanced error context
            error_context = {
                "success": False, 
                "error": error_msg, 
                "result": None,
            }
            
            return error_context

    def _handle_sql_error(self, error: Exception, sql_query: str = None) -> Dict[str, Any]:
        """Handle SQL execution errors with user-friendly messages.
        
        Args:
            error: The original exception
            sql_query: The SQL query that caused the error (optional)
            
        Returns:
            User-friendly error response
        """
        error_str = str(error)
        
        # Common error patterns and user-friendly messages
        if "does not exist" in error_str or "not authorized" in error_str:
            # Extract table name from error if possible
            import re
            table_match = re.search(r"Object '([^']+)' does not exist", error_str)
            if table_match:
                table_name = table_match.group(1).lower()
                user_message = f"❌ The table '{table_name}' doesn't exist in your database or you don't have permission to access it."
            else:
                user_message = "❌ The requested table doesn't exist in your database or you don't have permission to access it."
        
        elif "SQL compilation error" in error_str:
            user_message = "❌ There was an error in the SQL query. The database structure might be different than expected."
        
        elif "connection" in error_str.lower():
            user_message = "❌ Database connection error. Please check your connection settings."
        
        elif "timeout" in error_str.lower():
            user_message = "❌ The query took too long to execute. Try a simpler query or contact your administrator."
        
        else:
            user_message = f"❌ Database error: {error_str[:100]}{'...' if len(error_str) > 100 else ''}"
        
        self.log_step("🚨 User-Friendly Error", user_message)
        
        return {
            "success": False,
            "error": user_message,
            "technical_error": error_str,
            "sql_query": sql_query,
            "query_type": "data",
            "user_friendly": True
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
