import streamlit as st
import pandas as pd
from dotenv import load_dotenv
import os
import re
import ast
from src.agent.nlp_agent import SnowflakeNLPAgent
from src.database.snowflake_conn import SnowflakeConnection

# Cargar variables de entorno
load_dotenv()


# Configuración de página
st.set_page_config(page_title="Agente NLP Snowflake", page_icon="🤖", layout="wide")


def initialize_session_state():
    """Inicializa el estado de la sesión"""
    if "messages" not in st.session_state:
        st.session_state.messages = []
    if "processing_logs" not in st.session_state:
        st.session_state.processing_logs = []
    if "agent" not in st.session_state:
        st.session_state.agent = None
    if "db_connection" not in st.session_state:
        st.session_state.db_connection = None


def setup_sidebar():
    """Configura la barra lateral"""
    st.sidebar.header("🔧 Configuración")

    # Estado de conexión
    if st.session_state.db_connection:
        st.sidebar.success("✅ Conectado a Snowflake")
    else:
        st.sidebar.error("❌ No conectado")

    # Información del sistema
    st.sidebar.header("📊 Información del Sistema")
    if st.session_state.agent:
        # Detectar qué modelo LLM se está usando
        from src.utils.config import config
        provider = config.get_available_llm_provider()
        
        if provider == "gemini":
            model_info = f"LLM: {config.GEMINI_MODEL} (Google Gemini)"
        elif provider == "groq":
            model_info = f"LLM: {config.MODEL_NAME} (Groq)"
        else:
            model_info = "LLM: No detectado"
            
        st.sidebar.info(model_info)
        st.sidebar.info(f"Base de datos: {os.getenv('SNOWFLAKE_DATABASE')}")
        st.sidebar.info(f"Schema: {os.getenv('SNOWFLAKE_SCHEMA')}")

    # Botón para limpiar historial
    if st.sidebar.button("🗑️ Limpiar Historial"):
        st.session_state.messages = []
        st.session_state.processing_logs = []
        st.rerun()


# ========================
# Detección y respuestas híbridas
# ========================


