"""
Query Corrector - Suggest corrections for failed queries
"""

import logging
import re
from typing import Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)


class QueryCorrector:
    """Suggest corrections for failed queries"""

    # Common error patterns and fixes
    ERROR_PATTERNS = {
        "table.*not found": {
            "pattern": r"table\s+['\"]?(\w+)['\"]?\s+not found",
            "fix": "check_table_name",
            "suggestion": "Table name might be case-sensitive or doesn't exist. Check available tables.",
        },
        "column.*not found": {
            "pattern": r"column\s+['\"]?(\w+)['\"]?\s+not found",
            "fix": "check_column_name",
            "suggestion": "Column name might be incorrect. Check available columns.",
        },
        "syntax error": {
            "pattern": r"syntax error",
            "fix": "check_syntax",
            "suggestion": "SQL syntax error detected. Check parentheses, quotes, and keywords.",
        },
        "invalid identifier": {
            "pattern": r"invalid.*identifier",
            "fix": "check_identifier",
            "suggestion": "Invalid identifier. Check table/column names are correct.",
        },
    }

    def __init__(self):
        """Initialize query corrector"""
        pass

    def suggest_corrections(
        self, sql: str, error: str, schema: Optional[Dict] = None
    ) -> List[Dict[str, str]]:
        """
        Suggest query corrections based on error.

        Args:
            sql: Original SQL query
            error: Error message from database
            schema: Database schema information (optional)

        Returns:
            List of correction suggestions with:
            - original: Original problematic part
            - corrected: Suggested correction
            - reason: Explanation of the fix
            - confidence: Confidence level (0.0 to 1.0)
        """
        suggestions = []

        error_upper = error.upper()
        sql_upper = sql.upper()

        # Check for common error patterns
        for error_type, error_info in self.ERROR_PATTERNS.items():
            if re.search(error_info["pattern"], error_upper, re.IGNORECASE):
                fix_func = getattr(self, f"_fix_{error_info['fix']}", None)
                if fix_func:
                    corrections = fix_func(sql, error, schema)
                    suggestions.extend(corrections)
                else:
                    suggestions.append(
                        {
                            "original": sql,
                            "corrected": sql,
                            "reason": error_info["suggestion"],
                            "confidence": 0.5,
                        }
                    )

        # General corrections
        general_corrections = self._suggest_general_corrections(sql, error, schema)
        suggestions.extend(general_corrections)

        # Remove duplicates and sort by confidence
        suggestions = self._deduplicate_suggestions(suggestions)
        suggestions.sort(key=lambda x: x.get("confidence", 0.0), reverse=True)

        return suggestions[:5]  # Return top 5 suggestions

    def _fix_check_table_name(
        self, sql: str, error: str, schema: Optional[Dict] = None
    ) -> List[Dict[str, str]]:
        """Fix table name issues"""
        suggestions = []

        # Extract table name from error
        table_match = re.search(r"table\s+['\"]?(\w+)['\"]?\s+not found", error, re.IGNORECASE)
        if table_match:
            invalid_table = table_match.group(1)
            
            # Try uppercase
            corrected_sql = re.sub(
                rf"\b{re.escape(invalid_table)}\b",
                invalid_table.upper(),
                sql,
                flags=re.IGNORECASE,
            )
            if corrected_sql != sql:
                suggestions.append(
                    {
                        "original": invalid_table,
                        "corrected": invalid_table.upper(),
                        "reason": f"Table names in Snowflake are case-sensitive. Try uppercase: {invalid_table.upper()}",
                        "confidence": 0.7,
                    }
                )

            # Try to find similar table names
            if schema and "tables" in schema:
                similar_tables = self._find_similar_names(
                    invalid_table, schema["tables"]
                )
                for similar_table in similar_tables[:3]:
                    corrected_sql = re.sub(
                        rf"\b{re.escape(invalid_table)}\b",
                        similar_table,
                        sql,
                        flags=re.IGNORECASE,
                    )
                    suggestions.append(
                        {
                            "original": invalid_table,
                            "corrected": similar_table,
                            "reason": f"Similar table found: {similar_table}",
                            "confidence": 0.6,
                        }
                    )

        return suggestions

    def _fix_check_column_name(
        self, sql: str, error: str, schema: Optional[Dict] = None
    ) -> List[Dict[str, str]]:
        """Fix column name issues"""
        suggestions = []

        # Extract column name from error
        column_match = re.search(
            r"column\s+['\"]?(\w+)['\"]?\s+not found", error, re.IGNORECASE
        )
        if column_match:
            invalid_column = column_match.group(1)
            
            # Try uppercase
            corrected_sql = re.sub(
                rf"\b{re.escape(invalid_column)}\b",
                invalid_column.upper(),
                sql,
                flags=re.IGNORECASE,
            )
            if corrected_sql != sql:
                suggestions.append(
                    {
                        "original": invalid_column,
                        "corrected": invalid_column.upper(),
                        "reason": f"Column names in Snowflake are case-sensitive. Try uppercase: {invalid_column.upper()}",
                        "confidence": 0.7,
                    }
                )

        return suggestions

    def _fix_check_syntax(
        self, sql: str, error: str, schema: Optional[Dict] = None
    ) -> List[Dict[str, str]]:
        """Fix syntax issues"""
        suggestions = []

        # Check for unbalanced parentheses
        if sql.count("(") != sql.count(")"):
            # Try to add missing closing parenthesis
            open_count = sql.count("(")
            close_count = sql.count(")")
            if open_count > close_count:
                missing = open_count - close_count
                corrected_sql = sql + ")" * missing
                suggestions.append(
                    {
                        "original": sql,
                        "corrected": corrected_sql,
                        "reason": f"Added {missing} missing closing parentheses",
                        "confidence": 0.6,
                    }
                )

        # Check for common syntax errors
        # Missing comma in SELECT
        if re.search(r"SELECT\s+\w+\s+\w+\s+FROM", sql, re.IGNORECASE):
            corrected_sql = re.sub(
                r"SELECT\s+(\w+)\s+(\w+)\s+FROM",
                r"SELECT \1, \2 FROM",
                sql,
                flags=re.IGNORECASE,
            )
            if corrected_sql != sql:
                suggestions.append(
                    {
                        "original": sql,
                        "corrected": corrected_sql,
                        "reason": "Added missing comma in SELECT clause",
                        "confidence": 0.5,
                    }
                )

        return suggestions

    def _fix_check_identifier(
        self, sql: str, error: str, schema: Optional[Dict] = None
    ) -> List[Dict[str, str]]:
        """Fix identifier issues"""
        suggestions = []

        # Try uppercase for identifiers
        sql_upper = sql.upper()
        # This is a simple fix - in practice, would need more sophisticated parsing
        suggestions.append(
            {
                "original": sql,
                "corrected": sql_upper,
                "reason": "Try uppercase for all identifiers (tables, columns)",
                "confidence": 0.4,
            }
        )

        return suggestions

    def _suggest_general_corrections(
        self, sql: str, error: str, schema: Optional[Dict] = None
    ) -> List[Dict[str, str]]:
        """Suggest general corrections"""
        suggestions = []

        # Check for common mistakes
        sql_upper = sql.upper()

        # Missing FROM clause
        if "SELECT" in sql_upper and "FROM" not in sql_upper:
            suggestions.append(
                {
                    "original": sql,
                    "corrected": sql + " FROM <table_name>",
                    "reason": "Missing FROM clause. Add FROM <table_name>",
                    "confidence": 0.8,
                }
            )

        # Missing WHERE condition
        if "JOIN" in sql_upper and "WHERE" not in sql_upper and "ON" not in sql_upper:
            suggestions.append(
                {
                    "original": sql,
                    "corrected": sql + " ON <condition>",
                    "reason": "JOIN without ON condition. Add ON <condition>",
                    "confidence": 0.7,
                }
            )

        return suggestions

    def _find_similar_names(self, name: str, available_names: List[str]) -> List[str]:
        """Find similar names using simple string matching"""
        similar = []
        name_lower = name.lower()

        for available_name in available_names:
            available_lower = available_name.lower()
            # Simple similarity: contains or is contained
            if name_lower in available_lower or available_lower in name_lower:
                similar.append(available_name)
            # Check for common prefixes/suffixes
            elif (
                name_lower[:-1] in available_lower
                or available_lower[:-1] in name_lower
            ):
                similar.append(available_name)

        return similar

    def _deduplicate_suggestions(
        self, suggestions: List[Dict[str, str]]
    ) -> List[Dict[str, str]]:
        """Remove duplicate suggestions"""
        seen = set()
        unique = []

        for suggestion in suggestions:
            key = (
                suggestion.get("original", ""),
                suggestion.get("corrected", ""),
            )
            if key not in seen:
                seen.add(key)
                unique.append(suggestion)

        return unique

    def auto_correct(self, sql: str, error: str) -> Optional[str]:
        """
        Attempt automatic correction (simple cases).

        Args:
            sql: Original SQL query
            error: Error message

        Returns:
            Corrected SQL or None if auto-correction not possible
        """
        suggestions = self.suggest_corrections(sql, error)

        # Return highest confidence suggestion if confidence > 0.7
        if suggestions and suggestions[0].get("confidence", 0.0) > 0.7:
            return suggestions[0].get("corrected")

        return None


# Global corrector instance
_query_corrector: Optional[QueryCorrector] = None


def get_query_corrector() -> QueryCorrector:
    """Get or create global query corrector instance"""
    global _query_corrector
    if _query_corrector is None:
        _query_corrector = QueryCorrector()
    return _query_corrector




