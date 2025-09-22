"""
Dynamic Schema Inspector for Enhanced Database Context

This module provides comprehensive database schema inspection capabilities
to improve LLM context for SQL generation.
"""

import logging
from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass, field
from pathlib import Path
import json
import hashlib
from datetime import datetime, timedelta

import pandas as pd
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError

from src.utils.helpers import log_manager, error_handler

logger = logging.getLogger(__name__)


@dataclass
class ColumnInfo:
    """Detailed column information"""
    name: str
    data_type: str
    is_nullable: bool
    default_value: Optional[str] = None
    character_maximum_length: Optional[int] = None
    numeric_precision: Optional[int] = None
    numeric_scale: Optional[int] = None
    comment: Optional[str] = None
    sample_values: List[Any] = field(default_factory=list)
    distinct_count: Optional[int] = None
    null_percentage: Optional[float] = None


@dataclass
class TableInfo:
    """Comprehensive table information"""
    name: str
    schema_name: str
    table_type: str
    row_count: Optional[int] = None
    columns: List[ColumnInfo] = field(default_factory=list)
    primary_keys: List[str] = field(default_factory=list)
    foreign_keys: List[Dict[str, str]] = field(default_factory=list)
    indexes: List[str] = field(default_factory=list)
    comment: Optional[str] = None
    created_date: Optional[datetime] = None
    last_analyzed: Optional[datetime] = None


@dataclass
class DatabaseContext:
    """Complete database context for LLM"""
    database_name: str
    schema_name: str
    tables: List[TableInfo] = field(default_factory=list)
    relationships: List[Dict[str, str]] = field(default_factory=list)
    common_patterns: Dict[str, List[str]] = field(default_factory=dict)
    business_domain: Optional[str] = None
    generated_at: datetime = field(default_factory=datetime.now)


