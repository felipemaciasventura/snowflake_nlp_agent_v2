import streamlit as st
import pandas as pd
from dotenv import load_dotenv
import os
import re
import ast
from src.agent.nlp_agent import SnowflakeNLPAgent
from src.database.snowflake_conn import SnowflakeConnection

# Regex constants
DECIMAL_REGEX = r"Decimal\('([^']+)'\)"

# Load environment variables
load_dotenv()


# Page configuration
st.set_page_config(page_title="Snowflake NLP Agent", page_icon="🤖", layout="wide")


def initialize_session_state():
    """Initialize session state"""
    if "messages" not in st.session_state:
        st.session_state.messages = []
    if "processing_logs" not in st.session_state:
        st.session_state.processing_logs = []
    if "agent" not in st.session_state:
        st.session_state.agent = None
    if "db_connection" not in st.session_state:
        st.session_state.db_connection = None


def setup_sidebar():
    """Set up sidebar"""
    st.sidebar.header("🔧 Configuration")

    # Connection status
    if st.session_state.db_connection:
        st.sidebar.success("✅ Connected to Snowflake")
    else:
        st.sidebar.error("❌ Not connected")

    # System information + LLM controls
    st.sidebar.header("📊 System Information")
    from src.utils.config import config

    # Helper: determine available providers based on .env and availability
    def _available_providers():
        options = []
        if config.GROQ_API_KEY:
            options.append("groq")
        if config.GOOGLE_API_KEY:
            options.append("gemini")
        if config.is_ollama_available():
            options.append("ollama")
        return options

    current_provider = config.get_available_llm_provider() or "auto"
    providers = _available_providers()

    # Persist selection in session
    if "selected_llm_provider" not in st.session_state:
        st.session_state.selected_llm_provider = current_provider if current_provider != "auto" else (providers[0] if providers else "")

    # Provider selector (only if any available)
    if providers:
        sel = st.sidebar.selectbox(
            "LLM Provider",
            options=providers,
            index=(providers.index(st.session_state.selected_llm_provider) if st.session_state.selected_llm_provider in providers else 0),
            help="Choose which LLM to use. Changing this will re-initialize the agent.",
        )
        st.session_state.selected_llm_provider = sel

        # Model editor per provider
        if sel == "groq":
            model_val = st.sidebar.text_input("Groq model", value=str(config.MODEL_NAME or ""))
        elif sel == "gemini":
            model_val = st.sidebar.text_input("Gemini model", value=str(config.GEMINI_MODEL or ""))
        elif sel == "ollama":
            model_val = st.sidebar.text_input("Ollama model", value=str(config.OLLAMA_MODEL or ""))
            st.sidebar.caption(f"Server: {config.OLLAMA_BASE_URL}")
        else:
            model_val = ""

        # Apply changes button
        if st.sidebar.button("Apply LLM settings"):
            # Update config in-memory and re-create agent
            try:
                # Set provider
                config.LLM_PROVIDER = sel
                # Set model field accordingly
                if sel == "groq" and model_val:
                    config.MODEL_NAME = model_val
                elif sel == "gemini" and model_val:
                    config.GEMINI_MODEL = model_val
                elif sel == "ollama" and model_val:
                    config.OLLAMA_MODEL = model_val

                # Re-initialize agent if DB connection exists
                if st.session_state.db_connection:
                    google_api_key = os.getenv("GOOGLE_API_KEY")
                    groq_api_key = os.getenv("GROQ_API_KEY")
                    st.session_state.agent = SnowflakeNLPAgent(
                        st.session_state.db_connection.get_connection_string(),
                        groq_api_key=groq_api_key,
                        google_api_key=google_api_key,
                    )
                    st.sidebar.success("LLM updated and agent re-initialized ✅")
                else:
                    st.sidebar.warning("Connect to Snowflake first to initialize the agent.")
            except Exception as e:
                st.sidebar.error(f"Failed to apply LLM settings: {e}")

    # Show current info (after potential change)
    provider = config.get_available_llm_provider()
    if provider == "ollama":
        model_info = f"LLM: {config.OLLAMA_MODEL} (Ollama Local)"
        st.sidebar.success("🏠 Local Model Active")
        st.sidebar.info(f"📍 Server: {config.OLLAMA_BASE_URL}")
    elif provider == "gemini":
        model_info = f"LLM: {config.GEMINI_MODEL} (Google Gemini)"
    elif provider == "groq":
        model_info = f"LLM: {config.MODEL_NAME} (Groq)"
    else:
        model_info = "LLM: Not detected"

    st.sidebar.info(model_info)
    st.sidebar.info(f"Database: {os.getenv('SNOWFLAKE_DATABASE')}")
    st.sidebar.info(f"Schema: {os.getenv('SNOWFLAKE_SCHEMA')}")

    # Button to clear history
    if st.sidebar.button("🗑️ Clear History"):
        st.session_state.messages = []
        st.session_state.processing_logs = []
        st.rerun()


