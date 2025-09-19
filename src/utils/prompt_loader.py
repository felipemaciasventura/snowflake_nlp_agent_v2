"""
Prompt management utilities for cleaner code organization
"""
import os
from typing import Optional
from pathlib import Path

class PromptLoader:
    """Handles loading and managing prompt templates"""
    
    def __init__(self):
        self.project_root = Path(__file__).parent.parent.parent
        self.config_dir = self.project_root / "config"
        self.prompts_dir = self.project_root / "src" / "prompts"
    
    def load_prompt_from_file(self, filename: str, fallback: str = None) -> str:
        """Load prompt template from external file"""
        
        # Try config directory first
        config_path = self.config_dir / filename
        if config_path.exists():
            try:
                with open(config_path, 'r', encoding='utf-8') as f:
                    return f.read().strip()
            except Exception:
                pass
        
        # Try prompts directory
        prompts_path = self.prompts_dir / filename  
        if prompts_path.exists():
            try:
                with open(prompts_path, 'r', encoding='utf-8') as f:
                    return f.read().strip()
            except Exception:
                pass
        
        # Return fallback if provided
        if fallback:
            return fallback
        
        # Default minimal prompt if all else fails
        return self._get_minimal_prompt()
    
    def _get_minimal_prompt(self) -> str:
        """Minimal fallback prompt"""
        return """You are a SQL expert. Generate clean SQL queries.

DATABASE INFORMATION:
{table_info}

Question: {input}

Generate SQL query only, no explanations."""

    def get_sql_prompt(self, provider: str = "gemini") -> str:
        """Get SQL prompt for specific LLM provider"""
        
        # Try provider-specific prompt file first
        provider_prompt = self.load_prompt_from_file(f"{provider}_sql_prompt.txt")
        if provider_prompt and provider_prompt != self._get_minimal_prompt():
            return provider_prompt
        
        # Try generic SQL prompt file
        generic_prompt = self.load_prompt_from_file("sql_prompt_template.txt")
        if generic_prompt and generic_prompt != self._get_minimal_prompt():
            return generic_prompt
        
        # Fallback to built-in prompts
        return self._get_builtin_prompt(provider)
    
    def _get_builtin_prompt(self, provider: str) -> str:
        """Built-in prompt templates as fallback"""
        
        if provider in ["gemini", "groq"]:
            return """You are a Snowflake SQL expert. Generate ONLY pure SQL queries.

DATABASE INFORMATION:
{table_info}

Question: {input}

RULES:
1. Return pure SQL only - no markdown, no explanations
2. Use LIMIT 10 for SELECT queries
3. Use CURRENT_DATABASE() for database info queries
4. Use CURRENT_SCHEMA() for schema info queries

Generate SQL query:"""
        
        elif provider == "ollama":
            return """You are a SQL expert. Generate clean SQL queries.

DATABASE INFORMATION:
{table_info}

Question: {input}

Rules:
1. SQL only, no explanations
2. Add LIMIT 10 to SELECT queries  
3. Use system functions for metadata

SQL:"""
        
        return self._get_minimal_prompt()
    
    def save_prompt_template(self, content: str, filename: str) -> bool:
        """Save a prompt template to config directory"""
        try:
            os.makedirs(self.config_dir, exist_ok=True)
            filepath = self.config_dir / filename
            
            with open(filepath, 'w', encoding='utf-8') as f:
                f.write(content)
            return True
        except Exception:
            return False
    
    def list_available_prompts(self) -> list:
        """List all available prompt files"""
        prompts = []
        
        # Check config directory
        if self.config_dir.exists():
            prompts.extend([f.name for f in self.config_dir.glob("*.txt")])
        
        # Check prompts directory  
        if self.prompts_dir.exists():
            prompts.extend([f.name for f in self.prompts_dir.glob("*.txt")])
        
        return sorted(list(set(prompts)))

# Global instance for easy import
prompt_loader = PromptLoader()