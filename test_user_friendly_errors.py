#!/usr/bin/env python3
"""
Test script to verify user-friendly error handling works correctly.
"""

from dotenv import load_dotenv
from src.database.snowflake_conn import snowflake_conn
from src.agent.nlp_agent import SnowflakeNLPAgent

def test_user_friendly_errors():
    """Test user-friendly error messages."""
    print("🧪 TESTING USER-FRIENDLY ERROR MESSAGES")
    print("=" * 50)
    
    if not snowflake_conn.connect():
        print("❌ Cannot connect to Snowflake")
        return False
    
    try:
        conn_str = snowflake_conn.get_connection_string()
        import os
        # Force use of Gemini by temporarily disabling Ollama
        original_ollama = os.environ.get('OLLAMA_BASE_URL')
        os.environ.pop('OLLAMA_BASE_URL', None)  # Remove Ollama config
        os.environ['LLM_PROVIDER'] = 'gemini'  # Force Gemini
        
        google_api_key = os.getenv("GOOGLE_API_KEY")
        agent = SnowflakeNLPAgent(conn_str, google_api_key=google_api_key)
        
        # Restore original config after agent creation
        if original_ollama:
            os.environ['OLLAMA_BASE_URL'] = original_ollama
        
        # Test case 1: Query that should cause a "table does not exist" error
        test_query = "give me the list of owners, the names"
        print(f"🎯 Testing query: '{test_query}'")
        
        result = agent.process_query(test_query)
        
        print(f"Success: {result.get('success')}")
        print(f"User Friendly: {result.get('user_friendly')}")
        print(f"Error Message: {result.get('error', 'N/A')}")
        print(f"Technical Error: {result.get('technical_error', 'N/A')[:100]}...")
        
        if not result.get('success') and result.get('user_friendly'):
            print("✅ User-friendly error handling is working!")
            return True
        else:
            print("❌ User-friendly error handling failed!")
            return False
            
    except Exception as e:
        print(f"❌ Test failed with exception: {e}")
        return False
    finally:
        snowflake_conn.disconnect()

if __name__ == "__main__":
    load_dotenv()
    
    print("🔍 USER-FRIENDLY ERROR TESTING")
    print("=" * 60)
    
    success = test_user_friendly_errors()
    
    print("\n" + "=" * 60)
    if success:
        print("🎉 USER-FRIENDLY ERROR HANDLING: ✅ WORKING!")
        print("✅ Error messages are now user-friendly")
        print("✅ Technical details are available for debugging")
        print("\n🚀 Ready to test in web interface!")
    else:
        print("❌ USER-FRIENDLY ERROR HANDLING: ❌ NEEDS FIXING!")
    
    print("\n💡 To test in web interface:")
    print("   streamlit run streamlit_app.py --server.port 8501")
    print("   Try: 'give me the list of owners, the names'")