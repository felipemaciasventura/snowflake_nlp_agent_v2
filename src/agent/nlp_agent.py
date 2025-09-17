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

        # Create custom prompt for SQLDatabaseChain
        # English prompt to generate safe and executable SQL for Snowflake - Optimized for Real Estate
        sql_prompt = """You are a Snowflake SQL expert specialized in real estate. Generate ONLY pure SQL query.

DATABASE INFORMATION:
{table_info}

🏡 REAL ESTATE CONTEXT:
This database contains:
- PROPERTIES: Properties (bedrooms, bathrooms, sqft, price, property_type)
- LOCATIONS: Locations (city, state, population, median_income)
- AGENTS: Agents (transaction_count, avg_sale_price, commission_rate)
- TRANSACTIONS: Transactions (sale_date, sale_price, days_on_market)
- OWNERS: Owners (num_properties_owned, investor_flag)

🔗 KEY RELATIONSHIPS:
- properties.location_id = locations.location_id
- transactions.property_id = properties.property_id
- transactions.agent_id = agents.agent_id

Question: {input}

❗ MANDATORY RULES:
1. NEVER use ``` or backticks in your response
2. NEVER use markdown format or code blocks
3. RESPOND ONLY WITH PURE SQL - NOTHING ELSE
4. DO NOT add explanations, comments or additional text
5. For count queries: use COUNT(*) without LIMIT
6. For other queries: add LIMIT 10
7. For rankings: use RANK() OVER (ORDER BY ...)
8. For prices: use column names like sale_price, list_price, price

📝 SPECIFIC REAL ESTATE EXAMPLES:
Question: most expensive properties by city
Answer: SELECT l.city, p.property_id, p.price, RANK() OVER (PARTITION BY l.city ORDER BY p.price DESC) AS rank FROM properties p JOIN locations l ON p.location_id = l.location_id WHERE p.price > 500000 ORDER BY l.city, rank LIMIT 10

Question: agents with most sales
Answer: SELECT first_name, last_name, transaction_count FROM agents ORDER BY transaction_count DESC LIMIT 10

⛔ NEVER DO THIS:
- ``` SELECT ... ```
- ```sql SELECT ... ```
- Explanations before or after SQL

✅ PURE SQL ONLY:"""

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
