"""
Context Validation System

This module provides validation and quality assurance for the enhanced context system.
"""

import logging
from dataclasses import dataclass
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple

from src.database.schema_inspector import (ColumnInfo, DatabaseContext,
                                           TableInfo)
from src.utils.context_enhancer import EnhancedContext
from src.utils.query_context import QueryContext, QueryPattern

logger = logging.getLogger(__name__)


@dataclass
class ValidationResult:
    """Result of context validation"""

    is_valid: bool
    score: float
    warnings: List[str]
    recommendations: List[str]
    validation_details: Dict[str, Any]


class ContextValidator:
    """
    Validates and ensures quality of enhanced context for SQL generation.

    Features:
    - Schema context validation
    - Query history context validation
    - Domain insights validation
    - Overall context quality assessment
    - Recommendations for improvement
    """

    def __init__(self):
        self.validation_thresholds = {
            "schema_min_tables": 1,
            "schema_min_columns_per_table": 1,
            "query_history_min_patterns": 0,  # Optional
            "context_quality_minimum": 0.3,
            "large_table_row_threshold": 1000000,
            "max_tables_without_relationships": 5,
        }

    def validate_enhanced_context(self, context: EnhancedContext) -> ValidationResult:
        """
        Perform comprehensive validation of enhanced context.

        Args:
            context: Enhanced context to validate

        Returns:
            ValidationResult: Detailed validation results
        """
        try:
            warnings = []
            recommendations = []
            validation_details = {}

            # Validate database context
            db_validation = self._validate_database_context(context.database_context)
            warnings.extend(db_validation["warnings"])
            recommendations.extend(db_validation["recommendations"])
            validation_details["database_context"] = db_validation

            # Validate query context
            query_validation = self._validate_query_context(context.query_context)
            warnings.extend(query_validation["warnings"])
            recommendations.extend(query_validation["recommendations"])
            validation_details["query_context"] = query_validation

            # Validate domain insights
            domain_validation = self._validate_domain_insights(context.domain_insights)
            warnings.extend(domain_validation["warnings"])
            recommendations.extend(domain_validation["recommendations"])
            validation_details["domain_insights"] = domain_validation

            # Validate overall context quality
            quality_validation = self._validate_context_quality(context)
            warnings.extend(quality_validation["warnings"])
            recommendations.extend(quality_validation["recommendations"])
            validation_details["quality_assessment"] = quality_validation

            # Calculate overall validation score
            overall_score = self._calculate_overall_score(validation_details)

            # Determine if context is valid
            is_valid = (
                overall_score >= self.validation_thresholds["context_quality_minimum"]
                and db_validation["has_basic_schema"]
                and not any("CRITICAL" in warning for warning in warnings)
            )

            logger.info(
                f"Context validation completed: score={overall_score:.2f}, valid={is_valid}"
            )

            return ValidationResult(
                is_valid=is_valid,
                score=overall_score,
                warnings=warnings,
                recommendations=recommendations,
                validation_details=validation_details,
            )

        except Exception as e:
            logger.error(f"Context validation failed: {e}")
            return ValidationResult(
                is_valid=False,
                score=0.0,
                warnings=[f"CRITICAL: Validation system error - {str(e)}"],
                recommendations=["Fix validation system errors before proceeding"],
                validation_details={"error": str(e)},
            )

    def _validate_database_context(self, db_context: DatabaseContext) -> Dict[str, Any]:
        """Validate database schema context"""
        validation = {
            "has_basic_schema": False,
            "table_count": 0,
            "column_count": 0,
            "relationship_count": 0,
            "has_business_domain": False,
            "warnings": [],
            "recommendations": [],
        }

        try:
            # Basic schema validation
            if not db_context.tables:
                validation["warnings"].append("CRITICAL: No database tables found")
                validation["recommendations"].append(
                    "Verify database connection and schema permissions"
                )
                return validation

            validation["has_basic_schema"] = True
            validation["table_count"] = len(db_context.tables)

            # Count total columns
            total_columns = sum(len(table.columns) for table in db_context.tables)
            validation["column_count"] = total_columns

            # Check for minimum tables
            if len(db_context.tables) < self.validation_thresholds["schema_min_tables"]:
                validation["warnings"].append("LIMITED: Very few tables available")
                validation["recommendations"].append(
                    "Consider expanding database schema analysis"
                )

            # Validate table quality
            tables_with_few_columns = []
            tables_with_no_data = []
            large_tables = []

            for table in db_context.tables:
                # Check column count
                if (
                    len(table.columns)
                    < self.validation_thresholds["schema_min_columns_per_table"]
                ):
                    tables_with_few_columns.append(table.name)

                # Check data availability
                if table.row_count is not None and table.row_count == 0:
                    tables_with_no_data.append(table.name)

                # Check for large tables
                if (
                    table.row_count
                    and table.row_count
                    > self.validation_thresholds["large_table_row_threshold"]
                ):
                    large_tables.append((table.name, table.row_count))

            # Report table quality issues
            if tables_with_few_columns:
                validation["warnings"].append(
                    f"Limited columns in tables: {', '.join(tables_with_few_columns[:3])}"
                )

            if tables_with_no_data:
                validation["warnings"].append(
                    f"Empty tables detected: {', '.join(tables_with_no_data[:3])}"
                )
                validation["recommendations"].append(
                    "Consider excluding empty tables from queries"
                )

            if large_tables:
                validation["recommendations"].append(
                    "Use LIMIT clauses with large tables for better performance"
                )

            # Validate relationships
            validation["relationship_count"] = len(db_context.relationships)
            if (
                len(db_context.tables)
                > self.validation_thresholds["max_tables_without_relationships"]
                and not db_context.relationships
            ):
                validation["warnings"].append(
                    "No table relationships detected in multi-table schema"
                )
                validation["recommendations"].append(
                    "Verify foreign key constraints or use explicit join conditions"
                )

            # Check business domain detection
            if db_context.business_domain:
                validation["has_business_domain"] = True
            else:
                validation["recommendations"].append(
                    "Consider adding table/column comments to improve domain detection"
                )

        except Exception as e:
            validation["warnings"].append(
                f"Database context validation error: {str(e)}"
            )

        return validation

    def _validate_query_context(self, query_context: QueryContext) -> Dict[str, Any]:
        """Validate query history context"""
        validation = {
            "has_history": False,
            "similar_query_count": 0,
            "pattern_count": 0,
            "function_count": 0,
            "warnings": [],
            "recommendations": [],
        }

        try:
            # Check for query history
            similar_queries = query_context.similar_successful_queries
            validation["similar_query_count"] = len(similar_queries)

            if similar_queries:
                validation["has_history"] = True

                # Validate query quality
                high_quality_queries = [
                    q for q in similar_queries if q.success_score > 0.8
                ]
                if len(high_quality_queries) < len(similar_queries) * 0.5:
                    validation["warnings"].append(
                        "Many similar queries have low success scores"
                    )
                    validation["recommendations"].append(
                        "Review and improve query patterns"
                    )

                # Check for recent queries
                recent_queries = [
                    q
                    for q in similar_queries
                    if (datetime.now() - q.timestamp).days < 30
                ]
                if not recent_queries:
                    validation["warnings"].append("No recent similar queries found")
                    validation["recommendations"].append(
                        "Query patterns may be outdated"
                    )

            else:
                validation["recommendations"].append(
                    "No similar queries found - results will rely on schema only"
                )

            # Check patterns and functions
            validation["pattern_count"] = len(query_context.common_patterns)
            validation["function_count"] = len(query_context.preferred_functions)

            if not query_context.common_patterns and validation["has_history"]:
                validation["warnings"].append(
                    "No common patterns extracted from query history"
                )

        except Exception as e:
            validation["warnings"].append(f"Query context validation error: {str(e)}")

        return validation

    def _validate_domain_insights(
        self, domain_insights: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Validate domain-specific insights"""
        validation = {
            "has_intent": False,
            "has_suggestions": False,
            "has_performance_hints": False,
            "complexity_appropriate": True,
            "warnings": [],
            "recommendations": [],
        }

        try:
            # Check for detected intent
            if domain_insights.get("detected_intent"):
                validation["has_intent"] = True
            else:
                validation["recommendations"].append(
                    "Could not detect query intent - using generic approach"
                )

            # Check for table/column suggestions
            suggested_tables = domain_insights.get("suggested_tables", [])
            suggested_columns = domain_insights.get("suggested_columns", [])

            if suggested_tables or suggested_columns:
                validation["has_suggestions"] = True
            else:
                validation["warnings"].append("No relevant tables or columns suggested")
                validation["recommendations"].append(
                    "Review query wording to improve table/column matching"
                )

            # Check for performance hints
            performance_hints = domain_insights.get("performance_hints", [])
            if performance_hints:
                validation["has_performance_hints"] = True

            # Check complexity estimation
            complexity = domain_insights.get("complexity_level", "medium")
            if complexity == "complex" and not suggested_tables:
                validation["warnings"].append(
                    "Complex query detected but no specific tables suggested"
                )
                validation["complexity_appropriate"] = False

        except Exception as e:
            validation["warnings"].append(f"Domain insights validation error: {str(e)}")

        return validation

    def _validate_context_quality(self, context: EnhancedContext) -> Dict[str, Any]:
        """Validate overall context quality"""
        validation = {
            "quality_score": 0.0,
            "quality_level": "poor",
            "warnings": [],
            "recommendations": [],
        }

        try:
            quality_score = context.context_quality_score
            validation["quality_score"] = quality_score

            # Determine quality level
            if quality_score >= 0.9:
                validation["quality_level"] = "excellent"
            elif quality_score >= 0.7:
                validation["quality_level"] = "good"
            elif quality_score >= 0.5:
                validation["quality_level"] = "fair"
            elif quality_score >= 0.3:
                validation["quality_level"] = "poor"
            else:
                validation["quality_level"] = "inadequate"

            # Quality-based recommendations
            if quality_score < 0.5:
                validation["warnings"].append(
                    f"Low context quality score: {quality_score:.2f}"
                )
                validation["recommendations"].append(
                    "Consider refreshing schema cache or improving query history"
                )

            # Check for context warnings
            if context.warning_messages:
                validation["warnings"].extend(
                    [f"Context: {w}" for w in context.warning_messages]
                )

        except Exception as e:
            validation["warnings"].append(f"Context quality validation error: {str(e)}")

        return validation

    def _calculate_overall_score(self, validation_details: Dict[str, Any]) -> float:
        """Calculate overall validation score"""
        try:
            scores = []

            # Database context score (50% weight)
            db_val = validation_details.get("database_context", {})
            if db_val.get("has_basic_schema"):
                db_score = 0.5
                if db_val.get("table_count", 0) > 3:
                    db_score += 0.2
                if db_val.get("relationship_count", 0) > 0:
                    db_score += 0.2
                if db_val.get("has_business_domain"):
                    db_score += 0.1
                scores.append(db_score * 0.5)

            # Query context score (30% weight)
            query_val = validation_details.get("query_context", {})
            if query_val.get("has_history"):
                query_score = 0.5
                if query_val.get("similar_query_count", 0) > 2:
                    query_score += 0.3
                if query_val.get("pattern_count", 0) > 0:
                    query_score += 0.2
                scores.append(query_score * 0.3)

            # Domain insights score (20% weight)
            domain_val = validation_details.get("domain_insights", {})
            domain_score = 0.0
            if domain_val.get("has_intent"):
                domain_score += 0.3
            if domain_val.get("has_suggestions"):
                domain_score += 0.4
            if domain_val.get("has_performance_hints"):
                domain_score += 0.3
            scores.append(domain_score * 0.2)

            return sum(scores) if scores else 0.0

        except Exception as e:
            logger.warning(f"Score calculation error: {e}")
            return 0.0

    def generate_validation_report(self, result: ValidationResult) -> str:
        """Generate a human-readable validation report"""
        try:
            report_lines = [
                f"🔍 CONTEXT VALIDATION REPORT",
                f"📊 Overall Score: {result.score:.2f}/1.0",
                f"✅ Valid: {'Yes' if result.is_valid else 'No'}",
                "",
            ]

            # Add warnings if any
            if result.warnings:
                report_lines.append("⚠️ WARNINGS:")
                for warning in result.warnings:
                    report_lines.append(f"  • {warning}")
                report_lines.append("")

            # Add recommendations if any
            if result.recommendations:
                report_lines.append("💡 RECOMMENDATIONS:")
                for rec in result.recommendations:
                    report_lines.append(f"  • {rec}")
                report_lines.append("")

            # Add detailed validation info
            if result.validation_details:
                report_lines.append("📋 VALIDATION DETAILS:")

                db_details = result.validation_details.get("database_context", {})
                if db_details:
                    report_lines.append(
                        f"  Database: {db_details.get('table_count', 0)} tables, {db_details.get('column_count', 0)} columns"
                    )

                query_details = result.validation_details.get("query_context", {})
                if query_details:
                    report_lines.append(
                        f"  Query History: {query_details.get('similar_query_count', 0)} similar queries"
                    )

                quality_details = result.validation_details.get(
                    "quality_assessment", {}
                )
                if quality_details:
                    report_lines.append(
                        f"  Quality Level: {quality_details.get('quality_level', 'unknown')}"
                    )

            return "\n".join(report_lines)

        except Exception as e:
            return f"Error generating validation report: {str(e)}"


# Global validator instance
context_validator = ContextValidator()
