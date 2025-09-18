#!/usr/bin/env python3
"""
Test script to verify schema obfuscation translation works correctly
"""

from src.utils.schema_obfuscator import SchemaObfuscator

def test_translation():
    """Test the schema obfuscation translation"""
    
    # Test the specific query that was failing
    obfuscated_sql = "SELECT first_name, last_name FROM property_holders LIMIT 10"
    
    print("🧪 Testing Schema Obfuscation Translation")
    print("=" * 50)
    print(f"🔸 Obfuscated SQL: {obfuscated_sql}")
    
    # Translate to real SQL
    real_sql = SchemaObfuscator.translate_to_real_sql(obfuscated_sql)
    print(f"🔸 Translated SQL: {real_sql}")
    
    # Verify translation
    expected = "SELECT FIRST_NAME, LAST_NAME FROM OWNERS LIMIT 10"
    
    print(f"🔸 Expected SQL: {expected}")
    print(f"🔸 Match: {'✅ YES' if real_sql == expected else '❌ NO'}")
    
    # Test other tables
    test_cases = [
        ("SELECT * FROM real_estate_items", "SELECT * FROM PROPERTIES"),
        ("SELECT * FROM geographic_areas", "SELECT * FROM LOCATIONS"),  
        ("SELECT * FROM sales_representatives", "SELECT * FROM AGENTS"),
        ("SELECT * FROM commercial_events", "SELECT * FROM TRANSACTIONS"),
        ("SELECT * FROM property_holders", "SELECT * FROM OWNERS")
    ]
    
    print("\n🧪 Testing All Table Translations")
    print("=" * 50)
    
    for obfuscated, expected in test_cases:
        result = SchemaObfuscator.translate_to_real_sql(obfuscated)
        status = "✅" if result == expected else "❌"
        print(f"{status} {obfuscated} → {result}")
        if result != expected:
            print(f"   Expected: {expected}")
    
    # Test column translations
    column_test = "SELECT property_holders.first_name, property_holders.last_name FROM property_holders"
    expected_col = "SELECT OWNERS.FIRST_NAME, OWNERS.LAST_NAME FROM OWNERS"
    result_col = SchemaObfuscator.translate_to_real_sql(column_test)
    
    print(f"\n🧪 Testing Column Translation")
    print("=" * 50)
    print(f"🔸 Input: {column_test}")
    print(f"🔸 Result: {result_col}")
    print(f"🔸 Expected: {expected_col}")
    print(f"🔸 Match: {'✅ YES' if result_col == expected_col else '❌ NO'}")

if __name__ == "__main__":
    test_translation()