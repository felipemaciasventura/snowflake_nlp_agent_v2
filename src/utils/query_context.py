"""
Query Context System for Enhanced LLM Learning

This module manages query history, successful patterns, and contextual learning
to improve LLM performance over time.
"""

import hashlib
import json
import logging
import re
from collections import Counter, defaultdict
from dataclasses import asdict, dataclass, field
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import pandas as pd

logger = logging.getLogger(__name__)


@dataclass
class QueryPattern:
    """Represents a successful query pattern"""

    user_question: str
    generated_sql: str
    success_score: float
    execution_time: Optional[float] = None
    result_count: Optional[int] = None
    query_type: Optional[str] = None  # SELECT, UPDATE, DELETE, etc.
    tables_used: List[str] = field(default_factory=list)
    columns_used: List[str] = field(default_factory=list)
    functions_used: List[str] = field(default_factory=list)
    patterns_detected: List[str] = field(default_factory=list)
    timestamp: datetime = field(default_factory=datetime.now)


@dataclass
class QueryContext:
    """Context for improving future queries"""

    similar_successful_queries: List[QueryPattern] = field(default_factory=list)
    common_patterns: Dict[str, int] = field(default_factory=dict)
    preferred_functions: Dict[str, int] = field(default_factory=dict)
    table_usage_patterns: Dict[str, List[str]] = field(default_factory=dict)
    domain_vocabulary: Dict[str, int] = field(default_factory=dict)


