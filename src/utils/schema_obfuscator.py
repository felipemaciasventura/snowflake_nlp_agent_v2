"""
Schema Obfuscator - Hybrid Security Layer for SQL Generation

This module provides a security layer that obfuscates real database schema names
while maintaining semantic meaning for better LLM understanding.
"""

import re
import logging
from typing import Dict, List, Tuple, Optional

logger = logging.getLogger(__name__)


class SchemaObfuscator:
    """
    Hybrid schema obfuscation that maintains semantic meaning while hiding real names.
    
    Maps real table/column names to semantically clear but obfuscated names.
    Provides bidirectional translation for secure SQL generation.
    """
    
    # Hybrid mapping: real_name -> obfuscated_but_semantic_name
    TABLE_MAPPING = {
        'properties': 'real_estate_items',
        'locations': 'geographic_areas', 
        'agents': 'sales_representatives',
        'transactions': 'commercial_events',
        'owners': 'property_holders'
    }
    
    COLUMN_MAPPING = {
        # Properties/real_estate_items columns
        'properties.property_id': 'real_estate_items.item_id',
        'properties.location_id': 'real_estate_items.area_ref',
        'properties.price': 'real_estate_items.monetary_value',
        'properties.bedrooms': 'real_estate_items.sleeping_rooms',
        'properties.bathrooms': 'real_estate_items.bath_facilities',
        'properties.sqft': 'real_estate_items.floor_area',
        'properties.property_type': 'real_estate_items.item_category',
        'properties.status': 'real_estate_items.current_state',
        'properties.owner_id': 'real_estate_items.holder_ref',
        'properties.listing_agent_id': 'real_estate_items.rep_ref',
        
        # Locations/geographic_areas columns  
        'locations.location_id': 'geographic_areas.area_id',
        'locations.city': 'geographic_areas.city_name',
        'locations.state': 'geographic_areas.state_name',
        'locations.county': 'geographic_areas.county_name',
        'locations.zipcode': 'geographic_areas.postal_code',
        'locations.population': 'geographic_areas.resident_count',
        'locations.median_income': 'geographic_areas.income_median',
        'locations.avg_sale_price': 'geographic_areas.price_average',
        
        # Agents/sales_representatives columns
        'agents.agent_id': 'sales_representatives.rep_id',
        'agents.first_name': 'sales_representatives.first_name',
        'agents.last_name': 'sales_representatives.last_name',
        'agents.agency': 'sales_representatives.company_name',
        'agents.transaction_count': 'sales_representatives.deal_count',
        'agents.avg_sale_price': 'sales_representatives.average_deal_value',
        'agents.commission_rate': 'sales_representatives.fee_percentage',
        
        # Transactions/commercial_events columns
        'transactions.transaction_id': 'commercial_events.event_id',
        'transactions.property_id': 'commercial_events.item_ref',
        'transactions.agent_id': 'commercial_events.rep_ref',
        'transactions.sale_date': 'commercial_events.completion_date',
        'transactions.sale_price': 'commercial_events.final_amount',
        'transactions.days_on_market': 'commercial_events.market_duration',
        
        # Owners/property_holders columns
        'owners.owner_id': 'property_holders.holder_id',
        'owners.first_name': 'property_holders.first_name',
        'owners.last_name': 'property_holders.last_name',
        'owners.num_properties_owned': 'property_holders.item_count',
        'owners.total_portfolio_value': 'property_holders.portfolio_worth',
        'owners.investor_flag': 'property_holders.investor_status'
    }
    
    # Create reverse mappings for translation back to real names
    REVERSE_TABLE_MAPPING = {v: k for k, v in TABLE_MAPPING.items()}
    REVERSE_COLUMN_MAPPING = {v: k for k, v in COLUMN_MAPPING.items()}
    
    @classmethod
    def get_obfuscated_schema_info(cls) -> str:
        """
        Generate schema information using obfuscated names for LLM prompt.
        """
        return """
🏡 REAL ESTATE DATABASE SCHEMA (Secure Names):

**Main Tables:**
- REAL_ESTATE_ITEMS: Property information (item_id, monetary_value, sleeping_rooms, bath_facilities, floor_area, item_category)
- GEOGRAPHIC_AREAS: Location data (area_id, city_name, state_name, resident_count, income_median, price_average)
- SALES_REPRESENTATIVES: Agent information (rep_id, first_name, last_name, deal_count, average_deal_value, fee_percentage)
- COMMERCIAL_EVENTS: Transaction records (event_id, completion_date, final_amount, market_duration)
- PROPERTY_HOLDERS: Owner information (holder_id, item_count, portfolio_worth, investor_status)

🔗 **Key Relationships:**
- real_estate_items.area_ref = geographic_areas.area_id
- commercial_events.item_ref = real_estate_items.item_id
- commercial_events.rep_ref = sales_representatives.rep_id
- real_estate_items.holder_ref = property_holders.holder_id

**Common Fields for Analysis:**
- Monetary values: monetary_value, final_amount, average_deal_value, portfolio_worth
- Counts: sleeping_rooms, bath_facilities, deal_count, item_count
- Areas: floor_area, market_duration
- Categories: item_category, current_state, investor_status
"""
    
    @classmethod
    def obfuscate_query_context(cls, user_query: str) -> str:
        """
        Convert user's natural language query context to use obfuscated terms.
        This helps maintain consistency in the prompt.
        """
        # Don't change the user query itself - just provide context
        return f"""
User Question: {user_query}

Note: Use the secure table names (real_estate_items, geographic_areas, sales_representatives, 
commercial_events, property_holders) in your SQL response.
"""
    
    @classmethod  
    def translate_to_real_sql(cls, obfuscated_sql: str) -> str:
        """
        Translate obfuscated SQL to real database schema names.
        
        Args:
            obfuscated_sql: SQL query with obfuscated names
            
        Returns:
            SQL query with real database names
        """
        if not obfuscated_sql:
            return obfuscated_sql
            
        real_sql = obfuscated_sql
        
        try:
            # Replace table names (order matters - longer names first to avoid partial matches)
            table_replacements = sorted(cls.REVERSE_TABLE_MAPPING.items(), 
                                      key=lambda x: len(x[0]), reverse=True)
            
            for obfuscated_table, real_table in table_replacements:
                # Replace table names with word boundaries
                pattern = r'\b' + re.escape(obfuscated_table) + r'\b'
                real_sql = re.sub(pattern, real_table, real_sql, flags=re.IGNORECASE)
            
            # Replace column references (table.column format)
            column_replacements = sorted(cls.REVERSE_COLUMN_MAPPING.items(),
                                       key=lambda x: len(x[0]), reverse=True)
            
            for obfuscated_col, real_col in column_replacements:
                # Direct replacement for qualified column names
                real_sql = real_sql.replace(obfuscated_col, real_col)
                
                # Also handle unqualified column names by extracting just the column part
                if '.' in obfuscated_col:
                    obf_col_name = obfuscated_col.split('.')[1]
                    real_col_name = real_col.split('.')[1]
                    
                    # Replace unqualified column names with word boundaries
                    pattern = r'\b' + re.escape(obf_col_name) + r'\b'
                    real_sql = re.sub(pattern, real_col_name, real_sql, flags=re.IGNORECASE)
            
            logger.info(f"Translated obfuscated SQL to real SQL successfully")
            logger.debug(f"Obfuscated: {obfuscated_sql}")
            logger.debug(f"Real: {real_sql}")
            
            return real_sql
            
        except Exception as e:
            logger.error(f"Error translating obfuscated SQL: {e}")
            # Return original if translation fails - better than breaking
            return obfuscated_sql
    
    @classmethod
    def translate_to_obfuscated_sql(cls, real_sql: str) -> str:
        """
        Translate real SQL to obfuscated schema names.
        (Used mainly for testing and reverse operations)
        
        Args:
            real_sql: SQL query with real names
            
        Returns:
            SQL query with obfuscated names
        """
        if not real_sql:
            return real_sql
            
        obfuscated_sql = real_sql
        
        try:
            # Replace column references first (more specific)
            column_replacements = sorted(cls.COLUMN_MAPPING.items(),
                                       key=lambda x: len(x[0]), reverse=True)
            
            for real_col, obfuscated_col in column_replacements:
                obfuscated_sql = obfuscated_sql.replace(real_col, obfuscated_col)
                
                # Handle unqualified column names
                if '.' in real_col:
                    real_col_name = real_col.split('.')[1]
                    obf_col_name = obfuscated_col.split('.')[1]
                    
                    pattern = r'\b' + re.escape(real_col_name) + r'\b'
                    obfuscated_sql = re.sub(pattern, obf_col_name, obfuscated_sql, flags=re.IGNORECASE)
            
            # Replace table names
            table_replacements = sorted(cls.TABLE_MAPPING.items(),
                                      key=lambda x: len(x[0]), reverse=True)
            
            for real_table, obfuscated_table in table_replacements:
                pattern = r'\b' + re.escape(real_table) + r'\b'
                obfuscated_sql = re.sub(pattern, obfuscated_table, obfuscated_sql, flags=re.IGNORECASE)
            
            return obfuscated_sql
            
        except Exception as e:
            logger.error(f"Error translating real SQL to obfuscated: {e}")
            return real_sql
    
    @classmethod
    def validate_obfuscated_sql(cls, sql: str) -> Tuple[bool, List[str]]:
        """
        Validate that SQL only contains obfuscated names, no real schema names.
        
        Args:
            sql: SQL query to validate
            
        Returns:
            Tuple of (is_valid, list_of_violations)
        """
        violations = []
        
        if not sql:
            return True, violations
        
        sql_lower = sql.lower()
        
        # Check for real table names
        for real_table in cls.TABLE_MAPPING.keys():
            if re.search(r'\b' + re.escape(real_table.lower()) + r'\b', sql_lower):
                violations.append(f"Real table name found: {real_table}")
        
        # Check for real column names (just the column part, not table.column)
        for real_col in cls.COLUMN_MAPPING.keys():
            if '.' in real_col:
                real_col_name = real_col.split('.')[1].lower()
                # Only flag if it's a distinctive real estate column name
                distinctive_columns = ['property_id', 'location_id', 'agent_id', 'transaction_id']
                if real_col_name in distinctive_columns:
                    if re.search(r'\b' + re.escape(real_col_name) + r'\b', sql_lower):
                        violations.append(f"Real column name found: {real_col_name}")
        
        return len(violations) == 0, violations
    
    @classmethod
    def get_example_translations(cls) -> List[Dict[str, str]]:
        """
        Get example query translations for testing and documentation.
        """
        return [
            {
                "description": "Simple property selection",
                "real": "SELECT property_id, price FROM properties WHERE price > 500000",
                "obfuscated": "SELECT item_id, monetary_value FROM real_estate_items WHERE monetary_value > 500000"
            },
            {
                "description": "Complex JOIN with aggregation", 
                "real": "SELECT l.city, AVG(p.price) FROM properties p JOIN locations l ON p.location_id = l.location_id GROUP BY l.city",
                "obfuscated": "SELECT ga.city_name, AVG(rei.monetary_value) FROM real_estate_items rei JOIN geographic_areas ga ON rei.area_ref = ga.area_id GROUP BY ga.city_name"
            },
            {
                "description": "Agent performance query",
                "real": "SELECT first_name, last_name, transaction_count FROM agents ORDER BY transaction_count DESC LIMIT 10",
                "obfuscated": "SELECT first_name, last_name, deal_count FROM sales_representatives ORDER BY deal_count DESC LIMIT 10"
            }
        ]


# Global instance for easy access
schema_obfuscator = SchemaObfuscator()