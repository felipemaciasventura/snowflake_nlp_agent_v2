"""
Application configuration
"""

import os
import requests
from typing import Dict
from dotenv import load_dotenv

# Load environment variables
load_dotenv()


class Config:
    """Class to handle application configuration"""

    def __init__(self):
        # Snowflake
        self.SNOWFLAKE_ACCOUNT = os.getenv("SNOWFLAKE_ACCOUNT")
        self.SNOWFLAKE_USER = os.getenv("SNOWFLAKE_USER")
        self.SNOWFLAKE_PASSWORD = os.getenv("SNOWFLAKE_PASSWORD")
        self.SNOWFLAKE_WAREHOUSE = os.getenv("SNOWFLAKE_WAREHOUSE")
        self.SNOWFLAKE_DATABASE = os.getenv("SNOWFLAKE_DATABASE")
        self.SNOWFLAKE_SCHEMA = os.getenv("SNOWFLAKE_SCHEMA", "PUBLIC")

        # LLM Providers - Triple support (Groq + Gemini + Ollama)
        self.GROQ_API_KEY = os.getenv("GROQ_API_KEY")
        self.GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")
        
        # Ollama configuration (local model)
        self.OLLAMA_BASE_URL = os.getenv("OLLAMA_BASE_URL", "http://192.168.0.100:11434")
        self.OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "codellama:7b-instruct")
        
        # Model configuration
        self.MODEL_NAME = os.getenv("MODEL_NAME", "llama-3.3-70b-versatile")  # For Groq
        self.GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-1.5-flash")  # For Gemini
        
        # LLM Provider selection (auto-detect or manual)
        # When "auto": Gemini > Ollama > Groq (Gemini is preferred for best performance)
        self.LLM_PROVIDER = os.getenv("LLM_PROVIDER", "auto")  # auto, groq, gemini, ollama

        # App
        self.DEBUG = os.getenv("DEBUG", "False").lower() == "true"
    
    def is_ollama_available(self) -> bool:
        """Check if Ollama is available and accessible"""
        try:
            response = requests.get(f"{self.OLLAMA_BASE_URL}/api/tags", timeout=3)
            return response.status_code == 200
        except (requests.exceptions.RequestException, requests.exceptions.Timeout):
            return False

    def get_available_llm_provider(self) -> str:
        """Detect which LLM provider is available"""
        if self.LLM_PROVIDER == "groq" and self.GROQ_API_KEY:
            return "groq"
        elif self.LLM_PROVIDER == "gemini" and self.GOOGLE_API_KEY:
            return "gemini"
        elif self.LLM_PROVIDER == "ollama" and self.is_ollama_available():
            return "ollama"
        elif self.LLM_PROVIDER == "auto":
            # Auto-detect: priority Gemini > Ollama > Groq (Gemini preferred)
            if self.GOOGLE_API_KEY:
                return "gemini"
            elif self.is_ollama_available():
                return "ollama"
            elif self.GROQ_API_KEY:
                return "groq"
        return None
    
    def validate(self) -> Dict:
        """Validate that all required variables are configured"""
        required_vars = [
            "SNOWFLAKE_ACCOUNT",
            "SNOWFLAKE_USER",
            "SNOWFLAKE_PASSWORD",
            "SNOWFLAKE_WAREHOUSE",
            "SNOWFLAKE_DATABASE",
        ]
        
        # Verify that at least one LLM provider is available
        llm_provider = self.get_available_llm_provider()
        if not llm_provider:
            required_vars.extend(["GROQ_API_KEY or GOOGLE_API_KEY or OLLAMA_BASE_URL"])

        missing_vars = []
        for var in required_vars:
            if not getattr(self, var):
                missing_vars.append(var)

        return {"valid": len(missing_vars) == 0, "missing_vars": missing_vars}


# Global configuration instance
config = Config()