def is_database_query(user_input):
    """Detecta si la consulta es sobre bases de datos o fuera de contexto"""
    user_input_lower = user_input.lower()
    
    # Palabras clave que indican consulta de BD
    db_keywords = [
        "tabla", "datos", "consulta", "cuántos", "cuántas", "mostrar", "listar", 
        "región", "cliente", "venta", "promedio", "suma", "total", "count",
        "select", "database", "schema", "registros", "filas", "columnas",
        "pedidos", "ordenes", "productos", "categorías", "ingresos", "facturación",
        "análisis", "reporte", "estadísticas", "máximo", "mínimo", "buscar",
        "filtrar", "agrupar", "ordenar", "top", "mayor", "menor", "últimos", "últimas"
    ]
    
    # Palabras clave fuera de contexto  
    off_topic_keywords = [
        "clima", "tiempo", "noticias", "receta", "traducir", "como estas", "que tal",
        "chiste", "historia", "película", "música", "deporte", "política",
        "salud", "medicina", "viaje", "restaurante", "comprar", "precio",
        "horario", "dirección", "teléfono", "email", "programar", "código"
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
    
    # Si no es claro, asumir que podría ser de BD (dar el beneficio de la duda)
    # pero con precaución
    if len(user_input.split()) < 3:  # Muy corto, probablemente no es consulta DB
        return "unclear"
    
    return "database"  # Por defecto, intentar como consulta de BD


def get_help_response():
    """Devuelve respuesta educativa sobre las capacidades del sistema"""
    return {
        "type": "help",
        "message": """¡Hola! 👋 Soy tu asistente NLP para consultas en Snowflake.

🔍 **Te puedo ayudar con:**
• 📈 **Consultas sobre datos:** "?Cuántos clientes tengo?"
• 📊 **Análisis por región:** "?Cuál es el promedio de ventas por región?"
• 📋 **Listados:** "Muéstrame los productos más vendidos"
• 🖼️ **Información de tablas:** "?Qué tablas hay disponibles?"
• 🔢 **Conteos:** "?Cuántas órdenes hay en total?"
• 📅 **Consultas temporales:** "Muestra las ventas de los últimos 30 días"

🎨 **Ejemplos que puedes probar:**
• "Lista todas las regiones disponibles"
• "?Cuál es el cliente que más ha gastado?"
• "Muéstrame el promedio de ingresos por región"

¡Hazme cualquier pregunta sobre tus datos! 🚀"""
    }


def get_redirect_response():
    """Devuelve respuesta de redirección para consultas fuera de contexto"""
    return {
        "type": "redirect",
        "message": """🤖 Soy un asistente especializado en consultas de bases de datos Snowflake.

No puedo ayudarte con esa consulta, pero ¡sí puedo ayudarte a explorar tus datos! 📋

🎨 **Prueba preguntándome algo como:**
• "?Cuántos registros hay en la tabla de clientes?"
• "Muéstrame las regiones con mayor facturación"
• "?Qué tablas están disponibles?"

¿Hay alguna información de tu base de datos que te interese conocer? 😊"""
    }


# ========================
# Utilidades de formateo
# ========================


def parse_sql_result_string(result_string):
    """Parsea un string con resultados SQL y lo convierte en datos reales"""

    # Si no es string o no tiene el formato esperado, devolver tal como está
    if not isinstance(result_string, str) or not result_string.strip():
        return result_string

    # Limpiar el string de entrada
    cleaned_string = result_string.strip()

    try:
        # Caso 1: Lista de tuplas [(...), (...)]
        if cleaned_string.startswith("[") and cleaned_string.endswith("]"):
            # Reemplazar Decimal('...') con float
            cleaned_string = re.sub(r"Decimal\('([^']+)'\)", r"\1", cleaned_string)
            # Reemplazar None con 'None' para evaluación segura
            cleaned_string = re.sub(r"\bNone\b", "'None'", cleaned_string)

            # Intentar evaluar como literal de Python
            parsed_data = ast.literal_eval(cleaned_string)
            return parsed_data

        # Caso 2: Tupla simple (...)
        elif cleaned_string.startswith("(") and cleaned_string.endswith(")"):
            # Convertir tupla simple a lista de tuplas
            cleaned_string = f"[{cleaned_string}]"
            cleaned_string = re.sub(r"Decimal\('([^']+)'\)", r"\1", cleaned_string)
            cleaned_string = re.sub(r"\bNone\b", "'None'", cleaned_string)

            parsed_data = ast.literal_eval(cleaned_string)
            return parsed_data

        # Caso 3: String que parece ser datos pero no está bien formateado
        elif "Decimal(" in cleaned_string or "None" in cleaned_string:
            # Intentar arreglar el formato
            if not cleaned_string.startswith("["):
                cleaned_string = f"[{cleaned_string}]"

            cleaned_string = re.sub(r"Decimal\('([^']+)'\)", r"\1", cleaned_string)
            cleaned_string = re.sub(r"\bNone\b", "'None'", cleaned_string)

            parsed_data = ast.literal_eval(cleaned_string)
            return parsed_data

    except (ValueError, SyntaxError, TypeError):
        # Los errores de parsing son normales para datos complejos como datetime
        # El fallback manejará el caso

        # Fallback: intentar extraer datos usando regex
        try:
            # Buscar patrones de tuplas con números
            tuple_pattern = r"\(([^)]+)\)"
            matches = re.findall(tuple_pattern, cleaned_string)

            if matches:
                parsed_tuples = []
                for match in matches:
                    # Separar elementos por coma
                    elements = [elem.strip().strip("'\"") for elem in match.split(",")]
                    # Convertir números cuando sea posible
                    converted_elements = []
                    for elem in elements:
                        try:
                            # Intentar convertir a número
                            if "." in elem:
                                converted_elements.append(float(elem))
                            else:
                                converted_elements.append(int(elem))
                        except ValueError:
                            # Si no es número, mantener como string
                            converted_elements.append(elem)

                    parsed_tuples.append(tuple(converted_elements))

                return parsed_tuples

        except Exception:
            # Fallback también falló, se devolverá el string original
            pass

    # Si todo falla, devolver el string original
    return result_string


def format_sql_result_to_dataframe(data, sql_query="", user_question=""):
    """Convierte los resultados SQL en un DataFrame bien formateado"""
    from decimal import Decimal

    # Formateo inteligente de resultados SQL

    try:
        # Caso 1: Si es string, intentar parsearlo primero
        if isinstance(data, str):
            # Intentar parsear si parece ser datos de SQL
            if data.startswith("[") or data.startswith("("):
                parsed_data = parse_sql_result_string(data)
                if parsed_data != data:  # Si se pudo parsear
                    data = parsed_data
                    # String parseado exitosamente
                else:
                    return pd.DataFrame({"Resultado": [data]})
            else:
                return pd.DataFrame({"Resultado": [data]})

        # Caso 2: Si no hay datos o no es lista
        if not isinstance(data, list) or not data:
            return pd.DataFrame({"Resultado": ["Sin datos"]})

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

        # Caso 4: Para consultas COUNT (cantidad/cuántas)
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
                                "Descripción": "Total de ventas",
                                "Cantidad": f"{count_value:,}",
                            }
                        ]
                    )
                else:
                    return pd.DataFrame(
                        [
                            {
                                "Descripción": "Total de registros",
                                "Cantidad": f"{count_value:,}",
                            }
                        ]
                    )

        # Caso 5: Para CURRENT_DATABASE
        if "CURRENT_DATABASE" in sql_query.upper():
            return pd.DataFrame(data, columns=["Base de Datos"])

        # Caso 6: Para SHOW TABLES
        if "SHOW TABLES" in sql_query.upper():
            if len(data) > 0 and len(data[0]) >= 2:
                table_data = []
                for row in data:
                    table_data.append(
                        {
                            "Tabla": row[1],
                            "Tipo": row[4] if len(row) > 4 else "TABLE",
                            "Descripción": (
                                row[5] if len(row) > 5 else "Sin descripción"
                            ),
                        }
                    )
                return pd.DataFrame(table_data)

        # Caso 7: Para consultas por región (promedio, suma, etc.)
        if (
            "región" in user_question.lower()
            or "region" in user_question.lower()
            or "regiones" in user_question.lower()
        ) and len(data) > 0 and len(data[0]) == 2:
            # Detectar si es promedio, suma, total, etc.
            if "promedio" in user_question.lower() or "avg" in sql_query.lower():
                metric_name = "Promedio de Ingresos"
            elif "suma" in user_question.lower() or "total" in user_question.lower():
                metric_name = "Total de Ingresos"
            elif "count" in sql_query.lower():
                metric_name = "Cantidad"
            else:
                metric_name = "Valor"
            
            formatted_rows = []
            for row in data:
                region = row[0]
                value = row[1]
                
                # Formatear el valor como moneda si es numérico
                if isinstance(value, (int, float, Decimal)):
                    value_formatted = f"${float(value):,.2f}"
                else:
                    value_formatted = str(value)
                
                formatted_rows.append({
                    "Región": region,
                    metric_name: value_formatted
                })
            
            return pd.DataFrame(formatted_rows)

        # Caso 8: Por defecto - crear DataFrame de manera más robusta
        try:
            # Intentar crear DataFrame directamente
            df = pd.DataFrame(data)
            return df
        except Exception:
            # Si falla, intentar con nombres genéricos de columnas
            try:
                if len(data) > 0 and isinstance(data[0], (tuple, list)):
                    # Crear nombres de columna genéricos
                    num_cols = len(data[0]) if data[0] else 1
                    column_names = [f"Columna_{i+1}" for i in range(num_cols)]
                    df = pd.DataFrame(data, columns=column_names)
                    return df
                else:
                    # Datos en formato no esperado
                    df = pd.DataFrame({"Resultado": data if isinstance(data, list) else [data]})
                    return df
            except Exception:
                # Último recurso: convertir todo a string
                return pd.DataFrame({"Resultado": [str(data)]})

    except Exception as e:
        # Error en formateo, usar manejo robusto
        try:
            # Intentar crear DataFrame básico
            if isinstance(data, list) and len(data) > 0:
                if isinstance(data[0], (tuple, list)):
                    # Lista de tuplas/listas
                    num_cols = len(data[0]) if data[0] else 1
                    column_names = [f"Columna_{i+1}" for i in range(num_cols)]
                    return pd.DataFrame(data, columns=column_names)
                else:
                    # Lista simple
                    return pd.DataFrame({"Resultado": data})
            else:
                # Caso genérico
                return pd.DataFrame({"Resultado": [str(data)]})
        except Exception:
            # Último recurso absoluto
            return pd.DataFrame({"Error": [f"No se pudieron procesar los datos: {str(data)[:100]}..."]})


