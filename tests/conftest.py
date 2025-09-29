"""Test utilities and fixtures for the test suite."""

import pytest
from unittest.mock import Mock, MagicMock


@pytest.fixture
def mock_snowflake_connection():
    """Mock Snowflake connection for testing."""
    mock_conn = Mock()
    mock_conn.connect.return_value = True
    mock_conn.execute_query.return_value = ([], [])
    mock_conn.is_connected = True
    return mock_conn


@pytest.fixture
def mock_llm_response():
    """Mock LLM response for testing."""
    response = MagicMock()
    response.content = "SELECT * FROM table_name LIMIT 10;"
    return response


@pytest.fixture
def sample_sql_result():
    """Sample SQL result data for testing."""
    return [
        ('John Doe', 1000.50),
        ('Jane Smith', 2500.75),
        ('Bob Johnson', 1800.25)
    ]


@pytest.fixture
def sample_column_names():
    """Sample column names for testing."""
    return ['Name', 'Amount']