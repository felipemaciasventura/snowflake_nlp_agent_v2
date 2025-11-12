"""
Snowflake connection and management
"""

import logging
import os
import time
from typing import Any, Dict, Optional

import snowflake.connector
import streamlit as st
from sqlalchemy import create_engine
from sqlalchemy.pool import NullPool

from src.utils.config import config
from src.utils.helpers import error_handler, log_manager

logger = logging.getLogger(__name__)


class SnowflakeConnection:
    """Class to handle Snowflake connections.

    Provides:
    - connect(): validates configuration, opens native connection and creates SQLAlchemy engine
    - execute_query(): executes SQL and returns rows + column names
    - execute_query_to_df(): executes SQL and returns a DataFrame (pandas)
    - get_connection_string(): exposes connection string for integrations (LangChain)
    - get_connection_info(): returns current session metadata

    Note: Uses NullPool to avoid pooling conflicts with Snowflake.
    """

    def __init__(self):
        self.connection = None
        self.engine = None
        self.is_connected = False

    def connect(self, max_retries: int = 3, retry_delay: int = 5) -> bool:
        """Establish connection to Snowflake with retry logic.
        
        Args:
            max_retries: Maximum number of connection retry attempts (default: 3)
            retry_delay: Delay in seconds between retry attempts (default: 5)
        
        Returns:
            True if connection successful, False otherwise
        """
        for attempt in range(max_retries):
            try:
                return self._connect_attempt()
            except snowflake.connector.errors.OperationalError as e:
                error_str = str(e)
                # Check if error is retryable (network/connection issues)
                is_retryable = (
                    "Failed to resolve" in error_str or
                    "Name or service not known" in error_str or
                    "Connection refused" in error_str or
                    "timeout" in error_str.lower() or
                    "timed out" in error_str.lower()
                )
                
                if is_retryable and attempt < max_retries - 1:
                    logger.warning(
                        f"Connection attempt {attempt + 1} failed (retryable error), "
                        f"retrying in {retry_delay} seconds... Error: {error_str}"
                    )
                    log_manager.add_log(
                        "⚠️ Connection Retry",
                        f"Attempt {attempt + 1}/{max_retries} failed, retrying in {retry_delay}s...",
                        "WARNING"
                    )
                    time.sleep(retry_delay)
                    continue
                else:
                    # Non-retryable error or last attempt
                    return self._handle_connection_error(e, attempt, max_retries)
            except Exception as e:
                # Non-retryable errors
                return self._handle_connection_error(e, attempt, max_retries)
        
        return False

    def _connect_attempt(self) -> bool:
        """Single connection attempt to Snowflake"""
        try:
            log_manager.add_log("🔌 Connecting", "Starting connection to Snowflake...")

            # Validate configuration
            validation = config.validate(require_llm=False)
            if not validation["valid"]:
                missing_vars = ", ".join(validation["missing_vars"])
                error_msg = f"Missing environment variables: {missing_vars}"
                log_manager.add_log("❌ Configuration", error_msg, "ERROR")
                st.error(error_msg)
                return False

            # Clean and validate SNOWFLAKE_ACCOUNT format
            # Remove any trailing parts after # or @ (common mistake)
            account_clean = config.SNOWFLAKE_ACCOUNT.split("#")[0].split("@")[0].strip()
            
            # Connection configuration with timeouts
            connection_params = {
                "account": account_clean,
                "user": config.SNOWFLAKE_USER,
                "password": config.SNOWFLAKE_PASSWORD,
                "warehouse": config.SNOWFLAKE_WAREHOUSE,
                "database": config.SNOWFLAKE_DATABASE,
                "schema": config.SNOWFLAKE_SCHEMA,
                "client_session_keep_alive": True,
                "application": "StreamlitNLPAgent",
                # Timeout configuration (in seconds)
                "network_timeout": int(os.getenv("SNOWFLAKE_NETWORK_TIMEOUT", "60")),
                "login_timeout": int(os.getenv("SNOWFLAKE_LOGIN_TIMEOUT", "30")),
            }

            if account_clean != config.SNOWFLAKE_ACCOUNT:
                log_manager.add_log(
                    "⚠️ Account Format Warning",
                    f"SNOWFLAKE_ACCOUNT was cleaned from '{config.SNOWFLAKE_ACCOUNT}' to '{account_clean}'. "
                    f"Please remove any characters after # or @ in your .env file.",
                    "WARNING"
                )

            log_manager.add_log(
                "⚙️ Configuration",
                f"Connecting to {account_clean}/{config.SNOWFLAKE_DATABASE}",
            )

            # Establish direct connection
            self.connection = snowflake.connector.connect(**connection_params)

            # Create engine for SQLAlchemy
            connection_string = self._build_connection_string()
            self.engine = create_engine(
                connection_string,
                poolclass=NullPool,  # Avoid connection pool issues
                echo=config.DEBUG,
            )

            # Verify connection
            cursor = self.connection.cursor()
            cursor.execute(
                "SELECT CURRENT_USER(), CURRENT_WAREHOUSE(), "
                "CURRENT_DATABASE(), CURRENT_SCHEMA()"
            )
            result = cursor.fetchone()
            cursor.close()

            self.is_connected = True
            log_manager.add_log(
                "✅ Connected",
                f"User: {result[0]}, Warehouse: {result[1]}, "
                f"DB: {result[2]}, Schema: {result[3]}",
            )

            # Warn (but do not block) if no LLM provider is ready
            if not config.get_available_llm_provider():
                warning_msg = (
                    "No LLM provider is currently available. Configure at least one of "
                    "GROQ/Gemini/Ollama/SQLCoder to enable natural language queries."
                )
                log_manager.add_log("⚠️ LLM Unavailable", warning_msg, "WARNING")
                st.warning(warning_msg)

            return True
        except Exception as e:
            # Re-raise to be handled by retry logic
            raise

    def _handle_connection_error(self, e: Exception, attempt: int, max_retries: int) -> bool:
        """Handle connection errors with appropriate messaging"""
        error_str = str(e)
        
        if isinstance(e, snowflake.connector.errors.OperationalError):
            if "Failed to resolve" in error_str or "Name or service not known" in error_str:
                error_msg = (
                    f"❌ Cannot connect to Snowflake account '{config.SNOWFLAKE_ACCOUNT}' "
                    f"(attempt {attempt + 1}/{max_retries}).\n"
                    f"Please verify:\n"
                    f"1. The SNOWFLAKE_ACCOUNT format is correct (e.g., 'xy12345' or 'xy12345.us-east-1')\n"
                    f"2. You have internet connectivity\n"
                    f"3. The account name is correct (without extra characters like # or @)\n\n"
                    f"Error details: {error_str}"
                )
            else:
                error_msg = (
                    f"❌ Snowflake connection error (attempt {attempt + 1}/{max_retries}): {error_str}"
                )
        else:
            error_msg = error_handler.handle_exception(e, f"Snowflake connection (attempt {attempt + 1}/{max_retries})")
        
        log_manager.add_log("❌ Connection Error", error_msg, "ERROR")
        st.error(error_msg)
        logger.error(f"Connection failed after {attempt + 1} attempts: {error_str}")
        return False

    def disconnect(self):
        """Close connection to Snowflake"""
        try:
            if self.connection:
                self.connection.close()
                log_manager.add_log("🔌 Disconnected", "Connection closed successfully")

            if self.engine:
                self.engine.dispose()

            self.is_connected = False
            self.connection = None
            self.engine = None

        except Exception as e:
            error_handler.handle_exception(e, "Snowflake disconnection")

    def execute_query(self, query: str, retry_on_failure: bool = True) -> Optional[Any]:
        """Execute a SQL query with optional retry on connection failure.
        
        Args:
            query: SQL query to execute
            retry_on_failure: If True, attempt to reconnect and retry on connection errors
        
        Returns:
            Query result or None if execution failed
        """
        if not self.is_connected or not self.connection:
            if retry_on_failure:
                logger.info("No active connection, attempting to reconnect...")
                if self.connect(max_retries=1, retry_delay=2):
                    logger.info("Reconnected successfully, retrying query")
                else:
                    error_msg = "No active connection to Snowflake and reconnection failed"
                    log_manager.add_log("❌ Error", error_msg, "ERROR")
                    return None
            else:
                error_msg = "No active connection to Snowflake"
                log_manager.add_log("❌ Error", error_msg, "ERROR")
                return None

        try:
            cursor = self.connection.cursor()
            cursor.execute(query)
            results = cursor.fetchall()
            columns = (
                [desc[0] for desc in cursor.description] if cursor.description else []
            )
            cursor.close()

            log_manager.add_log("📊 Query", f"Executed query: {len(results)} rows")

            return {"data": results, "columns": columns, "row_count": len(results)}

        except snowflake.connector.errors.OperationalError as e:
            error_str = str(e)
            # Check if connection was lost
            if retry_on_failure and ("connection" in error_str.lower() or "closed" in error_str.lower()):
                logger.warning(f"Connection lost during query execution, attempting reconnect: {e}")
                if self.connect(max_retries=1, retry_delay=2):
                    logger.info("Reconnected, retrying query")
                    try:
                        cursor = self.connection.cursor()
                        cursor.execute(query)
                        results = cursor.fetchall()
                        columns = (
                            [desc[0] for desc in cursor.description] if cursor.description else []
                        )
                        cursor.close()
                        log_manager.add_log("📊 Query", f"Executed query after reconnect: {len(results)} rows")
                        return {"data": results, "columns": columns, "row_count": len(results)}
                    except Exception as retry_e:
                        logger.error(f"Query failed after reconnect: {retry_e}")
                        error_msg = error_handler.handle_exception(retry_e, "query execution after reconnect")
                        return None
                else:
                    error_msg = f"Connection lost and reconnection failed: {error_str}"
                    log_manager.add_log("❌ Error", error_msg, "ERROR")
                    return None
            else:
                error_msg = error_handler.handle_exception(e, "query execution")
                return None
        except Exception as e:
            error_msg = error_handler.handle_exception(e, "query execution")
            return None

    def execute_query_to_df(self, query: str):
        """Execute query and return DataFrame"""
        try:
            import pandas as pd

            if not self.engine:
                log_manager.add_log(
                    "❌ Error", "SQLAlchemy engine not available", "ERROR"
                )
                return None

            df = pd.read_sql(query, self.engine)
            log_manager.add_log("📊 DataFrame", f"Created DataFrame: {df.shape}")
            return df

        except Exception as e:
            error_handler.handle_exception(e, "DataFrame conversion")
            return None

    def test_connection(self) -> bool:
        """Test current connection"""
        return error_handler.validate_connection(self.connection)

    def get_connection_info(self) -> Dict[str, str]:
        """Get current connection information"""
        if not self.is_connected:
            return {}

        try:
            cursor = self.connection.cursor()
            cursor.execute(
                """
                SELECT
                    CURRENT_USER() as user,
                    CURRENT_WAREHOUSE() as warehouse,
                    CURRENT_DATABASE() as database,
                    CURRENT_SCHEMA() as schema,
                    CURRENT_VERSION() as version
            """
            )
            result = cursor.fetchone()
            cursor.close()

            return {
                "user": result[0],
                "warehouse": result[1],
                "database": result[2],
                "schema": result[3],
                "version": result[4],
            }

        except Exception as e:
            error_handler.handle_exception(e, "connection info retrieval")
            return {}

    def get_connection_string(self) -> str:
        """Get connection string for SQLAlchemy"""
        return self._build_connection_string()

    def _build_connection_string(self) -> str:
        """Build connection string for SQLAlchemy"""
        return (
            f"snowflake://{config.SNOWFLAKE_USER}:{config.SNOWFLAKE_PASSWORD}"
            f"@{config.SNOWFLAKE_ACCOUNT}/{config.SNOWFLAKE_DATABASE}"
            f"/{config.SNOWFLAKE_SCHEMA}?warehouse={config.SNOWFLAKE_WAREHOUSE}"
        )

    def __enter__(self):
        """Context manager entry"""
        self.connect()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit"""
        self.disconnect()


# Global connection instance
snowflake_conn = SnowflakeConnection()