# ========================
# Hybrid detection and responses
# ========================


def is_database_query(user_input):
    """Detects if the query is about databases or out of context"""
    user_input_lower = user_input.lower()
    
    # Keywords that indicate database queries (English only)
    db_keywords = [
        "table", "data", "query", "how many", "show", "list", "display",
        "region", "customer", "client", "sale", "average", "sum", "total", "count",
        "select", "database", "schema", "records", "rows", "columns",
        "orders", "products", "categories", "revenue", "income", "billing",
        "analysis", "report", "statistics", "maximum", "minimum", "search",
        "filter", "group", "sort", "top", "highest", "lowest", "latest", "recent",
        # Additional keywords for complex queries
        "city", "cities", "properties", "property", "price", "prices", "ranking",
        "rank", "position", "positions", "each", "get", "obtain", "include", "only",
        "dollars", "values", "value", "transactions", "transaction", "locations",
        "location", "expensive", "cheap", "more", "less", "most", "least",
        "join", "inner", "left", "right", "where", "order by", "group by", "partition",
        "over", "window", "function", "functions", "aggregate", "aggregation",
        # Real estate specific vocabulary (based on SQL schema)
        "agent", "agents", "owner", "owners", "buyer", "buyers", "seller", "sellers",
        "real estate", "house", "houses", "home", "homes", "apartment", "apartments",
        "mortgage", "mortgages", "credit", "financing", "loan", "loans",
        "bedroom", "bedrooms", "bathroom", "bathrooms", "sqft", "square feet",
        "garage", "parking", "pool", "garden", "yard", "patio", "deck",
        "county", "state", "zip code", "zipcode", "msa", "area", "neighborhood",
        "appraisal", "assessment", "tax", "taxes", "commission", "commissions",
        "listing", "listings", "offer", "offers", "closing", "closings", "deed",
        "inspection", "evaluation", "market", "trend", "trends", "growth",
        "profitability", "roi", "investment", "investments", "portfolio"
    ]
    
    # Off-topic keywords (be specific to avoid conflicts)
    off_topic_keywords = [
        "weather", "climate", "news", "cooking recipe", "translate language", "how are you", "hello",
        "joke", "personal story", "movie", "music", "sports", "politics",
        "personal health", "medicine", "travel", "restaurant", "buy clothes", "shopping",
        "personal schedule", "postal address", "personal phone", "personal email", "schedule appointment"
        # Removed "price" and "code" as they can be part of DB queries
    ]
    
    # Help/information questions (special case)
    help_keywords = [
        "help", "what can you do", "how does it work", "what do you do",
        "what are you for", "how to use", "instructions", "commands",
        "examples", "capabilities", "functions"
    ]
    
    # Verificar si es pregunta de ayuda
    if any(keyword in user_input_lower for keyword in help_keywords):
        return "help"
    
    # Verificar si contiene palabras claramente fuera de contexto
    if any(keyword in user_input_lower for keyword in off_topic_keywords):
        return "off_topic"
    
    # Verificar si contiene palabras clave de BD
    if any(keyword in user_input_lower for keyword in db_keywords):
        return "database"
    
    # If not clear, analyze more deeply
    if len(user_input.split()) < 3:  # Too short, probably not a DB query
        return "unclear"
    
    # For long queries (>10 words), probably complex DB queries
    if len(user_input.split()) > 10:
        # Check if it has data query structure
        data_structure_indicators = [
            "for each", "get", "obtain", "show", "list", "find",
            "calculate", "sum", "count", "group by", "order by",
            "with price", "with value", "greater than", "less than", "equal to",
            "include", "exclude", "only", "just", "exclusively"
        ]
        
        if any(indicator in user_input_lower for indicator in data_structure_indicators):
            return "database"
    
    return "database"  # By default, try as DB query


