import streamlit as st
import pandas as pd
import plotly.express as px
from dotenv import load_dotenv
import os

# Cargar variables de entorno
load_dotenv()

from src.agent.nlp_agent import SnowflakeNLPAgent
from src.database.snowflake_conn import SnowflakeConnection

# Configuración de página
st.set_page_config(
    page_title="Agente NLP Snowflake",
    page_icon="🤖",
    layout="wide"
)

def initialize_session_state():
    """Inicializa el estado de la sesión"""
    if 'messages' not in st.session_state:
        st.session_state.messages = []
    if 'processing_logs' not in st.session_state:
        st.session_state.processing_logs = []
    if 'agent' not in st.session_state:
        st.session_state.agent = None
    if 'db_connection' not in st.session_state:
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
        st.sidebar.info(f"LLM: Llama 3.3 70B Versatile (Groq)")
        st.sidebar.info(f"Base de datos: {os.getenv('SNOWFLAKE_DATABASE')}")
        st.sidebar.info(f"Schema: {os.getenv('SNOWFLAKE_SCHEMA')}")
    
    # Botón para limpiar historial
    if st.sidebar.button("🗑️ Limpiar Historial"):
        st.session_state.messages = []
        st.session_state.processing_logs = []
        st.rerun()

# ========================
# Utilidades de formateo
# ========================

def parse_sql_result_string(result_string):
    """Parsea un string con resultados SQL y lo convierte en datos reales"""
    import re
    from decimal import Decimal
    
    try:
        if isinstance(result_string, str) and result_string.startswith('[('): 
            # Reemplazar Decimal('...') con float
            cleaned_string = re.sub(r"Decimal\('([^']+)'\)", r'\1', result_string)
            # Ahora intentar evaluar
            import ast
            parsed_data = ast.literal_eval(cleaned_string)
            return parsed_data
    except (ValueError, SyntaxError, TypeError) as e:
        print(f"Error parsing result string: {e}")
    
    return result_string

def format_sql_result_to_dataframe(data, sql_query="", user_question=""):
    """Convierte los resultados SQL en un DataFrame bien formateado"""
    from decimal import Decimal
    
    # Formateo inteligente de resultados SQL
    
    try:
        # Caso 1: Si es string, intentar parsearlo primero
        if isinstance(data, str):
            # Intentar parsear si parece ser datos de SQL
            if data.startswith('[('): 
                parsed_data = parse_sql_result_string(data)
                if parsed_data != data:  # Si se pudo parsear
                    data = parsed_data
                    # String parseado exitosamente
                else:
                    return pd.DataFrame({'Resultado': [data]})
            else:
                return pd.DataFrame({'Resultado': [data]})
        
        # Caso 2: Si no hay datos o no es lista
        if not isinstance(data, list) or not data:
            return pd.DataFrame({'Resultado': ['Sin datos']})
        
        # Caso 3: Para la consulta específica de pedidos con mayor valor
        if ('mayor valor' in user_question.lower() or 
            'totalprice' in sql_query.lower() or
            'ORDER BY' in sql_query.upper()):
            
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
                    
                    formatted_rows.append({
                        'ID Pedido': id_pedido,
                        'Valor Total': valor_formateado
                    })
                
                df_result = pd.DataFrame(formatted_rows)
                # DataFrame creado con formato personalizado
                return df_result
        
        # Caso 4: Para CURRENT_DATABASE
        if 'CURRENT_DATABASE' in sql_query.upper():
            return pd.DataFrame(data, columns=['Base de Datos'])
        
        # Caso 5: Para SHOW TABLES
        if 'SHOW TABLES' in sql_query.upper():
            if len(data) > 0 and len(data[0]) >= 2:
                table_data = []
                for row in data:
                    table_data.append({
                        'Tabla': row[1],
                        'Tipo': row[4] if len(row) > 4 else 'TABLE',
                        'Descripción': row[5] if len(row) > 5 else 'Sin descripción'
                    })
                return pd.DataFrame(table_data)
        
        # Caso 6: Por defecto - usar los datos tal como vienen
        return pd.DataFrame(data)
        
    except Exception as e:
        # Error en formateo, usando formato básico
        # En caso de error, devolver DataFrame básico
        try:
            return pd.DataFrame(data)
        except:
            return pd.DataFrame({'Resultado': [str(data)]})

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
                    st.dataframe(message["data"], use_container_width=True)
                    # Mostrar número de registros
                    num_rows = len(message["data"])
                    st.caption(f"📊 {num_rows} registro{'s' if num_rows != 1 else ''} mostrado{'s' if num_rows != 1 else ''}")
            else:
                st.write(message["content"])

