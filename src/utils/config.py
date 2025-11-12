"""
Application configuration
"""

import os
from datetime import datetime, timedelta
from typing import Dict, Optional

import requests
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
        self.SNOWFLAKE_SCHEMA = os.getenv("SNOWFLAKE_SCHEMA", "PUBLIC").upper()

        # LLM Provider Enable/Disable Switches (clearer configuration)
        # Set to "true" or "1" to enable, "false" or "0" to disable
        self.ENABLE_GROQ = os.getenv("ENABLE_GROQ", "true").lower() in ("true", "1", "yes")
        self.ENABLE_GEMINI = os.getenv("ENABLE_GEMINI", "true").lower() in ("true", "1", "yes")
        self.ENABLE_OLLAMA = os.getenv("ENABLE_OLLAMA", "true").lower() in ("true", "1", "yes")
        self.ENABLE_SQLCODER = os.getenv("ENABLE_SQLCODER", "true").lower() in ("true", "1", "yes")

        # LLM Providers - API Keys and configuration
        self.GROQ_API_KEY = os.getenv("GROQ_API_KEY") if self.ENABLE_GROQ else None
        self.GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY") if self.ENABLE_GEMINI else None

        # Ollama configuration (local model)
        self.OLLAMA_BASE_URL = os.getenv(
            "OLLAMA_BASE_URL", "http://localhost:11434"
        ) if self.ENABLE_OLLAMA else None
        self.OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "codellama:7b-instruct")

        # SQLCoder configuration (specialized SQL model)
        self.SQLCODER_BASE_URL = os.getenv(
            "SQLCODER_BASE_URL", "http://localhost:11434"
        ) if self.ENABLE_SQLCODER else None
        self.SQLCODER_MODEL = os.getenv("SQLCODER_MODEL", "sqlcoder-fp16:latest")

        # Model configuration
        self.MODEL_NAME = os.getenv("MODEL_NAME", "llama-3.3-70b-versatile")  # For Groq
        self.GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-1.5-flash")  # For Gemini

        # LLM Provider selection (auto-detect or manual)
        # Options: "auto", "groq", "gemini", "ollama", "sqlcoder"
        # "auto" will use priority: SQLCoder > Ollama > Gemini > Groq
        self.LLM_PROVIDER = os.getenv(
            "LLM_PROVIDER", "auto"
        ).lower()

        # App
        self.DEBUG = os.getenv("DEBUG", "False").lower() == "true"

        # Data preview / table sample configuration
        # Default limit set to 100 if not specified in environment
        try:
            self.SHOW_TABLE_LIMIT = int(os.getenv("SHOW_TABLE_LIMIT", "100"))
        except ValueError:
            self.SHOW_TABLE_LIMIT = 100
        # Optional probabilistic sampling percentage (e.g., 0.1 for 0.1%)
        # If unset or invalid/<=0, sampling is disabled
        try:
            sample_percent_str = os.getenv("SHOW_TABLE_SAMPLE_PERCENT", "")
            self.SHOW_TABLE_SAMPLE_PERCENT = (
                float(sample_percent_str) if sample_percent_str != "" else 0.0
            )
            if self.SHOW_TABLE_SAMPLE_PERCENT <= 0:
                self.SHOW_TABLE_SAMPLE_PERCENT = 0.0
        except ValueError:
            self.SHOW_TABLE_SAMPLE_PERCENT = 0.0

        # Cache provider availability to avoid blocking HTTP requests on every rerun
        self._provider_status_cache: Dict[str, Dict[str, Optional[bool]]] = {}
        self.PROVIDER_STATUS_CACHE_TTL = int(
            os.getenv("LLM_STATUS_CACHE_TTL_SECONDS", "30")
        )

    # ------------------------------------------------------------------ #
    # Provider availability helpers
    # ------------------------------------------------------------------ #
    def _get_cached_provider_status(self, provider: str) -> Optional[bool]:
        """Return cached availability if fresh, else None."""
        cache_entry = self._provider_status_cache.get(provider)
        if not cache_entry:
            return None

        ttl = timedelta(seconds=max(self.PROVIDER_STATUS_CACHE_TTL, 1))
        if datetime.now() - cache_entry["timestamp"] > ttl:
            return None

        return cache_entry["value"]

    def _set_cached_provider_status(self, provider: str, value: bool) -> bool:
        """Store availability value and return it for convenience."""
        self._provider_status_cache[provider] = {
            "value": value,
            "timestamp": datetime.now(),
        }
        return value

    def refresh_provider_status(self, provider: Optional[str] = None):
        """Force refresh of cached provider status."""
        if provider:
            self._provider_status_cache.pop(provider, None)
        else:
            self._provider_status_cache.clear()

    def is_ollama_available(self) -> bool:
        """Check if Ollama is available and accessible"""
        if not self.ENABLE_OLLAMA or not self.OLLAMA_BASE_URL:
            return False

        cached = self._get_cached_provider_status("ollama")
        if cached is not None:
            return cached

        try:
            response = requests.get(f"{self.OLLAMA_BASE_URL}/api/tags", timeout=3)
            return self._set_cached_provider_status(
                "ollama", response.status_code == 200
            )
        except (requests.exceptions.RequestException, requests.exceptions.Timeout):
            return self._set_cached_provider_status("ollama", False)

    def is_sqlcoder_available(self) -> bool:
        """Check if SQLCoder is available and accessible"""
        if not self.ENABLE_SQLCODER or not self.SQLCODER_BASE_URL:
            return False
        cached = self._get_cached_provider_status("sqlcoder")
        if cached is not None:
            return cached
        try:
            response = requests.get(f"{self.SQLCODER_BASE_URL}/api/tags", timeout=3)
            return self._set_cached_provider_status(
                "sqlcoder", response.status_code == 200
            )
        except (requests.exceptions.RequestException, requests.exceptions.Timeout):
            return self._set_cached_provider_status("sqlcoder", False)

    def get_available_llm_provider(self) -> str:
        """Detect which LLM provider is available based on configuration and availability"""
        # Manual provider selection (if specified)
        if self.LLM_PROVIDER and self.LLM_PROVIDER != "auto":
            provider = self.LLM_PROVIDER.lower()
            if provider == "groq" and self.ENABLE_GROQ and self.GROQ_API_KEY:
                return "groq"
            elif provider == "gemini" and self.ENABLE_GEMINI and self.GOOGLE_API_KEY:
                return "gemini"
            elif provider == "ollama" and self.ENABLE_OLLAMA and self.is_ollama_available():
                return "ollama"
            elif provider == "sqlcoder" and self.ENABLE_SQLCODER and self.is_sqlcoder_available():
                return "sqlcoder"
        
        # Auto-detect mode: priority SQLCoder > Ollama > Gemini > Groq
        # (specialized first, then local first, then cloud)
        if self.LLM_PROVIDER == "auto" or not self.LLM_PROVIDER:
            if self.ENABLE_SQLCODER and self.is_sqlcoder_available():
                return "sqlcoder"
            elif self.ENABLE_OLLAMA and self.is_ollama_available():
                return "ollama"
            elif self.ENABLE_GEMINI and self.GOOGLE_API_KEY:
                return "gemini"
            elif self.ENABLE_GROQ and self.GROQ_API_KEY:
                return "groq"
        
        return None

    def get_active_provider_info(self) -> dict:
        """Get detailed information about the currently active provider"""
        provider = self.get_available_llm_provider()
        if not provider:
            return {
                "provider": None,
                "model": None,
                "status": "unavailable",
                "type": None,
                "description": "No LLM provider available"
            }
        
        info = {"provider": provider, "status": "active"}
        
        if provider == "groq":
            info.update({
                "model": self.MODEL_NAME,
                "type": "cloud",
                "description": "Groq Cloud (Fast Inference)",
                "enabled": self.ENABLE_GROQ
            })
        elif provider == "gemini":
            info.update({
                "model": self.GEMINI_MODEL,
                "type": "cloud",
                "description": "Google Gemini (Recommended)",
                "enabled": self.ENABLE_GEMINI
            })
        elif provider == "ollama":
            info.update({
                "model": self.OLLAMA_MODEL,
                "type": "local",
                "description": "Ollama Local (Maximum Privacy)",
                "server": self.OLLAMA_BASE_URL,
                "enabled": self.ENABLE_OLLAMA
            })
        elif provider == "sqlcoder":
            info.update({
                "model": self.SQLCODER_MODEL,
                "type": "local",
                "description": "SQLCoder (SQL Specialized)",
                "server": self.SQLCODER_BASE_URL,
                "enabled": self.ENABLE_SQLCODER
            })
        
        return info

    def get_all_providers_status(self) -> dict:
        """Get status of all configured providers"""
        return {
            "groq": {
                "enabled": self.ENABLE_GROQ,
                "configured": bool(self.GROQ_API_KEY),
                "available": self.ENABLE_GROQ and bool(self.GROQ_API_KEY),
                "model": self.MODEL_NAME if self.ENABLE_GROQ else None
            },
            "gemini": {
                "enabled": self.ENABLE_GEMINI,
                "configured": bool(self.GOOGLE_API_KEY),
                "available": self.ENABLE_GEMINI and bool(self.GOOGLE_API_KEY),
                "model": self.GEMINI_MODEL if self.ENABLE_GEMINI else None
            },
            "ollama": {
                "enabled": self.ENABLE_OLLAMA,
                "configured": bool(self.OLLAMA_BASE_URL),
                "available": self.ENABLE_OLLAMA and self.is_ollama_available(),
                "model": self.OLLAMA_MODEL if self.ENABLE_OLLAMA else None,
                "server": self.OLLAMA_BASE_URL if self.ENABLE_OLLAMA else None
            },
            "sqlcoder": {
                "enabled": self.ENABLE_SQLCODER,
                "configured": bool(self.SQLCODER_BASE_URL),
                "available": self.ENABLE_SQLCODER and self.is_sqlcoder_available(),
                "model": self.SQLCODER_MODEL if self.ENABLE_SQLCODER else None,
                "server": self.SQLCODER_BASE_URL if self.ENABLE_SQLCODER else None
            }
        }

    def validate(self, require_llm: bool = True) -> Dict:
        """Validate that all required variables are configured.
        
        Args:
            require_llm: When False, skip LLM availability checks (useful for DB-only flows)
        """
        import re
        
        required_vars = [
            "SNOWFLAKE_ACCOUNT",
            "SNOWFLAKE_USER",
            "SNOWFLAKE_PASSWORD",
            "SNOWFLAKE_WAREHOUSE",
            "SNOWFLAKE_DATABASE",
        ]

        missing_vars = []
        for var in required_vars:
            if not getattr(self, var):
                missing_vars.append(var)
        
        # Validate SNOWFLAKE_ACCOUNT format if it exists
        if self.SNOWFLAKE_ACCOUNT:
            # Snowflake account should be alphanumeric with optional region (e.g., "xy12345" or "xy12345.us-east-1")
            # Should not contain special characters like #, @, /, etc.
            account_pattern = r'^[a-zA-Z0-9_-]+(\.[a-zA-Z0-9_-]+)*$'
            if not re.match(account_pattern, self.SNOWFLAKE_ACCOUNT):
                missing_vars.append(
                    f"SNOWFLAKE_ACCOUNT has invalid format: '{self.SNOWFLAKE_ACCOUNT}'. "
                    f"Expected format: 'xy12345' or 'xy12345.us-east-1' (no #, @, or / characters)"
                )

        if require_llm:
            # Verify that at least one LLM provider is available
            llm_provider = self.get_available_llm_provider()
            if not llm_provider:
                # Check which LLM providers are missing
                llm_missing = []
                if not self.GROQ_API_KEY:
                    llm_missing.append("GROQ_API_KEY")
                if not self.GOOGLE_API_KEY:
                    llm_missing.append("GOOGLE_API_KEY")
                if not self.is_ollama_available():
                    llm_missing.append("OLLAMA_BASE_URL (or Ollama not accessible)")
                if not self.is_sqlcoder_available():
                    llm_missing.append("SQLCODER_BASE_URL (or SQLCoder not accessible)")
                
                # Add a summary message about LLM providers
                if len(llm_missing) >= 4:  # All are missing
                    missing_vars.append("At least one LLM provider (GROQ_API_KEY, GOOGLE_API_KEY, OLLAMA_BASE_URL, or SQLCODER_BASE_URL)")

        return {"valid": len(missing_vars) == 0, "missing_vars": missing_vars}


# Global configuration instance
config = Config()
