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
from src.utils.context_enhancer import get_context_enhancer
from src.utils.helpers import log_manager
import time


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

    def process_query(self, user_question: str, use_enhanced_context: bool = True) -> Dict[str, Any]:
        """Process user query with enhanced context and return data ready for the UI.

        Enhanced Flow:
        1) Get enhanced context (schema + query history + domain insights)
        2) Generate enhanced prompt with rich context
        3) Invoke SQL chain with enhanced prompt
        4) Extract generated SQL from LangChain intermediate_steps
        5) Record query execution for learning
        6) Return results with comprehensive logging
        
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
            
            # Check for metadata queries first (direct handling)
            metadata_result = self._handle_metadata_query(user_question)
            if metadata_result is not None:
                return metadata_result
            
            # Get enhanced context if enabled
            enhanced_context = None
            if use_enhanced_context:
                try:
                    self.log_step("🧠 Getting enhanced context", "Analyzing schema and query history")
                    enhanced_context = self.context_enhancer.get_enhanced_context(
                        user_question=user_question,
                        refresh_schema=False,
                        include_samples=True,
                        include_history=True
                    )
                    
                    self.log_step(
                        "📊 Context quality", 
                        f"Quality: {enhanced_context.context_quality_score:.2f}, "
                        f"Tables: {len(enhanced_context.database_context.tables)}, "
                        f"Similar queries: {len(enhanced_context.query_context.similar_successful_queries)}"
                    )
                    
                    # Generate enhanced prompt
                    base_prompt = prompt_loader.get_sql_prompt("enhanced")
                    enhanced_prompt = self.context_enhancer.generate_enhanced_prompt(
                        user_question=user_question,
                        base_prompt=base_prompt, 
                        enhanced_context=enhanced_context
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
                            template=enhanced_prompt
                        ),
                    )
                    
                    self.log_step("✨ Enhanced context applied", "Using context-aware prompt")
                    result = enhanced_chain.invoke({"input": user_question})
                    
                except Exception as e:
                    self.log_step("⚠️ Context enhancement failed", f"Falling back to standard mode: {str(e)}")
                    result = self.sql_chain.invoke(user_question)
            else:
                # Standard processing without enhanced context
                self.log_step("🔧 Standard processing", "Using base SQL chain")
                result = self.sql_chain.invoke(user_question)
            
            # Extract SQL and data from LangChain result
            sql_query = "N/A"
            chain_data = None
            
            if "intermediate_steps" in result and result["intermediate_steps"]:
                self.log_step("🔍 Analyzing intermediate_steps", f"Steps found: {len(result['intermediate_steps'])}")
                
                for i, step in enumerate(result["intermediate_steps"]):
                    self.log_step(f"📋 Step {i+1}", f"Type: {type(step)}, Content preview: {str(step)[:100]}...")
                    
                    # SQLDatabaseChain typically stores steps as tuples: (sql_query, sql_result)
                    if isinstance(step, tuple) and len(step) == 2:
                        potential_sql, potential_data = step
                        if isinstance(potential_sql, str) and 'SELECT' in potential_sql.upper():
                            sql_query = potential_sql
                            chain_data = potential_data
                            self.log_step(
                                "✅ Found SQL and data in tuple", 
                                f"SQL: {sql_query[:50]}..., Data preview: {str(potential_data)[:100]}..."
                            )
                            break
                    
                    # Legacy format handling
                    elif isinstance(step, dict):
                        potential_sql = (
                            step.get("sql_cmd") or step.get("query") or step.get("sql")
                        )
                        potential_data = (
                            step.get("sql_result") or step.get("result") or step.get("data")
                        )
                        
                        if potential_sql:
                            sql_query = potential_sql
                            self.log_step("📝 Found SQL in dict", sql_query)
                        if potential_data:
                            chain_data = potential_data
                            self.log_step("📊 Found data in dict", f"Data preview: {str(potential_data)[:100]}...")
                            
                        if sql_query != "N/A" and chain_data:
                            break
            
            # Store the generated SQL for learning
            generated_sql = sql_query if sql_query != "N/A" else None
            
            # Process results
            actual_result = None
            
            # If we found data in intermediate_steps, use it directly
            if chain_data is not None:
                self.log_step("🎯 Using data from intermediate_steps", f"Rows: {len(chain_data) if hasattr(chain_data, '__len__') else 'N/A'}")
                actual_result = chain_data
                execution_success = True
                result_count = len(chain_data) if hasattr(chain_data, '__len__') else None

            else:
                # FALLBACK: Manual SQL execution
                self.log_step("🔄 Fallback: Manual execution", "")
                execution_success = False  # Initialize for fallback path

                if isinstance(sql_query, str) and sql_query != "N/A":
                    # Clean SQL (remove markdown/backticks)
                    cleaned_sql = self.clean_sql_response(sql_query)
                    self.log_step("🧹 SQL after cleaning", f"Original: {sql_query[:50]}... -> Cleaned: {cleaned_sql[:50]}...")

                    if cleaned_sql and cleaned_sql.upper().startswith(("SELECT", "SHOW", "DESCRIBE")):
                        try:
                            self.log_step("🚀 Executing cleaned SQL", cleaned_sql)
                            actual_result = self.db.run(cleaned_sql)
                            execution_success = True
                            result_count = len(actual_result) if hasattr(actual_result, '__len__') else None
                            generated_sql = cleaned_sql  # Use cleaned version

                            self.log_step(
                                "✅ Manual execution successful",
                                f"Got {result_count} rows. Data preview: {str(actual_result)[:100]}..."
                            )

                            # DEBUG: Log the actual result type and content
                            self.log_step("🔍 DEBUG: Result type", f"Type: {type(actual_result)}, Length: {len(actual_result) if hasattr(actual_result, '__len__') else 'N/A'}")
                            if hasattr(actual_result, '__len__') and len(actual_result) > 0:
                                self.log_step("🔍 DEBUG: First row", f"First row: {str(actual_result[0])}")
                            else:
                                self.log_step("🔍 DEBUG: Empty result", "Result is empty or not a list")

                        except Exception as e:
                            execution_success = False
                            error_message = str(e)
                            self.log_step("⚠️ Error executing SQL", error_message)
                            actual_result = []
                    else:
                        execution_success = False
                        error_message = "Invalid or unrecognized SQL format"
                        self.log_step("⚠️ SQL format invalid", error_message)
                        actual_result = []
                else:
                    execution_success = False
                    error_message = "No SQL query found in LLM response"
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
                        error_message=error_message
                    )
                    self.log_step("📚 Query recorded", f"Learning from execution: success={execution_success}")
                except Exception as e:
                    self.log_step("⚠️ Failed to record query", str(e))
            
            # Prepare response
            response = {
                "success": execution_success or (actual_result is not None),
                "result": actual_result,
                "sql_query": generated_sql or "N/A",
                "intermediate_steps": result.get("intermediate_steps", []),
            }
            
            # Add enhanced context metadata if available
            if enhanced_context:
                response["context_quality"] = enhanced_context.context_quality_score
                response["context_warnings"] = enhanced_context.warning_messages
                response["suggested_tables"] = enhanced_context.domain_insights.get("suggested_tables", [])
            
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
