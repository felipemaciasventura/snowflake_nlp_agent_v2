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
    
    # Palabras clave que indican consulta de BD
    db_keywords = [
        "tabla", "datos", "consulta", "cuántos", "cuántas", "mostrar", "listar", 
        "región", "cliente", "venta", "promedio", "suma", "total", "count",
        "select", "database", "schema", "registros", "filas", "columnas",
        "pedidos", "ordenes", "productos", "categorías", "ingresos", "facturación",
        "análisis", "reporte", "estadísticas", "máximo", "mínimo", "buscar",
        "filtrar", "agrupar", "ordenar", "top", "mayor", "menor", "últimos", "últimas",
        # Palabras adicionales para consultas complejas
        "ciudad", "ciudades", "propiedades", "propiedad", "precio", "precios", "ranking",
        "rank", "posición", "posiciones", "cada", "obtén", "obtener", "incluir", "solo",
        "dólares", "valores", "valor", "transacciones", "transaction", "locations",
        "ubicación", "ubicaciones", "caros", "caras", "expensive", "más", "menos",
        "join", "inner", "left", "right", "where", "order by", "group by", "partition",
        "over", "window", "función", "funciones", "aggregate", "aggregation",
        # Vocabulario específico de bienes raíces (basado en esquema SQL)
        "agente", "agentes", "propietario", "propietarios", "dueño", "dueños",
        "venta", "ventas", "compra", "compras", "comprador", "compradores", "vendedor", "vendedores",
        "inmueble", "inmuebles", "casa", "casas", "apartamento", "apartamentos", "lote", "lotes",
        "hipoteca", "hipotecas", "crédito", "financiamiento", "prestamo", "préstamo",
        "dormitorios", "habitaciones", "baños", "metros", "m2", "pies", "sqft",
        "garaje", "estacionamiento", "piscina", "jardín", "patio", "terraza",
        "condado", "estado", "código postal", "zipcode", "msa", "zona", "vecindario",
        "avaluo", "avalúo", "tasación", "impuesto", "impuestos", "comisión", "comisiones",
        "listado", "listados", "oferta", "ofertas", "cierre", "cierres", "escritura",
        "inspección", "evaluación", "mercado", "tendencia", "tendencias", "crecimiento",
        "rentabilidad", "roi", "inversión", "inversiones", "portfolio", "cartera"
    ]
    
    # Palabras clave fuera de contexto (ser más específico para evitar conflictos)
    off_topic_keywords = [
        "clima", "tiempo atmosférico", "noticias", "receta de cocina", "traducir idioma", "como estas", "que tal",
        "chiste", "historia personal", "película", "música", "deporte", "política",
        "salud personal", "medicina", "viaje turístico", "restaurante", "comprar ropa",
        "horario personal", "dirección postal", "teléfono personal", "email personal", "programar cita"
        # Removido "precio" y "código" ya que pueden ser parte de consultas de BD
    ]
    
    # Preguntas de ayuda/información (caso especial)
    help_keywords = [
        "ayuda", "qué puedes hacer", "cómo funciona", "qué haces",
        "para qué sirves", "cómo usar", "instrucciones", "comandos",
        "ejemplos", "capacidades", "funciones"
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
    
    # Si no es claro, analizar más profundamente
    if len(user_input.split()) < 3:  # Muy corto, probablemente no es consulta DB
        return "unclear"
    
    # Para consultas largas (>10 palabras), probablemente son consultas de BD complejas
    if len(user_input.split()) > 10:
        # Verificar si tiene estructura de consulta de datos
        data_structure_indicators = [
            "para cada", "obtener", "obtener un", "mostrar", "listar", "encontrar",
            "calcular", "sumar", "contar", "agrupar por", "ordenar por",
            "con precio", "con valor", "mayor a", "menor a", "igual a",
            "incluir", "excluir", "solo", "solamente", "únicamente"
        ]
        
        if any(indicator in user_input_lower for indicator in data_structure_indicators):
            return "database"
    
    return "database"  # Por defecto, intentar como consulta de BD


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

        # Case 2: If there's no data or it's not a list
        if not isinstance(data, list) or not data:
            return pd.DataFrame({"Result": ["No data"]})

        # Caso 3: Para la consulta específica de pedidos con mayor valor
        if (
            "mayor valor" in user_question.lower()
            or "totalprice" in sql_query.lower()
            or "ORDER BY" in sql_query.upper()
        ):

            # Detectado como consulta de pedidos con valores
            if len(data[0]) >= 2:
                formatted_rows = []
                for row in data:
                    id_pedido = row[0]
                    valor = row[1]

                    # Formatear el valor como moneda
                    if isinstance(valor, (int, float, Decimal)):
                        valor_formateado = f"${float(valor):,.2f}"
                    else:
                        valor_formateado = str(valor)

                    formatted_rows.append(
                        {"ID Pedido": id_pedido, "Valor Total": valor_formateado}
                    )

                df_result = pd.DataFrame(formatted_rows)
                # DataFrame creado con formato personalizado
                return df_result

        # Caso 4: Para consultas inmobiliarias específicas
        if any(term in user_question.lower() for term in ["precio", "precios", "venta", "ventas", "propiedades", "agente"]):
            if len(data) > 0 and len(data[0]) >= 2:
                # Detectar si hay precios o valores monetarios
                if any(col_name in str(data[0]).lower() for col_name in ["price", "precio", "sale", "venta", "commission", "comision"]):
                    formatted_rows = []
                    for row in data:
                        formatted_row = {}
                        for i, value in enumerate(row):
                            col_name = f"Columna_{i+1}"
                            if i == 0 and any(term in user_question.lower() for term in ["ciudad", "city"]):
                                col_name = "Ciudad"
                            elif "price" in str(value).lower() or (isinstance(value, (int, float)) and value > 10000):
                                col_name = "Precio" if "precio" in user_question.lower() else "Valor"
                                value = f"${float(value):,.2f}" if isinstance(value, (int, float, Decimal)) else str(value)
                            elif "id" in str(value).lower() or (i == 0 and isinstance(value, int) and value < 10000):
                                col_name = "ID"
                            formatted_row[col_name] = value
                        formatted_rows.append(formatted_row)
                    return pd.DataFrame(formatted_rows)
        
        # Caso 5: Para consultas COUNT (cantidad/cuántas)
        if (
            "COUNT(*)" in sql_query.upper()
            or "count(*)" in user_question.lower()
            or "cuántas" in user_question.lower()
            or "cuántos" in user_question.lower()
            or "cantidad" in user_question.lower()
        ):
            if len(data) > 0 and len(data[0]) == 1:
                count_value = data[0][0]
                # Determinar qué se está contando basado en la pregunta
                if "tabla" in user_question.lower():
                    return pd.DataFrame(
                        [
                            {
                                "Descripción": "Total de tablas en la base de datos",
                                "Cantidad": f"{count_value:,}",
                            }
                        ]
                    )
                elif "cliente" in user_question.lower():
                    return pd.DataFrame(
                        [
                            {
                                "Descripción": "Total de clientes",
                                "Cantidad": f"{count_value:,}",
                            }
                        ]
                    )
                elif (
                    "pedido" in user_question.lower()
                    or "orden" in user_question.lower()
                ):
                    return pd.DataFrame(
                        [
                            {
                                "Descripción": "Total de pedidos",
                                "Cantidad": f"{count_value:,}",
                            }
                        ]
                    )
                elif "venta" in user_question.lower():
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

        # Case 8: For region-based queries (average, sum, etc.)
        if (
            "región" in user_question.lower()
            or "region" in user_question.lower()
            or "regiones" in user_question.lower()
        ) and len(data) > 0 and len(data[0]) == 2:
            # Detect if it's average, sum, total, etc.
            if "promedio" in user_question.lower() or "avg" in sql_query.lower():
                metric_name = "Average Revenue"
            elif "suma" in user_question.lower() or "total" in user_question.lower():
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

        # Case 9: Default - create DataFrame more robustly
        try:
            # Try to create DataFrame directly
            df = pd.DataFrame(data)
            return df
        except Exception:
            # If it fails, try with generic column names
            try:
                if len(data) > 0 and isinstance(data[0], (tuple, list)):
                    # Create generic column names
                    num_cols = len(data[0]) if data[0] else 1
                    column_names = [f"Column_{i+1}" for i in range(num_cols)]
                    df = pd.DataFrame(data, columns=column_names)
                    return df
                else:
                    # Data in unexpected format
                    df = pd.DataFrame({"Result": data if isinstance(data, list) else [data]})
                    return df
            except Exception:
                # Last resort: convert everything to string
                return pd.DataFrame({"Result": [str(data)]})

    except Exception:
        # Formatting error, use robust handling
        try:
            # Try to create basic DataFrame
            if isinstance(data, list) and len(data) > 0:
                if isinstance(data[0], (tuple, list)):
                    # List of tuples/lists
                    num_cols = len(data[0]) if data[0] else 1
                    column_names = [f"Column_{i+1}" for i in range(num_cols)]
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