def get_help_response():
    """Returns educational response about system capabilities"""
    return {
        "type": "help",
        "message": """Hello! 👋 I'm your NLP assistant for real estate queries in Snowflake.

🔍 **I can help you with:**
• 🏠 **Properties:** "How many properties are there per city?"
• 💰 **Prices:** "What's the average price per square foot?"
• 👥 **Agents:** "Show me agents with most sales"
• 📈 **Transactions:** "List the last 10 transactions"
• 📊 **Analysis:** "Which city has the most expensive properties?"
• 🏦 **Locations:** "Show me statistics by county"

🎨 **Examples you can try:**
• "For each city, get the average sale price"
• "Which agent has sold the most properties this year?"
• "List properties with more than 3 bedrooms and a pool"
• "What's the average commission of agents?"
• "Show me the most expensive properties by city"
• "How many transactions were made last month?"

Ask me any question about real estate! 🏡🚀"""
    }


def get_redirect_response():
    """Returns redirect response for out-of-context queries"""
    return {
        "type": "redirect",
        "message": """🤖 I'm an assistant specialized in Snowflake database queries.

I can't help you with that query, but I can help you explore your data! 📋

🎨 **Try asking me something like:**
• "How many records are in the customers table?"
• "Show me the regions with highest revenue"
• "What tables are available?"

Is there any information from your database you'd like to know? 😊"""
    }


# ========================
# Formatting utilities
# ========================


def parse_sql_result_string(result_string):
    """Parse a string with SQL results and convert it to real data"""

    # If it's not a string or doesn't have expected format, return as is
    if not isinstance(result_string, str) or not result_string.strip():
        return result_string

    # Clean input string
    cleaned_string = result_string.strip()

    try:
        # Case 1: List of tuples [(...), (...)]
        if cleaned_string.startswith("[") and cleaned_string.endswith("]"):
            # Replace Decimal('...') with float
            cleaned_string = re.sub(DECIMAL_REGEX, r"\1", cleaned_string)
            # Replace None with 'None' for safe evaluation
            cleaned_string = re.sub(r"\bNone\b", "'None'", cleaned_string)

            # Try to evaluate as Python literal
            parsed_data = ast.literal_eval(cleaned_string)
            return parsed_data

        # Case 2: Simple tuple (...)
        elif cleaned_string.startswith("(") and cleaned_string.endswith(")"):
            # Convert simple tuple to list of tuples
            cleaned_string = f"[{cleaned_string}]"
            cleaned_string = re.sub(DECIMAL_REGEX, r"\1", cleaned_string)
            cleaned_string = re.sub(r"\bNone\b", "'None'", cleaned_string)

            parsed_data = ast.literal_eval(cleaned_string)
            return parsed_data

        # Case 3: String that seems to be data but not well formatted
        elif "Decimal(" in cleaned_string or "None" in cleaned_string:
            # Try to fix the format
            if not cleaned_string.startswith("["):
                cleaned_string = f"[{cleaned_string}]"

            cleaned_string = re.sub(DECIMAL_REGEX, r"\1", cleaned_string)
            cleaned_string = re.sub(r"\bNone\b", "'None'", cleaned_string)

            parsed_data = ast.literal_eval(cleaned_string)
            return parsed_data

    except (ValueError, SyntaxError, TypeError):
        # Parsing errors are normal for complex data like datetime
        # The fallback will handle the case

        # Fallback: try to extract data using regex
        try:
            # Look for tuple patterns with numbers
            tuple_pattern = r"\(([^)]+)\)"
            matches = re.findall(tuple_pattern, cleaned_string)

            if matches:
                parsed_tuples = []
                for match in matches:
                    # Separate elements by comma
                    elements = [elem.strip().strip("'\"") for elem in match.split(",")]
                    # Convert numbers when possible
                    converted_elements = []
                    for elem in elements:
                        try:
                            # Try to convert to number
                            if "." in elem:
                                converted_elements.append(float(elem))
                            else:
                                converted_elements.append(int(elem))
                        except ValueError:
                            # If not a number, keep as string
                            converted_elements.append(elem)

                    parsed_tuples.append(tuple(converted_elements))

                return parsed_tuples

        except Exception:
            # Fallback also failed, will return original string
            pass

    # If everything fails, return original string
    return result_string


