"""
Enhanced Context System for LLM SQL Generation

This module integrates schema inspection with query history to provide
comprehensive context for improved SQL query generation.
"""

import logging
from typing import Dict, List, Optional, Any
from dataclasses import dataclass
from pathlib import Path

from src.database.schema_inspector import SchemaInspector, DatabaseContext
from src.utils.query_context import QueryContextManager, QueryContext

logger = logging.getLogger(__name__)


@dataclass
class EnhancedContext:
    """Complete enhanced context for LLM prompts"""
    database_context: DatabaseContext
    query_context: QueryContext
    domain_insights: Dict[str, Any]
    context_quality_score: float
    recommended_approach: str
    warning_messages: List[str]


class ContextEnhancer:
    """
    Advanced context enhancement system that combines:
    - Dynamic schema inspection
    - Query history analysis
    - Domain-specific insights
    - Context quality validation
    - Adaptive prompt generation
    """
    
    def __init__(self, connection, data_dir: str = "data"):
        self.connection = connection
        self.schema_inspector = SchemaInspector(connection)
        self.query_context_manager = QueryContextManager(data_dir)
        
        # Context quality thresholds
        self.quality_thresholds = {
            "excellent": 0.9,
            "good": 0.7,
            "fair": 0.5,
            "poor": 0.3
        }
    
    def get_enhanced_context(self, 
                            user_question: str,
                            refresh_schema: bool = False,
                            include_samples: bool = True,
                            include_history: bool = True) -> EnhancedContext:
        """
        Get comprehensive enhanced context for LLM SQL generation.
        
        Args:
            user_question: The user's question
            refresh_schema: Force refresh of schema cache
            include_samples: Include sample data in schema analysis
            include_history: Include query history context
            
        Returns:
            EnhancedContext: Complete context with quality assessment
        """
        try:
            logger.info("Starting enhanced context generation")
            
            # Get database schema context
            database_context = self.schema_inspector.get_comprehensive_context(
                refresh_cache=refresh_schema,
                include_samples=include_samples
            )
            
            # Get query history context
            query_context = QueryContext()
            if include_history:
                query_context = self.query_context_manager.get_context_for_question(
                    user_question
                )
            
            # Generate domain insights
            domain_insights = self._generate_domain_insights(
                database_context, query_context, user_question
            )
            
            # Calculate context quality score
            quality_score = self._calculate_context_quality(
                database_context, query_context, domain_insights
            )
            
            # Generate recommended approach
            recommended_approach = self._generate_recommended_approach(
                user_question, database_context, query_context, quality_score
            )
            
            # Generate warnings if needed
            warnings = self._generate_warnings(
                database_context, query_context, quality_score
            )
            
            enhanced_context = EnhancedContext(
                database_context=database_context,
                query_context=query_context,
                domain_insights=domain_insights,
                context_quality_score=quality_score,
                recommended_approach=recommended_approach,
                warning_messages=warnings
            )
            
            logger.info(f"Enhanced context generated: quality_score={quality_score:.2f}")
            return enhanced_context
            
        except Exception as e:
            logger.error(f"Failed to generate enhanced context: {e}")
            # Return minimal context as fallback
            return self._create_fallback_context(user_question)
    
    def generate_enhanced_prompt(self, 
                                user_question: str,
                                base_prompt: str,
                                enhanced_context: EnhancedContext) -> str:
        """
        Generate an enhanced prompt with rich context information.
        
        Args:
            user_question: The user's question
            base_prompt: Base prompt template
            enhanced_context: Enhanced context information
            
        Returns:
            str: Enhanced prompt with integrated context
        """
        try:
            # Start with base prompt
            enhanced_prompt_parts = [base_prompt]
            
            # Add schema context
            schema_summary = self.schema_inspector.generate_context_summary(
                enhanced_context.database_context
            )
            enhanced_prompt_parts.append(f"\n🗄️ ACTUAL DATABASE SCHEMA:\n{schema_summary}")
            
            # Add query history context if available
            if enhanced_context.query_context.similar_successful_queries:
                history_context = self.query_context_manager.generate_context_prompt_addition(
                    enhanced_context.query_context
                )
                enhanced_prompt_parts.append(history_context)
            
            # Add domain-specific insights
            domain_section = self._format_domain_insights(enhanced_context.domain_insights)
            if domain_section:
                enhanced_prompt_parts.append(domain_section)
            
            # Add recommended approach
            enhanced_prompt_parts.append(f"\n🎯 RECOMMENDED APPROACH:\n{enhanced_context.recommended_approach}")
            
            # Add warnings if any
            if enhanced_context.warning_messages:
                warnings_text = "\n".join([f"    ⚠️ {warning}" for warning in enhanced_context.warning_messages])
                enhanced_prompt_parts.append(f"\n⚠️ IMPORTANT WARNINGS:\n{warnings_text}")
            
            # Add context quality indicator
            quality_level = self._get_quality_level(enhanced_context.context_quality_score)
            enhanced_prompt_parts.append(f"\n📊 Context Quality: {quality_level.upper()} ({enhanced_context.context_quality_score:.2f})")
            
            return "\n".join(enhanced_prompt_parts)
            
        except Exception as e:
            logger.warning(f"Failed to generate enhanced prompt: {e}")
            return base_prompt
    
    def record_query_execution(self,
                              user_question: str,
                              generated_sql: str,
                              success: bool,
                              execution_time: Optional[float] = None,
                              result_count: Optional[int] = None,
                              error_message: Optional[str] = None) -> None:
        """
        Record query execution for learning and improvement.
        
        Args:
            user_question: Original user question
            generated_sql: Generated SQL query
            success: Whether execution was successful
            execution_time: Execution time in seconds
            result_count: Number of results returned
            error_message: Error message if failed
        """
        self.query_context_manager.record_query(
            user_question=user_question,
            generated_sql=generated_sql,
            success=success,
            execution_time=execution_time,
            result_count=result_count,
            error_message=error_message
        )
    
    def _generate_domain_insights(self, 
                                 db_context: DatabaseContext,
                                 query_context: QueryContext,
                                 user_question: str) -> Dict[str, Any]:
        """Generate domain-specific insights"""
        insights = {
            "detected_intent": None,
            "suggested_tables": [],
            "suggested_columns": [],
            "complexity_level": "medium",
            "data_freshness": None,
            "performance_hints": []
        }
        
        try:
            # Analyze user question intent
            insights["detected_intent"] = self._analyze_question_intent(user_question)
            
            # Suggest relevant tables
            insights["suggested_tables"] = self._suggest_relevant_tables(
                user_question, db_context
            )
            
            # Suggest relevant columns
            insights["suggested_columns"] = self._suggest_relevant_columns(
                user_question, db_context, insights["suggested_tables"]
            )
            
            # Estimate complexity
            insights["complexity_level"] = self._estimate_query_complexity(
                user_question, insights["suggested_tables"]
            )
            
            # Analyze data freshness if available
            insights["data_freshness"] = self._analyze_data_freshness(db_context)
            
            # Generate performance hints
            insights["performance_hints"] = self._generate_performance_hints(
                db_context, insights["suggested_tables"], query_context
            )
            
        except Exception as e:
            logger.warning(f"Failed to generate domain insights: {e}")
        
        return insights
    
    def _analyze_question_intent(self, user_question: str) -> str:
        """Analyze what the user is trying to accomplish"""
        question_lower = user_question.lower()
        
        # Aggregation queries
        if any(word in question_lower for word in ['count', 'total', 'sum', 'average', 'avg', 'maximum', 'minimum']):
            return "aggregation"
        
        # Ranking/sorting queries
        if any(word in question_lower for word in ['top', 'bottom', 'highest', 'lowest', 'best', 'worst', 'rank']):
            return "ranking"
        
        # Filter/search queries
        if any(word in question_lower for word in ['where', 'with', 'having', 'contains', 'like']):
            return "filtering"
        
        # Comparison queries
        if any(word in question_lower for word in ['compare', 'difference', 'between', 'vs', 'versus']):
            return "comparison"
        
        # Time-based queries
        if any(word in question_lower for word in ['recent', 'last', 'this month', 'this year', 'yesterday', 'today']):
            return "temporal"
        
        # Simple listing
        if any(word in question_lower for word in ['list', 'show', 'display', 'all']):
            return "listing"
        
        return "exploration"
    
    def _suggest_relevant_tables(self, user_question: str, db_context: DatabaseContext) -> List[str]:
        """Suggest tables that might be relevant to the question"""
        question_words = set(user_question.lower().split())
        suggested_tables = []
        
        for table in db_context.tables:
            table_score = 0
            
            # Check table name similarity
            table_name_words = set(table.name.lower().replace('_', ' ').split())
            table_score += len(question_words.intersection(table_name_words)) * 3
            
            # Check column name similarity
            for column in table.columns:
                column_words = set(column.name.lower().replace('_', ' ').split())
                table_score += len(question_words.intersection(column_words))
            
            # Check table comment if available
            if table.comment:
                comment_words = set(table.comment.lower().split())
                table_score += len(question_words.intersection(comment_words)) * 2
            
            if table_score > 0:
                suggested_tables.append((table.name, table_score))
        
        # Sort by relevance score and return top tables
        suggested_tables.sort(key=lambda x: x[1], reverse=True)
        return [table_name for table_name, _ in suggested_tables[:5]]
    
    def _suggest_relevant_columns(self, 
                                 user_question: str, 
                                 db_context: DatabaseContext,
                                 suggested_tables: List[str]) -> List[str]:
        """Suggest columns that might be relevant"""
        question_words = set(user_question.lower().split())
        suggested_columns = []
        
        # Focus on suggested tables first
        relevant_tables = [t for t in db_context.tables if t.name in suggested_tables]
        
        for table in relevant_tables:
            for column in table.columns:
                column_score = 0
                
                # Direct name match
                column_words = set(column.name.lower().replace('_', ' ').split())
                column_score += len(question_words.intersection(column_words)) * 2
                
                # Data type relevance
                if any(word in question_words for word in ['count', 'number']) and 'INT' in column.data_type:
                    column_score += 1
                elif any(word in question_words for word in ['price', 'cost', 'amount']) and 'DECIMAL' in column.data_type:
                    column_score += 2
                elif any(word in question_words for word in ['name', 'title']) and 'VARCHAR' in column.data_type:
                    column_score += 1
                
                if column_score > 0:
                    suggested_columns.append(f"{table.name}.{column.name}")
        
        return suggested_columns[:10]  # Limit to top 10
    
    def _estimate_query_complexity(self, user_question: str, suggested_tables: List[str]) -> str:
        """Estimate the complexity level of the required query"""
        complexity_indicators = {
            'simple': 0,
            'medium': 0,
            'complex': 0
        }
        
        question_lower = user_question.lower()
        
        # Simple indicators
        if len(suggested_tables) <= 1:
            complexity_indicators['simple'] += 2
        if any(word in question_lower for word in ['list', 'show', 'display']):
            complexity_indicators['simple'] += 1
        
        # Medium complexity indicators  
        if 2 <= len(suggested_tables) <= 3:
            complexity_indicators['medium'] += 2
        if any(word in question_lower for word in ['group', 'sum', 'count', 'average']):
            complexity_indicators['medium'] += 1
        if any(word in question_lower for word in ['where', 'filter', 'with']):
            complexity_indicators['medium'] += 1
        
        # Complex indicators
        if len(suggested_tables) > 3:
            complexity_indicators['complex'] += 2
        if any(word in question_lower for word in ['rank', 'window', 'partition', 'recursive']):
            complexity_indicators['complex'] += 2
        if 'compare' in question_lower or 'correlation' in question_lower:
            complexity_indicators['complex'] += 1
        
        # Return the level with highest score
        return max(complexity_indicators, key=complexity_indicators.get)
    
    def _analyze_data_freshness(self, db_context: DatabaseContext) -> Optional[str]:
        """Analyze how fresh the data appears to be"""
        if not db_context.tables:
            return None
        
        date_columns = []
        for table in db_context.tables:
            for column in table.columns:
                if any(keyword in column.name.lower() for keyword in ['date', 'time', 'created', 'updated']):
                    date_columns.append(f"{table.name}.{column.name}")
        
        if date_columns:
            return f"Found {len(date_columns)} date/time columns for temporal analysis"
        
        return "No obvious date columns detected"
    
    def _generate_performance_hints(self, 
                                   db_context: DatabaseContext,
                                   suggested_tables: List[str],
                                   query_context: QueryContext) -> List[str]:
        """Generate performance optimization hints"""
        hints = []
        
        try:
            # Check table sizes
            large_tables = [
                table.name for table in db_context.tables 
                if table.row_count and table.row_count > 1000000
            ]
            
            if any(table in suggested_tables for table in large_tables):
                hints.append("Consider using LIMIT clause for large tables")
                hints.append("Use specific WHERE conditions to reduce data scanning")
            
            # Check for common successful patterns
            if query_context.common_patterns:
                if "uses_limit" in query_context.common_patterns:
                    hints.append("LIMIT clause is commonly used in successful queries")
                if "uses_where" in query_context.common_patterns:
                    hints.append("WHERE conditions improve query performance")
            
            # Multi-table join hints
            if len(suggested_tables) > 2:
                hints.append("For multi-table joins, ensure proper join conditions")
                hints.append("Consider using table aliases for readability")
        
        except Exception as e:
            logger.warning(f"Failed to generate performance hints: {e}")
        
        return hints
    
    def _calculate_context_quality(self, 
                                  db_context: DatabaseContext,
                                  query_context: QueryContext,
                                  domain_insights: Dict[str, Any]) -> float:
        """Calculate overall context quality score"""
        quality_score = 0.0
        
        # Schema context quality (40% of total)
        if db_context.tables:
            schema_score = min(len(db_context.tables) / 10, 1.0)  # Up to 10 tables = full score
            if db_context.relationships:
                schema_score += min(len(db_context.relationships) / 5, 0.5)  # Bonus for relationships
            if db_context.business_domain:
                schema_score += 0.2  # Bonus for domain detection
            quality_score += schema_score * 0.4
        
        # Query history quality (30% of total)
        if query_context.similar_successful_queries:
            history_score = min(len(query_context.similar_successful_queries) / 5, 1.0)
            if query_context.common_patterns:
                history_score += min(len(query_context.common_patterns) / 10, 0.3)
            quality_score += history_score * 0.3
        
        # Domain insights quality (20% of total)
        insights_score = 0.0
        if domain_insights.get("suggested_tables"):
            insights_score += 0.4
        if domain_insights.get("suggested_columns"):
            insights_score += 0.3
        if domain_insights.get("performance_hints"):
            insights_score += 0.3
        quality_score += insights_score * 0.2
        
        # Completeness bonus (10% of total)
        completeness_score = 0.0
        if db_context.tables and query_context.similar_successful_queries:
            completeness_score = 1.0
        elif db_context.tables or query_context.similar_successful_queries:
            completeness_score = 0.5
        quality_score += completeness_score * 0.1
        
        return min(quality_score, 1.0)
    
    def _generate_recommended_approach(self, 
                                      user_question: str,
                                      db_context: DatabaseContext,
                                      query_context: QueryContext,
                                      quality_score: float) -> str:
        """Generate recommended approach based on context analysis"""
        
        quality_level = self._get_quality_level(quality_score)
        
        if quality_level == "excellent":
            return ("High-confidence context available. Generate SQL using actual schema, "
                   "leverage similar successful queries, and apply learned patterns.")
        
        elif quality_level == "good":
            return ("Good context available. Focus on verified table structures and "
                   "incorporate successful query patterns where applicable.")
        
        elif quality_level == "fair":
            return ("Limited context available. Use available schema information but "
                   "be conservative with assumptions. Recommend basic query structure.")
        
        else:
            return ("Minimal context available. Generate basic SQL structure and "
                   "recommend user verification of table and column names.")
    
    def _generate_warnings(self, 
                          db_context: DatabaseContext,
                          query_context: QueryContext,
                          quality_score: float) -> List[str]:
        """Generate context-based warnings"""
        warnings = []
        
        # Low quality warning
        if quality_score < self.quality_thresholds["fair"]:
            warnings.append("Limited context available - verify table and column names")
        
        # No query history warning
        if not query_context.similar_successful_queries:
            warnings.append("No similar successful queries found - using schema-only context")
        
        # Large table warning
        large_tables = [
            table.name for table in db_context.tables 
            if table.row_count and table.row_count > 5000000
        ]
        if large_tables:
            warnings.append(f"Large tables detected ({', '.join(large_tables[:3])}) - consider using LIMIT")
        
        # Missing relationships warning
        if len(db_context.tables) > 1 and not db_context.relationships:
            warnings.append("No foreign key relationships detected - verify join conditions")
        
        return warnings
    
    def _get_quality_level(self, quality_score: float) -> str:
        """Convert quality score to quality level"""
        for level, threshold in self.quality_thresholds.items():
            if quality_score >= threshold:
                return level
        return "poor"
    
    def _format_domain_insights(self, domain_insights: Dict[str, Any]) -> Optional[str]:
        """Format domain insights for prompt inclusion"""
        if not domain_insights:
            return None
        
        parts = ["\\n🧠 DOMAIN INSIGHTS:"]
        
        if domain_insights.get("detected_intent"):
            parts.append(f"    • Query Intent: {domain_insights['detected_intent']}")
        
        if domain_insights.get("suggested_tables"):
            tables_list = ", ".join(domain_insights["suggested_tables"][:5])
            parts.append(f"    • Relevant Tables: {tables_list}")
        
        if domain_insights.get("suggested_columns"):
            columns_list = ", ".join(domain_insights["suggested_columns"][:8])
            parts.append(f"    • Key Columns: {columns_list}")
        
        if domain_insights.get("complexity_level"):
            parts.append(f"    • Estimated Complexity: {domain_insights['complexity_level']}")
        
        if domain_insights.get("performance_hints"):
            parts.append("    • Performance Tips:")
            for hint in domain_insights["performance_hints"][:3]:
                parts.append(f"        - {hint}")
        
        return "\\n".join(parts) if len(parts) > 1 else None
    
    def _create_fallback_context(self, user_question: str) -> EnhancedContext:
        """Create minimal fallback context when enhancement fails"""
        return EnhancedContext(
            database_context=DatabaseContext(
                database_name="UNKNOWN",
                schema_name="UNKNOWN"
            ),
            query_context=QueryContext(),
            domain_insights={
                "detected_intent": "exploration",
                "complexity_level": "medium",
                "performance_hints": ["Use LIMIT clause for large result sets"]
            },
            context_quality_score=0.1,
            recommended_approach="Minimal context - use basic SQL structure",
            warning_messages=["Context enhancement failed - using fallback mode"]
        )
    
    def get_context_statistics(self) -> Dict[str, Any]:
        """Get statistics about context system performance"""
        return {
            "query_statistics": self.query_context_manager.get_statistics(),
            "schema_cache_status": "active" if self.schema_inspector.cache_file.exists() else "empty",
            "quality_thresholds": self.quality_thresholds
        }


# Global instance placeholder - will be initialized with connection
context_enhancer = None

def get_context_enhancer(connection) -> ContextEnhancer:
    """Get or create context enhancer instance"""
    global context_enhancer
    if context_enhancer is None:
        context_enhancer = ContextEnhancer(connection)
    return context_enhancer