def process_user_input(prompt):
    """Procesa la entrada del usuario y renderiza respuesta/tabla.

    Orquesta:
    - Persistir mensaje del usuario
    - Invocar al agente NLP (NL → SQL → ejecución)
    - Formatear resultados en DataFrame amigable
    - Mostrar tabla y contador de registros
    - Persistir respuesta en el historial de chat
    """
    # Agregar mensaje del usuario
    st.session_state.messages.append({"role": "user", "content": prompt})
    
    with st.chat_message("user"):
        st.write(prompt)
    
    # Procesar con el agente
    if st.session_state.agent:
        with st.chat_message("assistant"):
            with st.spinner("Procesando consulta..."):
                result = st.session_state.agent.process_query(prompt)
                
                if result['success']:
                    response_content = "Consulta ejecutada exitosamente:"
                    st.write(response_content)
                    
                    # Mostrar datos si existen
                    if result['result']:
                        try:
                            # Usar la función de formateo inteligente
                            df = format_sql_result_to_dataframe(
                                result['result'], 
                                result.get('sql_query', ''), 
                                prompt
                            )
                            
                            # Mostrar la tabla formateada
                            st.dataframe(df, use_container_width=True)
                            
                            # Mostrar información adicional
                            num_rows = len(df)
                            st.caption(f"📊 {num_rows} registro{'s' if num_rows != 1 else ''} encontrado{'s' if num_rows != 1 else ''}")
                            
                            # Agregar al historial con datos
                            st.session_state.messages.append({
                                "role": "assistant", 
                                "content": response_content,
                                "data": df
                            })
                        except Exception as e:
                            # Si falla la creación del DataFrame, mostrar como texto
                            result_text = str(result['result'])
                            st.code(result_text)
                            st.session_state.messages.append({
                                "role": "assistant", 
                                "content": f"{response_content}\n{result_text}",
                                "data": pd.DataFrame()
                            })
                    else:
                        st.write("No se encontraron resultados.")
                        st.session_state.messages.append({
                            "role": "assistant", 
                            "content": "No se encontraron resultados.",
                            "data": pd.DataFrame()
                        })
                else:
                    error_msg = f"Error: {result['error']}"
                    st.error(error_msg)
                    st.session_state.messages.append({
                        "role": "assistant", 
                        "content": error_msg,
                        "data": pd.DataFrame()
                    })

def display_logs_panel():
    """Muestra el panel de logs explicativos"""
    st.header("📋 Logs del Proceso")
    
    if st.session_state.processing_logs:
        # Mostrar logs en orden reverso (más reciente primero)
        for log in reversed(st.session_state.processing_logs[-10:]):  # Últimos 10 logs
            with st.expander(f"⏰ {log['timestamp']} - {log['step']}", expanded=False):
                st.code(log['content'])
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
    st.markdown("Haz preguntas en español y obten respuestas de tu base de datos Snowflake")
    
    # Inicializar estado
    initialize_session_state()
    
    # Configurar conexión si no existe
    if not st.session_state.db_connection:
        with st.spinner("Conectando a Snowflake..."):
            db_conn = SnowflakeConnection()
            if db_conn.connect():
                st.session_state.db_connection = db_conn
                
                # Inicializar agente
                groq_api_key = os.getenv('GROQ_API_KEY')
                if groq_api_key:
                    st.session_state.agent = SnowflakeNLPAgent(
                        db_conn.get_connection_string(),
                        groq_api_key
                    )
                    st.success("✅ Conexión establecida exitosamente!")
                else:
                    st.error("❌ GROQ_API_KEY no configurada")
            else:
                st.error("❌ No se pudo conectar a Snowflake. Verifica tu configuración.")
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