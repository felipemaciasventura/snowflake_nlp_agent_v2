"""
Utilidades y helpers para la aplicación
"""

import logging
import streamlit as st
from datetime import datetime
from typing import List, Dict, Any
import traceback


class LogManager:
    """Manejador de logs para la aplicación"""

    def __init__(self):
        self.logs: List[Dict[str, Any]] = []

    def add_log(self, category: str, message: str, level: str = "INFO"):
        """Agrega un nuevo log"""
        log_entry = {
            "timestamp": datetime.now().strftime("%H:%M:%S"),
            "category": category,
            "message": message,
            "level": level,
        }
        self.logs.append(log_entry)

        # También log al logger de Python
        if level == "ERROR":
            logging.error(f"{category}: {message}")
        elif level == "WARNING":
            logging.warning(f"{category}: {message}")
        else:
            logging.info(f"{category}: {message}")

    def get_logs(self) -> List[Dict[str, Any]]:
        """Obtiene todos los logs"""
        return self.logs

    def clear_logs(self):
        """Limpia todos los logs"""
        self.logs.clear()

    def display_logs(self):
        """Muestra los logs en Streamlit"""
        if self.logs:
            st.subheader("📝 Logs del Sistema")
            for log in self.logs[-10:]:  # Mostrar últimos 10 logs
                level_icon = {"INFO": "ℹ️", "WARNING": "⚠️", "ERROR": "❌"}.get(
                    log["level"], "📝"
                )

                st.text(
                    f"{log['timestamp']} {level_icon} "
                    f"{log['category']}: {log['message']}"
                )


class ErrorHandler:
    """Manejador de errores para la aplicación"""

    @staticmethod
    def handle_exception(e: Exception, context: str = "Operación") -> str:
        """Maneja excepciones y retorna mensaje de error amigable"""
        error_msg = f"Error en {context}: {str(e)}"

        # Log del error completo
        logging.error(f"{error_msg}\n{traceback.format_exc()}")

        # Agregar al log manager
        log_manager.add_log("❌ Error", error_msg, "ERROR")

        return error_msg

    @staticmethod
    def validate_connection(connection) -> bool:
        """Valida si una conexión está activa"""
        try:
            if connection is None:
                return False

            # Para conexiones de Snowflake, verificar con una query simple
            cursor = connection.cursor()
            cursor.execute("SELECT 1")
            cursor.fetchone()
            cursor.close()
            return True

        except Exception:
            return False

    @staticmethod
    def safe_execute(
        func, *args, default_return=None, context: str = "Operación", **kwargs
    ):
        """Ejecuta una función de forma segura con manejo de errores"""
        try:
            return func(*args, **kwargs)
        except Exception as e:
            ErrorHandler.handle_exception(e, context)
            return default_return


# Instancias globales
log_manager = LogManager()
error_handler = ErrorHandler()

# Configurar logging básico
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
