"""
Dynamic Schema Inspector for Enhanced Database Context

This module provides comprehensive database schema inspection capabilities
to improve LLM context for SQL generation.
"""

import hashlib
import json
import logging
import re
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import pandas as pd
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError, OperationalError, ProgrammingError, DatabaseError

from src.utils.helpers import error_handler, log_manager

logger = logging.getLogger(__name__)


def validate_table_name(table_name: str) -> str:
    """Validate and sanitize table name to prevent SQL injection.
    
    Args:
        table_name: Table name to validate
        
    Returns:
        Validated table name
        
    Raises:
        ValueError: If table name is invalid
    """
    if not table_name or not isinstance(table_name, str):
        raise ValueError(f"Table name must be a non-empty string, got: {type(table_name)}")
    
    # Remove leading/trailing whitespace
    table_name = table_name.strip()
    
    # Snowflake identifier rules:
    # - Must start with letter or underscore
    # - Can contain letters, digits, underscores
    # - Max 255 characters
    # - Case-insensitive (will be uppercased)
    
    # Strict validation pattern
    valid_pattern = r'^[a-zA-Z_][a-zA-Z0-9_]*$'
    
    if not re.match(valid_pattern, table_name):
        raise ValueError(
            f"Invalid table name '{table_name}'. "
            f"Table names must start with a letter or underscore and contain only "
            f"letters, digits, and underscores."
        )
    
    if len(table_name) > 255:
        raise ValueError(f"Table name too long: {len(table_name)} characters (max 255)")
    
    # Return uppercase (Snowflake standard)
    return table_name.upper()


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
        self.engine = connection  # This is actually an SQLAlchemy Engine
        self.cache_ttl_hours = cache_ttl_hours
        self.cache_file = Path("data/schema_cache.json")
        self.cache_file.parent.mkdir(exist_ok=True)
        self._table_cache: Optional[List[str]] = None  # Cache of table names for validation

    def get_comprehensive_context(
        self,
        refresh_cache: bool = False,
        include_samples: bool = True,
        max_sample_size: int = 10,
    ) -> DatabaseContext:
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
            log_manager.add_log(
                "🔍 Schema Inspector", "Starting comprehensive schema analysis"
            )

            # Check cache first
            if not refresh_cache:
                cached_context = self._load_from_cache()
                if cached_context:
                    log_manager.add_log(
                        "📋 Schema Cache", "Using cached schema context"
                    )
                    return cached_context

            # Get database basic info
            db_name, schema_name = self._get_database_info()

            # Initialize context
            context = DatabaseContext(database_name=db_name, schema_name=schema_name)

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
                    max_sample_size=max_sample_size,
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

            log_manager.add_log(
                "✅ Schema Analysis",
                f"Completed analysis: {len(context.tables)} tables, "
                f"{len(context.relationships)} relationships",
            )

            return context

        except OperationalError as e:
            logger.error(f"Database connection error during schema inspection: {e}")
            error_handler.handle_exception(e, "schema inspection")
            return DatabaseContext(database_name="UNKNOWN", schema_name="UNKNOWN")
        except ProgrammingError as e:
            logger.error(f"SQL error during schema inspection: {e}")
            error_handler.handle_exception(e, "schema inspection")
            return DatabaseContext(database_name="UNKNOWN", schema_name="UNKNOWN")
        except SQLAlchemyError as e:
            logger.error(f"Database error during schema inspection: {e}")
            error_handler.handle_exception(e, "schema inspection")
            return DatabaseContext(database_name="UNKNOWN", schema_name="UNKNOWN")
        except Exception as e:
            logger.exception(f"Unexpected error during schema inspection: {e}")
            error_handler.handle_exception(e, "schema inspection")
            return DatabaseContext(database_name="UNKNOWN", schema_name="UNKNOWN")

    def _get_database_info(self) -> Tuple[str, str]:
        """Get current database and schema names"""
        try:
            query = """
            SELECT 
                CURRENT_DATABASE() as db_name,
                CURRENT_SCHEMA() as schema_name
            """
            with self.engine.connect() as connection:
                result = connection.execute(text(query)).fetchone()
                return result[0], result[1]
        except OperationalError as e:
            logger.error(f"Database connection error getting database info: {e}")
            return "UNKNOWN", "PUBLIC"
        except ProgrammingError as e:
            logger.error(f"SQL error getting database info: {e}")
            return "UNKNOWN", "PUBLIC"
        except SQLAlchemyError as e:
            logger.warning(f"Database error getting database info: {e}")
            return "UNKNOWN", "PUBLIC"
        except Exception as e:
            logger.warning(f"Unexpected error getting database info: {e}")
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
            with self.engine.connect() as connection:
                result = connection.execute(text(query)).fetchall()
                tables = [(row[0], row[1]) for row in result]
                # Update table cache for validation
                self._table_cache = [table[0].upper() for table in tables]
                return tables
        except OperationalError as e:
            logger.error(f"Database connection error getting tables: {e}")
            return []
        except ProgrammingError as e:
            logger.error(f"SQL error getting tables: {e}")
            return []
        except SQLAlchemyError as e:
            logger.warning(f"Database error getting tables: {e}")
            return []
        except Exception as e:
            logger.warning(f"Unexpected error getting tables: {e}")
            return []

    def validate_table_exists(self, table_name: str) -> bool:
        """Validate that a table exists in the current schema.
        
        Args:
            table_name: Table name to validate
            
        Returns:
            True if table exists, False otherwise
        """
        try:
            # First validate format
            validated_name = validate_table_name(table_name)
            
            # Check cache first
            if self._table_cache is None:
                # Refresh cache by getting tables
                self._get_all_tables()
            
            # Check if table exists in cache
            if self._table_cache and validated_name in self._table_cache:
                return True
            
            # If not in cache, query database directly
            query = text("""
                SELECT COUNT(*) 
                FROM INFORMATION_SCHEMA.TABLES 
                WHERE TABLE_SCHEMA = CURRENT_SCHEMA() 
                AND UPPER(TABLE_NAME) = :table_name
                AND TABLE_TYPE IN ('BASE TABLE', 'VIEW')
            """)
            with self.engine.connect() as connection:
                result = connection.execute(query, {"table_name": validated_name}).fetchone()
                exists = result and result[0] > 0
                
                # Update cache if found
                if exists and validated_name not in (self._table_cache or []):
                    if self._table_cache is None:
                        self._table_cache = []
                    self._table_cache.append(validated_name)
                
                return exists
        except ValueError:
            # Invalid table name format
            return False
        except OperationalError as e:
            logger.error(f"Database connection error validating table existence: {e}")
            return False
        except ProgrammingError as e:
            logger.error(f"SQL error validating table existence: {e}")
            return False
        except SQLAlchemyError as e:
            logger.warning(f"Database error validating table existence: {e}")
            return False
        except Exception as e:
            logger.warning(f"Unexpected error validating table existence: {e}")
            return False

    def get_similar_table_names(self, table_name: str, limit: int = 5) -> List[str]:
        """Get similar table names for suggestions when a table doesn't exist.
        
        Args:
            table_name: Table name to find similar matches for
            limit: Maximum number of suggestions
            
        Returns:
            List of similar table names
        """
        try:
            validated_name = validate_table_name(table_name)
            
            # Get all tables
            if self._table_cache is None:
                self._get_all_tables()
            
            if not self._table_cache:
                return []
            
            # Simple similarity: tables that contain the search term or vice versa
            validated_lower = validated_name.lower()
            similar = []
            
            for cached_table in self._table_cache:
                cached_lower = cached_table.lower()
                if validated_lower in cached_lower or cached_lower in validated_lower:
                    similar.append(cached_table)
                elif validated_lower[:3] == cached_lower[:3]:  # Same first 3 chars
                    similar.append(cached_table)
                
                if len(similar) >= limit:
                    break
            
            return similar[:limit]
        except ValueError:
            # Invalid table name format
            return []
        except Exception as e:
            logger.warning(f"Unexpected error getting similar table names: {e}")
            return []

    def _analyze_table(
        self,
        table_name: str,
        schema_name: str,
        table_type: str,
        include_samples: bool = True,
        max_sample_size: int = 10,
    ) -> Optional[TableInfo]:
        """Comprehensive table analysis"""
        try:
            # Create table info
            table_info = TableInfo(
                name=table_name, schema_name=schema_name, table_type=table_type
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

            with self.engine.connect() as connection:
                result = connection.execute(
                    text(query), {"table_name": table_name}
                ).fetchall()

            columns = []
            for row in result:
                column = ColumnInfo(
                    name=row[0],
                    data_type=row[1],
                    is_nullable=row[2] == "YES",
                    default_value=row[3],
                    character_maximum_length=row[4],
                    numeric_precision=row[5],
                    numeric_scale=row[6],
                    comment=row[7],
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

            with self.engine.connect() as connection:
                result = connection.execute(
                    text(query), {"table_name": table_name}
                ).fetchone()

            if result and result[0] is not None:
                return result[0]

            # Fallback to COUNT(*) for small tables only
            # Validate table name to prevent SQL injection
            try:
                validated_table = validate_table_name(table_name)
                count_query = text(f"SELECT COUNT(*) FROM {validated_table} LIMIT 1000000")
                with self.engine.connect() as connection:
                    result = connection.execute(count_query).fetchone()
                return result[0] if result else None
            except ValueError as e:
                logger.warning(f"Invalid table name for COUNT query: {e}")
                return None

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

            with self.engine.connect() as connection:
                result = connection.execute(
                    text(query), {"table_name": table_name}
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

            with self.engine.connect() as connection:
                result = connection.execute(
                    text(query), {"table_name": table_name}
                ).fetchall()

            foreign_keys = []
            for row in result:
                foreign_keys.append(
                    {
                        "column_name": row[0],
                        "referenced_table": row[1],
                        "referenced_column": row[2],
                    }
                )

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

            with self.engine.connect() as connection:
                result = connection.execute(
                    text(query), {"table_name": table_name}
                ).fetchone()

            return result[0] if result and result[0] else None

        except Exception:
            return None

    def _add_sample_data(self, table_info: TableInfo, max_sample_size: int):
        """Add sample data for each column"""
        try:
            # Validate table name to prevent SQL injection
            validated_table = validate_table_name(table_info.name)
            
            # Limit sample size for performance
            # Use text() with validated table name
            sample_query = text(f"""
            SELECT * FROM {validated_table} 
            SAMPLE BERNOULLI (1)
            LIMIT :max_size
            """).bindparams(max_size=max_sample_size * 2)

            with self.engine.connect() as connection:
                result = connection.execute(sample_query).fetchall()

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
                    column.null_percentage = (
                        df.iloc[:, i].isnull().sum() / len(df)
                    ) * 100

        except Exception as e:
            logger.warning(f"Failed to get sample data for {table_info.name}: {e}")

    def _detect_relationships(self, tables: List[TableInfo]) -> List[Dict[str, str]]:
        """Detect table relationships based on column names and foreign keys"""
        relationships = []

        # Add explicit foreign key relationships
        for table in tables:
            for fk in table.foreign_keys:
                relationships.append(
                    {
                        "from_table": table.name,
                        "from_column": fk["column_name"],
                        "to_table": fk["referenced_table"],
                        "to_column": fk["referenced_column"],
                        "relationship_type": "foreign_key",
                    }
                )

        # Infer relationships from naming conventions
        for table in tables:
            for column in table.columns:
                column_name = column.name.lower()

                # Look for ID columns that might reference other tables
                if column_name.endswith("_id") and column_name != "id":
                    potential_table = column_name[:-3]  # Remove '_id'

                    # Check if there's a table with a similar name
                    for other_table in tables:
                        if other_table.name.lower().startswith(potential_table):
                            relationships.append(
                                {
                                    "from_table": table.name,
                                    "from_column": column.name,
                                    "to_table": other_table.name,
                                    "to_column": "id",  # Assume 'id' as target
                                    "relationship_type": "inferred",
                                }
                            )
                            break

        return relationships

    def _infer_business_domain(self, tables: List[TableInfo]) -> Optional[str]:
        """Infer business domain from table and column names"""
        domain_keywords = {
            "real_estate": [
                "property",
                "properties",
                "agent",
                "agents",
                "transaction",
                "location",
                "owner",
                "sale",
                "listing",
                "bedroom",
                "bathroom",
            ],
            "ecommerce": [
                "product",
                "order",
                "customer",
                "cart",
                "payment",
                "shipping",
                "inventory",
                "category",
                "supplier",
            ],
            "finance": [
                "account",
                "transaction",
                "balance",
                "payment",
                "loan",
                "credit",
                "debit",
                "interest",
                "portfolio",
            ],
            "healthcare": [
                "patient",
                "doctor",
                "appointment",
                "diagnosis",
                "treatment",
                "prescription",
                "medical",
                "clinic",
            ],
            "hr": [
                "employee",
                "department",
                "salary",
                "payroll",
                "position",
                "hire",
                "performance",
                "benefit",
            ],
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
            "common_data_types": {},
        }

        for table in tables:
            for column in table.columns:
                column_name = column.name.lower()
                data_type = column.data_type.upper()

                # ID patterns
                if "id" in column_name:
                    patterns["id_columns"].append(f"{table.name}.{column.name}")

                # Date patterns
                if any(
                    keyword in column_name
                    for keyword in ["date", "time", "created", "updated"]
                ):
                    patterns["date_columns"].append(f"{table.name}.{column.name}")

                # Price patterns
                if any(
                    keyword in column_name
                    for keyword in ["price", "cost", "amount", "value"]
                ):
                    patterns["price_columns"].append(f"{table.name}.{column.name}")

                # Name patterns
                if any(
                    keyword in column_name
                    for keyword in ["name", "title", "description"]
                ):
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

            with open(self.cache_file, "r", encoding="utf-8") as f:
                data = json.load(f)

            # Check if cache is still valid
            generated_at = datetime.fromisoformat(data["generated_at"])
            if datetime.now() - generated_at > timedelta(hours=self.cache_ttl_hours):
                logger.info("Cache expired, will refresh")
                return None

            # Reconstruct DatabaseContext with full deserialization
            tables = []
            for table_data in data.get("tables", []):
                # Deserialize columns
                columns = []
                for col_data in table_data.get("columns", []):
                    column = ColumnInfo(
                        name=col_data["name"],
                        data_type=col_data["data_type"],
                        is_nullable=col_data["is_nullable"],
                        default_value=col_data.get("default_value"),
                        character_maximum_length=col_data.get("character_maximum_length"),
                        numeric_precision=col_data.get("numeric_precision"),
                        numeric_scale=col_data.get("numeric_scale"),
                        comment=col_data.get("comment"),
                        sample_values=col_data.get("sample_values", []),
                        distinct_count=col_data.get("distinct_count"),
                        null_percentage=col_data.get("null_percentage"),
                    )
                    columns.append(column)

                # Deserialize table
                table = TableInfo(
                    name=table_data["name"],
                    schema_name=table_data["schema_name"],
                    table_type=table_data["table_type"],
                    row_count=table_data.get("row_count"),
                    columns=columns,
                    primary_keys=table_data.get("primary_keys", []),
                    foreign_keys=table_data.get("foreign_keys", []),
                    indexes=table_data.get("indexes", []),
                    comment=table_data.get("comment"),
                    created_date=(
                        datetime.fromisoformat(table_data["created_date"])
                        if table_data.get("created_date")
                        else None
                    ),
                    last_analyzed=(
                        datetime.fromisoformat(table_data["last_analyzed"])
                        if table_data.get("last_analyzed")
                        else None
                    ),
                )
                tables.append(table)

            # Reconstruct context
            context = DatabaseContext(
                database_name=data["database_name"],
                schema_name=data["schema_name"],
                tables=tables,
                relationships=data.get("relationships", []),
                common_patterns=data.get("common_patterns", {}),
                business_domain=data.get("business_domain"),
                generated_at=generated_at,
            )

            logger.info(f"Loaded schema cache with {len(tables)} tables")
            return context

        except (json.JSONDecodeError, KeyError, ValueError) as e:
            logger.warning(f"Failed to load cache: {e}, will refresh")
            return None
        except Exception as e:
            logger.warning(f"Unexpected error loading cache: {e}, will refresh")
            return None

    def _save_to_cache(self, context: DatabaseContext):
        """Save schema context to cache with full serialization"""
        try:
            # Serialize tables with all their information
            tables_data = []
            for table in context.tables:
                # Serialize columns
                columns_data = []
                for column in table.columns:
                    col_data = {
                        "name": column.name,
                        "data_type": column.data_type,
                        "is_nullable": column.is_nullable,
                        "default_value": column.default_value,
                        "character_maximum_length": column.character_maximum_length,
                        "numeric_precision": column.numeric_precision,
                        "numeric_scale": column.numeric_scale,
                        "comment": column.comment,
                        "sample_values": column.sample_values,
                        "distinct_count": column.distinct_count,
                        "null_percentage": column.null_percentage,
                    }
                    columns_data.append(col_data)

                # Serialize table
                table_data = {
                    "name": table.name,
                    "schema_name": table.schema_name,
                    "table_type": table.table_type,
                    "row_count": table.row_count,
                    "columns": columns_data,
                    "primary_keys": table.primary_keys,
                    "foreign_keys": table.foreign_keys,
                    "indexes": table.indexes,
                    "comment": table.comment,
                    "created_date": (
                        table.created_date.isoformat() if table.created_date else None
                    ),
                    "last_analyzed": (
                        table.last_analyzed.isoformat() if table.last_analyzed else None
                    ),
                }
                tables_data.append(table_data)

            # Complete serialization
            data = {
                "database_name": context.database_name,
                "schema_name": context.schema_name,
                "tables": tables_data,
                "relationships": context.relationships,
                "common_patterns": context.common_patterns,
                "business_domain": context.business_domain,
                "generated_at": context.generated_at.isoformat(),
                "table_count": len(context.tables),
                "relationship_count": len(context.relationships),
            }

            with open(self.cache_file, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2, default=str)

            logger.info(f"Saved schema cache with {len(context.tables)} tables")

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
                summary_parts.append(
                    f"    ... and {len(table.columns) - 10} more columns"
                )

        # Relationships
        if context.relationships:
            summary_parts.append(
                f"\n🔗 TABLE RELATIONSHIPS ({len(context.relationships)}):"
            )
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
