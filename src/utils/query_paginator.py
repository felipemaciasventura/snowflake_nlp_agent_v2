"""
Query Result Paginator - Paginate large query results for better performance
"""

import logging
import math
import re
from typing import Any, Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)


class QueryPaginator:
    """Paginate query results for improved performance and UX"""

    def __init__(self, default_page_size: int = 100):
        """
        Initialize query paginator.

        Args:
            default_page_size: Default number of rows per page
        """
        self.default_page_size = default_page_size

    def paginate_sql(
        self, sql: str, page: int = 1, page_size: Optional[int] = None
    ) -> Tuple[str, str]:
        """
        Modify SQL query to include pagination (LIMIT and OFFSET).

        Args:
            sql: Original SQL query
            page: Page number (1-based)
            page_size: Number of rows per page (uses default if None)

        Returns:
            Tuple of (paginated_sql, count_sql)
        """
        if page_size is None:
            page_size = self.default_page_size

        # Normalize SQL
        sql_clean = sql.strip()

        # Calculate offset
        offset = (page - 1) * page_size

        # Check if query already has LIMIT/OFFSET
        sql_upper = sql_clean.upper()
        has_limit = "LIMIT" in sql_upper
        has_offset = "OFFSET" in sql_upper

        if has_limit or has_offset:
            # Remove existing LIMIT and OFFSET
            # Use regex to remove LIMIT and OFFSET clauses
            sql_clean = re.sub(
                r"\s+LIMIT\s+\d+(\s+OFFSET\s+\d+)?\s*$",
                "",
                sql_clean,
                flags=re.IGNORECASE,
            )
            sql_clean = re.sub(
                r"\s+OFFSET\s+\d+\s*$",
                "",
                sql_clean,
                flags=re.IGNORECASE,
            )

        # Add pagination
        paginated_sql = f"{sql_clean} LIMIT {page_size} OFFSET {offset}"

        # Generate count query (wrap original query in subquery)
        # Remove any existing ORDER BY for count query (not needed for counting)
        count_sql_clean = re.sub(
            r"\s+ORDER\s+BY\s+[^;]+",
            "",
            sql_clean,
            flags=re.IGNORECASE,
        )

        # Generate count query
        count_sql = f"SELECT COUNT(*) as total_count FROM ({count_sql_clean}) AS paginated_query"

        return paginated_sql, count_sql

    def paginate_results(
        self,
        sql: str,
        results: List[Any],
        total_count: Optional[int] = None,
        page: int = 1,
        page_size: Optional[int] = None,
    ) -> Dict[str, Any]:
        """
        Create paginated result structure.

        Args:
            sql: Original SQL query
            results: Query results (already paginated)
            total_count: Total number of rows (if available)
            page: Current page number
            page_size: Number of rows per page

        Returns:
            Dictionary with paginated results and metadata
        """
        if page_size is None:
            page_size = self.default_page_size

        if total_count is None:
            # If total_count not provided, use length of results as estimate
            total_count = len(results)
            # If we got a full page, there might be more results
            if len(results) == page_size:
                total_count = page * page_size + 1  # Estimate: at least one more

        total_pages = math.ceil(total_count / page_size) if total_count > 0 else 1

        return {
            "data": results,
            "pagination": {
                "page": page,
                "page_size": page_size,
                "total_count": total_count,
                "total_pages": total_pages,
                "has_next": page < total_pages,
                "has_previous": page > 1,
                "start_index": (page - 1) * page_size + 1,
                "end_index": min(page * page_size, total_count),
            },
        }

    def should_paginate(self, result_count: int, threshold: Optional[int] = None) -> bool:
        """
        Determine if results should be paginated.

        Args:
            result_count: Number of results
            threshold: Threshold for pagination (uses default_page_size if None)

        Returns:
            True if results should be paginated
        """
        if threshold is None:
            threshold = self.default_page_size
        return result_count > threshold

    @staticmethod
    def extract_count_from_result(result: Any) -> Optional[int]:
        """
        Extract total count from count query result.

        Args:
            result: Result from count query

        Returns:
            Total count or None if not found
        """
        try:
            if isinstance(result, dict):
                if "data" in result:
                    data = result["data"]
                    if data and len(data) > 0:
                        if isinstance(data[0], (list, tuple)):
                            return int(data[0][0])
                        elif isinstance(data[0], dict):
                            # Try common count column names
                            for key in ["total_count", "count", "COUNT", "TOTAL_COUNT"]:
                                if key in data[0]:
                                    return int(data[0][key])
            elif isinstance(result, list):
                if result and len(result) > 0:
                    if isinstance(result[0], (list, tuple)):
                        return int(result[0][0])
                    elif isinstance(result[0], dict):
                        for key in ["total_count", "count", "COUNT", "TOTAL_COUNT"]:
                            if key in result[0]:
                                return int(result[0][key])
        except (ValueError, TypeError, IndexError) as e:
            logger.warning(f"Failed to extract count from result: {e}")
            return None

        return None



