from langchain_groq import ChatGroq  # Para usar con Groq (código conservado)
from langchain_google_genai import ChatGoogleGenerativeAI  # Para usar con Gemini

# Importar ChatOllama con compatibilidad para diferentes versiones
try:
    from langchain_ollama import ChatOllama  # Versión más reciente
except ImportError:
    from langchain_community.chat_models import ChatOllama  # Versión legacy
from langchain_community.utilities import SQLDatabase
from langchain_experimental.sql import SQLDatabaseChain
from langchain.prompts import PromptTemplate
import streamlit as st
from typing import Dict, Any, Optional

import pandas as pd
from src.utils.config import config


class SnowflakeNLPAgent:
    """Agente NLP que traduce preguntas en español a SQL para Snowflake.

    Ejecuta la consulta.

    Responsabilidades principales:
    - Configurar el LLM (Groq, Gemini u Ollama, según configuración)
    - Configurar una cadena SQL (SQLDatabaseChain) con un prompt en español
    - Invocar la cadena con la pregunta del usuario
    - Extraer la SQL generada de los intermediate_steps
    - Ejecutar la SQL de forma segura en la base de datos y devolver filas reales
    - Registrar pasos del proceso para visibilidad en la UI
    """

    def __init__(self, db_connection: str, groq_api_key: Optional[str] = None, google_api_key: Optional[str] = None):
        # Seleccionar proveedor LLM disponible
        provider = config.get_available_llm_provider()

        # Permitir override desde parámetros si se pasan explícitamente
        groq_key = groq_api_key or config.GROQ_API_KEY
        google_key = google_api_key or config.GOOGLE_API_KEY

        if provider == "ollama":
            # Usar Ollama (modelo local - prioridad máxima por privacidad)
            self.llm = ChatOllama(
                base_url=config.OLLAMA_BASE_URL,
                model=config.OLLAMA_MODEL,
                temperature=0.1,
            )
            st.sidebar.info(f"LLM en uso: Ollama ({config.OLLAMA_MODEL}) - Local")
        elif provider == "gemini" and google_key:
            # Usar Gemini (recomendado si tienes plan estudiante)
            self.llm = ChatGoogleGenerativeAI(
                google_api_key=google_key,
                model=config.GEMINI_MODEL,
                temperature=0.1,
                max_output_tokens=4000,
            )
            st.sidebar.info("LLM en uso: Gemini (Google)")
        elif provider == "groq" and groq_key:
            # USO CON GROQ (código conservado):
            # self.llm = ChatGroq(
            #     groq_api_key=groq_key,
            #     model_name=config.MODEL_NAME,
            #     temperature=0.1,
            #     max_tokens=4000,
            # )
            # Se mantiene funcionalidad Groq activa, por defecto
            self.llm = ChatGroq(
                groq_api_key=groq_key,
                model_name=config.MODEL_NAME,
                temperature=0.1,
                max_tokens=4000,
            )
            st.sidebar.info("LLM en uso: Groq (Llama)")
        else:
            raise RuntimeError("No hay proveedor LLM disponible. Configura GOOGLE_API_KEY, GROQ_API_KEY o OLLAMA_BASE_URL.")

        self.db = SQLDatabase.from_uri(db_connection)

        # Crear prompt personalizado para SQLDatabaseChain
        # Prompt en español para generar SQL segura y ejecutable en Snowflake - Optimizado para Bienes Raíces
        sql_prompt = """Eres un experto en SQL para Snowflake especializado en bienes raíces. Genera SOLAMENTE la consulta SQL pura.

INFORMACIÓN DE LA BASE DE DATOS:
{table_info}

🏡 CONTEXTO DE BIENES RAÍCES:
Esta base de datos contiene:
- PROPERTIES: Propiedades (bedrooms, bathrooms, sqft, price, property_type)
- LOCATIONS: Ubicaciones (city, state, population, median_income)
- AGENTS: Agentes (transaction_count, avg_sale_price, commission_rate)
- TRANSACTIONS: Transacciones (sale_date, sale_price, days_on_market)
- OWNERS: Propietarios (num_properties_owned, investor_flag)

🔗 RELACIONES CLAVE:
- properties.location_id = locations.location_id
- transactions.property_id = properties.property_id
- transactions.agent_id = agents.agent_id

Pregunta: {input}

❗ REGLAS OBLIGATORIAS:
1. NUNCA uses ``` o backticks en tu respuesta
2. NUNCA uses formato markdown o bloques de código
3. RESPONDE SOLO CON SQL PURA - NADA MÁS
4. NO agregues explicaciones, comentarios o texto adicional
5. Para consultas de conteo: usa COUNT(*) sin LIMIT
6. Para otras consultas: agrega LIMIT 10
7. Para rankings: usa RANK() OVER (ORDER BY ...)
8. Para precios: usa nombres de columnas como sale_price, list_price, price

📝 EJEMPLOS ESPECÍFICOS DE BIENES RAÍCES:
Pregunta: propiedades más caras por ciudad
Respuesta: SELECT l.city, p.property_id, p.price, RANK() OVER (PARTITION BY l.city ORDER BY p.price DESC) AS rank FROM properties p JOIN locations l ON p.location_id = l.location_id WHERE p.price > 500000 ORDER BY l.city, rank LIMIT 10

Pregunta: agentes con más ventas
Respuesta: SELECT first_name, last_name, transaction_count FROM agents ORDER BY transaction_count DESC LIMIT 10

⛔ NUNCA HAGAS ESTO:
- ``` SELECT ... ```
- ```sql SELECT ... ```
- Explicaciones antes o después del SQL

✅ SQL PURA SOLAMENTE:"""

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
        """Limpia respuesta SQL removiendo markdown y formato extra - Optimizado para CodeLlama"""
        if not isinstance(sql_text, str):
            return ""
        
        import re
        
        # Remover espacios al inicio y final
        cleaned = sql_text.strip()
        
        # PASO 1: Remover bloques de código markdown multilínea
        # Patrón para ```\nSELECT...\n```
        multiline_pattern = r'^```\s*\n(.*?)\n```$'
        match = re.search(multiline_pattern, cleaned, re.DOTALL | re.IGNORECASE)
        if match:
            cleaned = match.group(1).strip()
        else:
            # PASO 2: Remover bloques de código inline ```sql...```
            inline_pattern = r'^```(?:sql)?\s*\n?(.*?)\n?```$'
            match = re.search(inline_pattern, cleaned, re.DOTALL | re.IGNORECASE)
            if match:
                cleaned = match.group(1).strip()
        
        # PASO 3: Remover backticks sueltos al inicio o final (múltiples iteraciones)
        while cleaned.startswith('`') or cleaned.endswith('`'):
            cleaned = cleaned.strip('`').strip()
        
        # PASO 4: Si aún hay backticks al inicio de líneas, removerlos
        lines = cleaned.split('\n')
        cleaned_lines = []
        for line in lines:
            line = line.strip()
            # Remover backticks al inicio de línea
            while line.startswith('`'):
                line = line[1:].strip()
            if line:  # Solo agregar líneas no vacías
                cleaned_lines.append(line)
        
        # PASO 5: Filtrar solo líneas SQL válidas
        sql_lines = []
        for line in cleaned_lines:
            # Mantener líneas que parecen SQL
            if (line.upper().startswith(('SELECT', 'INSERT', 'UPDATE', 'DELETE', 'WITH', 'FROM', 'WHERE', 'GROUP', 'ORDER', 'HAVING', 'LIMIT', 'SHOW', 'DESCRIBE', 'EXPLAIN')) or
                any(keyword in line.upper() for keyword in ['FROM', 'WHERE', 'AND', 'OR', 'ORDER BY', 'GROUP BY', 'HAVING', 'INNER JOIN', 'LEFT JOIN', 'RIGHT JOIN'])):
                sql_lines.append(line)
        
        # PASO 6: Unir las líneas SQL
        result = ' '.join(sql_lines).strip()  # Usar espacio en lugar de \n para una línea
        
        # PASO 7: Limpiar espacios múltiples
        result = re.sub(r'\s+', ' ', result)
        
        return result

    def process_query(self, user_question: str) -> Dict[str, Any]:
        """Procesa la consulta de usuario y devuelve datos listos para la UI.

        Flujo:
        1) Invoca la cadena SQL para obtener SQL a partir de lenguaje natural
        2) Extrae la SQL generada desde intermediate_steps de LangChain
        3) Normaliza/remueve formato markdown si existe
        4) Ejecuta la SQL directamente contra Snowflake (vía SQLDatabase)
        5) Si no hay SQL clara, intenta alternativas (intermediate_steps, respuesta LLM)
        6) Registra cada paso para trazabilidad en Streamlit
        """
        try:
            # Log del inicio del procesamiento
            self.log_step("🔍 Procesando consulta", user_question)

            # Ejecutar la cadena SQL usando el método invoke
            result = self.sql_chain.invoke(user_question)

            # Log de la consulta generada
            sql_query = "N/A"
            if "intermediate_steps" in result and result["intermediate_steps"]:
                try:
                    # Intentar diferentes estructuras posibles
                    step = result["intermediate_steps"][0]
                    if isinstance(step, dict):
                        # Verificar diferentes claves posibles
                        sql_query = (
                            step.get("sql_cmd")
                            or step.get("query")
                            or step.get("sql")
                            or str(step)
                        )
                    else:
                        sql_query = str(step)
                    self.log_step("📝 Consulta SQL generada", sql_query)
                except (KeyError, IndexError, TypeError):
                    self.log_step(
                        "⚠️ No se pudo extraer SQL",
                        f"Estructura: {result.get('intermediate_steps', 'N/A')}",
                    )

            # Si tenemos una SQL clara, ejecutarla directamente para obtener datos
            # reales
            actual_result = None
            if isinstance(sql_query, str):
                # Normaliza la SQL (remueve posibles backticks/markdown) - Mejorado para CodeLlama
                cleaned_sql = self.clean_sql_response(sql_query)
                if cleaned_sql and cleaned_sql.upper().startswith(("SELECT", "SHOW", "DESCRIBE")):
                    try:
                        self.log_step("🚀 Ejecutando SQL detectada", cleaned_sql)
                        actual_result = self.db.run(cleaned_sql)
                        self.log_step(
                            "✅ Resultados obtenidos",
                            f"{len(actual_result) if hasattr(actual_result, '__len__') else 'N/A'} filas",  # noqa: E501
                        )
                    except Exception as e:
                        self.log_step(
                            "⚠️ Error ejecutando SQL generada", f"Error: {str(e)}"
                        )
                        actual_result = None

            # Si no pudimos ejecutar la SQL anterior, intentar extraer datos de
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
                                    "✅ Datos encontrados en intermediate_steps",
                                    f"Campo: {key}, "
                                    f"Datos: {str(actual_result)[:100]}...",
                                )
                                break
                    if actual_result:
                        break

            # Último recurso: si el resultado final es una SQL, ejecutarla
            if actual_result is None:
                final_answer = result.get("result")
                if isinstance(final_answer, str):
                    # Limpiar la respuesta final también
                    cleaned_final = self.clean_sql_response(final_answer)
                    if cleaned_final and cleaned_final.upper().startswith(
                        ("SELECT", "SHOW", "DESCRIBE")
                    ):
                        try:
                            self.log_step(
                                "🚀 Ejecutando respuesta LLM como SQL", cleaned_final
                            )
                            actual_result = self.db.run(cleaned_final)
                        except Exception as e:
                            self.log_step(
                                "⚠️ Error ejecutando respuesta LLM", f"Error: {str(e)}"
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
        """Registra pasos del procesamiento en Streamlit"""
        if "processing_logs" not in st.session_state:
            st.session_state.processing_logs = []

        log_entry = {
            "step": step_name,
            "content": content,
            "timestamp": pd.Timestamp.now().strftime("%H:%M:%S"),
        }

        st.session_state.processing_logs.append(log_entry)