# ========================
# Render de UI (mensajes y chat)
# ========================


def display_chat_messages():
    """Muestra el historial de mensajes del chat con tablas y contadores."""
    st.header("💬 Chat con tu Base de Datos")

    # Mostrar historial de mensajes
    for message in st.session_state.messages:
        with st.chat_message(message["role"]):
            if message["role"] == "assistant" and "data" in message:
                st.write(message["content"])
                if not message["data"].empty:
                    st.dataframe(message["data"], width='stretch')
                    # Mostrar número de registros
                    num_rows = len(message["data"])
                    st.caption(
                        f"📊 {num_rows} registro{
                            's' if num_rows != 1 else ''} mostrado{
                            's' if num_rows != 1 else ''}"
                    )
            else:
                st.write(message["content"])


def process_user_input(prompt):
    """Procesa la entrada del usuario con detección híbrida.

    Flujo híbrido:
    1. Detectar tipo de consulta (BD, ayuda, fuera de contexto)
    2. Responder apropiadamente según el tipo
    3. Para consultas DB: invocar agente NLP → SQL → ejecución
    4. Para otras: mostrar respuestas educativas/redirección
    """
    # Agregar mensaje del usuario
    st.session_state.messages.append({"role": "user", "content": prompt})

    with st.chat_message("user"):
        st.write(prompt)

    # Detectar tipo de consulta
    query_type = is_database_query(prompt)
    
    with st.chat_message("assistant"):
        if query_type == "help":
            # Respuesta educativa
            help_resp = get_help_response()
            st.markdown(help_resp["message"])
            st.session_state.messages.append({
                "role": "assistant",
                "content": help_resp["message"],
                "data": pd.DataFrame()
            })
            return
            
        elif query_type == "off_topic":
            # Respuesta de redirección
            redirect_resp = get_redirect_response()
            st.markdown(redirect_resp["message"])
            st.session_state.messages.append({
                "role": "assistant",
                "content": redirect_resp["message"],
                "data": pd.DataFrame()
            })
            return
            
        elif query_type == "unclear":
            # Dar el beneficio de la duda pero advertir
            st.info("🤔 No estoy seguro si preguntas sobre datos. Intentaré como consulta de BD...")
    
    # Procesar como consulta de base de datos
    if st.session_state.agent:
        with st.chat_message("assistant"):
            with st.spinner("Procesando consulta..."):
                result = st.session_state.agent.process_query(prompt)

                if result["success"]:
                    response_content = "Consulta ejecutada exitosamente:"
                    st.write(response_content)

                    # Mostrar datos si existen
                    if result["result"]:
                        try:
                            # Usar la función de formateo inteligente
                            df = format_sql_result_to_dataframe(
                                result["result"], result.get("sql_query", ""), prompt
                            )

                            # Mostrar la tabla formateada
                            st.dataframe(df, width='stretch')

                            # Mostrar información adicional
                            num_rows = len(df)
                            st.caption(
                                f"📊 {num_rows} registro{
                                    's' if num_rows != 1 else ''} encontrado{
                                    's' if num_rows != 1 else ''}"
                            )

                            # Agregar al historial con datos
                            st.session_state.messages.append(
                                {
                                    "role": "assistant",
                                    "content": response_content,
                                    "data": df,
                                }
                            )
                        except Exception:
                            # Si falla la creación del DataFrame, mostrar como texto
                            result_text = str(result["result"])
                            st.code(result_text)
                            st.session_state.messages.append(
                                {
                                    "role": "assistant",
                                    "content": f"{response_content}\n{result_text}",
                                    "data": pd.DataFrame(),
                                }
                            )
                    else:
                        st.write("No se encontraron resultados.")
                        st.session_state.messages.append(
                            {
                                "role": "assistant",
                                "content": "No se encontraron resultados.",
                                "data": pd.DataFrame(),
                            }
                        )
                else:
                    error_msg = f"Error: {result['error']}"
                    st.error(error_msg)
                    st.session_state.messages.append(
                        {
                            "role": "assistant",
                            "content": error_msg,
                            "data": pd.DataFrame(),
                        }
                    )