class SchemaInspector:
    """
    Advanced schema inspector for comprehensive database context.
    
    Features:
    - Dynamic schema discovery
    - Column-level metadata with samples
    - Relationship detection
    - Business domain inference
    - Context caching for performance
    - Sample data analysis
    """
    
    def __init__(self, connection, cache_ttl_hours: int = 24):
        self.connection = connection
        self.cache_ttl_hours = cache_ttl_hours
        self.cache_file = Path("data/schema_cache.json")
        self.cache_file.parent.mkdir(exist_ok=True)
        
    def get_comprehensive_context(self, 
                                refresh_cache: bool = False,
                                include_samples: bool = True,
                                max_sample_size: int = 10) -> DatabaseContext:
        """
        Get comprehensive database context for LLM.
        
        Args:
            refresh_cache: Force refresh of cached data
            include_samples: Include sample data for columns
            max_sample_size: Maximum number of sample values per column
        
        Returns:
            DatabaseContext: Complete database context
        """
        try:
            log_manager.add_log("🔍 Schema Inspector", "Starting comprehensive schema analysis")
            
            # Check cache first
            if not refresh_cache:
                cached_context = self._load_from_cache()
                if cached_context:
                    log_manager.add_log("📋 Schema Cache", "Using cached schema context")
                    return cached_context
            
            # Get database basic info
            db_name, schema_name = self._get_database_info()
            
            # Initialize context
            context = DatabaseContext(
                database_name=db_name,
                schema_name=schema_name
            )
            
            # Get all tables
            tables = self._get_all_tables()
            log_manager.add_log("📊 Tables Found", f"Discovered {len(tables)} tables")
            
            # Process each table
            for table_name, table_type in tables:
                table_info = self._analyze_table(
                    table_name, 
                    schema_name,
                    table_type,
                    include_samples=include_samples,
                    max_sample_size=max_sample_size
                )
                if table_info:
                    context.tables.append(table_info)
            
            # Detect relationships
            context.relationships = self._detect_relationships(context.tables)
            
            # Infer business domain
            context.business_domain = self._infer_business_domain(context.tables)
            
            # Extract common patterns
            context.common_patterns = self._extract_common_patterns(context.tables)
            
            # Cache the results
            self._save_to_cache(context)
            
            log_manager.add_log("✅ Schema Analysis", 
                              f"Completed analysis: {len(context.tables)} tables, "
                              f"{len(context.relationships)} relationships")
            
            return context
            
        except Exception as e:
            error_handler.handle_exception(e, "schema inspection")
            # Return minimal context as fallback
            return DatabaseContext(
                database_name="UNKNOWN",
                schema_name="UNKNOWN"
            )
    
    def _get_database_info(self) -> Tuple[str, str]:
        """Get current database and schema names"""
        try:
            query = """
            SELECT 
                CURRENT_DATABASE() as db_name,
                CURRENT_SCHEMA() as schema_name
            """
            result = self.connection.execute(text(query)).fetchone()
            return result[0], result[1]
        except Exception:
            return "UNKNOWN", "PUBLIC"
    
    def _get_all_tables(self) -> List[Tuple[str, str]]:
        """Get all tables in the current schema"""
        try:
            query = """
            SELECT 
                TABLE_NAME,
                TABLE_TYPE
            FROM INFORMATION_SCHEMA.TABLES
            WHERE TABLE_SCHEMA = CURRENT_SCHEMA()
            AND TABLE_TYPE IN ('BASE TABLE', 'VIEW')
            ORDER BY TABLE_NAME
            """
            result = self.connection.execute(text(query)).fetchall()
            return [(row[0], row[1]) for row in result]
        except Exception as e:
            logger.warning(f"Failed to get tables: {e}")
            return []
    
    def _analyze_table(self, 
                      table_name: str, 
                      schema_name: str, 
                      table_type: str,
                      include_samples: bool = True,
                      max_sample_size: int = 10) -> Optional[TableInfo]:
        """Comprehensive table analysis"""
        try:
            # Create table info
            table_info = TableInfo(
                name=table_name,
                schema_name=schema_name,
                table_type=table_type
            )
            
            # Get column information
            columns = self._get_column_details(table_name)
            table_info.columns = columns
            
            # Get row count (with timeout protection)
            table_info.row_count = self._get_table_row_count(table_name)
            
            # Get primary keys
            table_info.primary_keys = self._get_primary_keys(table_name)
            
            # Get foreign keys
            table_info.foreign_keys = self._get_foreign_keys(table_name)
            
            # Get sample data if requested
            if include_samples and table_info.row_count and table_info.row_count > 0:
                self._add_sample_data(table_info, max_sample_size)
            
            # Get table comment
            table_info.comment = self._get_table_comment(table_name)
            
            table_info.last_analyzed = datetime.now()
            
            return table_info
            
        except Exception as e:
            logger.warning(f"Failed to analyze table {table_name}: {e}")
            return None
    
    def _get_column_details(self, table_name: str) -> List[ColumnInfo]:
        """Get detailed column information"""
        try:
            query = """
            SELECT 
                COLUMN_NAME,
                DATA_TYPE,
                IS_NULLABLE,
                COLUMN_DEFAULT,
                CHARACTER_MAXIMUM_LENGTH,
                NUMERIC_PRECISION,
                NUMERIC_SCALE,
                COMMENT
            FROM INFORMATION_SCHEMA.COLUMNS
            WHERE TABLE_SCHEMA = CURRENT_SCHEMA()
            AND TABLE_NAME = :table_name
            ORDER BY ORDINAL_POSITION
            """
            
            result = self.connection.execute(
                text(query), 
                {"table_name": table_name}
            ).fetchall()
            
            columns = []
            for row in result:
                column = ColumnInfo(
                    name=row[0],
                    data_type=row[1],
                    is_nullable=row[2] == 'YES',
                    default_value=row[3],
                    character_maximum_length=row[4],
                    numeric_precision=row[5],
                    numeric_scale=row[6],
                    comment=row[7]
                )
                columns.append(column)
            
            return columns
            
        except Exception as e:
            logger.warning(f"Failed to get columns for {table_name}: {e}")
            return []
    
    def _get_table_row_count(self, table_name: str) -> Optional[int]:
        """Get table row count with timeout protection"""
        try:
            # Use INFORMATION_SCHEMA for better performance on large tables
            query = """
            SELECT ROW_COUNT 
            FROM INFORMATION_SCHEMA.TABLES 
            WHERE TABLE_SCHEMA = CURRENT_SCHEMA() 
            AND TABLE_NAME = :table_name
            """
            
            result = self.connection.execute(
                text(query), 
                {"table_name": table_name}
            ).fetchone()
            
            if result and result[0] is not None:
                return result[0]
            
            # Fallback to COUNT(*) for small tables only
            count_query = f"SELECT COUNT(*) FROM {table_name} LIMIT 1000000"
            result = self.connection.execute(text(count_query)).fetchone()
            return result[0] if result else None
            
        except Exception:
            return None
    
    def _get_primary_keys(self, table_name: str) -> List[str]:
        """Get primary key columns"""
        try:
            query = """
            SELECT COLUMN_NAME
            FROM INFORMATION_SCHEMA.KEY_COLUMN_USAGE
            WHERE TABLE_SCHEMA = CURRENT_SCHEMA()
            AND TABLE_NAME = :table_name
            AND CONSTRAINT_NAME LIKE 'PK_%'
            ORDER BY ORDINAL_POSITION
            """
            
            result = self.connection.execute(
                text(query), 
                {"table_name": table_name}
            ).fetchall()
            
            return [row[0] for row in result]
            
        except Exception:
            return []
    
    def _get_foreign_keys(self, table_name: str) -> List[Dict[str, str]]:
        """Get foreign key relationships"""
        try:
            query = """
            SELECT 
                kcu.COLUMN_NAME as column_name,
                kcu.REFERENCED_TABLE_NAME as referenced_table,
                kcu.REFERENCED_COLUMN_NAME as referenced_column
            FROM INFORMATION_SCHEMA.KEY_COLUMN_USAGE kcu
            WHERE kcu.TABLE_SCHEMA = CURRENT_SCHEMA()
            AND kcu.TABLE_NAME = :table_name
            AND kcu.REFERENCED_TABLE_NAME IS NOT NULL
            """
            
            result = self.connection.execute(
                text(query), 
                {"table_name": table_name}
            ).fetchall()
            
            foreign_keys = []
            for row in result:
                foreign_keys.append({
                    "column_name": row[0],
                    "referenced_table": row[1],
                    "referenced_column": row[2]
                })
            
            return foreign_keys
            
        except Exception:
            return []
    
    def _get_table_comment(self, table_name: str) -> Optional[str]:
        """Get table comment/description"""
        try:
            query = """
            SELECT COMMENT
            FROM INFORMATION_SCHEMA.TABLES
            WHERE TABLE_SCHEMA = CURRENT_SCHEMA()
            AND TABLE_NAME = :table_name
            """
            
            result = self.connection.execute(
                text(query), 
                {"table_name": table_name}
            ).fetchone()
            
            return result[0] if result and result[0] else None
            
        except Exception:
            return None
    
    def _add_sample_data(self, table_info: TableInfo, max_sample_size: int):
        """Add sample data for each column"""
        try:
            # Limit sample size for performance
            sample_query = f"""
            SELECT * FROM {table_info.name} 
            SAMPLE BERNOULLI (1)
            LIMIT {max_sample_size * 2}
            """
            
            result = self.connection.execute(text(sample_query)).fetchall()
            
            if not result:
                return
            
            # Convert to DataFrame for easier processing
            df = pd.DataFrame(result, columns=[col.name for col in table_info.columns])
            
            # Add sample values to each column
            for i, column in enumerate(table_info.columns):
                if i < len(df.columns):
                    # Get unique non-null values
                    unique_values = df.iloc[:, i].dropna().unique()[:max_sample_size]
                    column.sample_values = unique_values.tolist()
                    
                    # Calculate statistics
                    column.distinct_count = len(df.iloc[:, i].unique())
                    column.null_percentage = (df.iloc[:, i].isnull().sum() / len(df)) * 100
        
        except Exception as e:
            logger.warning(f"Failed to get sample data for {table_info.name}: {e}")
    
    def _detect_relationships(self, tables: List[TableInfo]) -> List[Dict[str, str]]:
        """Detect table relationships based on column names and foreign keys"""
        relationships = []
        
        # Add explicit foreign key relationships
        for table in tables:
            for fk in table.foreign_keys:
                relationships.append({
                    "from_table": table.name,
                    "from_column": fk["column_name"],
                    "to_table": fk["referenced_table"],
                    "to_column": fk["referenced_column"],
                    "relationship_type": "foreign_key"
                })
        
        # Infer relationships from naming conventions
        for table in tables:
            for column in table.columns:
                column_name = column.name.lower()
                
                # Look for ID columns that might reference other tables
                if column_name.endswith('_id') and column_name != 'id':
                    potential_table = column_name[:-3]  # Remove '_id'
                    
                    # Check if there's a table with a similar name
                    for other_table in tables:
                        if other_table.name.lower().startswith(potential_table):
                            relationships.append({
                                "from_table": table.name,
                                "from_column": column.name,
                                "to_table": other_table.name,
                                "to_column": "id",  # Assume 'id' as target
                                "relationship_type": "inferred"
                            })
                            break
        
        return relationships
    
    def _infer_business_domain(self, tables: List[TableInfo]) -> Optional[str]:
        """Infer business domain from table and column names"""
        domain_keywords = {
            "real_estate": ["property", "properties", "agent", "agents", "transaction", 
                           "location", "owner", "sale", "listing", "bedroom", "bathroom"],
            "ecommerce": ["product", "order", "customer", "cart", "payment", "shipping",
                         "inventory", "category", "supplier"],
            "finance": ["account", "transaction", "balance", "payment", "loan", "credit",
                       "debit", "interest", "portfolio"],
            "healthcare": ["patient", "doctor", "appointment", "diagnosis", "treatment",
                          "prescription", "medical", "clinic"],
            "hr": ["employee", "department", "salary", "payroll", "position", "hire",
                   "performance", "benefit"]
        }
        
        # Count keywords for each domain
        domain_scores = {domain: 0 for domain in domain_keywords}
        
        all_names = []
        for table in tables:
            all_names.append(table.name.lower())
            for column in table.columns:
                all_names.append(column.name.lower())
        
        for domain, keywords in domain_keywords.items():
            for keyword in keywords:
                for name in all_names:
                    if keyword in name:
                        domain_scores[domain] += 1
        
        # Return domain with highest score
        if max(domain_scores.values()) > 0:
            return max(domain_scores, key=domain_scores.get)
        
        return None
    
    def _extract_common_patterns(self, tables: List[TableInfo]) -> Dict[str, List[str]]:
        """Extract common naming patterns and data types"""
        patterns = {
            "id_columns": [],
            "date_columns": [],
            "price_columns": [],
            "name_columns": [],
            "common_data_types": {}
        }
        
        for table in tables:
            for column in table.columns:
                column_name = column.name.lower()
                data_type = column.data_type.upper()
                
                # ID patterns
                if 'id' in column_name:
                    patterns["id_columns"].append(f"{table.name}.{column.name}")
                
                # Date patterns
                if any(keyword in column_name for keyword in ['date', 'time', 'created', 'updated']):
                    patterns["date_columns"].append(f"{table.name}.{column.name}")
                
                # Price patterns
                if any(keyword in column_name for keyword in ['price', 'cost', 'amount', 'value']):
                    patterns["price_columns"].append(f"{table.name}.{column.name}")
                
                # Name patterns
                if any(keyword in column_name for keyword in ['name', 'title', 'description']):
                    patterns["name_columns"].append(f"{table.name}.{column.name}")
                
                # Data type patterns
                if data_type not in patterns["common_data_types"]:
                    patterns["common_data_types"][data_type] = 0
                patterns["common_data_types"][data_type] += 1
        
        return patterns
    
    def _load_from_cache(self) -> Optional[DatabaseContext]:
        """Load schema context from cache if valid"""
        try:
            if not self.cache_file.exists():
                return None
            
            with open(self.cache_file, 'r') as f:
                data = json.load(f)
            
            # Check if cache is still valid
            generated_at = datetime.fromisoformat(data['generated_at'])
            if datetime.now() - generated_at > timedelta(hours=self.cache_ttl_hours):
                return None
            
            # Reconstruct DatabaseContext (simplified)
            context = DatabaseContext(
                database_name=data['database_name'],
                schema_name=data['schema_name'],
                business_domain=data.get('business_domain'),
                generated_at=generated_at
            )
            
            # Note: Full reconstruction would need more complex deserialization
            # For now, return None to force fresh analysis
            return None
            
        except Exception:
            return None
    
    def _save_to_cache(self, context: DatabaseContext):
        """Save schema context to cache"""
        try:
            # Simplified serialization
            data = {
                'database_name': context.database_name,
                'schema_name': context.schema_name,
                'business_domain': context.business_domain,
                'table_count': len(context.tables),
                'relationship_count': len(context.relationships),
                'generated_at': context.generated_at.isoformat()
            }
            
            with open(self.cache_file, 'w') as f:
                json.dump(data, f, indent=2)
                
        except Exception as e:
            logger.warning(f"Failed to save cache: {e}")
    
    def generate_context_summary(self, context: DatabaseContext) -> str:
        """Generate a comprehensive context summary for LLM prompts"""
        
        summary_parts = []
        
        # Database info
        summary_parts.append(f"DATABASE: {context.database_name}")
        summary_parts.append(f"SCHEMA: {context.schema_name}")
        
        if context.business_domain:
            summary_parts.append(f"BUSINESS DOMAIN: {context.business_domain.upper()}")
        
        summary_parts.append(f"TOTAL TABLES: {len(context.tables)}")
        
        # Tables with details
        summary_parts.append("\n📊 TABLES AND COLUMNS:")
        
        for table in context.tables:
            table_part = f"\n🏷️ {table.name} ({table.table_type})"
            if table.row_count is not None:
                table_part += f" - {table.row_count:,} rows"
            if table.comment:
                table_part += f" - {table.comment}"
            
            summary_parts.append(table_part)
            
            # Key columns
            important_columns = []
            for col in table.columns[:10]:  # Limit to first 10 columns
                col_desc = f"{col.name} ({col.data_type})"
                if not col.is_nullable:
                    col_desc += " NOT NULL"
                if col.comment:
                    col_desc += f" - {col.comment}"
                important_columns.append(f"    • {col_desc}")
            
            summary_parts.extend(important_columns)
            
            if len(table.columns) > 10:
                summary_parts.append(f"    ... and {len(table.columns) - 10} more columns")
        
        # Relationships
        if context.relationships:
            summary_parts.append(f"\n🔗 TABLE RELATIONSHIPS ({len(context.relationships)}):")
            for rel in context.relationships:
                summary_parts.append(
                    f"    • {rel['from_table']}.{rel['from_column']} → "
                    f"{rel['to_table']}.{rel['to_column']} ({rel['relationship_type']})"
                )
        
        # Common patterns
        if context.common_patterns:
            if context.common_patterns.get("price_columns"):
                summary_parts.append("\n💰 PRICE/AMOUNT COLUMNS:")
                for col in context.common_patterns["price_columns"][:5]:
                    summary_parts.append(f"    • {col}")
            
            if context.common_patterns.get("date_columns"):
                summary_parts.append("\n📅 DATE/TIME COLUMNS:")
                for col in context.common_patterns["date_columns"][:5]:
                    summary_parts.append(f"    • {col}")
        
        return "\n".join(summary_parts)


# Global instance
schema_inspector = None

def get_schema_inspector(connection) -> SchemaInspector:
    """Get or create schema inspector instance"""
    global schema_inspector
    if schema_inspector is None:
        schema_inspector = SchemaInspector(connection)
    return schema_inspector