def extract_column_names_from_sql(sql_query):
    """Extract meaningful column names from SQL query using aliases or column names."""
    import re
    
    # If it's already a list of column names, return it directly
    if isinstance(sql_query, list):
        return sql_query
    
    if not sql_query or not isinstance(sql_query, str):
        return None
    
    # Clean the SQL query
    sql_clean = sql_query.strip().upper()
    
    try:
        # Look for SELECT statement
        select_match = re.search(r'SELECT\s+(.*?)\s+FROM', sql_clean, re.DOTALL | re.IGNORECASE)
        if not select_match:
            return None
        
        select_part = select_match.group(1).strip()
        
        # Handle SELECT * case
        if select_part.strip() == '*':
            return None
        
        # Split by comma to get individual column expressions
        column_expressions = [expr.strip() for expr in select_part.split(',')]
        
        column_names = []
        
        for expr in column_expressions:
            # Case 1: Look for AS alias (e.g., "column_name AS alias")
            as_match = re.search(r'\bAS\s+([\w_]+)$', expr, re.IGNORECASE)
            if as_match:
                alias = as_match.group(1).lower()
                # Convert to more readable format
                readable_name = alias.replace('_', ' ').title()
                column_names.append(readable_name)
                continue
            
            # Case 2: Look for function calls with aliases (e.g., "COUNT(*) AS count")
            func_as_match = re.search(r'\w+\([^)]*\)\s+AS\s+([\w_]+)', expr, re.IGNORECASE)
            if func_as_match:
                alias = func_as_match.group(1).lower()
                readable_name = alias.replace('_', ' ').title()
                column_names.append(readable_name)
                continue
            
            # Case 3: Simple column reference (e.g., "p.property_id", "city")
            simple_col_match = re.search(r'(?:[\w]+\.)?([\w_]+)$', expr)
            if simple_col_match:
                col_name = simple_col_match.group(1).lower()
                readable_name = col_name.replace('_', ' ').title()
                column_names.append(readable_name)
                continue
            
            # Case 4: Function calls without aliases (e.g., "COUNT(*)", "AVG(price)")
            func_match = re.search(r'(\w+)\(', expr)
            if func_match:
                func_name = func_match.group(1).upper()
                if func_name == 'COUNT':
                    column_names.append('Count')
                elif func_name == 'AVG':
                    column_names.append('Average')
                elif func_name == 'SUM':
                    column_names.append('Total')
                elif func_name == 'MAX':
                    column_names.append('Maximum')
                elif func_name == 'MIN':
                    column_names.append('Minimum')
                elif func_name == 'CURRENT_DATABASE':
                    column_names.append('Database')
                elif func_name == 'CURRENT_SCHEMA':
                    column_names.append('Schema')
                else:
                    column_names.append(func_name.title())
                continue
            
            # Fallback: use a generic name
            column_names.append(f'Column {len(column_names) + 1}')
        
        return column_names if column_names else None
        
    except Exception:
        # If parsing fails, return None to use fallback
        return None


