"""
Query Templates - Manage reusable query templates
"""

import json
import logging
import re
from pathlib import Path
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


class QueryTemplate:
    """Represents a query template with parameters"""

    def __init__(
        self,
        name: str,
        description: str,
        template: str,
        parameters: List[str],
        category: str = "general",
        tags: Optional[List[str]] = None,
    ):
        """
        Initialize query template.

        Args:
            name: Template name
            description: Template description
            template: SQL template with {parameter} placeholders
            parameters: List of parameter names
            category: Template category (e.g., "analytics", "reporting")
            tags: Optional tags for categorization
        """
        self.name = name
        self.description = description
        self.template = template
        self.parameters = parameters
        self.category = category
        self.tags = tags or []

    def fill(self, params: Dict[str, Any]) -> str:
        """
        Fill template with parameters.

        Args:
            params: Dictionary of parameter values

        Returns:
            Filled SQL query
        """
        # Validate all required parameters are provided
        missing_params = set(self.parameters) - set(params.keys())
        if missing_params:
            raise ValueError(
                f"Missing required parameters: {', '.join(missing_params)}"
            )

        # Fill template
        try:
            return self.template.format(**params)
        except KeyError as e:
            raise ValueError(f"Invalid parameter: {e}")

    def to_dict(self) -> Dict[str, Any]:
        """Convert template to dictionary"""
        return {
            "name": self.name,
            "description": self.description,
            "template": self.template,
            "parameters": self.parameters,
            "category": self.category,
            "tags": self.tags,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "QueryTemplate":
        """Create template from dictionary"""
        return cls(
            name=data["name"],
            description=data["description"],
            template=data["template"],
            parameters=data["parameters"],
            category=data.get("category", "general"),
            tags=data.get("tags", []),
        )


class QueryTemplateManager:
    """Manage query templates"""

    def __init__(self, templates_dir: str = "data/templates"):
        """
        Initialize template manager.

        Args:
            templates_dir: Directory to store templates
        """
        self.templates_dir = Path(templates_dir)
        self.templates_dir.mkdir(parents=True, exist_ok=True)
        self.templates_file = self.templates_dir / "query_templates.json"
        self.templates: Dict[str, QueryTemplate] = {}
        self._load_templates()
        self._load_default_templates()

    def _load_default_templates(self):
        """Load default query templates"""
        default_templates = [
            {
                "name": "Top N by Metric",
                "description": "Get top N items by a metric (e.g., price, count)",
                "template": "SELECT * FROM {table} ORDER BY {metric} DESC LIMIT {n}",
                "parameters": ["table", "metric", "n"],
                "category": "analytics",
                "tags": ["top", "ranking", "analytics"],
            },
            {
                "name": "Time Series Analysis",
                "description": "Analyze data over time with grouping",
                "template": "SELECT DATE_TRUNC('{granularity}', {date_column}) as date, SUM({metric}) as total FROM {table} WHERE {date_column} >= '{start_date}' AND {date_column} <= '{end_date}' GROUP BY date ORDER BY date",
                "parameters": ["granularity", "date_column", "metric", "table", "start_date", "end_date"],
                "category": "analytics",
                "tags": ["time-series", "analytics", "trends"],
            },
            {
                "name": "Count by Category",
                "description": "Count records grouped by a category column",
                "template": "SELECT {category_column}, COUNT(*) as count FROM {table} GROUP BY {category_column} ORDER BY count DESC",
                "parameters": ["category_column", "table"],
                "category": "reporting",
                "tags": ["count", "grouping", "reporting"],
            },
            {
                "name": "Average by Category",
                "description": "Calculate average of a metric grouped by category",
                "template": "SELECT {category_column}, AVG({metric_column}) as average FROM {table} GROUP BY {category_column} ORDER BY average DESC",
                "parameters": ["category_column", "metric_column", "table"],
                "category": "analytics",
                "tags": ["average", "grouping", "analytics"],
            },
            {
                "name": "Filtered Search",
                "description": "Search with multiple filters",
                "template": "SELECT * FROM {table} WHERE {conditions} ORDER BY {order_by} LIMIT {limit}",
                "parameters": ["table", "conditions", "order_by", "limit"],
                "category": "search",
                "tags": ["filter", "search"],
            },
            {
                "name": "Join Tables",
                "description": "Join two tables with a common key",
                "template": "SELECT {columns} FROM {table1} {join_type} JOIN {table2} ON {table1}.{key1} = {table2}.{key2}",
                "parameters": ["columns", "table1", "table2", "join_type", "key1", "key2"],
                "category": "analytics",
                "tags": ["join", "relationships"],
            },
        ]

        # Add default templates if they don't exist
        for template_data in default_templates:
            if template_data["name"] not in self.templates:
                template = QueryTemplate.from_dict(template_data)
                self.templates[template.name] = template
                logger.info(f"Loaded default template: {template.name}")

        # Save after loading defaults
        self._save_templates()

    def _load_templates(self):
        """Load templates from file"""
        try:
            if self.templates_file.exists():
                with open(self.templates_file, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    for template_data in data.get("templates", []):
                        template = QueryTemplate.from_dict(template_data)
                        self.templates[template.name] = template
                    logger.info(f"Loaded {len(self.templates)} templates from file")
        except Exception as e:
            logger.warning(f"Failed to load templates: {e}")
            self.templates = {}

    def _save_templates(self):
        """Save templates to file"""
        try:
            templates_data = {
                "templates": [t.to_dict() for t in self.templates.values()]
            }
            with open(self.templates_file, "w", encoding="utf-8") as f:
                json.dump(templates_data, f, indent=2)
            logger.debug(f"Saved {len(self.templates)} templates to file")
        except Exception as e:
            logger.warning(f"Failed to save templates: {e}")

    def get_template(self, name: str) -> Optional[QueryTemplate]:
        """Get template by name"""
        return self.templates.get(name)

    def get_templates(
        self, category: Optional[str] = None, tag: Optional[str] = None
    ) -> List[QueryTemplate]:
        """
        Get templates filtered by category or tag.

        Args:
            category: Filter by category
            tag: Filter by tag

        Returns:
            List of matching templates
        """
        templates = list(self.templates.values())

        if category:
            templates = [t for t in templates if t.category == category]

        if tag:
            templates = [t for t in templates if tag in t.tags]

        return templates

    def add_template(self, template: QueryTemplate) -> None:
        """Add a new template"""
        self.templates[template.name] = template
        self._save_templates()
        logger.info(f"Added template: {template.name}")

    def remove_template(self, name: str) -> bool:
        """Remove a template"""
        if name in self.templates:
            del self.templates[name]
            self._save_templates()
            logger.info(f"Removed template: {name}")
            return True
        return False

    def update_template(self, name: str, template: QueryTemplate) -> bool:
        """Update an existing template"""
        if name in self.templates:
            self.templates[name] = template
            self._save_templates()
            logger.info(f"Updated template: {name}")
            return True
        return False

    def get_categories(self) -> List[str]:
        """Get all template categories"""
        return sorted(set(t.category for t in self.templates.values()))

    def get_tags(self) -> List[str]:
        """Get all template tags"""
        tags = set()
        for template in self.templates.values():
            tags.update(template.tags)
        return sorted(list(tags))


# Global template manager instance
_template_manager: Optional[QueryTemplateManager] = None


def get_template_manager() -> QueryTemplateManager:
    """Get or create global template manager instance"""
    global _template_manager
    if _template_manager is None:
        _template_manager = QueryTemplateManager()
    return _template_manager



