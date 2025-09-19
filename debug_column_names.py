#!/usr/bin/env python3
"""
Debug script to test column name extraction independently
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from streamlit_app import extract_column_names_from_sql, format_sql_result_to_dataframe

def test_column_extraction():
    print("=" * 50)
    print("Testing Column Name Extraction")
    print("=" * 50)
    
    # Test SQL from the logs
    test_sql = "SELECT l.city AS city_name, p.property_id AS property_id, p.price AS property_price FROM properties p JOIN locations l ON p.location_id = l.location_id WHERE p.price IS NOT NULL ORDER BY p.price DESC LIMIT 10"
    
    # Test data from the logs  
    test_data = [
        ('Ronaldburgh', 20, 986092),
        ('New Ronaldhaven', 24, 982011),
        ('North Sarah', 5, 973107),
        ('East Nicole', 32, 972691),
        ('New Matthewmouth', 1, 970087)
    ]
    
    test_question = "most expensive properties by city"
    
    print(f"SQL: {test_sql[:60]}...")
    print(f"Data: {test_data[:2]}...")
    print(f"Question: {test_question}")
    print()
    
    # Test column extraction
    print("1. Testing extract_column_names_from_sql:")
    columns = extract_column_names_from_sql(test_sql)
    print(f"   Result: {columns}")
    print()
    
    # Test full DataFrame creation
    print("2. Testing format_sql_result_to_dataframe:")
    df = format_sql_result_to_dataframe(test_data, test_sql, test_question)
    print(f"   DataFrame columns: {list(df.columns)}")
    print(f"   DataFrame shape: {df.shape}")
    print()
    print("   DataFrame preview:")
    print(df.head().to_string())

if __name__ == "__main__":
    test_column_extraction()