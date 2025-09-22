#!/usr/bin/env python3
"""
Enhanced Context System Test Script

This script demonstrates the new enhanced context system capabilities
without requiring a full Streamlit setup.
"""

import os
import sys
import json
from dotenv import load_dotenv
from pathlib import Path

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent / "src"))

# Load environment variables
load_dotenv()

def test_enhanced_context_system():
    """Test the enhanced context system components"""
    
    print("🧠 Enhanced Context System Test")
    print("=" * 50)
    
    # Test 1: Configuration Check
    print("\n1. 📋 Configuration Check")
    print("-" * 30)
    
    required_vars = [
        "SNOWFLAKE_ACCOUNT", "SNOWFLAKE_USER", "SNOWFLAKE_PASSWORD",
        "SNOWFLAKE_WAREHOUSE", "SNOWFLAKE_DATABASE"
    ]
    
    missing_vars = []
    for var in required_vars:
        if not os.getenv(var):
            missing_vars.append(var)
        else:
            print(f"✅ {var}: {os.getenv(var)[:20]}...")
    
    if missing_vars:
        print(f"❌ Missing variables: {', '.join(missing_vars)}")
        print("Please configure your .env file before testing")
        return False
    
    # Test 2: Import Check
    print("\n2. 📦 Module Import Check")
    print("-" * 30)
    
    try:
        from src.database.schema_inspector import SchemaInspector, DatabaseContext
        print("✅ Schema Inspector imported successfully")
        
        from src.utils.query_context import QueryContextManager, QueryContext
        print("✅ Query Context Manager imported successfully")
        
        from src.utils.context_enhancer import ContextEnhancer, EnhancedContext
        print("✅ Context Enhancer imported successfully")
        
        from src.utils.context_validator import ContextValidator, ValidationResult
        print("✅ Context Validator imported successfully")
        
        from src.database.snowflake_conn import SnowflakeConnection
        print("✅ Snowflake Connection imported successfully")
        
    except ImportError as e:
        print(f"❌ Import error: {e}")
        return False
    
    # Test 3: Database Connection
    print("\n3. 🔌 Database Connection Test")
    print("-" * 30)
    
    try:
        conn = SnowflakeConnection()
        success = conn.connect()
        
        if success:
            print("✅ Snowflake connection established")
            
            # Get connection info
            info = conn.get_connection_info()
            print(f"📊 Database: {info.get('database', 'N/A')}")
            print(f"📊 Schema: {info.get('schema', 'N/A')}")
            print(f"📊 Warehouse: {info.get('warehouse', 'N/A')}")
            
        else:
            print("❌ Failed to connect to Snowflake")
            return False
            
    except Exception as e:
        print(f"❌ Connection error: {e}")
        return False
    
    # Test 4: Schema Inspector
    print("\n4. 🔍 Schema Inspector Test")
    print("-" * 30)
    
    try:
        inspector = SchemaInspector(conn._engine)
        
        # Get basic database info
        db_name, schema_name = inspector._get_database_info()
        print(f"📋 Database: {db_name}")
        print(f"📋 Schema: {schema_name}")
        
        # Get tables
        tables = inspector._get_all_tables()
        print(f"📊 Found {len(tables)} tables")
        
        if tables:
            print("🏷️ Sample tables:")
            for table_name, table_type in tables[:5]:
                print(f"   • {table_name} ({table_type})")
        
        # Get comprehensive context (limited for demo)
        print("\n📊 Getting comprehensive context...")
        context = inspector.get_comprehensive_context(
            refresh_cache=True,
            include_samples=False,  # Disable samples for faster testing
            max_sample_size=5
        )
        
        print(f"✅ Context generated: {len(context.tables)} tables analyzed")
        print(f"🔗 Relationships found: {len(context.relationships)}")
        print(f"🏢 Business domain: {context.business_domain or 'Not detected'}")
        
    except Exception as e:
        print(f"❌ Schema inspector error: {e}")
        return False
    
    # Test 5: Query Context Manager
    print("\n5. 📚 Query Context Manager Test")
    print("-" * 30)
    
    try:
        # Create data directory if it doesn't exist
        Path("data").mkdir(exist_ok=True)
        
        manager = QueryContextManager("data")
        
        # Record a test query
        manager.record_query(
            user_question="What tables are available?",
            generated_sql="SELECT TABLE_NAME FROM INFORMATION_SCHEMA.TABLES",
            success=True,
            execution_time=0.5,
            result_count=len(tables)
        )
        
        print("✅ Test query recorded successfully")
        
        # Get context for a question
        query_context = manager.get_context_for_question("Show me all tables")
        print(f"📊 Similar queries found: {len(query_context.similar_successful_queries)}")
        print(f"🔧 Common patterns: {len(query_context.common_patterns)}")
        
        # Get statistics
        stats = manager.get_statistics()
        print(f"📈 Total queries in history: {stats.get('total_queries', 0)}")
        
    except Exception as e:
        print(f"❌ Query context manager error: {e}")
        return False
    
    # Test 6: Context Enhancer
    print("\n6. 🧠 Context Enhancer Test")
    print("-" * 30)
    
    try:
        enhancer = ContextEnhancer(conn._engine, "data")
        
        # Get enhanced context
        test_question = "What are the available tables in the database?"
        enhanced_context = enhancer.get_enhanced_context(
            user_question=test_question,
            refresh_schema=False,  # Use cached schema
            include_samples=False,
            include_history=True
        )
        
        print(f"✅ Enhanced context generated")
        print(f"📊 Context quality score: {enhanced_context.context_quality_score:.2f}")
        print(f"🎯 Recommended approach: {enhanced_context.recommended_approach}")
        
        if enhanced_context.warning_messages:
            print(f"⚠️ Warnings: {len(enhanced_context.warning_messages)}")
            for warning in enhanced_context.warning_messages[:3]:
                print(f"   • {warning}")
        
        # Test domain insights
        insights = enhanced_context.domain_insights
        print(f"🧠 Detected intent: {insights.get('detected_intent', 'Unknown')}")
        print(f"🏷️ Suggested tables: {len(insights.get('suggested_tables', []))}")
        
    except Exception as e:
        print(f"❌ Context enhancer error: {e}")
        return False
    
    # Test 7: Context Validator
    print("\n7. ✅ Context Validator Test")
    print("-" * 30)
    
    try:
        from src.utils.context_validator import context_validator
        
        # Validate the enhanced context
        validation = context_validator.validate_enhanced_context(enhanced_context)
        
        print(f"✅ Context validation completed")
        print(f"📊 Validation score: {validation.score:.2f}")
        print(f"✅ Is valid: {validation.is_valid}")
        
        if validation.warnings:
            print(f"⚠️ Warnings ({len(validation.warnings)}):")
            for warning in validation.warnings[:3]:
                print(f"   • {warning}")
        
        if validation.recommendations:
            print(f"💡 Recommendations ({len(validation.recommendations)}):")
            for rec in validation.recommendations[:3]:
                print(f"   • {rec}")
        
        # Generate validation report
        report = context_validator.generate_validation_report(validation)
        print(f"\n📋 Validation Report Preview:")
        print(report.split('\n')[0])  # Just show the header
        
    except Exception as e:
        print(f"❌ Context validator error: {e}")
        return False
    
    # Test 8: Enhanced Prompt Generation
    print("\n8. ✨ Enhanced Prompt Test")
    print("-" * 30)
    
    try:
        # Create a base prompt
        base_prompt = """You are a SQL expert. Generate queries for: {input}
        
DATABASE INFO:
{table_info}

Generate pure SQL only."""
        
        # Generate enhanced prompt
        enhanced_prompt = enhancer.generate_enhanced_prompt(
            user_question=test_question,
            base_prompt=base_prompt,
            enhanced_context=enhanced_context
        )
        
        print("✅ Enhanced prompt generated successfully")
        print(f"📏 Prompt length: {len(enhanced_prompt)} characters")
        print(f"🔍 Contains schema info: {'🗄️ ACTUAL DATABASE SCHEMA:' in enhanced_prompt}")
        print(f"🎯 Contains recommendations: {'🎯 RECOMMENDED APPROACH:' in enhanced_prompt}")
        
    except Exception as e:
        print(f"❌ Enhanced prompt error: {e}")
        return False
    
    # Cleanup
    try:
        conn.disconnect()
        print("\n🔌 Database connection closed")
    except:
        pass
    
    # Summary
    print("\n" + "=" * 50)
    print("🎉 Enhanced Context System Test Completed!")
    print("✅ All core components are working correctly")
    print("\n💡 Next Steps:")
    print("1. Run the main Streamlit app: streamlit run streamlit_app.py")
    print("2. Try queries with enhanced context enabled")
    print("3. Check the context quality scores in the sidebar")
    print("4. Review the processing logs for context information")
    
    return True

def main():
    """Main test function"""
    try:
        success = test_enhanced_context_system()
        
        if success:
            print("\n🎯 Test Result: SUCCESS")
            sys.exit(0)
        else:
            print("\n❌ Test Result: FAILED")
            sys.exit(1)
            
    except KeyboardInterrupt:
        print("\n\n⏹️ Test interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n💥 Unexpected error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

if __name__ == "__main__":
    main()