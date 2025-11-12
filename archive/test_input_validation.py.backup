"""
Unit tests for input validation functionality
"""
import pytest
import sys
import os

# Add the project root to Python path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Import the validation function from streamlit_app
from streamlit_app import validate_user_input


class TestInputValidation:
    """Test cases for user input validation"""

    def test_valid_natural_language_queries(self):
        """Test that valid natural language queries pass validation"""
        valid_queries = [
            "Show me the top 10 customers",
            "What are the sales for 2023?",
            "How many orders do we have",
            "List products with price greater than 100",
            "Get customer data from last month",
            "Show me customer's information",
            "What's the average revenue?",
            "Find all orders from January",
            "Display revenue by region",
            "Count total users"
        ]
        
        for query in valid_queries:
            is_valid, cleaned, error = validate_user_input(query)
            assert is_valid, f"Query '{query}' should be valid but got error: {error}"
            assert cleaned == query.strip()
            assert error == ""

    def test_reject_too_short_queries(self):
        """Test that too short queries are rejected"""
        short_queries = ["hi", "ok", "no", "a", "ab"]
        
        for query in short_queries:
            is_valid, _, error = validate_user_input(query)
            assert not is_valid, f"Query '{query}' should be invalid (too short)"
            assert "too short" in error.lower()

    def test_reject_empty_or_whitespace(self):
        """Test that empty or whitespace-only queries are rejected"""
        empty_queries = ["", "   ", "\t", "\n", "  \t  \n  "]
        
        for query in empty_queries:
            is_valid, _, error = validate_user_input(query)
            assert not is_valid, f"Query '{query}' should be invalid (empty/whitespace)"
            assert "valid query" in error

    def test_reject_special_characters(self):
        """Test that queries with special characters are rejected"""
        queries_with_special_chars = [
            "Show me data<script>",
            "What is @username", 
            "Check #hashtag",
            "Price $100",
            "Data & results",
            "Show me 50% data",
            "User ID = 123",
            "Price > 100 AND < 200",
            "Data [filtered]",
            "Data {grouped}",
            "Show users|filtered",
            "Results\\processed"
        ]
        
        for query in queries_with_special_chars:
            is_valid, _, error = validate_user_input(query)
            assert not is_valid, f"Query '{query}' should be invalid (special characters)"
            assert "Invalid characters detected" in error

    def test_reject_sql_injection_attempts(self):
        """Test that potential SQL injection attempts are rejected"""
        sql_injections = [
            "DROP TABLE users",
            "DELETE FROM customers", 
            "INSERT INTO users VALUES",
            "ALTER TABLE structure",
            "TRUNCATE TABLE data",
            "Show data -- comment",
            "users UNION SELECT password"
        ]
        
        for query in sql_injections:
            is_valid, _, error = validate_user_input(query)
            assert not is_valid, f"Query '{query}' should be invalid (SQL injection)"
            assert ("unsafe content" in error or "Invalid characters" in error)

    def test_allow_basic_punctuation(self):
        """Test that basic punctuation is allowed"""
        queries_with_punctuation = [
            "What's the customer data?",
            "Show me John's orders",
            "List top-rated products", 
            "Get Q1, Q2, Q3 data",
            "How many items are there?",
            "Display customer information.",
            "Show me year-over-year growth!"
        ]
        
        for query in queries_with_punctuation:
            is_valid, cleaned, error = validate_user_input(query)
            assert is_valid, f"Query '{query}' should be valid (basic punctuation) but got error: {error}"
            assert cleaned == query.strip()

    def test_whitespace_trimming(self):
        """Test that leading/trailing whitespace is properly trimmed"""
        query = "  Show me the data  "
        is_valid, cleaned, error = validate_user_input(query)
        
        assert is_valid
        assert cleaned == "Show me the data"
        assert error == ""

    def test_length_limits(self):
        """Test that length limits are enforced"""
        # Test too long query
        long_query = "a" * 501  # Over 500 character limit
        is_valid, _, error = validate_user_input(long_query)
        assert not is_valid
        assert "too long" in error.lower()
        
        # Test exactly at limit (should be valid)
        limit_query = "a" * 500
        is_valid, _, error = validate_user_input(limit_query)
        assert is_valid

    def test_return_format(self):
        """Test that the function returns the expected tuple format"""
        is_valid, cleaned, error = validate_user_input("valid query")
        
        assert isinstance(is_valid, bool)
        assert isinstance(cleaned, str)
        assert isinstance(error, str)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])