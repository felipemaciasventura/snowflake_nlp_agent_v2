from langchain_groq import ChatGroq
from langchain_community.utilities import SQLDatabase
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
            model_name="llama-3.3-70b-versatile",
            temperature=0.1,
            max_tokens=4000
        )
        
        self.db = SQLDatabase.from_uri(db_connection)
        
        # Crear prompt personalizado para SQLDatabaseChain
        sql_prompt = """
Eres un experto en SQL para Snowflake. Debes convertir preguntas en español a consultas SQL válidas.

INFORMACIÓN DE LA BASE DE DATOS:
{table_info}

Pregunta: {input}

REGLAS ESTRICTAS:
1. Responde SOLAMENTE con la consulta SQL sin formato markdown
2. NO uses ```sql ni ``` en tu respuesta
3. NO agregues explicaciones ni texto adicional
4. Usa nombres exactos de tablas y columnas mostradas arriba
5. Agrega LIMIT 10 para evitar resultados masivos
6. Para preguntas sobre la base de datos actual: SELECT CURRENT_DATABASE()
7. Para listar tablas disponibles: SHOW TABLES

SQL:"""
        
        self.sql_chain = SQLDatabaseChain.from_llm(
            self.llm,
            self.db,
            verbose=True,
            return_intermediate_steps=True,
            prompt=PromptTemplate(
                input_variables=["input", "table_info"],
                template=sql_prompt
            )
        )
        
    
    def process_query(self, user_question: str) -> Dict[str, Any]:
        """Procesa una consulta del usuario y retorna resultado estructurado"""
        try:
            # Log del inicio del procesamiento
            self.log_step("🔍 Procesando consulta", user_question)
            
            # Ejecutar la cadena SQL usando el método invoke
            result = self.sql_chain.invoke(user_question)
            
            # Log de la consulta generada
            sql_query = 'N/A'
            if 'intermediate_steps' in result and result['intermediate_steps']:
                try:
                    # Intentar diferentes estructuras posibles
                    step = result['intermediate_steps'][0]
                    if isinstance(step, dict):
                        # Verificar diferentes claves posibles
                        sql_query = step.get('sql_cmd') or step.get('query') or step.get('sql') or str(step)
                    else:
                        sql_query = str(step)
                    self.log_step("📝 Consulta SQL generada", sql_query)
                except (KeyError, IndexError, TypeError):
                    self.log_step("⚠️ No se pudo extraer SQL", f"Estructura: {result.get('intermediate_steps', 'N/A')}")
            
            # Si tenemos una SQL clara, ejecutarla directamente para obtener datos reales
            actual_result = None
            if isinstance(sql_query, str):
                cleaned_sql = sql_query.strip().strip('`').strip()
                # Quitar posible formato markdown
                if cleaned_sql.startswith('```'):
                    cleaned_sql = cleaned_sql.strip('`')
                if cleaned_sql.upper().startswith(('SELECT', 'SHOW', 'DESCRIBE')):
                    try:
                        self.log_step("🚀 Ejecutando SQL detectada", cleaned_sql)
                        actual_result = self.db.run(cleaned_sql)
                        self.log_step("✅ Resultados obtenidos", f"{len(actual_result) if hasattr(actual_result, '__len__') else 'N/A'} filas")
                    except Exception as e:
                        self.log_step("⚠️ Error ejecutando SQL generada", f"Error: {str(e)}")
                        actual_result = None
            
            # Si no pudimos ejecutar la SQL anterior, intentar extraer datos de intermediate_steps
            if actual_result is None and 'intermediate_steps' in result and result['intermediate_steps']:
                for step in result['intermediate_steps']:
                    if isinstance(step, dict):
                        for key in ['sql_result', 'result', 'data', 'query_result']:
                            if key in step and step[key] and step[key] != result.get('result'):
                                actual_result = step[key]
                                self.log_step("✅ Datos encontrados en intermediate_steps", f"Campo: {key}, Datos: {str(actual_result)[:100]}...")
                                break
                    if actual_result:
                        break
            
            # Último recurso: si el resultado final es una SQL, ejecutarla
            if actual_result is None:
                final_answer = result.get('result')
                if isinstance(final_answer, str) and final_answer.strip().upper().startswith(('SELECT', 'SHOW', 'DESCRIBE')):
                    try:
                        self.log_step("🚀 Ejecutando respuesta LLM como SQL", final_answer)
                        actual_result = self.db.run(final_answer)
                    except Exception as e:
                        self.log_step("⚠️ Error ejecutando respuesta LLM", f"Error: {str(e)}")
                        actual_result = final_answer
                else:
                    actual_result = final_answer
            
            return {
                'success': True,
                'result': actual_result,
                'sql_query': sql_query if isinstance(sql_query, str) else str(sql_query),
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