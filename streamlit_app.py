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
        st.sidebar.info(f"LLM: Llama 3 (Groq)")
        st.sidebar.info(f"Base de datos: {os.getenv('SNOWFLAKE_DATABASE')}")
        st.sidebar.info(f"Schema: {os.getenv('SNOWFLAKE_SCHEMA')}")
    
    # Botón para limpiar historial
    if st.sidebar.button("🗑️ Limpiar Historial"):
        st.session_state.messages = []
        st.session_state.processing_logs = []
        st.rerun()

def display_chat_interface():
    """Muestra la interfaz de chat principal"""
    st.header("💬 Chat con tu Base de Datos")
    
    # Mostrar historial de mensajes
    for message in st.session_state.messages:
        with st.chat_message(message["role"]):
            if message["role"] == "assistant" and "data" in message:
                st.write(message["content"])
                if not message["data"].empty:
                    st.dataframe(message["data"])
            else:
                st.write(message["content"])
    
    # Input del usuario
    if prompt := st.chat_input("Escribe tu consulta en español..."):
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
                            df = pd.DataFrame(result['result'])
                            st.dataframe(df)
                            
                            # Agregar al historial con datos
                            st.session_state.messages.append({
                                "role": "assistant", 
                                "content": response_content,
                                "data": df
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
    """Función principal"""
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
        display_chat_interface()
    
    with col2:
        setup_sidebar()
        display_logs_panel()

if __name__ == "__main__":
    main()