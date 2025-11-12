"""
Confidence Scorer - Calculate confidence score for generated SQL queries
"""

import logging
import re
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


class ConfidenceScorer:
    """Calculate confidence score for generated SQL queries"""

    def __init__(self):
        """Initialize confidence scorer"""
        pass

    def calculate_confidence(
        self,
        sql: str,
        user_question: Optional[str] = None,
        context: Optional[Dict] = None,
        validation_result: Optional[Dict] = None,
    ) -> Dict[str, Any]:
        """
        Calculate confidence score for generated SQL query.

        Args:
            sql: SQL query string
            user_question: Original user question
            context: Context information (schema, tables, etc.)
            validation_result: Result from SQL validator

        Returns:
            Dictionary with confidence scores:
            - overall: float - Overall confidence (0.0 to 1.0)
            - syntax: float - Syntax confidence
            - semantic: float - Semantic confidence
            - context_match: float - Context match confidence
            - table_validation: float - Table validation confidence
            - warnings: List[str] - Confidence warnings
        """
        scores = {
            "syntax": self._calculate_syntax_confidence(sql),
            "semantic": self._calculate_semantic_confidence(sql, user_question),
            "context_match": self._calculate_context_match_confidence(
                sql, context
            ),
            "table_validation": self._calculate_table_validation_confidence(
                sql, context
            ),
        }

        # Get warnings from validation if available
        warnings = []
        if validation_result:
            warnings.extend(validation_result.get("warnings", []))
            if validation_result.get("errors"):
                warnings.extend(validation_result.get("errors", []))

        # Calculate overall confidence (weighted average)
        overall = (
            scores["syntax"] * 0.3
            + scores["semantic"] * 0.3
            + scores["context_match"] * 0.2
            + scores["table_validation"] * 0.2
        )

        # Penalize for warnings
        if warnings:
            overall -= len(warnings) * 0.05

        # Ensure overall is between 0.0 and 1.0
        overall = max(0.0, min(1.0, overall))

        return {
            "overall": round(overall, 2),
            "syntax": round(scores["syntax"], 2),
            "semantic": round(scores["semantic"], 2),
            "context_match": round(scores["context_match"], 2),
            "table_validation": round(scores["table_validation"], 2),
            "warnings": warnings,
        }

    def _calculate_syntax_confidence(self, sql: str) -> float:
        """Calculate syntax confidence (0.0 to 1.0)"""
        score = 1.0

        if not sql or not sql.strip():
            return 0.0

        sql_upper = sql.strip().upper()

        # Check for balanced parentheses
        if sql.count("(") != sql.count(")"):
            score -= 0.3

        # Check for balanced quotes
        single_quotes = sql.count("'") - sql.count("''")
        if single_quotes % 2 != 0:
            score -= 0.2

        # Check for valid SQL keywords
        valid_keywords = ["SELECT", "FROM", "WHERE", "JOIN", "GROUP", "ORDER", "LIMIT"]
        has_valid_keywords = any(keyword in sql_upper for keyword in valid_keywords)
        if not has_valid_keywords:
            score -= 0.5

        # Check for SQL injection patterns
        sql_injection_patterns = [
            r"--",  # SQL comments
            r"/\*",  # Block comments
            r"';",  # Quote termination
        ]
        for pattern in sql_injection_patterns:
            if re.search(pattern, sql_upper):
                score -= 0.2

        return max(0.0, min(1.0, score))

    def _calculate_semantic_confidence(
        self, sql: str, user_question: Optional[str] = None
    ) -> float:
        """Calculate semantic confidence (0.0 to 1.0)"""
        score = 1.0

        if not user_question:
            return 0.7  # Default if no user question

        sql_upper = sql.strip().upper()
        user_lower = user_question.lower()

        # Check if query type matches user intent
        # Count queries
        if "count" in user_lower or "how many" in user_lower:
            if "COUNT(" not in sql_upper:
                score -= 0.3
            else:
                score += 0.1

        # Top N queries
        if "top" in user_lower or "highest" in user_lower or "most" in user_lower:
            if "ORDER BY" not in sql_upper or "DESC" not in sql_upper:
                score -= 0.2
            if "LIMIT" not in sql_upper:
                score -= 0.1

        # Average queries
        if "average" in user_lower or "avg" in user_lower:
            if "AVG(" not in sql_upper:
                score -= 0.3

        # Sum queries
        if "sum" in user_lower or "total" in user_lower:
            if "SUM(" not in sql_upper:
                score -= 0.3

        # Time-based queries
        if any(
            word in user_lower
            for word in ["date", "time", "month", "year", "day", "week"]
        ):
            if "DATE" not in sql_upper and "TIME" not in sql_upper:
                score -= 0.2

        return max(0.0, min(1.0, score))

    def _calculate_context_match_confidence(
        self, sql: str, context: Optional[Dict] = None
    ) -> float:
        """Calculate context match confidence (0.0 to 1.0)"""
        if not context:
            return 0.5  # Default if no context

        score = 1.0
        sql_upper = sql.strip().upper()

        # Check if tables in SQL match context tables
        available_tables = context.get("tables", [])
        if available_tables:
            # Extract tables from SQL
            sql_tables = self._extract_tables_from_sql(sql_upper)
            
            # Check if SQL tables are in context
            for table in sql_tables:
                if table.upper() not in [t.upper() for t in available_tables]:
                    score -= 0.2

        return max(0.0, min(1.0, score))

    def _calculate_table_validation_confidence(
        self, sql: str, context: Optional[Dict] = None
    ) -> float:
        """Calculate table validation confidence (0.0 to 1.0)"""
        if not context:
            return 0.5  # Default if no context

        score = 1.0
        sql_upper = sql.strip().upper()

        # Extract tables from SQL
        sql_tables = self._extract_tables_from_sql(sql_upper)

        # Check if tables exist in context
        available_tables = context.get("tables", [])
        if available_tables:
            for table in sql_tables:
                table_upper = table.upper()
                available_upper = [t.upper() for t in available_tables]
                if table_upper not in available_upper:
                    score -= 0.3
                    # Check for similar table names
                    similar = self._find_similar_table_names(table, available_tables)
                    if similar:
                        score += 0.1  # Slight boost if similar name found

        return max(0.0, min(1.0, score))

    def _extract_tables_from_sql(self, sql_upper: str) -> List[str]:
        """Extract table names from SQL"""
        tables = []

        # FROM clause
        from_match = re.search(r"\bFROM\s+(\w+)", sql_upper)
        if from_match:
            tables.append(from_match.group(1))

        # JOINs
        join_matches = re.finditer(r"\bJOIN\s+(\w+)", sql_upper)
        for match in join_matches:
            tables.append(match.group(1))

        return tables

    def _find_similar_table_names(
        self, table_name: str, available_tables: List[str]
    ) -> List[str]:
        """Find similar table names"""
        similar = []
        table_lower = table_name.lower()

        for available_table in available_tables:
            available_lower = available_table.lower()
            # Simple similarity check
            if table_lower in available_lower or available_lower in table_lower:
                similar.append(available_table)

        return similar


# Global confidence scorer instance
_confidence_scorer: Optional[ConfidenceScorer] = None


def get_confidence_scorer() -> ConfidenceScorer:
    """Get or create global confidence scorer instance"""
    global _confidence_scorer
    if _confidence_scorer is None:
        _confidence_scorer = ConfidenceScorer()
    return _confidence_scorer



