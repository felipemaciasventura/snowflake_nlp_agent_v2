"""Basic unit tests for the configuration module."""

import os
import pytest
from unittest.mock import patch
from src.utils.config import Config


class TestConfig:
    """Test cases for Config class."""

    def test_config_initialization(self):
        """Test that Config can be initialized."""
        config = Config()
        assert config is not None

    @patch.dict(os.environ, {
        'SNOWFLAKE_ACCOUNT': 'test-account',
        'SNOWFLAKE_USER': 'test-user',
        'SNOWFLAKE_PASSWORD': 'test-password',
        'SNOWFLAKE_WAREHOUSE': 'test-warehouse',
        'SNOWFLAKE_DATABASE': 'test-database',
    })
    def test_config_with_environment_variables(self):
        """Test Config with environment variables set."""
        config = Config()
        assert config.SNOWFLAKE_ACCOUNT == 'test-account'
        assert config.SNOWFLAKE_USER == 'test-user'
        assert config.SNOWFLAKE_PASSWORD == 'test-password'
        assert config.SNOWFLAKE_WAREHOUSE == 'test-warehouse'
        assert config.SNOWFLAKE_DATABASE == 'test-database'

    def test_config_defaults(self):
        """Test Config default values."""
        config = Config()
        assert config.SNOWFLAKE_SCHEMA == "PUBLIC"
        assert config.LLM_PROVIDER == "auto"
        assert config.DEBUG is False

    @patch.dict(os.environ, {'DEBUG': 'true'})
    def test_debug_flag_true(self):
        """Test DEBUG flag when set to true."""
        config = Config()
        assert config.DEBUG is True

    @patch.dict(os.environ, {'DEBUG': 'false'})
    def test_debug_flag_false(self):
        """Test DEBUG flag when set to false."""
        config = Config()
        assert config.DEBUG is False