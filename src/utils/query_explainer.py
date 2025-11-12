"""
Query Explainer - Explain SQL queries in natural language
"""

import logging
import re
from typing import Dict, List, Optional

logger = logging.getLogger(__name__)


class QueryExplainer:
    """Explain SQL queries in natural language"""

    def __init__(self):
        """Initialize query explainer"""
        pass

    def explain_query(self, sql: str, user_question: Optional[str] = None) -> str:
        """
        Generate natural language explanation of SQL query.

        Args:
            sql: SQL query string
            user_question: Original user question (optional)

        Returns:
            Natural language explanation
        """
        try:
            sql_upper = sql.strip().upper()

            # Parse query components
            components = self._parse_query(sql_upper, sql)

            # Generate explanation
            explanation_parts = []

            # Main operation
            if components["operation"]:
                explanation_parts.append(
                    f"This query {components['operation'].lower()}s data"
                )

            # Tables involved
            if components["tables"]:
                if len(components["tables"]) == 1:
                    explanation_parts.append(
                        f"from the {components['tables'][0]} table"
                    )
                else:
                    explanation_parts.append(
                        f"from {', '.join(components['tables'][:-1])} and {components['tables'][-1]} tables"
                    )

            # JOINs
            if components["joins"]:
                join_explanations = []
                for join in components["joins"]:
                    join_explanations.append(
                        f"{join['type']} joins {join['table']} on {join['condition']}"
                    )
                explanation_parts.append("and " + ", ".join(join_explanations))

            # WHERE conditions
            if components["where_conditions"]:
                conditions = ", ".join(components["where_conditions"][:3])
                explanation_parts.append(f"where {conditions}")
                if len(components["where_conditions"]) > 3:
                    explanation_parts.append(
                        f"and {len(components['where_conditions']) - 3} more conditions"
                    )

            # GROUP BY
            if components["group_by"]:
                explanation_parts.append(
                    f"grouped by {', '.join(components['group_by'])}"
                )

            # ORDER BY
            if components["order_by"]:
                order_dir = components["order_by"].get("direction", "ascending")
                explanation_parts.append(
                    f"ordered by {components['order_by']['column']} in {order_dir} order"
                )

            # LIMIT
            if components["limit"]:
                explanation_parts.append(f"limited to {components['limit']} results")

            # Aggregate functions
            if components["aggregates"]:
                agg_explanations = []
                for agg in components["aggregates"]:
                    agg_explanations.append(f"{agg['function']}({agg['column']})")
                explanation_parts.append(
                    f"and calculates {', '.join(agg_explanations)}"
                )

            # Combine explanation
            explanation = " ".join(explanation_parts) + "."

            # Capitalize first letter
            explanation = explanation[0].upper() + explanation[1:]

            return explanation

        except Exception as e:
            logger.warning(f"Failed to explain query: {e}")
            return "This query retrieves data from the database."

    def explain_step_by_step(self, sql: str) -> List[Dict[str, str]]:
        """
        Break down query into steps.

        Args:
            sql: SQL query string

        Returns:
            List of step dictionaries with 'step', 'action', and 'details'
        """
        try:
            sql_upper = sql.strip().upper()
            steps = []

            # Step 1: Identify operation
            if sql_upper.startswith("SELECT"):
                steps.append(
                    {
                        "step": 1,
                        "action": "SELECT",
                        "details": "Selects columns from the table(s)",
                    }
                )
            elif sql_upper.startswith("SHOW"):
                steps.append(
                    {
                        "step": 1,
                        "action": "SHOW",
                        "details": "Shows database metadata",
                    }
                )
            elif sql_upper.startswith("WITH"):
                steps.append(
                    {
                        "step": 1,
                        "action": "WITH (CTE)",
                        "details": "Defines a common table expression (CTE)",
                    }
                )

            # Step 2: FROM clause
            from_match = re.search(r"\bFROM\s+(\w+)", sql_upper)
            if from_match:
                table = from_match.group(1)
                steps.append(
                    {
                        "step": len(steps) + 1,
                        "action": "FROM",
                        "details": f"Reads from the {table} table",
                    }
                )

            # Step 3: JOINs
            join_matches = re.finditer(
                r"\b(INNER|LEFT|RIGHT|FULL)?\s*JOIN\s+(\w+)\s+ON\s+([^WHERE\s]+)",
                sql_upper,
            )
            for i, match in enumerate(join_matches):
                join_type = match.group(1) or "INNER"
                table = match.group(2)
                condition = match.group(3).strip()
                steps.append(
                    {
                        "step": len(steps) + 1,
                        "action": f"{join_type} JOIN",
                        "details": f"Joins with {table} table on {condition}",
                    }
                )

            # Step 4: WHERE clause
            where_match = re.search(r"\bWHERE\s+(.+?)(?:\s+GROUP|\s+ORDER|\s+LIMIT|$)", sql_upper, re.DOTALL)
            if where_match:
                conditions = where_match.group(1).strip()
                steps.append(
                    {
                        "step": len(steps) + 1,
                        "action": "WHERE",
                        "details": f"Filters rows where {conditions[:50]}...",
                    }
                )

            # Step 5: GROUP BY
            group_match = re.search(r"\bGROUP\s+BY\s+([^ORDER\s]+)", sql_upper)
            if group_match:
                columns = group_match.group(1).strip()
                steps.append(
                    {
                        "step": len(steps) + 1,
                        "action": "GROUP BY",
                        "details": f"Groups results by {columns}",
                    }
                )

            # Step 6: ORDER BY
            order_match = re.search(r"\bORDER\s+BY\s+(\w+)\s+(ASC|DESC)?", sql_upper)
            if order_match:
                column = order_match.group(1)
                direction = order_match.group(2) or "ASC"
                steps.append(
                    {
                        "step": len(steps) + 1,
                        "action": "ORDER BY",
                        "details": f"Orders results by {column} in {direction} order",
                    }
                )

            # Step 7: LIMIT
            limit_match = re.search(r"\bLIMIT\s+(\d+)", sql_upper)
            if limit_match:
                limit = limit_match.group(1)
                steps.append(
                    {
                        "step": len(steps) + 1,
                        "action": "LIMIT",
                        "details": f"Limits results to {limit} rows",
                    }
                )

            return steps

        except Exception as e:
            logger.warning(f"Failed to explain query step by step: {e}")
            return [
                {
                    "step": 1,
                    "action": "EXECUTE",
                    "details": "Executes the SQL query",
                }
            ]

    def _parse_query(self, sql_upper: str, sql: str) -> Dict[str, any]:
        """Parse SQL query into components"""
        components = {
            "operation": None,
            "tables": [],
            "joins": [],
            "where_conditions": [],
            "group_by": [],
            "order_by": {},
            "limit": None,
            "aggregates": [],
        }

        # Operation
        if sql_upper.startswith("SELECT"):
            components["operation"] = "SELECT"
        elif sql_upper.startswith("SHOW"):
            components["operation"] = "SHOW"
        elif sql_upper.startswith("WITH"):
            components["operation"] = "WITH"

        # Tables (FROM clause)
        from_match = re.search(r"\bFROM\s+(\w+)", sql_upper)
        if from_match:
            components["tables"].append(from_match.group(1))

        # JOINs
        join_matches = re.finditer(
            r"\b(INNER|LEFT|RIGHT|FULL)?\s*JOIN\s+(\w+)", sql_upper
        )
        for match in join_matches:
            join_type = match.group(1) or "INNER"
            table = match.group(2)
            components["joins"].append({"type": join_type, "table": table, "condition": ""})
            components["tables"].append(table)

        # WHERE conditions (simplified)
        where_match = re.search(r"\bWHERE\s+(.+?)(?:\s+GROUP|\s+ORDER|\s+LIMIT|$)", sql_upper, re.DOTALL)
        if where_match:
            conditions = where_match.group(1).strip()
            # Split by AND/OR (simplified)
            conditions_list = re.split(r"\s+AND\s+|\s+OR\s+", conditions, flags=re.IGNORECASE)
            components["where_conditions"] = [c.strip()[:50] for c in conditions_list[:5]]

        # GROUP BY
        group_match = re.search(r"\bGROUP\s+BY\s+([^ORDER\s]+)", sql_upper)
        if group_match:
            columns = group_match.group(1).strip()
            components["group_by"] = [c.strip() for c in columns.split(",")]

        # ORDER BY
        order_match = re.search(r"\bORDER\s+BY\s+(\w+)\s+(ASC|DESC)?", sql_upper)
        if order_match:
            column = order_match.group(1)
            direction = order_match.group(2) or "ASC"
            components["order_by"] = {"column": column, "direction": direction.lower()}

        # LIMIT
        limit_match = re.search(r"\bLIMIT\s+(\d+)", sql_upper)
        if limit_match:
            components["limit"] = int(limit_match.group(1))

        # Aggregate functions
        agg_matches = re.finditer(r"\b(COUNT|SUM|AVG|MAX|MIN)\s*\(([^)]+)\)", sql_upper)
        for match in agg_matches:
            function = match.group(1)
            column = match.group(2)
            components["aggregates"].append({"function": function, "column": column})

        return components


# Global explainer instance
_query_explainer: Optional[QueryExplainer] = None


def get_query_explainer() -> QueryExplainer:
    """Get or create global query explainer instance"""
    global _query_explainer
    if _query_explainer is None:
        _query_explainer = QueryExplainer()
    return _query_explainer




