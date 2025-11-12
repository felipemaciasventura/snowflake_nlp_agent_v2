"""
Saved Queries - Manage saved queries for reuse
"""

import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


class SavedQuery:
    """Represents a saved query"""

    def __init__(
        self,
        name: str,
        sql: str,
        description: str,
        user_question: Optional[str] = None,
        category: str = "general",
        tags: Optional[List[str]] = None,
        created_at: Optional[str] = None,
        last_used: Optional[str] = None,
        use_count: int = 0,
        parameters: Optional[Dict[str, Any]] = None,
    ):
        """
        Initialize saved query.

        Args:
            name: Query name
            sql: SQL query string
            description: Query description
            user_question: Original natural language question
            category: Query category
            tags: Optional tags
            created_at: Creation timestamp (ISO format)
            last_used: Last usage timestamp (ISO format)
            use_count: Number of times used
            parameters: Optional parameters for parameterized queries
        """
        self.name = name
        self.sql = sql
        self.description = description
        self.user_question = user_question
        self.category = category
        self.tags = tags or []
        self.created_at = created_at or datetime.now().isoformat()
        self.last_used = last_used
        self.use_count = use_count
        self.parameters = parameters or {}

    def to_dict(self) -> Dict[str, Any]:
        """Convert saved query to dictionary"""
        return {
            "name": self.name,
            "sql": self.sql,
            "description": self.description,
            "user_question": self.user_question,
            "category": self.category,
            "tags": self.tags,
            "created_at": self.created_at,
            "last_used": self.last_used,
            "use_count": self.use_count,
            "parameters": self.parameters,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "SavedQuery":
        """Create saved query from dictionary"""
        return cls(
            name=data["name"],
            sql=data["sql"],
            description=data["description"],
            user_question=data.get("user_question"),
            category=data.get("category", "general"),
            tags=data.get("tags", []),
            created_at=data.get("created_at"),
            last_used=data.get("last_used"),
            use_count=data.get("use_count", 0),
            parameters=data.get("parameters", {}),
        )

    def fill_parameters(self, params: Dict[str, Any]) -> str:
        """
        Fill parameterized query with values.

        Args:
            params: Parameter values

        Returns:
            Filled SQL query
        """
        sql = self.sql
        for key, value in params.items():
            # Replace {parameter} placeholders
            sql = sql.replace(f"{{{key}}}", str(value))
        return sql

    def record_usage(self):
        """Record that this query was used"""
        self.last_used = datetime.now().isoformat()
        self.use_count += 1


class SavedQueryManager:
    """Manage saved queries"""

    def __init__(self, data_dir: str = "data"):
        """
        Initialize saved query manager.

        Args:
            data_dir: Directory to store saved queries
        """
        self.data_dir = Path(data_dir)
        self.data_dir.mkdir(parents=True, exist_ok=True)
        self.saved_queries_file = self.data_dir / "saved_queries.json"
        self.saved_queries: Dict[str, SavedQuery] = {}
        self._load_queries()

    def _load_queries(self):
        """Load saved queries from file"""
        try:
            if self.saved_queries_file.exists():
                with open(self.saved_queries_file, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    for query_data in data.get("queries", []):
                        query = SavedQuery.from_dict(query_data)
                        self.saved_queries[query.name] = query
                    logger.info(
                        f"Loaded {len(self.saved_queries)} saved queries from file"
                    )
        except Exception as e:
            logger.warning(f"Failed to load saved queries: {e}")
            self.saved_queries = {}

    def _save_queries(self):
        """Save saved queries to file"""
        try:
            queries_data = {
                "queries": [q.to_dict() for q in self.saved_queries.values()]
            }
            with open(self.saved_queries_file, "w", encoding="utf-8") as f:
                json.dump(queries_data, f, indent=2)
            logger.debug(f"Saved {len(self.saved_queries)} queries to file")
        except Exception as e:
            logger.warning(f"Failed to save saved queries: {e}")

    def save_query(
        self,
        name: str,
        sql: str,
        description: str,
        user_question: Optional[str] = None,
        category: str = "general",
        tags: Optional[List[str]] = None,
        parameters: Optional[Dict[str, Any]] = None,
    ) -> SavedQuery:
        """
        Save a query.

        Args:
            name: Query name (must be unique)
            sql: SQL query string
            description: Query description
            user_question: Original natural language question
            category: Query category
            tags: Optional tags
            parameters: Optional parameters for parameterized queries

        Returns:
            Saved query object
        """
        # Check if name already exists
        if name in self.saved_queries:
            raise ValueError(f"Query with name '{name}' already exists")

        query = SavedQuery(
            name=name,
            sql=sql,
            description=description,
            user_question=user_question,
            category=category,
            tags=tags,
            parameters=parameters,
        )

        self.saved_queries[name] = query
        self._save_queries()
        logger.info(f"Saved query: {name}")
        return query

    def get_query(self, name: str) -> Optional[SavedQuery]:
        """Get saved query by name"""
        return self.saved_queries.get(name)

    def get_queries(
        self,
        category: Optional[str] = None,
        tag: Optional[str] = None,
        search: Optional[str] = None,
    ) -> List[SavedQuery]:
        """
        Get saved queries with optional filtering.

        Args:
            category: Filter by category
            tag: Filter by tag
            search: Search in name, description, or SQL

        Returns:
            List of matching queries
        """
        queries = list(self.saved_queries.values())

        if category:
            queries = [q for q in queries if q.category == category]

        if tag:
            queries = [q for q in queries if tag in q.tags]

        if search:
            search_lower = search.lower()
            queries = [
                q
                for q in queries
                if search_lower in q.name.lower()
                or search_lower in q.description.lower()
                or search_lower in q.sql.lower()
            ]

        # Sort by last_used (most recent first) or use_count (most used first)
        queries.sort(
            key=lambda q: (
                q.last_used or "1900-01-01",
                q.use_count,
            ),
            reverse=True,
        )

        return queries

    def delete_query(self, name: str) -> bool:
        """Delete a saved query"""
        if name in self.saved_queries:
            del self.saved_queries[name]
            self._save_queries()
            logger.info(f"Deleted query: {name}")
            return True
        return False

    def update_query(self, name: str, **kwargs) -> bool:
        """Update a saved query"""
        if name not in self.saved_queries:
            return False

        query = self.saved_queries[name]
        for key, value in kwargs.items():
            if hasattr(query, key):
                setattr(query, key, value)

        self._save_queries()
        logger.info(f"Updated query: {name}")
        return True

    def run_query(
        self, name: str, params: Optional[Dict[str, Any]] = None
    ) -> Optional[str]:
        """
        Get SQL for a saved query with optional parameters.

        Args:
            name: Query name
            params: Optional parameters to fill

        Returns:
            SQL query string or None if not found
        """
        query = self.get_query(name)
        if not query:
            return None

        # Record usage
        query.record_usage()
        self._save_queries()

        # Fill parameters if provided
        if params:
            return query.fill_parameters(params)
        return query.sql

    def get_categories(self) -> List[str]:
        """Get all query categories"""
        return sorted(set(q.category for q in self.saved_queries.values()))

    def get_tags(self) -> List[str]:
        """Get all query tags"""
        tags = set()
        for query in self.saved_queries.values():
            tags.update(query.tags)
        return sorted(list(tags))

    def get_statistics(self) -> Dict[str, Any]:
        """Get statistics about saved queries"""
        return {
            "total_queries": len(self.saved_queries),
            "categories": len(self.get_categories()),
            "tags": len(self.get_tags()),
            "most_used": sorted(
                self.saved_queries.values(),
                key=lambda q: q.use_count,
                reverse=True,
            )[:5],
            "recently_used": sorted(
                [
                    q
                    for q in self.saved_queries.values()
                    if q.last_used is not None
                ],
                key=lambda q: q.last_used,
                reverse=True,
            )[:5],
        }


# Global saved query manager instance
_saved_query_manager: Optional[SavedQueryManager] = None


def get_saved_query_manager() -> SavedQueryManager:
    """Get or create global saved query manager instance"""
    global _saved_query_manager
    if _saved_query_manager is None:
        _saved_query_manager = SavedQueryManager()
    return _saved_query_manager



