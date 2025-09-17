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
from src.utils.schema_obfuscator import schema_obfuscator


class SnowflakeNLPAgent:
    """NLP Agent that translates Spanish questions to SQL for Snowflake.

    Executes the query.

    Main responsibilities:
    - Configure the LLM (Groq, Gemini or Ollama, according to configuration)
    - Set up an SQL chain (SQLDatabaseChain) with a Spanish prompt
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

        # Create custom prompt for SQLDatabaseChain with obfuscated schema
        # Secure prompt using obfuscated table/column names to protect real schema
        obfuscated_schema_info = schema_obfuscator.get_obfuscated_schema_info()
        
        sql_prompt = f"""You are a Snowflake SQL expert specialized in real estate. Generate ONLY pure SQL query using the secure schema names provided.

IMPORTANT SECURITY NOTE: Use ONLY the secure table/column names shown below. Never use real database names.

{obfuscated_schema_info}

📋 ADDITIONAL CONTEXT FROM DATABASE:
{{table_info}}

Question: {{input}}

❗ MANDATORY RULES:
1. NEVER use ``` or backticks in your response
2. NEVER use markdown format or code blocks  
3. RESPOND ONLY WITH PURE SQL - NOTHING ELSE
4. USE ONLY the secure table names: real_estate_items, geographic_areas, sales_representatives, commercial_events, property_holders
5. For count queries: use COUNT(*) without LIMIT
6. For other queries: add LIMIT 10
7. For rankings: use RANK() OVER (ORDER BY ...) or ROW_NUMBER() OVER
8. For monetary values: use monetary_value, final_amount, average_deal_value fields

📝 SECURE QUERY EXAMPLES:
Question: most expensive properties by city
Answer: SELECT ga.city_name, rei.item_id, rei.monetary_value, RANK() OVER (PARTITION BY ga.city_name ORDER BY rei.monetary_value DESC) AS rank FROM real_estate_items rei JOIN geographic_areas ga ON rei.area_ref = ga.area_id WHERE rei.monetary_value > 500000 ORDER BY ga.city_name, rank LIMIT 10

Question: agents with most sales
Answer: SELECT first_name, last_name, deal_count FROM sales_representatives ORDER BY deal_count DESC LIMIT 10

Question: recent transactions
Answer: SELECT ce.completion_date, ce.final_amount, rei.item_id FROM commercial_events ce JOIN real_estate_items rei ON ce.item_ref = rei.item_id ORDER BY ce.completion_date DESC LIMIT 10

⛔ NEVER DO THIS:
- Use real table names (properties, locations, agents, transactions, owners)
- Use ``` SELECT ... ``` or ```sql SELECT ... ```
- Add explanations before or after SQL
- Use real column names like property_id, location_id, agent_id

✅ ALWAYS USE SECURE NAMES:
- real_estate_items instead of properties
- geographic_areas instead of locations  
- sales_representatives instead of agents
- commercial_events instead of transactions
- property_holders instead of owners

Generate PURE SQL using ONLY the secure schema names."""

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

    def process_query(self, user_question: str) -> Dict[str, Any]:
        """Process user query and return data ready for the UI.

        Secure Flow with Schema Obfuscation:
        1) Invoke SQL chain to get obfuscated SQL from natural language
        2) Extract generated obfuscated SQL from LangChain intermediate_steps
        3) Normalize/remove markdown format if it exists
        4) Translate obfuscated SQL to real schema names using SchemaObfuscator
        5) Execute real SQL against Snowflake (via SQLDatabase)
        6) Log each step for traceability in Streamlit
        """
        try:
            # Log processing start
            self.log_step("🔍 Processing query", user_question)

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

            # If we have clear SQL, translate and execute it to get real data
            actual_result = None
            if isinstance(sql_query, str):
                # Normalize SQL (remove possible backticks/markdown) - Enhanced for CodeLlama
                cleaned_obfuscated_sql = self.clean_sql_response(sql_query)
                
                if cleaned_obfuscated_sql and cleaned_obfuscated_sql.upper().startswith(("SELECT", "SHOW", "DESCRIBE")):
                    try:
                        # Log the obfuscated SQL generated by LLM
                        self.log_step("🔐 Obfuscated SQL generated", cleaned_obfuscated_sql)
                        
                        # Validate that SQL uses only obfuscated names for security
                        is_secure, violations = schema_obfuscator.validate_obfuscated_sql(cleaned_obfuscated_sql)
                        if not is_secure:
                            self.log_step(
                                "⚠️ Security violation in SQL", 
                                f"Real schema names detected: {', '.join(violations)}"
                            )
                        
                        # Translate obfuscated SQL to real schema names
                        real_sql = schema_obfuscator.translate_to_real_sql(cleaned_obfuscated_sql)
                        self.log_step("🔄 Translated to real SQL", real_sql)
                        
                        # Execute the real SQL against Snowflake
                        self.log_step("🚀 Executing real SQL", real_sql)
                        actual_result = self.db.run(real_sql)
                        self.log_step(
                            "✅ Results obtained",
                            f"{len(actual_result) if hasattr(actual_result, '__len__') else 'N/A'} rows",  # noqa: E501
                        )
                        
                    except Exception as e:
                        self.log_step(
                            "⚠️ Error executing SQL", f"Error: {str(e)}"
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

            # Last resort: if the final result is SQL, translate and execute it
            if actual_result is None:
                final_answer = result.get("result")
                if isinstance(final_answer, str):
                    # Clean the final response too
                    cleaned_final_obfuscated = self.clean_sql_response(final_answer)
                    if cleaned_final_obfuscated and cleaned_final_obfuscated.upper().startswith(
                        ("SELECT", "SHOW", "DESCRIBE")
                    ):
                        try:
                            # Translate obfuscated final response to real SQL
                            real_final_sql = schema_obfuscator.translate_to_real_sql(cleaned_final_obfuscated)
                            self.log_step(
                                "🚀 Executing translated LLM response", real_final_sql
                            )
                            actual_result = self.db.run(real_final_sql)
                        except Exception as e:
                            self.log_step(
                                "⚠️ Error executing LLM response", f"Error: {str(e)}"
                            )
                            actual_result = final_answer
                    else:
                        actual_result = final_answer
                else:
                    actual_result = final_answer

            # Prepare final result with both obfuscated and real SQL for debugging
            final_sql_query = sql_query if isinstance(sql_query, str) else str(sql_query)
            
            return {
                "success": True,
                "result": actual_result,
                "sql_query": final_sql_query,
                "obfuscated_sql": final_sql_query,  # For debugging - shows what LLM generated
                "real_sql": schema_obfuscator.translate_to_real_sql(final_sql_query) if final_sql_query else None,
                "intermediate_steps": result.get("intermediate_steps", []),
                "security_layer": "obfuscated",  # Indicate security layer is active
            }

        except Exception as e:
            error_msg = str(e)
            self.log_step("❌ Error in query processing", error_msg)
            
            # Enhanced error context for schema obfuscation issues
            error_context = {
                "success": False, 
                "error": error_msg, 
                "result": None,
                "security_layer": "obfuscated"
            }
            
            # Add specific error details if it's a translation issue
            if "schema" in error_msg.lower() or "translate" in error_msg.lower():
                error_context["error_type"] = "schema_translation"
                error_context["suggestion"] = "Check if LLM used correct obfuscated table names"
                self.log_step(
                    "⚠️ Schema Translation Error", 
                    "LLM may have used real schema names instead of obfuscated ones"
                )
            
            return error_context

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