def format_sql_result_to_dataframe(data, sql_query="", user_question=""):
    """Convert SQL results into a well-formatted DataFrame"""
    from decimal import Decimal

    # Smart formatting of SQL results

    try:
        # Case 1: If it's a string, try to parse it first
        if isinstance(data, str):
            # Try to parse if it looks like SQL data
            if data.startswith("[") or data.startswith("("):
                parsed_data = parse_sql_result_string(data)
                if parsed_data != data:  # If it could be parsed
                    data = parsed_data
                    # String parsed successfully
                else:
                    return pd.DataFrame({"Result": [data]})
            else:
                return pd.DataFrame({"Result": [data]})

        # Normalize single-row structures into a list so downstream logic works uniformly
        # Single SQLAlchemy Row
        if not isinstance(data, list) and hasattr(data, "_mapping"):
            data = [data]
        # Single dict row
        if isinstance(data, dict):
            data = [data]
        # Single tuple/list row
        if isinstance(data, tuple):
            data = [data]

        # Case 2: If there's no data or it's not a list
        if not isinstance(data, list) or not data:
            return pd.DataFrame({"Result": ["No data"]})


        
        # Normalization utilities (used across formats)
        def _normalize_value(v):
            # Normalize common DB types for Arrow compatibility
            if isinstance(v, (bytes, bytearray)):
                try:
                    return v.decode("utf-8", errors="ignore")
                except Exception:
                    return str(v)
            if isinstance(v, Decimal):
                try:
                    return float(v)
                except Exception:
                    return str(v)
            return v

        def _readable_names(names):
            return [str(n).replace("_", " ").title() for n in names]

        # Pre-extract column names from SQL if possible
        extracted_column_names = extract_column_names_from_sql(sql_query)

        # Case 3: Handle rows returned as SQLAlchemy Row/RowMapping or dicts
        first_row = data[0]
        # SQLAlchemy Row -> use _mapping for stable order
        if hasattr(first_row, "_mapping") and hasattr(first_row._mapping, "keys"):
            mapping_keys = list(first_row._mapping.keys())
            rows = []
            for r in data:
                vals = [ _normalize_value(r._mapping[k]) for k in mapping_keys ]
                rows.append(vals)
            # Prefer names extracted from SQL if they match; else mapping keys prettified
            if extracted_column_names and len(extracted_column_names) == len(mapping_keys):
                columns = extracted_column_names
            else:
                columns = _readable_names(mapping_keys)
            return pd.DataFrame(rows, columns=columns)

        # Dict rows
        if isinstance(first_row, dict):
            dict_keys = list(first_row.keys())
            rows = []
            for r in data:
                vals = [ _normalize_value(r.get(k)) for k in dict_keys ]
                rows.append(vals)
            if extracted_column_names and len(extracted_column_names) == len(dict_keys):
                columns = extracted_column_names
            else:
                columns = _readable_names(dict_keys)
            return pd.DataFrame(rows, columns=columns)

        # Case 5: COUNT queries (English only)
        if "COUNT(*)" in sql_query.upper():
            if len(data) > 0 and len(data[0]) == 1:
                count_value = data[0][0]
                # Determine what's being counted based on the query context
                if "table" in user_question.lower():
                    return pd.DataFrame(
                        [
                            {
                                "Description": "Total database tables",
                                "Count": f"{count_value:,}",
                            }
                        ]
                    )
                elif "customer" in user_question.lower() or "client" in user_question.lower():
                    return pd.DataFrame(
                        [
                            {
                                "Description": "Total customers",
                                "Count": f"{count_value:,}",
                            }
                        ]
                    )
                elif "order" in user_question.lower():
                    return pd.DataFrame(
                        [
                            {
                                "Description": "Total orders",
                                "Count": f"{count_value:,}",
                            }
                        ]
                    )
                elif "sale" in user_question.lower():
                    return pd.DataFrame(
                        [
                            {
                                "Description": "Total sales",
                                "Count": f"{count_value:,}",
                            }
                        ]
                    )
                else:
                    return pd.DataFrame(
                        [
                            {
                                "Description": "Total records",
                                "Count": f"{count_value:,}",
                            }
                        ]
                    )

        # Case 6: For CURRENT_DATABASE
        if "CURRENT_DATABASE" in sql_query.upper():
            return pd.DataFrame(data, columns=["Database"])

        # Case 7: For SHOW TABLES
        if "SHOW TABLES" in sql_query.upper():
            if len(data) > 0 and len(data[0]) >= 2:
                table_data = []
                for row in data:
                    table_data.append(
                        {
                            "Table": row[1],
                            "Type": row[4] if len(row) > 4 else "TABLE",
                            "Description": (
                                row[5] if len(row) > 5 else "No description"
                            ),
                        }
                    )
                return pd.DataFrame(table_data)

        # Case 8: For region-based queries (English only)
        if "region" in user_question.lower() and len(data) > 0 and len(data[0]) == 2:
            # Detect if it's average, sum, total, etc.
            if "average" in user_question.lower() or "avg" in sql_query.lower():
                metric_name = "Average Revenue"
            elif "sum" in user_question.lower() or "total" in user_question.lower():
                metric_name = "Total Revenue"
            elif "count" in sql_query.lower():
                metric_name = "Count"
            else:
                metric_name = "Value"
            
            formatted_rows = []
            for row in data:
                region = row[0]
                value = row[1]
                
                # Format value as currency if numeric
                if isinstance(value, (int, float, Decimal)):
                    value_formatted = f"${float(value):,.2f}"
                else:
                    value_formatted = str(value)
                
                formatted_rows.append({
                    "Region": region,
                    metric_name: value_formatted
                })
            
            return pd.DataFrame(formatted_rows)

        # Case 9: Default - create DataFrame with intelligent column names
        try:
            # Normalize tuple/list rows
            if len(data) > 0 and isinstance(data[0], (tuple, list)):
                num_cols = len(data[0]) if data[0] else 1
                normalized_rows = [ [_normalize_value(v) for v in row] for row in data ]
                if extracted_column_names and len(extracted_column_names) == num_cols:
                    df = pd.DataFrame(normalized_rows, columns=extracted_column_names)
                    return df
                # Fall back to generic names to avoid unnamed columns
                df = pd.DataFrame(normalized_rows, columns=[f"Column {i+1}" for i in range(num_cols)])
                return df

            # Fallback attempt
            df = pd.DataFrame([[_normalize_value(v) for v in data]])
            return df
        except Exception:
            # If it fails, try with intelligent column names
            try:
                if len(data) > 0 and isinstance(data[0], (tuple, list)):
                    # Try to extract column names from SQL first
                    num_cols = len(data[0]) if data[0] else 1
                    
                    if extracted_column_names and len(extracted_column_names) == num_cols:
                        column_names = extracted_column_names
                    else:
                        # Create more descriptive generic column names
                        column_names = [f"Column {i+1}" for i in range(num_cols)]
                    
                    normalized_rows = [ [_normalize_value(v) for v in row] for row in data ]
                    df = pd.DataFrame(normalized_rows, columns=column_names)
                    return df
                else:
                    # Data in unexpected format
                    df = pd.DataFrame({"Result": data if isinstance(data, list) else [data]})
                    return df
            except Exception:
                # Last resort: convert everything to string
                return pd.DataFrame({"Result": [str(data)]})

    except Exception:
        # Formatting error, use robust handling with intelligent column names
        try:
            # Try to create basic DataFrame
            if isinstance(data, list) and len(data) > 0:
                if isinstance(data[0], (tuple, list)):
                    # List of tuples/lists - try to extract column names from SQL
                    extracted_column_names = extract_column_names_from_sql(sql_query)
                    num_cols = len(data[0]) if data[0] else 1
                    
                    if extracted_column_names and len(extracted_column_names) == num_cols:
                        column_names = extracted_column_names
                    else:
                        # Use more readable generic names
                        column_names = [f"Column {i+1}" for i in range(num_cols)]
                    
                    return pd.DataFrame(data, columns=column_names)
                else:
                    # Simple list
                    return pd.DataFrame({"Result": data})
            else:
                # Generic case
                return pd.DataFrame({"Result": [str(data)]})
        except Exception:
            # Absolute last resort
            return pd.DataFrame({"Error": [f"Could not process data: {str(data)[:100]}..."]})


