"""
Snowflake connection and management
"""

import snowflake.connector
from sqlalchemy import create_engine
from sqlalchemy.pool import NullPool

from typing import Optional, Dict, Any
import streamlit as st
import logging

from src.utils.config import config
from src.utils.helpers import log_manager, error_handler

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
        self._context_cache = None
        self._cache_timestamp = None
        self._cache_ttl = 300  # Cache TTL: 5 minutes

    def connect(self) -> bool:
        """Establish connection to Snowflake"""
        try:
            log_manager.add_log("🔌 Connecting", "Starting connection to Snowflake...")

            # Validate configuration
            validation = config.validate()
            if not validation["valid"]:
                missing_vars = ", ".join(validation["missing_vars"])
                error_msg = f"Missing environment variables: {missing_vars}"
                log_manager.add_log("❌ Configuration", error_msg, "ERROR")
                st.error(error_msg)
                return False

            # Connection configuration
            connection_params = {
                "account": config.SNOWFLAKE_ACCOUNT,
                "user": config.SNOWFLAKE_USER,
                "password": config.SNOWFLAKE_PASSWORD,
                "warehouse": config.SNOWFLAKE_WAREHOUSE,
                "database": config.SNOWFLAKE_DATABASE,
                "schema": config.SNOWFLAKE_SCHEMA,
                "client_session_keep_alive": True,
                "application": "StreamlitNLPAgent",
            }

            log_manager.add_log(
                "⚙️ Configuration",
                f"Connecting to {config.SNOWFLAKE_ACCOUNT}/{config.SNOWFLAKE_DATABASE}",
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

            return True

        except Exception as e:
            error_msg = error_handler.handle_exception(e, "Snowflake connection")
            st.error(error_msg)
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
            
            # Clear context cache
            self._context_cache = None
            self._cache_timestamp = None

        except Exception as e:
            error_handler.handle_exception(e, "Snowflake disconnection")

    def execute_query(self, query: str) -> Optional[Any]:
        """Execute a SQL query"""
        if not self.is_connected or not self.connection:
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
    
    def get_database_context(self) -> Dict[str, Any]:
        """Get comprehensive database context for NLP agent.
        
        Uses caching to avoid repeated metadata queries.
        Cache TTL: 5 minutes
        
        Returns:
            Dict with current database, schema, table count, and sample tables
        """
        if not self.is_connected:
            return {"error": "Not connected to Snowflake"}
        
        # Check cache validity
        import time
        current_time = time.time()
        
        if (self._context_cache is not None and 
            self._cache_timestamp is not None and 
            (current_time - self._cache_timestamp) < self._cache_ttl):
            
            log_manager.add_log(
                "💾 Cache Hit", 
                "Using cached database context"
            )
            return self._context_cache
        
        try:
            cursor = self.connection.cursor()
            context = {}
            
            # Get basic connection info
            cursor.execute(
                "SELECT CURRENT_DATABASE(), CURRENT_SCHEMA(), CURRENT_WAREHOUSE()"
            )
            result = cursor.fetchone()
            context["database"] = result[0]
            context["schema"] = result[1]
            context["warehouse"] = result[2]
            
            # Get table count in current schema
            cursor.execute(
                "SELECT COUNT(*) FROM INFORMATION_SCHEMA.TABLES WHERE TABLE_SCHEMA = CURRENT_SCHEMA()"
            )
            context["table_count"] = cursor.fetchone()[0]
            
            # Get sample tables (up to 10)
            cursor.execute(
                "SELECT TABLE_NAME, TABLE_TYPE FROM INFORMATION_SCHEMA.TABLES WHERE TABLE_SCHEMA = CURRENT_SCHEMA() LIMIT 10"
            )
            tables = cursor.fetchall()
            context["sample_tables"] = [{
                "name": table[0], 
                "type": table[1]
            } for table in tables]
            
            # Get total schemas in database
            cursor.execute(
                "SELECT COUNT(*) FROM INFORMATION_SCHEMA.SCHEMATA"
            )
            context["schema_count"] = cursor.fetchone()[0]
            
            cursor.close()
            
            # Cache the result
            self._context_cache = context
            self._cache_timestamp = current_time
            
            log_manager.add_log(
                "📋 Database Context", 
                f"DB: {context['database']}, Schema: {context['schema']}, Tables: {context['table_count']} (cached)"
            )
            
            return context
            
        except Exception as e:
            error_msg = error_handler.handle_exception(e, "database context retrieval")
            return {"error": error_msg}
    
    def get_metadata_summary(self) -> str:
        """Get formatted metadata summary for LLM context.
        
        Returns:
            Formatted string with database information for prompt inclusion
        """
        context = self.get_database_context()
        
        if "error" in context:
            return f"❌ Database context unavailable: {context['error']}"
        
        summary = f"""📋 CURRENT DATABASE CONTEXT:
• Database: {context['database']}
• Schema: {context['schema']} 
• Warehouse: {context['warehouse']}
• Tables in current schema: {context['table_count']}
• Total schemas in database: {context['schema_count']}

📊 SAMPLE TABLES AVAILABLE:"""
        
        for table in context.get('sample_tables', [])[:5]:
            summary += f"\n• {table['name']} ({table['type']})"
        
        if context['table_count'] > 5:
            summary += f"\n• ... and {context['table_count'] - 5} more tables"
        
        return summary

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