def display_logs_panel():
    """Muestra el panel de logs explicativos"""
    st.header("📋 Logs del Proceso")

    if st.session_state.processing_logs:
        # Mostrar logs en orden reverso (más reciente primero)
        for log in reversed(st.session_state.processing_logs[-10:]):  # Últimos 10 logs
            with st.expander(f"⏰ {log['timestamp']} - {log['step']}", expanded=False):
                st.code(log["content"])
    else:
        st.info("No hay logs disponibles. Realiza una consulta para ver el proceso.")


def main():
    """Función principal de la app Streamlit.

    Ensambla la UI y bootstrapping:
    - Inicializa estado de sesión (mensajes, logs, conexión, agente)
    - Gestiona conexión a Snowflake y crea el agente si hay credenciales
    - Organiza layout (chat a la izquierda, sidebar + logs a la derecha)
    - Coloca chat_input al final (fuera de columnas) para cumplir reglas Streamlit
    """
    st.title("🤖 Agente NLP para Consultas en Snowflake")
    st.markdown(
        "Haz preguntas en español y obten respuestas de tu base de datos Snowflake"
    )

    # Inicializar estado
    initialize_session_state()

    # Configurar conexión si no existe
    if not st.session_state.db_connection:
        with st.spinner("Conectando a Snowflake..."):
            db_conn = SnowflakeConnection()
            if db_conn.connect():
                st.session_state.db_connection = db_conn

                # Inicializar agente (auto-detecta proveedor LLM)
                google_api_key = os.getenv("GOOGLE_API_KEY")
                groq_api_key = os.getenv("GROQ_API_KEY")
                try:
                    st.session_state.agent = SnowflakeNLPAgent(
                        db_conn.get_connection_string(),
                        groq_api_key=groq_api_key,
                        google_api_key=google_api_key,
                    )
                    st.success("✅ Conexión establecida exitosamente!")
                except Exception as e:
                    st.error(f"❌ Error inicializando LLM: {e}")
                    st.stop()
            else:
                st.error(
                    "❌ No se pudo conectar a Snowflake. Verifica tu configuración."
                )
                st.stop()

    # Layout en columnas
    col1, col2 = st.columns([2, 1])

    with col1:
        display_chat_messages()

    with col2:
        setup_sidebar()
        display_logs_panel()

    # Input del usuario (fuera del layout de columnas)
    if prompt := st.chat_input("Escribe tu consulta en español..."):
        process_user_input(prompt)


if __name__ == "__main__":
    main()
