"""
Configuración de la aplicación
"""

import os
from typing import Dict
from dotenv import load_dotenv

# Cargar variables de entorno
load_dotenv()


class Config:
    """Clase para manejar la configuración de la aplicación"""

    def __init__(self):
        # Snowflake
        self.SNOWFLAKE_ACCOUNT = os.getenv("SNOWFLAKE_ACCOUNT")
        self.SNOWFLAKE_USER = os.getenv("SNOWFLAKE_USER")
        self.SNOWFLAKE_PASSWORD = os.getenv("SNOWFLAKE_PASSWORD")
        self.SNOWFLAKE_WAREHOUSE = os.getenv("SNOWFLAKE_WAREHOUSE")
        self.SNOWFLAKE_DATABASE = os.getenv("SNOWFLAKE_DATABASE")
        self.SNOWFLAKE_SCHEMA = os.getenv("SNOWFLAKE_SCHEMA", "PUBLIC")

        # Groq/LLM
        self.GROQ_API_KEY = os.getenv("GROQ_API_KEY")
        self.MODEL_NAME = os.getenv("MODEL_NAME", "llama-3.3-70b-versatile")

        # App
        self.DEBUG = os.getenv("DEBUG", "False").lower() == "true"

    def validate(self) -> Dict:
        """Valida que todas las variables requeridas estén configuradas"""
        required_vars = [
            "SNOWFLAKE_ACCOUNT",
            "SNOWFLAKE_USER",
            "SNOWFLAKE_PASSWORD",
            "SNOWFLAKE_WAREHOUSE",
            "SNOWFLAKE_DATABASE",
            "GROQ_API_KEY",
        ]

        missing_vars = []
        for var in required_vars:
            if not getattr(self, var):
                missing_vars.append(var)

        return {"valid": len(missing_vars) == 0, "missing_vars": missing_vars}


# Instancia global de configuración
config = Config()