# ========================
# UI rendering (messages and chat)
# ========================


def _render_single_message(message):
    """Render a single message from history."""
    with st.chat_message(message["role"]):
        is_assistant_with_data = message["role"] == "assistant" and "data" in message
        if not is_assistant_with_data:
            st.write(message["content"])
            return

        st.write(message["content"])
        if not message["data"].empty:
            df_hist = message["data"]
            executed_sql_hist = message.get("sql", "")

            # Reuse intelligent column selection with persistent checkbox
            def _norm(name: str) -> str:
                return str(name).strip().lower().replace(" ", "_")

            key_candidates = [
                "id", "agent_id", "agent_uid", "property_id",
                "name", "first_name", "last_name", "full_name",
                "email", "phone", "agency", "city", "state",
                "license_number", "active_flag", "date_joined"
            ]
            key_norms = set(key_candidates)
            column_norm_map = {c: _norm(c) for c in df_hist.columns}
            selected_cols = [c for c, n in column_norm_map.items() if n in key_norms]

            df_to_show_hist = df_hist
            if df_hist.shape[1] > 12 and len(selected_cols) >= 3:
                show_all_key_hist = f"show_all_cols_{abs(hash(executed_sql_hist)) % (10**8)}"
                show_all_hist = st.checkbox("Show all columns", value=False, key=show_all_key_hist)
                if not show_all_hist:
                    df_to_show_hist = df_hist[selected_cols]

            st.dataframe(df_to_show_hist, use_container_width=True)
            num_rows = len(df_hist)
            st.caption(
                f"📊 {num_rows} record{'s' if num_rows != 1 else ''} shown"
            )


