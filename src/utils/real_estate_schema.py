"""
Módulo de esquema inteligente para bienes raíces
Basado en create_tables.sql - Contiene información del esquema para mejorar queries NLP
"""


class RealEstateSchema:
    """Clase que contiene información del esquema de bienes raíces para mejorar la generación de SQL"""
    
    # Información de tablas principales y sus propósitos
    TABLES_INFO = {
        'locations': {
            'description': 'Información demográfica y geográfica de ubicaciones',
            'key_columns': ['location_id', 'city', 'state', 'county', 'zipcode', 'population', 'median_income', 'avg_sale_price'],
            'common_queries': ['estadísticas por ciudad', 'información demográfica', 'precios por ubicación']
        },
        'agents': {
            'description': 'Información de agentes de bienes raíces',
            'key_columns': ['agent_id', 'first_name', 'last_name', 'agency', 'transaction_count', 'avg_sale_price', 'commission_rate'],
            'common_queries': ['agentes con más ventas', 'comisiones promedio', 'performance de agentes']
        },
        'owners': {
            'description': 'Información de propietarios de inmuebles',
            'key_columns': ['owner_id', 'first_name', 'last_name', 'num_properties_owned', 'total_portfolio_value', 'investor_flag'],
            'common_queries': ['propietarios con más propiedades', 'inversionistas', 'portafolios más valiosos']
        },
        'properties': {
            'description': 'Información detallada de propiedades inmobiliarias',
            'key_columns': ['property_id', 'location_id', 'price', 'bedrooms', 'bathrooms', 'sqft', 'property_type', 'status'],
            'common_queries': ['propiedades por características', 'precios por tipo', 'inventario disponible']
        },
        'transactions': {
            'description': 'Registros de transacciones de compra-venta',
            'key_columns': ['transaction_id', 'property_id', 'sale_date', 'sale_price', 'agent_id', 'days_on_market'],
            'common_queries': ['ventas recientes', 'volumen de transacciones', 'tiempo en mercado']
        }
    }
    
    # Relaciones principales entre tablas
    RELATIONSHIPS = {
        'properties_locations': 'properties.location_id = locations.location_id',
        'properties_owners': 'properties.owner_id = owners.owner_id',
        'transactions_properties': 'transactions.property_id = properties.property_id',
        'transactions_agents': 'transactions.agent_id = agents.agent_id',
        'properties_listing_agent': 'properties.listing_agent_id = agents.agent_id'
    }
    
    # Campos comunes para formateo monetario
    MONEY_FIELDS = [
        'price', 'sale_price', 'list_price', 'avg_sale_price', 'avg_listing_price',
        'median_income', 'closing_costs', 'mortgage_amount', 'down_payment',
        'commission_rate', 'hoa_fee', 'total_portfolio_value', 'average_property_value'
    ]
    
    # Campos de área/tamaño
    AREA_FIELDS = ['sqft', 'lot_size', 'price_per_sqft']
    
    # Palabras clave que indican diferentes tipos de consultas
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
        """Sugiere qué tablas pueden ser relevantes para la consulta del usuario"""
        query_lower = user_query.lower()
        relevant_tables = []
        
        # Detectar tablas relevantes basado en palabras clave
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
        """Sugiere JOINs apropiados para las tablas especificadas"""
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
        """Genera contexto del esquema relevante para la consulta del usuario"""
        relevant_tables = cls.get_table_suggestions(user_query)
        
        context = "CONTEXTO DEL ESQUEMA DE BIENES RAÍCES:\n\n"
        context += "TABLAS PRINCIPALES:\n"
        
        for table in relevant_tables:
            if table in cls.TABLES_INFO:
                info = cls.TABLES_INFO[table]
                context += f"- {table.upper()}: {info['description']}\n"
                context += f"  Columnas clave: {', '.join(info['key_columns'])}\n"
        
        if len(relevant_tables) > 1:
            joins = cls.get_join_suggestions(relevant_tables)
            if joins:
                context += f"\nRELACIONES SUGERIDAS:\n"
                for join in joins:
                    context += f"- {join}\n"
        
        return context
    
    @classmethod
    def get_example_queries(cls) -> dict:
        """Devuelve ejemplos de consultas por categoría"""
        return {
            'precios': [
                "¿Cuál es el precio promedio por ciudad?",
                "Muéstrame las 10 propiedades más caras",
                "¿Qué ciudad tiene los precios más altos?"
            ],
            'agentes': [
                "¿Qué agente ha vendido más propiedades?",
                "¿Cuál es la comisión promedio de los agentes?",
                "Muéstrame los agentes con mejor performance"
            ],
            'ubicaciones': [
                "¿Qué ciudades tienen más población?",
                "Muéstrame estadísticas demográficas por condado",
                "¿Cuál es el ingreso promedio por ubicación?"
            ],
            'propiedades': [
                "Lista propiedades con más de 3 dormitorios",
                "¿Cuántas propiedades tienen piscina?",
                "Muéstrame propiedades disponibles por tipo"
            ],
            'transacciones': [
                "¿Cuántas transacciones hubo el mes pasado?",
                "¿Cuál es el tiempo promedio en mercado?",
                "Muéstrame las ventas más recientes"
            ]
        }


# Instancia global para uso en la aplicación
real_estate_schema = RealEstateSchema()