class QueryContextManager:
    """
    Manages query history and contextual learning for improved SQL generation.

    Features:
    - Query pattern storage and retrieval
    - Success pattern analysis
    - Similar query detection
    - Context-aware suggestions
    - Performance tracking
    """

    def __init__(self, data_dir: str = "data"):
        self.data_dir = Path(data_dir)
        self.data_dir.mkdir(exist_ok=True)

        self.history_file = self.data_dir / "query_history.json"
        self.patterns_file = self.data_dir / "query_patterns.json"
        self.context_file = self.data_dir / "query_context.json"

        self.query_history: List[QueryPattern] = []
        self.successful_patterns: Dict[str, List[QueryPattern]] = defaultdict(list)
        self.load_history()

    def record_query(
        self,
        user_question: str,
        generated_sql: str,
        success: bool,
        execution_time: Optional[float] = None,
        result_count: Optional[int] = None,
        error_message: Optional[str] = None,
    ) -> None:
        """
        Record a query execution for future learning.

        Args:
            user_question: Original user question
            generated_sql: SQL query that was generated
            success: Whether the query executed successfully
            execution_time: Query execution time in seconds
            result_count: Number of results returned
            error_message: Error message if query failed
        """
        try:
            # Calculate success score
            success_score = self._calculate_success_score(
                success, execution_time, result_count, error_message
            )

            # Analyze query
            query_analysis = self._analyze_sql_query(generated_sql)

            # Create pattern
            pattern = QueryPattern(
                user_question=user_question.strip(),
                generated_sql=generated_sql.strip(),
                success_score=success_score,
                execution_time=execution_time,
                result_count=result_count,
                query_type=query_analysis.get("query_type"),
                tables_used=query_analysis.get("tables_used", []),
                columns_used=query_analysis.get("columns_used", []),
                functions_used=query_analysis.get("functions_used", []),
                patterns_detected=query_analysis.get("patterns_detected", []),
            )

            # Store in history
            self.query_history.append(pattern)

            # If successful, add to successful patterns
            if success_score > 0.7:  # Threshold for "successful"
                question_key = self._normalize_question(user_question)
                self.successful_patterns[question_key].append(pattern)

            # Cleanup old entries (keep last 1000 queries)
            if len(self.query_history) > 1000:
                self.query_history = self.query_history[-1000:]

            # Save to disk periodically
            if len(self.query_history) % 10 == 0:  # Every 10 queries
                self.save_history()

            logger.info(f"Recorded query pattern: success_score={success_score:.2f}")

        except Exception as e:
            logger.warning(f"Failed to record query: {e}")

    def get_context_for_question(self, user_question: str) -> QueryContext:
        """
        Get contextual information for a user question to improve SQL generation.

        Args:
            user_question: The user's question

        Returns:
            QueryContext: Context information to enhance LLM prompts
        """
        try:
            context = QueryContext()

            # Find similar successful queries
            context.similar_successful_queries = self._find_similar_queries(
                user_question, limit=5
            )

            # Extract common patterns from successful queries
            context.common_patterns = self._extract_common_patterns()

            # Get preferred functions based on success
            context.preferred_functions = self._get_preferred_functions()

            # Get table usage patterns
            context.table_usage_patterns = self._get_table_usage_patterns()

            # Build domain vocabulary
            context.domain_vocabulary = self._build_domain_vocabulary()

            return context

        except Exception as e:
            logger.warning(f"Failed to get context: {e}")
            return QueryContext()

    def _calculate_success_score(
        self,
        success: bool,
        execution_time: Optional[float],
        result_count: Optional[int],
        error_message: Optional[str],
    ) -> float:
        """Calculate a success score for the query (0.0 to 1.0)"""
        if not success:
            return 0.0

        score = 1.0

        # Penalize very slow queries
        if execution_time:
            if execution_time > 30:  # Very slow
                score -= 0.3
            elif execution_time > 10:  # Moderately slow
                score -= 0.1

        # Consider result usefulness
        if result_count is not None:
            if result_count == 0:  # No results might indicate poor query
                score -= 0.2
            elif result_count > 1000:  # Too many results might be too broad
                score -= 0.1

        return max(0.0, min(1.0, score))

    def _analyze_sql_query(self, sql: str) -> Dict[str, Any]:
        """Analyze SQL query to extract patterns and components"""
        sql_upper = sql.upper()
        analysis = {
            "query_type": None,
            "tables_used": [],
            "columns_used": [],
            "functions_used": [],
            "patterns_detected": [],
        }

        try:
            # Determine query type
            if sql_upper.strip().startswith("SELECT"):
                analysis["query_type"] = "SELECT"
            elif sql_upper.strip().startswith("INSERT"):
                analysis["query_type"] = "INSERT"
            elif sql_upper.strip().startswith("UPDATE"):
                analysis["query_type"] = "UPDATE"
            elif sql_upper.strip().startswith("DELETE"):
                analysis["query_type"] = "DELETE"

            # Extract tables (simple pattern matching)
            from_match = re.search(r"FROM\s+([\w_]+)", sql_upper)
            if from_match:
                analysis["tables_used"].append(from_match.group(1))

            join_matches = re.findall(r"JOIN\s+([\w_]+)", sql_upper)
            analysis["tables_used"].extend(join_matches)

            # Extract common SQL functions
            functions = [
                "COUNT",
                "SUM",
                "AVG",
                "MAX",
                "MIN",
                "GROUP_CONCAT",
                "UPPER",
                "LOWER",
                "SUBSTR",
                "LENGTH",
                "TRIM",
                "DATE",
                "YEAR",
                "MONTH",
                "DAY",
                "NOW",
                "CURRENT_DATE",
                "RANK",
                "ROW_NUMBER",
                "DENSE_RANK",
                "LEAD",
                "LAG",
            ]

            for func in functions:
                if f"{func}(" in sql_upper:
                    analysis["functions_used"].append(func)

            # Detect common patterns
            if "LIMIT" in sql_upper:
                analysis["patterns_detected"].append("uses_limit")
            if "ORDER BY" in sql_upper:
                analysis["patterns_detected"].append("uses_order_by")
            if "GROUP BY" in sql_upper:
                analysis["patterns_detected"].append("uses_group_by")
            if "JOIN" in sql_upper:
                analysis["patterns_detected"].append("uses_joins")
            if "WHERE" in sql_upper:
                analysis["patterns_detected"].append("uses_where")
            if any(agg in sql_upper for agg in ["COUNT", "SUM", "AVG", "MAX", "MIN"]):
                analysis["patterns_detected"].append("uses_aggregation")

        except Exception as e:
            logger.warning(f"Failed to analyze SQL: {e}")

        return analysis

    def _normalize_question(self, question: str) -> str:
        """Normalize question for similarity matching"""
        # Convert to lowercase and remove extra whitespace
        normalized = re.sub(r"\s+", " ", question.lower().strip())

        # Remove common question words for better matching
        stop_words = [
            "what",
            "how",
            "when",
            "where",
            "who",
            "which",
            "show",
            "me",
            "get",
            "find",
        ]
        words = normalized.split()
        filtered_words = [w for w in words if w not in stop_words]

        return " ".join(filtered_words[:10])  # Limit to first 10 meaningful words

    def _find_similar_queries(
        self, user_question: str, limit: int = 5
    ) -> List[QueryPattern]:
        """Find similar successful queries based on question similarity"""
        if not self.successful_patterns:
            return []

        normalized_question = self._normalize_question(user_question)
        similarities = []

        for question_key, patterns in self.successful_patterns.items():
            # Simple similarity based on word overlap
            similarity = self._calculate_text_similarity(
                normalized_question, question_key
            )

            if similarity > 0.3:  # Minimum similarity threshold
                # Get the best pattern for this question
                best_pattern = max(patterns, key=lambda p: p.success_score)
                similarities.append((similarity, best_pattern))

        # Sort by similarity and return top results
        similarities.sort(key=lambda x: x[0], reverse=True)
        return [pattern for _, pattern in similarities[:limit]]

    def _calculate_text_similarity(self, text1: str, text2: str) -> float:
        """Simple text similarity based on word overlap"""
        words1 = set(text1.split())
        words2 = set(text2.split())

        if not words1 or not words2:
            return 0.0

        intersection = len(words1.intersection(words2))
        union = len(words1.union(words2))

        return intersection / union if union > 0 else 0.0

    def _extract_common_patterns(self) -> Dict[str, int]:
        """Extract common patterns from successful queries"""
        pattern_counts = Counter()

        for patterns in self.successful_patterns.values():
            for pattern in patterns:
                if pattern.success_score > 0.8:  # Only high-success patterns
                    for detected_pattern in pattern.patterns_detected:
                        pattern_counts[detected_pattern] += 1

        return dict(pattern_counts.most_common(20))

    def _get_preferred_functions(self) -> Dict[str, int]:
        """Get most successful SQL functions"""
        function_counts = Counter()

        for patterns in self.successful_patterns.values():
            for pattern in patterns:
                if pattern.success_score > 0.8:
                    for function in pattern.functions_used:
                        function_counts[function] += 1

        return dict(function_counts.most_common(15))

    def _get_table_usage_patterns(self) -> Dict[str, List[str]]:
        """Get common table usage patterns"""
        table_patterns = defaultdict(Counter)

        for patterns in self.successful_patterns.values():
            for pattern in patterns:
                if pattern.success_score > 0.8 and len(pattern.tables_used) > 1:
                    # Sort tables to create consistent pattern
                    sorted_tables = sorted(pattern.tables_used)
                    for i, table in enumerate(sorted_tables):
                        for other_table in sorted_tables[i + 1 :]:
                            table_patterns[table][other_table] += 1

        # Convert to lists of most common combinations
        result = {}
        for table, counter in table_patterns.items():
            result[table] = [other_table for other_table, _ in counter.most_common(5)]

        return result

    def _build_domain_vocabulary(self) -> Dict[str, int]:
        """Build domain-specific vocabulary from successful queries"""
        vocab = Counter()

        for patterns in self.successful_patterns.values():
            for pattern in patterns:
                if pattern.success_score > 0.8:
                    # Extract words from user question
                    words = re.findall(r"\b\w{3,}\b", pattern.user_question.lower())
                    for word in words:
                        if word not in [
                            "the",
                            "and",
                            "for",
                            "are",
                            "but",
                            "not",
                            "you",
                            "all",
                        ]:
                            vocab[word] += 1

        return dict(vocab.most_common(50))

    def generate_context_prompt_addition(self, context: QueryContext) -> str:
        """Generate additional context for LLM prompts"""
        if not context.similar_successful_queries:
            return ""

        prompt_parts = ["\n🎯 SUCCESSFUL QUERY EXAMPLES FROM HISTORY:"]

        for i, query in enumerate(context.similar_successful_queries[:3], 1):
            prompt_parts.append(f"\nExample {i}:")
            prompt_parts.append(f"Question: {query.user_question}")
            prompt_parts.append(f"SQL: {query.generated_sql}")
            if query.result_count:
                prompt_parts.append(f"Results: {query.result_count} rows")

        if context.common_patterns:
            prompt_parts.append("\n📊 RECOMMENDED PATTERNS:")
            for pattern, count in list(context.common_patterns.items())[:5]:
                prompt_parts.append(
                    f"    • {pattern} (used {count} times successfully)"
                )

        if context.preferred_functions:
            prompt_parts.append("\n🔧 PREFERRED FUNCTIONS:")
            functions_list = ", ".join(list(context.preferred_functions.keys())[:8])
            prompt_parts.append(f"    • {functions_list}")

        return "\n".join(prompt_parts)

    def save_history(self) -> None:
        """Save query history to disk"""
        try:
            # Save full history
            history_data = [asdict(pattern) for pattern in self.query_history[-100:]]
            for item in history_data:
                item["timestamp"] = item["timestamp"].isoformat()

            with open(self.history_file, "w") as f:
                json.dump(history_data, f, indent=2)

            # Save successful patterns summary
            patterns_summary = {}
            for key, patterns in self.successful_patterns.items():
                if patterns:  # Only save if there are patterns
                    best_pattern = max(patterns, key=lambda p: p.success_score)
                    patterns_summary[key] = {
                        "user_question": best_pattern.user_question,
                        "generated_sql": best_pattern.generated_sql,
                        "success_score": best_pattern.success_score,
                        "usage_count": len(patterns),
                    }

            with open(self.patterns_file, "w") as f:
                json.dump(patterns_summary, f, indent=2)

            logger.info(f"Saved {len(self.query_history)} query patterns")

        except Exception as e:
            logger.warning(f"Failed to save query history: {e}")

    def load_history(self) -> None:
        """Load query history from disk"""
        try:
            if self.history_file.exists():
                with open(self.history_file, "r") as f:
                    history_data = json.load(f)

                self.query_history = []
                for item in history_data:
                    item["timestamp"] = datetime.fromisoformat(item["timestamp"])
                    pattern = QueryPattern(**item)
                    self.query_history.append(pattern)

                    # Rebuild successful patterns
                    if pattern.success_score > 0.7:
                        question_key = self._normalize_question(pattern.user_question)
                        self.successful_patterns[question_key].append(pattern)

                logger.info(f"Loaded {len(self.query_history)} query patterns")

        except Exception as e:
            logger.warning(f"Failed to load query history: {e}")

    def get_statistics(self) -> Dict[str, Any]:
        """Get query statistics for monitoring"""
        if not self.query_history:
            return {}

        total_queries = len(self.query_history)
        successful_queries = sum(1 for q in self.query_history if q.success_score > 0.7)

        # Recent performance (last 50 queries)
        recent_queries = self.query_history[-50:]
        recent_success_rate = sum(
            1 for q in recent_queries if q.success_score > 0.7
        ) / len(recent_queries)

        avg_execution_time = None
        if any(q.execution_time for q in recent_queries):
            times = [q.execution_time for q in recent_queries if q.execution_time]
            avg_execution_time = sum(times) / len(times)

        return {
            "total_queries": total_queries,
            "successful_queries": successful_queries,
            "success_rate": successful_queries / total_queries,
            "recent_success_rate": recent_success_rate,
            "avg_execution_time": avg_execution_time,
            "unique_question_patterns": len(self.successful_patterns),
            "most_common_patterns": dict(
                Counter(
                    [
                        pattern
                        for patterns in self.successful_patterns.values()
                        for pattern in patterns
                        for detected in pattern.patterns_detected
                    ]
                ).most_common(5)
            ),
        }


# Global instance
query_context_manager = QueryContextManager()
