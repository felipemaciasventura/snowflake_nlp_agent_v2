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

    # System information
    st.sidebar.header("📊 System Information")
    if st.session_state.agent:
        # Detect which LLM model is being used
        from src.utils.config import config
        provider = config.get_available_llm_provider()
        
        if provider == "ollama":
            model_info = f"LLM: {config.OLLAMA_MODEL} (Ollama Local)"
            # Additional information for Ollama
            st.sidebar.success(f"🏠 Local Model Active")
            st.sidebar.info(f"📍 Server: {config.OLLAMA_BASE_URL}")
        elif provider == "gemini":
            model_info = f"LLM: {config.GEMINI_MODEL} (Google Gemini)"
        elif provider == "groq":
            model_info = f"LLM: {config.MODEL_NAME} (Groq)"
        else:
            model_info = "LLM: Not detected"
            
        st.sidebar.info(model_info)
        
        # Show dynamic database context instead of static environment vars
        if st.session_state.db_connection:
            try:
                context = st.session_state.db_connection.get_database_context()
                if "error" not in context:
                    st.sidebar.header("🗂️ Database Context")
                    st.sidebar.success(f"🏢 Database: **{context.get('database', 'N/A')}**")
                    st.sidebar.info(f"📋 Schema: **{context.get('schema', 'N/A')}**")
                    st.sidebar.info(f"🏗️ Warehouse: **{context.get('warehouse', 'N/A')}**")
                    st.sidebar.metric("📊 Tables", context.get('table_count', 0))
                    st.sidebar.metric("🗃️ Schemas", context.get('schema_count', 0))
                    
                    # Show sample tables
                    if context.get('sample_tables'):
                        with st.sidebar.expander("🔍 Sample Tables"):
                            for table in context['sample_tables'][:5]:
                                st.write(f"• {table['name']} ({table['type']})")
                else:
                    st.sidebar.warning(f"⚠️ {context['error']}")
            except Exception as e:
                st.sidebar.error(f"❌ Context error: {str(e)[:50]}...")
        else:
            # Fallback to environment variables
            st.sidebar.info(f"Database: {os.getenv('SNOWFLAKE_DATABASE', 'Not set')}")
            st.sidebar.info(f"Schema: {os.getenv('SNOWFLAKE_SCHEMA', 'Not set')}")

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
    
    # Keywords indicating database queries
    db_keywords = [
        "table", "data", "query", "how many", "show", "list", "display",
        "region", "customer", "sale", "average", "sum", "total", "count",
        "select", "database", "schema", "records", "rows", "columns",
        "orders", "products", "categories", "revenue", "billing",
        "analysis", "report", "statistics", "maximum", "minimum", "search",
        "filter", "group", "sort", "top", "highest", "lowest", "latest", "recent",
        # Additional keywords for complex queries
        "city", "cities", "properties", "property", "price", "prices", "ranking",
        "rank", "position", "positions", "each", "get", "obtain", "include", "only",
        "dollars", "values", "value", "transactions", "transaction", "locations",
        "location", "expensive", "more", "less", "most", "least",
        "join", "inner", "left", "right", "where", "order by", "group by", "partition",
        "over", "window", "function", "functions", "aggregate", "aggregation",
        # Real estate specific vocabulary (based on SQL schema)
        "agent", "agents", "owner", "owners", "buyer", "buyers", "seller", "sellers",
        "sale", "sales", "purchase", "purchases", "listing", "listings",
        "property", "properties", "house", "houses", "apartment", "apartments", "lot", "lots",
        "mortgage", "mortgages", "credit", "financing", "loan", "loans",
        "bedrooms", "rooms", "bathrooms", "meters", "m2", "feet", "sqft",
        "garage", "parking", "pool", "garden", "yard", "patio", "terrace",
        "county", "state", "zip code", "zipcode", "msa", "zone", "neighborhood",
        "appraisal", "valuation", "tax", "taxes", "commission", "commissions",
        "listing", "listings", "offer", "offers", "closing", "closings", "deed",
        "inspection", "evaluation", "market", "trend", "trends", "growth",
        "profitability", "roi", "investment", "investments", "portfolio"
    ]
    
    # Off-topic keywords (specific to avoid conflicts)
    off_topic_keywords = [
        "weather", "climate", "news", "recipe", "translate language", "how are you", "hello",
        "joke", "personal story", "movie", "music", "sport", "politics",
        "personal health", "medicine", "travel", "restaurant", "buy clothes",
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
    if len(user_input.split()) < 3:  # Very short, probably not a DB query
        return "unclear"
    
    # For long queries (>10 words), probably complex DB queries
    if len(user_input.split()) > 10:
        # Check if it has data query structure
        data_structure_indicators = [
            "for each", "get", "obtain", "show", "list", "find",
            "calculate", "sum", "count", "group by", "order by",
            "with price", "with value", "greater than", "less than", "equal to",
            "include", "exclude", "only", "just", "uniquely"
        ]
        
        if any(indicator in user_input_lower for indicator in data_structure_indicators):
            return "database"
    
    return "database"  # By default, try as database query


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
        # First, handle datetime objects in string representation
        # Replace datetime.date(YYYY, M, D) with a simple string representation
        datetime_pattern = r"datetime\.date\((\d+),\s*(\d+),\s*(\d+)\)"
        cleaned_string = re.sub(datetime_pattern, r"'\1-\2-\3'", cleaned_string)
        
        # Replace datetime.datetime patterns too
        datetime_full_pattern = r"datetime\.datetime\(([^)]+)\)"
        def datetime_replacer(match):
            # Convert datetime components to a simple string
            components = match.group(1)
            return f"'datetime({components})'"
        cleaned_string = re.sub(datetime_full_pattern, datetime_replacer, cleaned_string)

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
        elif "Decimal(" in cleaned_string or "None" in cleaned_string or "datetime" in cleaned_string:
            # Try to fix the format
            if not cleaned_string.startswith("["):
                cleaned_string = f"[{cleaned_string}]"

            cleaned_string = re.sub(DECIMAL_REGEX, r"\1", cleaned_string)
            cleaned_string = re.sub(r"\bNone\b", "'None'", cleaned_string)

            parsed_data = ast.literal_eval(cleaned_string)
            return parsed_data

    except (ValueError, SyntaxError, TypeError):
        # Parsing errors are normal for complex data like datetime
        # Try a more robust approach using regex to extract structured data

        # Advanced fallback: try to manually parse the tuple structure
        try:
            # For the complex case with datetime objects, extract tuples manually
            # This handles the case where we have string representations of tuples with complex objects
            
            # Remove the outer brackets if present
            work_string = cleaned_string
            if work_string.startswith("[") and work_string.endswith("]"):
                work_string = work_string[1:-1]
            
            # Split by tuple boundaries - this is tricky because tuples can contain commas
            # Use a more sophisticated approach
            tuples = []
            current_tuple = []
            paren_depth = 0
            current_element = ""
            i = 0
            
            while i < len(work_string):
                char = work_string[i]
                
                if char == '(' and paren_depth == 0:
                    # Start of new tuple
                    if current_tuple:
                        tuples.append(current_tuple)
                        current_tuple = []
                    paren_depth = 1
                    current_element = ""
                elif char == ')' and paren_depth == 1:
                    # End of current tuple
                    if current_element.strip():
                        current_tuple.append(current_element.strip())
                    if current_tuple:
                        tuples.append(current_tuple)
                    current_tuple = []
                    paren_depth = 0
                    current_element = ""
                elif char == '(' and paren_depth > 0:
                    paren_depth += 1
                    current_element += char
                elif char == ')' and paren_depth > 1:
                    paren_depth -= 1
                    current_element += char
                elif char == ',' and paren_depth == 1:
                    # Element separator within tuple
                    if current_element.strip():
                        current_tuple.append(current_element.strip())
                    current_element = ""
                elif paren_depth > 0:
                    current_element += char
                
                i += 1
            
            # Convert string elements to appropriate types
            parsed_tuples = []
            for tuple_elements in tuples:
                converted_tuple = []
                for element in tuple_elements:
                    element = element.strip().strip("'\"")
                    
                    # Try to convert to appropriate type
                    if element in ['None', 'null', 'NULL']:
                        converted_tuple.append('')
                    elif element in ['True', 'true']:
                        converted_tuple.append(True)
                    elif element in ['False', 'false']:
                        converted_tuple.append(False)
                    elif element.replace('.', '').replace('-', '').isdigit():
                        # Numeric value
                        try:
                            if '.' in element:
                                converted_tuple.append(float(element))
                            else:
                                converted_tuple.append(int(element))
                        except:
                            converted_tuple.append(element)
                    else:
                        # String value
                        converted_tuple.append(element)
                
                if converted_tuple:
                    parsed_tuples.append(tuple(converted_tuple))
            
            if parsed_tuples:
                return parsed_tuples

        except Exception:
            # If advanced parsing fails too, return original
            pass

    # If everything fails, return original string
    return result_string


def format_data_for_display(df):
    """Format DataFrame values for better visual presentation"""
    try:
        df_formatted = df.copy()
        
        for col in df_formatted.columns:
            # Format specific column types for better display
            if col in ['Phone', 'phone']:
                # Clean up phone number display
                df_formatted[col] = df_formatted[col].str.replace('x', ' ext. ')
            
            elif col in ['Email', 'email']:
                # Email formatting is fine as-is
                pass
            
            elif col in ['Total_Value', 'Price', 'Commission_Rate', 'Conversion_Rate']:
                # Format monetary and percentage values
                for idx in df_formatted.index:
                    val = str(df_formatted.loc[idx, col])
                    if val.replace('.', '').replace('-', '').isdigit():
                        try:
                            num_val = float(val)
                            if col in ['Total_Value', 'Price'] and num_val > 1000:
                                df_formatted.loc[idx, col] = f"${num_val:,.2f}"
                            elif col in ['Commission_Rate', 'Conversion_Rate'] and num_val < 100:
                                df_formatted.loc[idx, col] = f"{num_val}%"
                        except:
                            pass
            
            elif col in ['Address', 'address']:
                # Clean up address formatting
                df_formatted[col] = df_formatted[col].str.replace('\\n', ', ')
            
            elif col in ['Bio', 'Description', 'bio', 'description']:
                # Truncate long text fields for better display
                df_formatted[col] = df_formatted[col].apply(
                    lambda x: x[:100] + '...' if len(str(x)) > 100 else x
                )
            
            elif col in ['Languages', 'languages', 'Specialization', 'specialization']:
                # Format comma-separated values
                df_formatted[col] = df_formatted[col].str.replace(',', ', ')
        
        return df_formatted
    except Exception:
        # If formatting fails, return original
        return df

def clean_dataframe_for_streamlit(df):
    """Clean DataFrame to ensure Streamlit/PyArrow compatibility"""
    try:
        # Make a copy to avoid modifying the original
        df_cleaned = df.copy()
        
        # First apply formatting for better visual presentation
        df_cleaned = format_data_for_display(df_cleaned)
        
        # Force all columns to string type to prevent PyArrow inference issues
        for col in df_cleaned.columns:
            # First handle null values, then convert to string
            df_cleaned[col] = df_cleaned[col].fillna('')  # Use empty string instead of 'N/A'
            df_cleaned[col] = df_cleaned[col].astype(str)
            
            # Clean up common problematic values
            df_cleaned[col] = df_cleaned[col].replace({
                'nan': '',
                'NaN': '',
                'None': '',
                'null': '',
                'NULL': ''
            })
        
        return df_cleaned
    except Exception as e:
        # If cleaning fails, create a simple string-only DataFrame
        try:
            cleaned_data = {}
            for col in df.columns:
                # Convert each value to string, handling None/NaN properly
                cleaned_values = []
                for val in df[col].values:
                    if pd.isna(val) or val is None or str(val).lower() in ['nan', 'none', 'null']:
                        cleaned_values.append('')
                    else:
                        cleaned_values.append(str(val))
                cleaned_data[col] = cleaned_values
            return pd.DataFrame(cleaned_data)
        except:
            # Last resort: return original
            return df

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
                    # Continue processing with the parsed data
                else:
                    return pd.DataFrame({"Result": [data]})
            else:
                # Check if it's a direct SQL result that looks like a query
                if any(keyword in data.upper() for keyword in ['SELECT', 'WITH', 'FROM', 'WHERE']):
                    # This is a SQL query that wasn't executed - show helpful message
                    return pd.DataFrame({
                        "Status": ["⚠️ Query Generated But Not Executed"],
                        "SQL_Query": [data],
                        "Suggestion": ["The query was generated successfully but couldn't be executed. This might be due to a database connection issue, query timeout, or data availability. Please try a simpler query or check your connection."]
                    })
                else:
                    return pd.DataFrame({"Result": [data]})

        # Case 2: If there's no data or it's not a list
        if not isinstance(data, list) or not data:
            return pd.DataFrame({"Result": ["No data"]})

        # Case 3: For specific high-value order queries
        if (
            "highest value" in user_question.lower()
            or "totalprice" in sql_query.lower()
            or "ORDER BY" in sql_query.upper()
        ):

            # Detected as order value query
            if len(data[0]) >= 2:
                formatted_rows = []
                for row in data:
                    order_id = row[0]
                    value = row[1]

                    # Format value as currency
                    if isinstance(value, (int, float, Decimal)):
                        formatted_value = f"${float(value):,.2f}"
                    else:
                        formatted_value = str(value)

                    formatted_rows.append(
                        {"Order ID": order_id, "Total Value": formatted_value}
                    )

                df_result = pd.DataFrame(formatted_rows)
                # DataFrame created with custom formatting
                df_result = clean_dataframe_for_streamlit(df_result)
                return df_result

        # Case 4: For specific real estate queries
        if any(term in user_question.lower() for term in ["price", "prices", "sale", "sales", "properties", "agent"]):
            if len(data) > 0 and len(data[0]) >= 2:
                # Detect if there are prices or monetary values
                if any(col_name in str(data[0]).lower() for col_name in ["price", "sale", "commission"]):
                    formatted_rows = []
                    for row in data:
                        formatted_row = {}
                        for i, value in enumerate(row):
                            col_name = f"Column_{i+1}"
                            if i == 0 and any(term in user_question.lower() for term in ["city"]):
                                col_name = "City"
                            elif "price" in str(value).lower() or (isinstance(value, (int, float)) and value > 10000):
                                col_name = "Price" if "price" in user_question.lower() else "Value"
                                value = f"${float(value):,.2f}" if isinstance(value, (int, float, Decimal)) else str(value)
                            elif "id" in str(value).lower() or (i == 0 and isinstance(value, int) and value < 10000):
                                col_name = "ID"
                            formatted_row[col_name] = value
                        formatted_rows.append(formatted_row)
                    df_result = pd.DataFrame(formatted_rows)
                    df_result = clean_dataframe_for_streamlit(df_result)
                    return df_result
        
        # Case 5: For COUNT queries (how many/quantity)
        if (
            "COUNT(*)" in sql_query.upper()
            or "count(*)" in user_question.lower()
            or "how many" in user_question.lower()
            or "quantity" in user_question.lower()
        ):
            if len(data) > 0 and len(data[0]) == 1:
                count_value = data[0][0]
                # Determine what is being counted based on the question
                if "table" in user_question.lower():
                    return pd.DataFrame(
                        [
                            {
                                "Description": "Total tables in database",
                                "Count": f"{count_value:,}",
                            }
                        ]
                    )
                elif "customer" in user_question.lower():
                    return pd.DataFrame(
                        [
                            {
                                "Description": "Total customers",
                                "Count": f"{count_value:,}",
                            }
                        ]
                    )
                elif (
                    "order" in user_question.lower()
                ):
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

        # Case 7: For metadata queries (direct table listing)
        if ("INFORMATION_SCHEMA.TABLES" in sql_query.upper() and "TABLE_NAME" in sql_query.upper()) or "SHOW TABLES" in sql_query.upper():
            if len(data) > 0:
                # Check if it's the clean metadata query format (TABLE_NAME, TABLE_TYPE)
                if len(data[0]) == 2:
                    # Clean metadata format: just table name and type
                    table_list = []
                    for i, row in enumerate(data, 1):
                        table_name = row[0]  # TABLE_NAME
                        table_type = row[1]  # TABLE_TYPE
                        table_list.append({
                            "#": i,
                            "Table": table_name,
                            "Type": table_type
                        })
                    df_result = pd.DataFrame(table_list)
                    df_result = clean_dataframe_for_streamlit(df_result)
                    return df_result
                elif len(data[0]) >= 2:
                    # Legacy SHOW TABLES format with lots of columns
                    table_names = []
                    for i, row in enumerate(data, 1):
                        table_name = row[1]  # Table name is in the second column for SHOW TABLES
                        table_names.append({
                            "#": i,
                            "Table": table_name
                        })
                    df_result = pd.DataFrame(table_names)
                    df_result = clean_dataframe_for_streamlit(df_result)
                    return df_result

        # Case 8: For region-based queries (average, sum, etc.)
        if (
            "region" in user_question.lower()
            or "regions" in user_question.lower()
        ) and len(data) > 0 and len(data[0]) == 2:
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
            
            df_result = pd.DataFrame(formatted_rows)
            df_result = clean_dataframe_for_streamlit(df_result)
            return df_result

        # Case 9: For simple table queries (like "first five rows from agents")
        if any(table_name in user_question.lower() for table_name in ["agents", "properties", "locations", "owners", "transactions"]):
            try:
                # Create DataFrame with proper handling for mixed types
                # First, ensure all data is in consistent tuple format
                cleaned_data = []
                for row in data:
                    if isinstance(row, (tuple, list)):
                        # Convert all elements to strings to avoid type issues
                        cleaned_row = [str(item) if item is not None else '' for item in row]
                        cleaned_data.append(cleaned_row)
                    else:
                        cleaned_data.append([str(row)])
                
                # Create DataFrame with meaningful column names for known tables
                if cleaned_data:
                    num_cols = len(cleaned_data[0]) if cleaned_data[0] else 1
                    
                    # Define meaningful column names for the agents table (37 columns)
                    if ("agent" in user_question.lower() and num_cols >= 35) or num_cols == 37:
                        column_names = [
                            "ID", "UUID", "First_Name", "Last_Name", "Company", "Phone", "Email", 
                            "License", "State", "Years_Experience", "Total_Sales", "Total_Value", 
                            "Commission_Rate", "Address", "City", "State_Code", "Zip_Code", 
                            "Languages", "Specialization", "Rating", "Bio", "Website", 
                            "Personal_Info_1", "Personal_Info_2", "Active", "Hire_Date", 
                            "Last_Active", "Clients_Count", "Referrals", "Marketing_Budget", 
                            "Lead_Count", "Conversion_Rate", "Team_Size", "Contract_End", 
                            "CRM_System", "Social_Media", "Profile_Image"
                        ]
                        # Truncate or extend column names to match actual data
                        if len(column_names) > num_cols:
                            column_names = column_names[:num_cols]
                        elif len(column_names) < num_cols:
                            column_names.extend([f"Column_{i}" for i in range(len(column_names), num_cols)])
                    
                    # Define meaningful column names for properties table (if applicable)
                    elif "propert" in user_question.lower() and num_cols >= 20:
                        column_names = [
                            "Property_ID", "Address", "City", "State", "Zip_Code", "Price", 
                            "Bedrooms", "Bathrooms", "Square_Feet", "Lot_Size", "Year_Built", 
                            "Property_Type", "Status", "Agent_ID", "Owner_ID", "Listed_Date", 
                            "Sold_Date", "Days_On_Market", "Description", "Features"
                        ]
                        # Adjust column names to match data
                        if len(column_names) > num_cols:
                            column_names = column_names[:num_cols]
                        elif len(column_names) < num_cols:
                            column_names.extend([f"Column_{i}" for i in range(len(column_names), num_cols)])
                    
                    else:
                        # Generic column names for unknown structures
                        column_names = [f"Column_{i+1}" for i in range(num_cols)]
                    
                    df = pd.DataFrame(cleaned_data, columns=column_names)
                    # Clean the DataFrame to ensure Streamlit compatibility
                    df = clean_dataframe_for_streamlit(df)
                    return df
                else:
                    return pd.DataFrame({"Result": ["No data"]})
            except Exception as e:
                # Fallback to string conversion
                try:
                    # Create a simple string representation
                    string_data = []
                    for i, row in enumerate(data):
                        string_data.append({"Row": i+1, "Data": str(row)})
                    df = pd.DataFrame(string_data)
                    df = clean_dataframe_for_streamlit(df)
                    return df
                except:
                    pass

        # Case 10: Default - create DataFrame more robustly
        try:
            # First attempt: clean the data before creating DataFrame
            if len(data) > 0 and isinstance(data[0], (tuple, list)):
                # Clean complex tuple data
                cleaned_data = []
                for row in data:
                    if isinstance(row, (tuple, list)):
                        # Convert all elements to strings to avoid type issues
                        cleaned_row = [str(item) if item is not None else '' for item in row]
                        cleaned_data.append(cleaned_row)
                    else:
                        cleaned_data.append([str(row)])
                
                # Create DataFrame with meaningful column names based on size
                num_cols = len(cleaned_data[0]) if cleaned_data else 1
                
                # Smart column naming based on common database result patterns
                if num_cols >= 35 or num_cols == 37:  # Likely agents table
                    column_names = [
                        "ID", "UUID", "First_Name", "Last_Name", "Company", "Phone", "Email", 
                        "License", "State", "Years_Experience", "Total_Sales", "Total_Value", 
                        "Commission_Rate", "Address", "City", "State_Code", "Zip_Code", 
                        "Languages", "Specialization", "Rating", "Bio", "Website", 
                        "Personal_Info_1", "Personal_Info_2", "Active", "Hire_Date", 
                        "Last_Active", "Clients_Count", "Referrals", "Marketing_Budget", 
                        "Lead_Count", "Conversion_Rate", "Team_Size", "Contract_End", 
                        "CRM_System", "Social_Media", "Profile_Image"
                    ]
                elif num_cols >= 20:  # Likely properties table
                    column_names = [
                        "Property_ID", "Address", "City", "State", "Zip_Code", "Price", 
                        "Bedrooms", "Bathrooms", "Square_Feet", "Lot_Size", "Year_Built", 
                        "Property_Type", "Status", "Agent_ID", "Owner_ID", "Listed_Date", 
                        "Sold_Date", "Days_On_Market", "Description", "Features"
                    ]
                elif num_cols >= 10:  # Medium table - generic descriptive names
                    column_names = [
                        "ID", "Name", "Description", "Value_1", "Value_2", "Date_1", 
                        "Date_2", "Status", "Category", "Notes"
                    ]
                elif num_cols >= 5:  # Small table - basic names
                    column_names = ["ID", "Name", "Value", "Status", "Date"]
                else:
                    column_names = ["Column_1", "Column_2", "Column_3", "Column_4"][:num_cols]
                
                # Adjust column names to match actual data length
                if len(column_names) > num_cols:
                    column_names = column_names[:num_cols]
                elif len(column_names) < num_cols:
                    column_names.extend([f"Column_{i+1}" for i in range(len(column_names), num_cols)])
                
                df = pd.DataFrame(cleaned_data, columns=column_names)
                # Clean the DataFrame to ensure Streamlit compatibility
                df = clean_dataframe_for_streamlit(df)
                return df
            else:
                # Simple data - try direct creation
                df = pd.DataFrame(data)
                # Clean the DataFrame to ensure Streamlit compatibility
                df = clean_dataframe_for_streamlit(df)
                return df
        except Exception:
            # If it fails, try with string conversion
            try:
                # Convert everything to string first
                if isinstance(data, list) and len(data) > 0:
                    string_data = []
                    for i, row in enumerate(data):
                        if isinstance(row, (tuple, list)):
                            string_row = [str(item) if item is not None else '' for item in row]
                            string_data.append(string_row)
                        else:
                            string_data.append([str(row)])
                    
                    # Create with smart column names based on data structure
                    num_cols = len(string_data[0]) if string_data else 1
                    
                    # Use the same smart naming logic as above
                    if num_cols >= 35 or num_cols == 37:  # Likely agents table
                        column_names = [
                            "ID", "UUID", "First_Name", "Last_Name", "Company", "Phone", "Email", 
                            "License", "State", "Years_Experience", "Total_Sales", "Total_Value", 
                            "Commission_Rate", "Address", "City", "State_Code", "Zip_Code", 
                            "Languages", "Specialization", "Rating", "Bio", "Website", 
                            "Personal_Info_1", "Personal_Info_2", "Active", "Hire_Date", 
                            "Last_Active", "Clients_Count", "Referrals", "Marketing_Budget", 
                            "Lead_Count", "Conversion_Rate", "Team_Size", "Contract_End", 
                            "CRM_System", "Social_Media", "Profile_Image"
                        ][:num_cols]  # Truncate to actual size
                    elif num_cols >= 20:  # Likely properties table
                        column_names = [
                            "Property_ID", "Address", "City", "State", "Zip_Code", "Price", 
                            "Bedrooms", "Bathrooms", "Square_Feet", "Lot_Size", "Year_Built", 
                            "Property_Type", "Status", "Agent_ID", "Owner_ID", "Listed_Date", 
                            "Sold_Date", "Days_On_Market", "Description", "Features"
                        ][:num_cols]  # Truncate to actual size
                    else:
                        column_names = [f"Column_{i+1}" for i in range(num_cols)]
                    
                    # Extend if needed
                    if len(column_names) < num_cols:
                        column_names.extend([f"Column_{i+1}" for i in range(len(column_names), num_cols)])
                    
                    df = pd.DataFrame(string_data, columns=column_names)
                    df = clean_dataframe_for_streamlit(df)
                    return df
                else:
                    # Data in unexpected format
                    df = pd.DataFrame({"Result": [str(data)] if not isinstance(data, list) else [str(item) for item in data]})
                    return df
            except Exception:
                # Last resort: convert everything to string
                return pd.DataFrame({"Result": [str(data)]})

    except Exception:
        # Formatting error, use robust handling
        try:
            # Try to create basic DataFrame with string conversion
            if isinstance(data, list) and len(data) > 0:
                if isinstance(data[0], (tuple, list)):
                    # List of tuples/lists - convert all to strings
                    string_data = []
                    for row in data:
                        if isinstance(row, (tuple, list)):
                            string_row = [str(item) if item is not None else '' for item in row]
                            string_data.append(string_row)
                        else:
                            string_data.append([str(row)])
                    
                    # Create with generic column names
                    num_cols = len(string_data[0]) if string_data else 1
                    column_names = [f"Column_{i}" for i in range(num_cols)]
                    df = pd.DataFrame(string_data, columns=column_names)
                    df = clean_dataframe_for_streamlit(df)
                    return df
                else:
                    # Simple list
                    df = pd.DataFrame({"Result": [str(item) for item in data]})
                    df = clean_dataframe_for_streamlit(df)
                    return df
            else:
                # Generic case
                df = pd.DataFrame({"Result": [str(data)]})
                df = clean_dataframe_for_streamlit(df)
                return df
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
            st.dataframe(message["data"], width='stretch')
            num_rows = len(message["data"])
            st.caption(
                f"📊 {num_rows} record{'s' if num_rows != 1 else ''} shown"
            )


def display_chat_messages():
    """Display chat message history with tables and counters."""
    st.header("💬 Chat with your Database")

    # Show message history
    for message in st.session_state.messages:
        _render_single_message(message)


def _append_assistant_message(content, df=None):
    """Add an assistant message to history with optional DataFrame."""
    st.session_state.messages.append({
        "role": "assistant",
        "content": content,
        "data": df if df is not None else pd.DataFrame(),
    })


def _render_successful_result(result, prompt):
    """Render a successful agent result and update history."""
    response_content = "Query executed successfully:"
    st.write(response_content)

    if not result.get("result"):
        st.write("No results found.")
        _append_assistant_message("No results found.")
        return

    try:
        df = format_sql_result_to_dataframe(
            result["result"], result.get("sql_query", ""), prompt
        )
        st.dataframe(df, width='stretch')
        num_rows = len(df)
        st.caption(
            f"📊 {num_rows} record{'s' if num_rows != 1 else ''} found"
        )
        _append_assistant_message(response_content, df)
    except Exception:
        result_text = str(result.get("result"))
        st.code(result_text)
        _append_assistant_message(f"{response_content}\n{result_text}")


def _render_error_result(result):
    """Render an agent error and update history."""
    if isinstance(result, dict) and result.get('user_friendly'):
        # User-friendly error message
        error_msg = result.get('error', 'Unknown error')
        st.error(error_msg)
        _append_assistant_message(error_msg)
        
        # Optionally show technical details in expander
        if result.get('technical_error') and result['technical_error'] != error_msg:
            with st.expander("🔧 Technical Details (for debugging)", expanded=False):
                st.code(result['technical_error'])
    else:
        # Legacy error handling
        error_text = result if isinstance(result, str) else result.get('error', 'Unknown error')
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
            _render_error_result({
                "success": False,
                "error": "❌ Error: No agent initialized. Please check your connection.",
                "user_friendly": True
            })
            return

        with st.spinner("Processing query..."):
            result = st.session_state.agent.process_query(prompt)
        
        # Manejo especial: SHOW TABLES → listar nombres, no dataframe crudo
        sql_q = (result.get("sql_query") or "").upper()
        if "SHOW TABLES" in sql_q and isinstance(result.get("result"), list):
            tables = [row[1] for row in result["result"] if isinstance(row, (list, tuple)) and len(row) > 1]
            st.write("Tables:")
            for t in tables:
                st.write(f"• {t}")
            _append_assistant_message("Query executed successfully:", pd.DataFrame({"Tables": tables}))
            return

        if result.get("success"):
            _render_successful_result(result, prompt)
            return

        _render_error_result(result)


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
