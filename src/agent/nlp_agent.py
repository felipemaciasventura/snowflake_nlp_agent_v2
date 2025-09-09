from langchain_groq import ChatGroq
from langchain.sql_database import SQLDatabase
from langchain_experimental.sql import SQLDatabaseChain
from langchain.prompts import PromptTemplate
import streamlit as st
from typing import Dict, Any
import logging
import pandas as pd

class SnowflakeNLPAgent:
    def __init__(self, db_connection, groq_api_key: str):
        self.llm = ChatGroq(
            groq_api_key=groq_api_key,
            model_name="llama3-70b-8192",
            temperature=0.1,
            max_tokens=4000
        )
        
        self.db = SQLDatabase.from_uri(db_connection)
        self.sql_chain = SQLDatabaseChain.from_llm(
            self.llm,
            self.db,
            verbose=True,
            return_intermediate_steps=True
        )
        
        self.setup_custom_prompts()
        
    def setup_custom_prompts(self):
        """Configura prompts personalizados en español"""
        template = """
        Eres un experto en SQL y análisis de datos. Tu tarea es convertir preguntas en español a consultas SQL para Snowflake.
        
        Contexto de la base de datos:
        {table_info}
        
        Pregunta del usuario: {input}
        
        Instrucciones:
        1. Analiza cuidadosamente la pregunta
        2. Genera una consulta SQL precisa y eficiente
        3. Usa nombres de tablas y columnas exactos
        4. Incluye LIMIT para evitar resultados masivos
        5. Responde solo con la consulta SQL
        
        Consulta SQL:
        """
        
        self.prompt = PromptTemplate(
            input_variables=["table_info", "input"],
            template=template
        )
    
    def process_query(self, user_question: str) -> Dict[str, Any]:
        """Procesa una consulta del usuario y retorna resultado estructurado"""
        try:
            # Log del inicio del procesamiento
            self.log_step("🔍 Procesando consulta", user_question)
            
            # Ejecutar la cadena SQL
            result = self.sql_chain(user_question)
            
            # Log de la consulta generada
            if 'intermediate_steps' in result:
                sql_query = result['intermediate_steps'][0]['sql_cmd']
                self.log_step("📝 Consulta SQL generada", sql_query)
            
            # Log del resultado
            self.log_step("✅ Resultado obtenido", f"{len(result.get('result', []))} registros")
            
            return {
                'success': True,
                'result': result['result'],
                'sql_query': sql_query if 'sql_query' in locals() else 'N/A',
                'intermediate_steps': result.get('intermediate_steps', [])
            }
            
        except Exception as e:
            error_msg = str(e)
            self.log_step("❌ Error", error_msg)
            return {
                'success': False,
                'error': error_msg,
                'result': None
            }
    
    def log_step(self, step_name: str, content: str):
        """Registra pasos del procesamiento en Streamlit"""
        if 'processing_logs' not in st.session_state:
            st.session_state.processing_logs = []
        
        log_entry = {
            'step': step_name,
            'content': content,
            'timestamp': pd.Timestamp.now().strftime('%H:%M:%S')
        }
        
        st.session_state.processing_logs.append(log_entry)