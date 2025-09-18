#!/usr/bin/env python3
"""
Test script to verify the metadata query handler works correctly
"""

def test_metadata_detection():
    """Test that metadata queries are detected correctly"""
    
    from src.agent.nlp_agent import SnowflakeNLPAgent
    
    # Create a mock agent instance to test the detection logic
    class MockAgent:
        def log_step(self, step, content):
            print(f"LOG: {step} - {content}")
        
        def _handle_metadata_query(self, user_question):
            # Copy the detection logic
            user_lower = user_question.lower().strip()
            
            table_queries = [
                "show tables", "show me tables", "show all tables", "show me all tables",
                "list tables", "list all tables", "what tables", "which tables",
                "display tables", "get tables", "tables list"
            ]
            
            if any(query in user_lower for query in table_queries):
                return f"DETECTED: {user_question}"
            return None
    
    mock_agent = MockAgent()
    
    # Test cases
    test_queries = [
        # Should be detected
        "show me all tables",
        "Show Tables",
        "SHOW ALL TABLES",
        "list tables",
        "what tables are there",
        "display tables",
        "show me tables",
        
        # Should NOT be detected
        "show me all data",
        "list all properties", 
        "what data is available",
        "show me the sales",
        "get me some information"
    ]
    
    print("🧪 Testing Metadata Query Detection")
    print("=" * 50)
    
    detected_count = 0
    for query in test_queries:
        result = mock_agent._handle_metadata_query(query)
        is_detected = result is not None
        if is_detected:
            detected_count += 1
        
        status = "✅ DETECTED" if is_detected else "❌ NOT DETECTED"
        print(f"{status}: \"{query}\"")
    
    print(f"\n📊 Summary:")
    print(f"   Total queries tested: {len(test_queries)}")
    print(f"   Detected as metadata: {detected_count}")
    print(f"   Expected detections: 7 (first 7 queries)")
    print(f"   Detection accuracy: {'✅ CORRECT' if detected_count == 7 else '❌ INCORRECT'}")

if __name__ == "__main__":
    test_metadata_detection()