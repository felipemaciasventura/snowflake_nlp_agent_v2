#!/usr/bin/env python3
"""
Simulate the error handling to test user-friendly messages.
"""

from dotenv import load_dotenv
from src.agent.nlp_agent import SnowflakeNLPAgent
from snowflake.connector.errors import ProgrammingError

def test_error_handler():
    """Test the _handle_sql_error method directly."""
    print("🧪 TESTING ERROR HANDLER DIRECTLY")
    print("=" * 50)
    
    # Create a mock agent instance
    class MockAgent:
        def __init__(self):
            pass
        
        def log_step(self, step_name: str, content: str):
            print(f"LOG: {step_name} - {content}")
    
    # Import the error handler from the agent
    from src.agent.nlp_agent import SnowflakeNLPAgent
    
    # Create the error handler
    agent = MockAgent()
    # Add the method to our mock
    agent._handle_sql_error = SnowflakeNLPAgent._handle_sql_error.__get__(agent, MockAgent)
    
    # Test case 1: Property holders not found
    error_msg = "(snowflake.connector.errors.ProgrammingError) 002003 (42S02): 01bf1e21-0005-1d21-0000-457100027f5a: SQL compilation error: Object 'PROPERTY_HOLDERS' does not exist or not authorized."
    error = ProgrammingError(error_msg)
    
    print("🎯 Testing PROPERTY_HOLDERS error:")
    result = agent._handle_sql_error(error, "SELECT * FROM property_holders")
    
    print(f"Success: {result.get('success')}")
    print(f"User Friendly: {result.get('user_friendly')}")
    print(f"Error Message: {result.get('error')}")
    print(f"Technical: {result.get('technical_error', 'N/A')[:100]}...")
    
    if not result.get('success') and result.get('user_friendly'):
        print("✅ Error handling is working correctly!")
        return True
    else:
        print("❌ Error handling failed!")
        return False

if __name__ == "__main__":
    load_dotenv()
    
    print("🔍 ERROR HANDLER SIMULATION")
    print("=" * 60)
    
    success = test_error_handler()
    
    print("\n" + "=" * 60)
    if success:
        print("🎉 USER-FRIENDLY ERROR HANDLING: ✅ WORKING!")
        print("✅ Error messages are properly formatted")
        print("✅ User-friendly flag is set correctly")
        print("\n🚀 The error handling system is ready!")
    else:
        print("❌ USER-FRIENDLY ERROR HANDLING: ❌ NEEDS FIXING!")
    
    print("\n💡 The real test will be in the web interface:")
    print("   streamlit run streamlit_app.py --server.port 8501")
    print("   Try: 'give me the list of owners, the names'")