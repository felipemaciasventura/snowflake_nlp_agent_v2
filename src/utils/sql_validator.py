"""
SQL Validator - Validate SQL queries before execution
"""

import logging
import re
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


class SQLValidator:
    """Validate SQL queries before execution"""

    # Dangerous operations that should be blocked
    DANGEROUS_OPERATIONS = [
        "DROP",
        "DELETE",
        "TRUNCATE",
        "ALTER",
        "CREATE",
        "INSERT",
        "UPDATE",
        "GRANT",
        "REVOKE",
    ]

    # Allowed operations for read-only queries
    ALLOWED_OPERATIONS = [
        "SELECT",
        "SHOW",
        "DESCRIBE",
        "DESC",
        "EXPLAIN",
        "WITH",  # CTEs
    ]

    def __init__(self):
        """Initialize SQL validator"""
        self.warnings: List[str] = []
        self.errors: List[str] = []

    def validate_query(self, sql: str) -> Dict[str, Any]:
        """
        Validate SQL query structure and safety.

        Args:
            sql: SQL query string

        Returns:
            Dictionary with validation results:
            - valid: bool - Whether query is valid
            - warnings: List[str] - Warnings (non-blocking)
            - errors: List[str] - Errors (blocking)
            - safety_score: float - Safety score (0.0 to 1.0)
            - estimated_cost: Optional[float] - Estimated cost (if available)
        """
        self.warnings = []
        self.errors = []

        if not sql or not sql.strip():
            self.errors.append("Empty SQL query")
            return self._build_response()

        # Normalize SQL
        sql_upper = sql.strip().upper()

        # Check for dangerous operations
        self._check_dangerous_operations(sql_upper)

        # Check for allowed operations
        self._check_allowed_operations(sql_upper)

        # Check syntax basics
        self._check_syntax_basics(sql_upper, sql)

        # Check for potential issues
        self._check_potential_issues(sql_upper, sql)

        # Calculate safety score
        safety_score = self._calculate_safety_score()

        return self._build_response(safety_score=safety_score)

    def _check_dangerous_operations(self, sql_upper: str):
        """Check for dangerous operations"""
        for operation in self.DANGEROUS_OPERATIONS:
            # Use word boundaries to avoid false positives
            pattern = r"\b" + operation + r"\b"
            if re.search(pattern, sql_upper):
                self.errors.append(
                    f"Dangerous operation detected: {operation}. "
                    f"Only SELECT, SHOW, DESCRIBE, and EXPLAIN queries are allowed."
                )
                break

    def _check_allowed_operations(self, sql_upper: str):
        """Check if query starts with allowed operation"""
        starts_with_allowed = False
        for operation in self.ALLOWED_OPERATIONS:
            if sql_upper.startswith(operation):
                starts_with_allowed = True
                break

        # Also check for CTEs (WITH ... SELECT)
        if sql_upper.startswith("WITH"):
            starts_with_allowed = True

        if not starts_with_allowed:
            self.errors.append(
                f"Query must start with one of: {', '.join(self.ALLOWED_OPERATIONS)}"
            )

    def _check_syntax_basics(self, sql_upper: str, sql: str):
        """Check basic SQL syntax"""
        # Check for balanced parentheses
        if sql.count("(") != sql.count(")"):
            self.warnings.append("Unbalanced parentheses detected")

        # Check for balanced quotes (basic check)
        single_quotes = sql.count("'") - sql.count("''")
        if single_quotes % 2 != 0:
            self.warnings.append("Unbalanced single quotes detected")

        # Check for SQL injection patterns (basic)
        sql_injection_patterns = [
            r"--",  # SQL comments
            r"/\*",  # Block comments
            r"';",  # Quote termination
            r"UNION.*SELECT",  # Union-based injection
        ]

        for pattern in sql_injection_patterns:
            if re.search(pattern, sql_upper, re.IGNORECASE):
                self.warnings.append(f"Potential SQL injection pattern detected: {pattern}")

    def _check_potential_issues(self, sql_upper: str, sql: str):
        """Check for potential performance or correctness issues"""
        # Check for SELECT * (might be inefficient)
        if "SELECT *" in sql_upper and "COUNT(*)" not in sql_upper:
            self.warnings.append(
                "SELECT * detected. Consider selecting specific columns for better performance."
            )

        # Check for missing LIMIT in SELECT queries
        if sql_upper.startswith("SELECT") and "LIMIT" not in sql_upper:
            # Allow COUNT queries without LIMIT
            if "COUNT(" not in sql_upper:
                self.warnings.append(
                    "No LIMIT clause detected. Query might return many rows."
                )

        # Check for CROSS JOIN (might be expensive)
        if "CROSS JOIN" in sql_upper:
            self.warnings.append(
                "CROSS JOIN detected. This might be expensive. Consider using INNER JOIN with proper conditions."
            )

        # Check for multiple JOINs without conditions
        join_count = len(re.findall(r"\bJOIN\b", sql_upper))
        where_count = len(re.findall(r"\bWHERE\b", sql_upper))
        if join_count > 3 and where_count == 0:
            self.warnings.append(
                f"Multiple JOINs ({join_count}) without WHERE clause. This might be expensive."
            )

        # Check for subqueries (might be slow)
        subquery_count = sql_upper.count("SELECT") - 1
        if subquery_count > 2:
            self.warnings.append(
                f"Multiple subqueries detected ({subquery_count}). This might be slow. Consider using CTEs or JOINs."
            )

    def _calculate_safety_score(self) -> float:
        """Calculate safety score (0.0 to 1.0)"""
        score = 1.0

        # Penalize for errors (blocking)
        score -= len(self.errors) * 0.5

        # Penalize for warnings (non-blocking but concerning)
        score -= len(self.warnings) * 0.1

        # Ensure score is between 0.0 and 1.0
        return max(0.0, min(1.0, score))

    def _build_response(self, safety_score: Optional[float] = None) -> Dict[str, Any]:
        """Build validation response"""
        if safety_score is None:
            safety_score = self._calculate_safety_score()

        return {
            "valid": len(self.errors) == 0,
            "warnings": self.warnings,
            "errors": self.errors,
            "safety_score": safety_score,
            "estimated_cost": None,  # Can be implemented later with EXPLAIN
        }

    def validate_with_explain(
        self, sql: str, db_connection: Any
    ) -> Dict[str, Any]:
        """
        Validate SQL query using database EXPLAIN (if available).

        Args:
            sql: SQL query string
            db_connection: Database connection object

        Returns:
            Dictionary with validation results including execution plan
        """
        result = self.validate_query(sql)

        if not result["valid"]:
            return result

        # Try to get execution plan using EXPLAIN
        try:
            explain_sql = f"EXPLAIN {sql}"
            # This would execute EXPLAIN on the database
            # For now, we'll just add a note that EXPLAIN validation is available
            result["explain_available"] = True
            result["explain_note"] = "EXPLAIN validation can be implemented with database connection"
        except Exception as e:
            logger.warning(f"Failed to get execution plan: {e}")
            result["explain_available"] = False

        return result

    def estimate_cost(self, sql: str) -> Optional[float]:
        """
        Estimate query execution cost (placeholder for future implementation).

        Args:
            sql: SQL query string

        Returns:
            Estimated cost or None if not available
        """
        # This is a placeholder for cost estimation
        # Can be implemented using Snowflake's query profiler or EXPLAIN output
        return None


# Global validator instance
_sql_validator: Optional[SQLValidator] = None


def get_sql_validator() -> SQLValidator:
    """Get or create global SQL validator instance"""
    global _sql_validator
    if _sql_validator is None:
        _sql_validator = SQLValidator()
    return _sql_validator

