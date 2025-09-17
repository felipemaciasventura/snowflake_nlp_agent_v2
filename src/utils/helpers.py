"""
Utilities and helpers for the application
"""

import logging
import streamlit as st
from datetime import datetime
from typing import List, Dict, Any
import traceback


class LogManager:
    """Log manager for the application"""

    def __init__(self):
        self.logs: List[Dict[str, Any]] = []

    def add_log(self, category: str, message: str, level: str = "INFO"):
        """Add a new log entry"""
        log_entry = {
            "timestamp": datetime.now().strftime("%H:%M:%S"),
            "category": category,
            "message": message,
            "level": level,
        }
        self.logs.append(log_entry)

        # Also log to Python logger
        if level == "ERROR":
            logging.error(f"{category}: {message}")
        elif level == "WARNING":
            logging.warning(f"{category}: {message}")
        else:
            logging.info(f"{category}: {message}")

    def get_logs(self) -> List[Dict[str, Any]]:
        """Get all logs"""
        return self.logs

    def clear_logs(self):
        """Clear all logs"""
        self.logs.clear()

    def display_logs(self):
        """Display logs in Streamlit"""
        if self.logs:
            st.subheader("📝 System Logs")
            for log in self.logs[-10:]:  # Show last 10 logs
                level_icon = {"INFO": "ℹ️", "WARNING": "⚠️", "ERROR": "❌"}.get(
                    log["level"], "📝"
                )

                st.text(
                    f"{log['timestamp']} {level_icon} "
                    f"{log['category']}: {log['message']}"
                )


class ErrorHandler:
    """Error handler for the application"""

    @staticmethod
    def handle_exception(e: Exception, context: str = "Operation") -> str:
        """Handle exceptions and return user-friendly error message"""
        error_msg = f"Error in {context}: {str(e)}"

        # Log the complete error
        logging.error(f"{error_msg}\n{traceback.format_exc()}")

        # Add to log manager
        log_manager.add_log("❌ Error", error_msg, "ERROR")

        return error_msg

    @staticmethod
    def validate_connection(connection) -> bool:
        """Validate if a connection is active"""
        try:
            if connection is None:
                return False

            # For Snowflake connections, verify with a simple query
            cursor = connection.cursor()
            cursor.execute("SELECT 1")
            cursor.fetchone()
            cursor.close()
            return True

        except Exception:
            return False

    @staticmethod
    def safe_execute(
        func, *args, default_return=None, context: str = "Operation", **kwargs
    ):
        """Execute a function safely with error handling"""
        try:
            return func(*args, **kwargs)
        except Exception as e:
            ErrorHandler.handle_exception(e, context)
            return default_return


# Global instances
log_manager = LogManager()
error_handler = ErrorHandler()

# Configure basic logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
