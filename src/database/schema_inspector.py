"""
Inspector de esquemas de Snowflake
"""
import streamlit as st
from typing import Dict, List, Any, Optional
import pandas as pd
import logging

logger = logging.getLogger(__name__)

class SchemaInspector:
    """Clase para inspeccionar esquemas de Snowflake"""
    
    def __init__(self, connection):
        self.connection = connection
        
    def get_available_tables(self, schema: str = None) -> List[Dict[str, str]]:
        """Obtiene lista de tablas disponibles"""
        try:
            cursor = self.connection.cursor()
            
            if schema:
                query = f"""
                SELECT TABLE_NAME, TABLE_TYPE, COMMENT
                FROM INFORMATION_SCHEMA.TABLES 
                WHERE TABLE_SCHEMA = '{schema.upper()}'
                ORDER BY TABLE_NAME
                """
            else:
                query = """
                SELECT TABLE_SCHEMA, TABLE_NAME, TABLE_TYPE, COMMENT
                FROM INFORMATION_SCHEMA.TABLES 
                WHERE TABLE_SCHEMA NOT IN ('INFORMATION_SCHEMA', 'ACCOUNT_USAGE')
                ORDER BY TABLE_SCHEMA, TABLE_NAME
                """
            
            cursor.execute(query)
            results = cursor.fetchall()
            
            tables = []
            for row in results:
                if schema:
                    table_info = {
                        'name': row[0],
                        'type': row[1],
                        'comment': row[2] or 'Sin descripción'
                    }
                else:
                    table_info = {
                        'schema': row[0],
                        'name': row[1],
                        'type': row[2],
                        'comment': row[3] or 'Sin descripción'
                    }
                tables.append(table_info)
            
            return tables
            
        except Exception as e:
            logger.error(f"Error obteniendo tablas: {str(e)}")
            return []
    
    def get_table_columns(self, table_name: str, schema: str = None) -> List[Dict[str, Any]]:
        """Obtiene información de columnas de una tabla"""
        try:
            cursor = self.connection.cursor()
            
            if schema:
                query = f"""
                SELECT COLUMN_NAME, DATA_TYPE, IS_NULLABLE, COLUMN_DEFAULT, COMMENT
                FROM INFORMATION_SCHEMA.COLUMNS 
                WHERE TABLE_SCHEMA = '{schema.upper()}' 
                AND TABLE_NAME = '{table_name.upper()}'
                ORDER BY ORDINAL_POSITION
                """
            else:
                # Usar schema por defecto de la configuración
                from src.utils.config import config
                query = f"""
                SELECT COLUMN_NAME, DATA_TYPE, IS_NULLABLE, COLUMN_DEFAULT, COMMENT
                FROM INFORMATION_SCHEMA.COLUMNS 
                WHERE TABLE_SCHEMA = '{config.SNOWFLAKE_SCHEMA}' 
                AND TABLE_NAME = '{table_name.upper()}'
                ORDER BY ORDINAL_POSITION
                """
            
            cursor.execute(query)
            results = cursor.fetchall()
            
            columns = []
            for row in results:
                column_info = {
                    'name': row[0],
                    'type': row[1],
                    'nullable': row[2] == 'YES',
                    'default': row[3],
                    'comment': row[4] or 'Sin descripción'
                }
                columns.append(column_info)
            
            return columns
            
        except Exception as e:
            logger.error(f"Error obteniendo columnas de {table_name}: {str(e)}")
            return []
    
    def get_table_sample(self, table_name: str, schema: str = None, limit: int = 5) -> pd.DataFrame:
        """Obtiene una muestra de datos de la tabla"""
        try:
            if schema:
                full_table_name = f"{schema}.{table_name}"
            else:
                from src.utils.config import config
                full_table_name = f"{config.SNOWFLAKE_SCHEMA}.{table_name}"
            
            query = f"SELECT * FROM {full_table_name} LIMIT {limit}"
            
            cursor = self.connection.cursor()
            cursor.execute(query)
            results = cursor.fetchall()
            columns = [desc[0] for desc in cursor.description]
            
            # Crear DataFrame
            df = pd.DataFrame(results, columns=columns)
            return df
            
        except Exception as e:
            logger.error(f"Error obteniendo muestra de {table_name}: {str(e)}")
            return pd.DataFrame()
    
    def get_table_stats(self, table_name: str, schema: str = None) -> Dict[str, Any]:
        """Obtiene estadísticas básicas de la tabla"""
        try:
            if schema:
                full_table_name = f"{schema}.{table_name}"
            else:
                from src.utils.config import config
                full_table_name = f"{config.SNOWFLAKE_SCHEMA}.{table_name}"
            
            cursor = self.connection.cursor()
            
            # Contar filas
            cursor.execute(f"SELECT COUNT(*) FROM {full_table_name}")
            row_count = cursor.fetchone()[0]
            
            # Obtener información de la tabla
            cursor.execute(f"""
                SELECT TABLE_SCHEMA, TABLE_NAME, TABLE_TYPE, CREATED, LAST_ALTERED
                FROM INFORMATION_SCHEMA.TABLES
                WHERE TABLE_NAME = '{table_name.upper()}'
                AND TABLE_SCHEMA = '{schema.upper() if schema else config.SNOWFLAKE_SCHEMA}'
            """)
            table_info = cursor.fetchone()
            
            stats = {
                'row_count': row_count,
                'schema': table_info[0] if table_info else 'Unknown',
                'name': table_info[1] if table_info else table_name,
                'type': table_info[2] if table_info else 'Unknown',
                'created': str(table_info[3]) if table_info and table_info[3] else 'Unknown',
                'last_altered': str(table_info[4]) if table_info and table_info[4] else 'Unknown'
            }
            
            return stats
            
        except Exception as e:
            logger.error(f"Error obteniendo estadísticas de {table_name}: {str(e)}")
            return {}
    
    def get_schemas(self) -> List[str]:
        """Obtiene lista de esquemas disponibles"""
        try:
            cursor = self.connection.cursor()
            cursor.execute("""
                SELECT SCHEMA_NAME 
                FROM INFORMATION_SCHEMA.SCHEMATA 
                WHERE SCHEMA_NAME NOT IN ('INFORMATION_SCHEMA', 'ACCOUNT_USAGE')
                ORDER BY SCHEMA_NAME
            """)
            results = cursor.fetchall()
            return [row[0] for row in results]
            
        except Exception as e:
            logger.error(f"Error obteniendo esquemas: {str(e)}")
            return []
    
    def search_tables(self, search_term: str) -> List[Dict[str, str]]:
        """Busca tablas que contengan el término de búsqueda"""
        try:
            cursor = self.connection.cursor()
            query = f"""
            SELECT TABLE_SCHEMA, TABLE_NAME, TABLE_TYPE, COMMENT
            FROM INFORMATION_SCHEMA.TABLES 
            WHERE UPPER(TABLE_NAME) LIKE '%{search_term.upper()}%'
            AND TABLE_SCHEMA NOT IN ('INFORMATION_SCHEMA', 'ACCOUNT_USAGE')
            ORDER BY TABLE_SCHEMA, TABLE_NAME
            """
            
            cursor.execute(query)
            results = cursor.fetchall()
            
            tables = []
            for row in results:
                table_info = {
                    'schema': row[0],
                    'name': row[1],
                    'type': row[2],
                    'comment': row[3] or 'Sin descripción'
                }
                tables.append(table_info)
            
            return tables
            
        except Exception as e:
            logger.error(f"Error buscando tablas con '{search_term}': {str(e)}")
            return []
    
    def get_table_relationships(self, table_name: str, schema: str = None) -> Dict[str, List]:
        """Obtiene información sobre relaciones de la tabla (foreign keys, etc.)"""
        try:
            cursor = self.connection.cursor()
            
            if schema:
                schema_filter = f"'{schema.upper()}'"
            else:
                from src.utils.config import config
                schema_filter = f"'{config.SNOWFLAKE_SCHEMA}'"
            
            # Obtener foreign keys
            query = f"""
            SELECT 
                CONSTRAINT_NAME,
                CONSTRAINT_TYPE,
                COLUMN_NAME
            FROM INFORMATION_SCHEMA.KEY_COLUMN_USAGE
            WHERE TABLE_SCHEMA = {schema_filter}
            AND TABLE_NAME = '{table_name.upper()}'
            """
            
            cursor.execute(query)
            constraints = cursor.fetchall()
            
            relationships = {
                'foreign_keys': [],
                'primary_keys': [],
                'unique_keys': []
            }
            
            for constraint in constraints:
                constraint_info = {
                    'name': constraint[0],
                    'type': constraint[1],
                    'column': constraint[2]
                }
                
                if constraint[1] == 'FOREIGN KEY':
                    relationships['foreign_keys'].append(constraint_info)
                elif constraint[1] == 'PRIMARY KEY':
                    relationships['primary_keys'].append(constraint_info)
                elif constraint[1] == 'UNIQUE':
                    relationships['unique_keys'].append(constraint_info)
            
            return relationships
            
        except Exception as e:
            logger.error(f"Error obteniendo relaciones de {table_name}: {str(e)}")
            return {'foreign_keys': [], 'primary_keys': [], 'unique_keys': []}
