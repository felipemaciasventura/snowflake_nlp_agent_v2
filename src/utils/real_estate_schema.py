"""
Intelligent schema module for real estate
Based on create_tables.sql - Contains schema information to improve NLP queries
"""


class RealEstateSchema:
    """Class that contains real estate schema information to improve SQL generation"""
    
    # Information about main tables and their purposes
    TABLES_INFO = {
        'locations': {
            'description': 'Demographic and geographic information of locations',
            'key_columns': ['location_id', 'city', 'state', 'county', 'zipcode', 'population', 'median_income', 'avg_sale_price'],
            'common_queries': ['statistics by city', 'demographic information', 'prices by location']
        },
        'agents': {
            'description': 'Real estate agent information',
            'key_columns': ['agent_id', 'first_name', 'last_name', 'agency', 'transaction_count', 'avg_sale_price', 'commission_rate'],
            'common_queries': ['agents with most sales', 'average commissions', 'agent performance']
        },
        'owners': {
            'description': 'Property owner information',
            'key_columns': ['owner_id', 'first_name', 'last_name', 'num_properties_owned', 'total_portfolio_value', 'investor_flag'],
            'common_queries': ['owners with most properties', 'investors', 'most valuable portfolios']
        },
        'properties': {
            'description': 'Detailed real estate property information',
            'key_columns': ['property_id', 'location_id', 'price', 'bedrooms', 'bathrooms', 'sqft', 'property_type', 'status'],
            'common_queries': ['properties by characteristics', 'prices by type', 'available inventory']
        },
        'transactions': {
            'description': 'Buy-sell transaction records',
            'key_columns': ['transaction_id', 'property_id', 'sale_date', 'sale_price', 'agent_id', 'days_on_market'],
            'common_queries': ['recent sales', 'transaction volume', 'time on market']
        }
    }
    
    # Main relationships between tables
    RELATIONSHIPS = {
        'properties_locations': 'properties.location_id = locations.location_id',
        'properties_owners': 'properties.owner_id = owners.owner_id',
        'transactions_properties': 'transactions.property_id = properties.property_id',
        'transactions_agents': 'transactions.agent_id = agents.agent_id',
        'properties_listing_agent': 'properties.listing_agent_id = agents.agent_id'
    }
    
    # Common fields for monetary formatting
    MONEY_FIELDS = [
        'price', 'sale_price', 'list_price', 'avg_sale_price', 'avg_listing_price',
        'median_income', 'closing_costs', 'mortgage_amount', 'down_payment',
        'commission_rate', 'hoa_fee', 'total_portfolio_value', 'average_property_value'
    ]
    
    # Area/size fields
    AREA_FIELDS = ['sqft', 'lot_size', 'price_per_sqft']
    
    # Keywords that indicate different query types
    QUERY_PATTERNS = {
        'ranking': ['ranking', 'top', 'mejores', 'primeros', 'más caros', 'más baratos', 'mayor', 'menor'],
        'aggregation': ['promedio', 'suma', 'total', 'count', 'máximo', 'mínimo', 'avg', 'sum', 'max', 'min'],
        'temporal': ['último', 'últimos', 'reciente', 'recientes', 'mes pasado', 'año pasado', 'este año', 'este mes'],
        'geographic': ['ciudad', 'ciudades', 'estado', 'condado', 'zona', 'ubicación', 'región'],
        'property_features': ['dormitorios', 'habitaciones', 'baños', 'metros', 'sqft', 'piscina', 'garaje'],
        'financial': ['precio', 'precios', 'caro', 'barato', 'comisión', 'hipoteca', 'financiamiento']
    }
    
    @classmethod
    def get_table_suggestions(cls, user_query: str) -> list:
        """Suggest which tables might be relevant for the user's query"""
        query_lower = user_query.lower()
        relevant_tables = []
        
        # Detect relevant tables based on keywords
        if any(word in query_lower for word in ['ciudad', 'ubicación', 'zona', 'demográfico', 'población']):
            relevant_tables.append('locations')
            
        if any(word in query_lower for word in ['agente', 'vendedor', 'comisión', 'agency']):
            relevant_tables.append('agents')
            
        if any(word in query_lower for word in ['propietario', 'dueño', 'owner', 'inversionista']):
            relevant_tables.append('owners')
            
        if any(word in query_lower for word in ['propiedad', 'casa', 'inmueble', 'dormitorios', 'baños']):
            relevant_tables.append('properties')
            
        if any(word in query_lower for word in ['transacción', 'venta', 'compra', 'vendió', 'compró']):
            relevant_tables.append('transactions')
        
        return relevant_tables if relevant_tables else ['properties']  # Default
    
    @classmethod
    def get_join_suggestions(cls, tables: list) -> list:
        """Suggest appropriate JOINs for the specified tables"""
        joins = []
        
        if 'properties' in tables and 'locations' in tables:
            joins.append(cls.RELATIONSHIPS['properties_locations'])
            
        if 'properties' in tables and 'owners' in tables:
            joins.append(cls.RELATIONSHIPS['properties_owners'])
            
        if 'transactions' in tables and 'properties' in tables:
            joins.append(cls.RELATIONSHIPS['transactions_properties'])
            
        if 'transactions' in tables and 'agents' in tables:
            joins.append(cls.RELATIONSHIPS['transactions_agents'])
            
        if 'properties' in tables and 'agents' in tables:
            joins.append(cls.RELATIONSHIPS['properties_listing_agent'])
        
        return joins
    
    @classmethod
    def get_schema_context(cls, user_query: str) -> str:
        """Generate relevant schema context for the user's query"""
        relevant_tables = cls.get_table_suggestions(user_query)
        
        context = "REAL ESTATE SCHEMA CONTEXT:\n\n"
        context += "MAIN TABLES:\n"
        
        for table in relevant_tables:
            if table in cls.TABLES_INFO:
                info = cls.TABLES_INFO[table]
                context += f"- {table.upper()}: {info['description']}\n"
                context += f"  Key columns: {', '.join(info['key_columns'])}\n"
        
        if len(relevant_tables) > 1:
            joins = cls.get_join_suggestions(relevant_tables)
            if joins:
                context += f"\nSUGGESTED RELATIONSHIPS:\n"
                for join in joins:
                    context += f"- {join}\n"
        
        return context
    
    @classmethod
    def get_example_queries(cls) -> dict:
        """Return example queries by category"""
        return {
            'prices': [
                "What is the average price per city?",
                "Show me the 10 most expensive properties",
                "Which city has the highest prices?"
            ],
            'agents': [
                "Which agent has sold the most properties?",
                "What is the average commission of agents?",
                "Show me agents with best performance"
            ],
            'locations': [
                "Which cities have the most population?",
                "Show me demographic statistics by county",
                "What is the average income by location?"
            ],
            'properties': [
                "List properties with more than 3 bedrooms",
                "How many properties have a pool?",
                "Show me available properties by type"
            ],
            'transactions': [
                "How many transactions were there last month?",
                "What is the average time on market?",
                "Show me the most recent sales"
            ]
        }


# Global instance for use in the application
real_estate_schema = RealEstateSchema()