def display_chat_messages():
    """Display chat message history with tables and counters."""
    st.header("💬 Chat with your Database")

    # Show message history
    for message in st.session_state.messages:
        _render_single_message(message)


def _append_assistant_message(content, df=None, sql: str | None = None):
    """Add an assistant message to history with optional DataFrame and SQL string for stable UI keys."""
    st.session_state.messages.append({
        "role": "assistant",
        "content": content,
        "data": df if df is not None else pd.DataFrame(),
        "sql": sql or "",
    })


def _render_successful_result(result, prompt):
    """Render a successful agent result and update history."""
    response_content = "Query executed successfully:"
    st.write(response_content)

    # The agent's process_query method should return actual executed data
    # If result["result"] contains SQL instead of data, there's a logic issue
    
    actual_data = result.get("result")
    # Try to parse stringified list/tuple results into Python objects
    if isinstance(actual_data, str):
        from ast import literal_eval
        import re as _re
        sanitized = actual_data
        try:
            # Replace datetime.date(Y, M, D) with 'YYYY-MM-DD' to make it literal-evaluable
            def _date_repl(match):
                y, m, d = match.group(1), match.group(2), match.group(3)
                try:
                    y_i, m_i, d_i = int(y), int(m), int(d)
                    return f"'{y_i:04d}-{m_i:02d}-{d_i:02d}'"
                except Exception:
                    return match.group(0)
            sanitized = _re.sub(r"datetime\.date\(\s*(\d{1,4})\s*,\s*(\d{1,2})\s*,\s*(\d{1,2})\s*\)", _date_repl, sanitized)
            actual_data = literal_eval(sanitized)
        except Exception:
            # Keep as-is if parsing fails
            pass
    
    # Check for truly empty results
    if actual_data is None or (isinstance(actual_data, list) and len(actual_data) == 0):
        st.write("Query executed successfully. No results found.")
        _append_assistant_message("Query executed successfully. No results found.")
        return

    try:
        # actual_data is already extracted/parsed above
        
        # Check if we received SQL instead of data (indicates a problem)
        if isinstance(actual_data, str) and actual_data.strip().upper().startswith('SELECT'):
            st.error("⚠️ Received SQL query instead of data results. This indicates a processing issue.")
            st.code(actual_data)
            _append_assistant_message(f"Processing issue - received SQL instead of results: {actual_data}")
            return
        
        # Get the SQL that was executed for column name extraction
        executed_sql = result.get('sql_query', '')
        
        # Format the actual data into a DataFrame
        df = format_sql_result_to_dataframe(
            actual_data, executed_sql, prompt
        )
        
        # Intelligent column selection when there are too many columns
        def _norm(name: str) -> str:
            return str(name).strip().lower().replace(" ", "_")

        key_candidates = [
            "id", "agent_id", "agent_uid", "property_id",
            "name", "first_name", "last_name", "full_name",
            "email", "phone", "agency", "city", "state",
            "license_number", "active_flag", "date_joined"
        ]
        key_norms = set(key_candidates)
        column_norm_map = {c: _norm(c) for c in df.columns}
        selected_cols = [c for c, n in column_norm_map.items() if n in key_norms]

        show_all_key = f"show_all_cols_{abs(hash(executed_sql)) % (10**8)}"
        use_subset = False
        df_to_show = df
        if df.shape[1] > 12:
            show_all = st.checkbox("Show all columns", value=False, key=show_all_key)
            if not show_all and len(selected_cols) >= 3:
                use_subset = True
                df_to_show = df[selected_cols]

        # Detect URL-like columns for link rendering
        url_cols = [c for c in df_to_show.columns if ("url" in c.lower() or "website" in c.lower())]
        column_config = {}
        for uc in url_cols:
            try:
                column_config[uc] = st.column_config.LinkColumn(label=uc)
            except Exception:
                pass  # Fallback silently if not supported

        # Row display control
        st.dataframe(df_to_show, use_container_width=True, column_config=column_config)
        num_rows = len(df)
        st.caption(
            f"📊 {num_rows} record{'s' if num_rows != 1 else ''} found"
        )

        # Export buttons
        import io
        csv_data = df.to_csv(index=False).encode("utf-8")
        st.download_button(
            label="Download CSV",
            data=csv_data,
            file_name="results.csv",
            mime="text/csv",
        )
        try:
            buf = io.BytesIO()
            df.to_parquet(buf, index=False)
            st.download_button(
                label="Download Parquet",
                data=buf.getvalue(),
                file_name="results.parquet",
                mime="application/octet-stream",
            )
        except Exception:
            pass  # Parquet dependencies not installed; skip

        _append_assistant_message(response_content, df, executed_sql)
        
    except Exception as e:
        st.error(f"Error formatting results: {str(e)}")
        result_text = str(result.get("result"))
        st.code(result_text)
        _append_assistant_message(f"{response_content}\n{result_text}")


