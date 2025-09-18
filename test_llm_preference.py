#!/usr/bin/env python3
"""
Test script to verify Gemini is selected as the preferred LLM provider
"""

import os
from src.utils.config import config

def test_llm_preference():
    """Test LLM provider selection with different configurations"""
    
    print("🧪 Testing LLM Provider Preference")
    print("=" * 50)
    
    # Show current environment configuration
    print(f"🔸 Current LLM_PROVIDER setting: {config.LLM_PROVIDER}")
    print(f"🔸 GOOGLE_API_KEY present: {'✅ Yes' if config.GOOGLE_API_KEY else '❌ No'}")
    print(f"🔸 GROQ_API_KEY present: {'✅ Yes' if config.GROQ_API_KEY else '❌ No'}")
    print(f"🔸 Ollama available: {'✅ Yes' if config.is_ollama_available() else '❌ No'}")
    
    # Test the provider selection
    selected_provider = config.get_available_llm_provider()
    print(f"\n🔸 Selected Provider: {selected_provider}")
    
    # Expected behavior
    if config.LLM_PROVIDER == "auto":
        if config.GOOGLE_API_KEY:
            expected = "gemini"
        elif config.is_ollama_available():
            expected = "ollama" 
        elif config.GROQ_API_KEY:
            expected = "groq"
        else:
            expected = None
    else:
        expected = config.LLM_PROVIDER if getattr(config, f"{config.LLM_PROVIDER.upper()}_API_KEY", None) else None
    
    print(f"🔸 Expected Provider: {expected}")
    print(f"🔸 Match: {'✅ YES' if selected_provider == expected else '❌ NO'}")
    
    # Show the priority order
    print(f"\n📋 Priority Order (when LLM_PROVIDER=auto):")
    print(f"   1. 🥇 Gemini (Google) - {'✅ Available' if config.GOOGLE_API_KEY else '❌ Not configured'}")
    print(f"   2. 🥈 Ollama (Local) - {'✅ Available' if config.is_ollama_available() else '❌ Not available'}")  
    print(f"   3. 🥉 Groq (Llama) - {'✅ Available' if config.GROQ_API_KEY else '❌ Not configured'}")
    
    if selected_provider == "gemini":
        print(f"\n🎉 SUCCESS: Gemini is selected as the preferred provider!")
        print(f"   Model: {config.GEMINI_MODEL}")
    else:
        print(f"\n⚠️  NOTE: Gemini not selected. Using: {selected_provider}")
        if not config.GOOGLE_API_KEY:
            print("   💡 To use Gemini, set GOOGLE_API_KEY in your .env file")

if __name__ == "__main__":
    test_llm_preference()