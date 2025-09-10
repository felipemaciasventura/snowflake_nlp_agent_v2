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

        # LLM Providers - Dual support (Groq + Gemini)
        self.GROQ_API_KEY = os.getenv("GROQ_API_KEY")
        self.GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")
        
        # Model configuration
        self.MODEL_NAME = os.getenv("MODEL_NAME", "llama-3.3-70b-versatile")  # For Groq
        self.GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-pro")  # For Gemini
        
        # LLM Provider selection (auto-detect or manual)
        self.LLM_PROVIDER = os.getenv("LLM_PROVIDER", "auto")  # auto, groq, gemini

        # App
        self.DEBUG = os.getenv("DEBUG", "False").lower() == "true"

    def get_available_llm_provider(self) -> str:
        """Detecta qué proveedor de LLM está disponible"""
        if self.LLM_PROVIDER == "groq" and self.GROQ_API_KEY:
            return "groq"
        elif self.LLM_PROVIDER == "gemini" and self.GOOGLE_API_KEY:
            return "gemini"
        elif self.LLM_PROVIDER == "auto":
            # Auto-detectar: priorizar Gemini si está disponible
            if self.GOOGLE_API_KEY:
                return "gemini"
            elif self.GROQ_API_KEY:
                return "groq"
        return None
    
    def validate(self) -> Dict:
        """Valida que todas las variables requeridas estén configuradas"""
        required_vars = [
            "SNOWFLAKE_ACCOUNT",
            "SNOWFLAKE_USER",
            "SNOWFLAKE_PASSWORD",
            "SNOWFLAKE_WAREHOUSE",
            "SNOWFLAKE_DATABASE",
        ]
        
        # Verificar que al menos un proveedor LLM esté disponible
        llm_provider = self.get_available_llm_provider()
        if not llm_provider:
            required_vars.extend(["GROQ_API_KEY or GOOGLE_API_KEY"])

        missing_vars = []
        for var in required_vars:
            if not getattr(self, var):
                missing_vars.append(var)

        return {"valid": len(missing_vars) == 0, "missing_vars": missing_vars}


# Instancia global de configuración
config = Config()