def _render_error_result(error_text):
    """Render an agent error and update history."""
    st.error(error_text)
    _append_assistant_message(error_text)


def process_user_input(prompt):
    """Process user input with hybrid detection.

    Hybrid flow:
    1. Detect query type (DB, help, out of context)
    2. Respond appropriately according to type
    3. For DB queries: invoke NLP agent → SQL → execution
    4. For others: show educational/redirect responses
    """
    # Add user message
    st.session_state.messages.append({"role": "user", "content": prompt})

    with st.chat_message("user"):
        st.write(prompt)

    # Detect query type
    query_type = is_database_query(prompt)
    
    # Single assistant response block
    with st.chat_message("assistant"):
        if query_type == "help":
            help_resp = get_help_response()
            st.markdown(help_resp["message"])
            _append_assistant_message(help_resp["message"])
            return

        if query_type == "off_topic":
            redirect_resp = get_redirect_response()
            st.markdown(redirect_resp["message"])
            _append_assistant_message(redirect_resp["message"])
            return

        if query_type == "unclear":
            st.info("🤔 I'm not sure if you're asking about data. I'll try as a DB query...")

        if not st.session_state.agent:
            _render_error_result("Error: No agent initialized")
            return

        with st.spinner("Processing query..."):
            result = st.session_state.agent.process_query(prompt)

        if result.get("success"):
            _render_successful_result(result, prompt)
            return

        _render_error_result(f"Error: {result.get('error')}")


def display_logs_panel():
    """Show explanatory logs panel"""
    st.header("📋 Process Logs")

    if st.session_state.processing_logs:
        # Show logs in reverse order (most recent first)
        for log in reversed(st.session_state.processing_logs[-10:]):  # Last 10 logs
            with st.expander(f"⏰ {log['timestamp']} - {log['step']}", expanded=False):
                st.code(log["content"])
    else:
        st.info("No logs available. Make a query to see the process.")


def main():
    """Main Streamlit app function.

    Assembles UI and bootstrapping:
    - Initialize session state (messages, logs, connection, agent)
    - Manage Snowflake connection and create agent if credentials exist
    - Organize layout (chat on left, sidebar + logs on right)
    - Place chat_input at the end (outside columns) to comply with Streamlit rules
    """
    st.title("🤖 NLP Agent for Snowflake Queries")
    st.markdown(
        "Ask questions in English and get answers from your Snowflake database"
    )

    # Initialize state
    initialize_session_state()

    # Set up connection if it doesn't exist
    if not st.session_state.db_connection:
        with st.spinner("Connecting to Snowflake..."):
            db_conn = SnowflakeConnection()
            if db_conn.connect():
                st.session_state.db_connection = db_conn

                # Initialize agent (auto-detects LLM provider)
                google_api_key = os.getenv("GOOGLE_API_KEY")
                groq_api_key = os.getenv("GROQ_API_KEY")
                try:
                    st.session_state.agent = SnowflakeNLPAgent(
                        db_conn.get_connection_string(),
                        groq_api_key=groq_api_key,
                        google_api_key=google_api_key,
                    )
                    st.success("✅ Connection established successfully!")
                except Exception as e:
                    st.error(f"❌ Error initializing LLM: {e}")
                    st.stop()
            else:
                st.error(
                    "❌ Could not connect to Snowflake. Check your configuration."
                )
                st.stop()

    # Column layout
    col1, col2 = st.columns([2, 1])

    with col1:
        display_chat_messages()

    with col2:
        setup_sidebar()
        display_logs_panel()

    # User input (outside column layout)
    if prompt := st.chat_input("Write your query in English..."):
        process_user_input(prompt)


if __name__ == "__main__":
    main()
