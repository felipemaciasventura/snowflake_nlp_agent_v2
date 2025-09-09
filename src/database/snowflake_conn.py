"""
Conexión y manejo de Snowflake
"""

import snowflake.connector
from sqlalchemy import create_engine
from sqlalchemy.pool import NullPool

from typing import Optional, Dict, Any
import streamlit as st
import logging

from src.utils.config import config
from src.utils.helpers import log_manager, error_handler

logger = logging.getLogger(__name__)


class SnowflakeConnection:
    """Clase para manejar conexiones con Snowflake.

    Ofrece:
    - connect(): valida configuración, abre conexión nativa y crea engine SQLAlchemy
    - execute_query(): ejecuta SQL y devuelve filas + nombres de columnas
    - execute_query_to_df(): ejecuta SQL y devuelve un DataFrame (pandas)
    - get_connection_string(): expone cadena de conexión para integraciones (LangChain)
    - get_connection_info(): devuelve metadatos de sesión actuales

    Nota: Se usa NullPool para evitar conflictos de pooling con Snowflake.
    """

    def __init__(self):
        self.connection = None
        self.engine = None
        self.is_connected = False

    def connect(self) -> bool:
        """Establece conexión con Snowflake"""
        try:
            log_manager.add_log("🔌 Conectando", "Iniciando conexión con Snowflake...")

            # Validar configuración
            validation = config.validate()
            if not validation["valid"]:
                missing_vars = ", ".join(validation["missing_vars"])
                error_msg = f"Variables de entorno faltantes: {missing_vars}"
                log_manager.add_log("❌ Configuración", error_msg, "ERROR")
                st.error(error_msg)
                return False

            # Configuración de conexión
            connection_params = {
                "account": config.SNOWFLAKE_ACCOUNT,
                "user": config.SNOWFLAKE_USER,
                "password": config.SNOWFLAKE_PASSWORD,
                "warehouse": config.SNOWFLAKE_WAREHOUSE,
                "database": config.SNOWFLAKE_DATABASE,
                "schema": config.SNOWFLAKE_SCHEMA,
                "client_session_keep_alive": True,
                "application": "StreamlitNLPAgent",
            }

            log_manager.add_log(
                "⚙️ Configuración",
                f"Conectando a {config.SNOWFLAKE_ACCOUNT}/{config.SNOWFLAKE_DATABASE}",
            )

            # Establecer conexión directa
            self.connection = snowflake.connector.connect(**connection_params)

            # Crear engine para SQLAlchemy
            connection_string = self._build_connection_string()
            self.engine = create_engine(
                connection_string,
                poolclass=NullPool,  # Evita problemas con pools de conexiones
                echo=config.DEBUG,
            )

            # Verificar conexión
            cursor = self.connection.cursor()
            cursor.execute(
                "SELECT CURRENT_USER(), CURRENT_WAREHOUSE(), CURRENT_DATABASE(), CURRENT_SCHEMA()"
            )
            result = cursor.fetchone()
            cursor.close()

            self.is_connected = True
            log_manager.add_log(
                "✅ Conectado",
                f"Usuario: {result[0]}, Warehouse: {result[1]}, "
                f"DB: {result[2]}, Schema: {result[3]}",
            )

            return True

        except Exception as e:
            error_msg = error_handler.handle_exception(e, "conexión a Snowflake")
            st.error(error_msg)
            return False

    def disconnect(self):
        """Cierra la conexión con Snowflake"""
        try:
            if self.connection:
                self.connection.close()
                log_manager.add_log("🔌 Desconectado", "Conexión cerrada correctamente")

            if self.engine:
                self.engine.dispose()

            self.is_connected = False
            self.connection = None
            self.engine = None

        except Exception as e:
            error_handler.handle_exception(e, "desconexión de Snowflake")

    def execute_query(self, query: str) -> Optional[Any]:
        """Ejecuta una consulta SQL"""
        if not self.is_connected or not self.connection:
            error_msg = "No hay conexión activa con Snowflake"
            log_manager.add_log("❌ Error", error_msg, "ERROR")
            return None

        try:
            cursor = self.connection.cursor()
            cursor.execute(query)
            results = cursor.fetchall()
            columns = (
                [desc[0] for desc in cursor.description] if cursor.description else []
            )
            cursor.close()

            log_manager.add_log("📊 Query", f"Ejecutada consulta: {len(results)} filas")

            return {"data": results, "columns": columns, "row_count": len(results)}

        except Exception as e:
            error_msg = error_handler.handle_exception(e, "ejecución de consulta")
            return None

    def execute_query_to_df(self, query: str):
        """Ejecuta consulta y retorna DataFrame"""
        try:
            import pandas as pd

            if not self.engine:
                log_manager.add_log(
                    "❌ Error", "Engine SQLAlchemy no disponible", "ERROR"
                )
                return None

            df = pd.read_sql(query, self.engine)
            log_manager.add_log("📊 DataFrame", f"Creado DataFrame: {df.shape}")
            return df

        except Exception as e:
            error_handler.handle_exception(e, "conversión a DataFrame")
            return None

    def test_connection(self) -> bool:
        """Prueba la conexión actual"""
        return error_handler.validate_connection(self.connection)

    def get_connection_info(self) -> Dict[str, str]:
        """Obtiene información de la conexión actual"""
        if not self.is_connected:
            return {}

        try:
            cursor = self.connection.cursor()
            cursor.execute(
                """
                SELECT
                    CURRENT_USER() as user,
                    CURRENT_WAREHOUSE() as warehouse,
                    CURRENT_DATABASE() as database,
                    CURRENT_SCHEMA() as schema,
                    CURRENT_VERSION() as version
            """
            )
            result = cursor.fetchone()
            cursor.close()

            return {
                "user": result[0],
                "warehouse": result[1],
                "database": result[2],
                "schema": result[3],
                "version": result[4],
            }

        except Exception as e:
            error_handler.handle_exception(e, "obtención de info de conexión")
            return {}

    def get_connection_string(self) -> str:
        """Obtiene string de conexión para SQLAlchemy"""
        return self._build_connection_string()

    def _build_connection_string(self) -> str:
        """Construye string de conexión para SQLAlchemy"""
        return (
            f"snowflake://{config.SNOWFLAKE_USER}:{config.SNOWFLAKE_PASSWORD}"
            f"@{config.SNOWFLAKE_ACCOUNT}/{config.SNOWFLAKE_DATABASE}"
            f"/{config.SNOWFLAKE_SCHEMA}?warehouse={config.SNOWFLAKE_WAREHOUSE}"
        )

    def __enter__(self):
        """Context manager entry"""
        self.connect()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit"""
        self.disconnect()


# Instancia global de conexión
snowflake_conn = SnowflakeConnection()
