#!/usr/bin/env python3
"""
Final test to ensure the YOUR_SCHEMA_NAME problem is completely resolved.
This test validates English patterns work correctly.
"""

from dotenv import load_dotenv
from src.database.snowflake_conn import snowflake_conn
from src.agent.nlp_agent import SnowflakeNLPAgent

def test_english_patterns():
    """Test English metadata patterns comprehensively."""
    print("🇺🇸 ENGLISH PATTERNS TEST")
    print("=" * 50)
    
    if not snowflake_conn.connect():
        print("❌ Cannot connect to Snowflake")
        return False
    
    try:
        conn_str = snowflake_conn.get_connection_string()
        agent = SnowflakeNLPAgent(conn_str)
        
        # Test cases that should be detected as metadata
        metadata_test_cases = [
            # Table count queries
            ("How many tables are there in the database?", "table_count"),
            ("count of tables", "table_count"), 
            ("how many tables", "table_count"),
            ("tables count", "table_count"),
            ("count tables", "table_count"),
            
            # Database info queries
            ("What database am I connected to?", "database_info"),
            ("current database", "database_info"),
            ("which database", "database_info"),
            
            # Show tables queries
            ("Show me the tables", "show_tables"),
            ("list tables", "show_tables"),
            ("display tables", "show_tables"),
            
            # Schema info queries
            ("What schema am I using?", "schema_info"),
            ("current schema", "schema_info"),
            ("which schema", "schema_info"),
        ]
        
        # Test cases that should NOT be detected (data queries)
        data_test_cases = [
            "What are the most expensive properties?",
            "Show me properties by city",
            "Which agents have sold the most?",
            "List recent transactions",
        ]
        
        print("🧪 Testing metadata detection:")
        success_count = 0
        
        for query, expected_type in metadata_test_cases:
            detection = agent._detect_metadata_query(query)
            
            if detection['is_metadata'] and detection['query_type'] == expected_type:
                print(f"   ✅ '{query}' -> {expected_type}")
                success_count += 1
            else:
                detected_type = detection.get('query_type', 'none')
                print(f"   ❌ '{query}' -> Expected: {expected_type}, Got: {detected_type}")
        
        print(f"\n📊 Metadata Detection: {success_count}/{len(metadata_test_cases)} passed")
        
        # Test data queries (should not be detected)
        print(f"\n🧪 Testing data queries (should NOT be metadata):")
        data_success = 0
        
        for query in data_test_cases:
            detection = agent._detect_metadata_query(query)
            
            if not detection['is_metadata']:
                print(f"   ✅ '{query}' -> correctly NOT detected as metadata")
                data_success += 1
            else:
                print(f"   ❌ '{query}' -> incorrectly detected as {detection['query_type']}")
        
        print(f"\n📊 Data Query Detection: {data_success}/{len(data_test_cases)} passed")
        
        return success_count == len(metadata_test_cases) and data_success == len(data_test_cases)
        
    finally:
        snowflake_conn.disconnect()

def test_execution_flow():
    """Test the complete execution flow for the problematic query."""
    print("\n\n🚀 EXECUTION FLOW TEST")
    print("=" * 50)
    
    if not snowflake_conn.connect():
        print("❌ Cannot connect to Snowflake")
        return False
    
    try:
        conn_str = snowflake_conn.get_connection_string()
        agent = SnowflakeNLPAgent(conn_str)
        
        # The original problematic query
        problem_query = "How many tables are there in the database?"
        print(f"🎯 Testing: '{problem_query}'")
        
        result = agent.process_query(problem_query)
        
        print(f"Success: {result.get('success')}")
        print(f"Query Type: {result.get('query_type', 'N/A')}")
        print(f"SQL Query: {result.get('sql_query', 'N/A')}")
        
        if result.get('success'):
            actual_result = result.get('result')
            if actual_result and len(actual_result) > 0:
                print(f"✅ TABLE COUNT: {actual_result}")
                # Handle different result formats
                if isinstance(actual_result, str):
                    # Try to parse string result
                    import ast
                    try:
                        parsed_result = ast.literal_eval(actual_result)
                        if isinstance(parsed_result, list) and len(parsed_result) > 0:
                            count = int(parsed_result[0][0])
                        else:
                            count = int(parsed_result)
                    except:
                        # Extract number from string
                        import re
                        numbers = re.findall(r'\d+', actual_result)
                        count = int(numbers[0]) if numbers else 0
                elif isinstance(actual_result, list) and len(actual_result) > 0:
                    count = int(actual_result[0][0])
                else:
                    count = int(actual_result) if actual_result else 0
                
                print(f"✅ PARSED COUNT: {count}")
                
                # Verify it's not 0 and contains no YOUR_SCHEMA_NAME
                sql_query = result.get('sql_query', '')
                if 'YOUR_SCHEMA_NAME' in sql_query.upper():
                    print("❌ PROBLEM: SQL still contains YOUR_SCHEMA_NAME!")
                    return False
                elif count > 0:
                    print("✅ SUCCESS: Correct table count returned!")
                    return True
                else:
                    print("❌ PROBLEM: Table count is still 0!")
                    return False
            else:
                print("❌ No result data")
                return False
        else:
            print(f"❌ Execution failed: {result.get('error')}")
            return False
            
    finally:
        snowflake_conn.disconnect()

if __name__ == "__main__":
    load_dotenv()
    
    print("🇺🇸 ENGLISH METADATA SYSTEM - FINAL VALIDATION")
    print("=" * 60)
    
    # Run tests
    patterns_ok = test_english_patterns()
    execution_ok = test_execution_flow()
    
    print("\n" + "=" * 60)
    print("📊 FINAL RESULTS:")
    print("-" * 30)
    print(f"English Patterns: {'✅ PASS' if patterns_ok else '❌ FAIL'}")
    print(f"Execution Flow:   {'✅ PASS' if execution_ok else '❌ FAIL'}")
    
    if patterns_ok and execution_ok:
        print("\n🎉 ALL TESTS PASSED!")
        print("✅ English metadata system is working correctly")
        print("✅ YOUR_SCHEMA_NAME problem is RESOLVED")
        print("✅ Table count queries now return correct results")
        print("\n🚀 Ready for production use!")
    else:
        print("\n❌ Some tests failed. Check the results above.")
    
    print("\n💡 To test the web interface:")
    print("   streamlit run streamlit_app.py --server.port 8501")
    print("   Try: 'How many tables are there in the database?'")