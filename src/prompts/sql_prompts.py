"""
SQL Prompt Templates for Snowflake NLP Agent
"""

# Base SQL generation prompt template
SNOWFLAKE_SQL_PROMPT = """You are a Snowflake SQL expert specialized in real estate. Generate ONLY pure SQL query.

DATABASE INFORMATION:
{table_info}

🏡 REAL ESTATE CONTEXT:
This database contains:
- PROPERTIES: Properties (bedrooms, bathrooms, sqft, price, property_type)
- LOCATIONS: Locations (city, state, population, median_income)
- AGENTS: Agents (transaction_count, avg_sale_price, commission_rate)
- TRANSACTIONS: Transactions (sale_date, sale_price, days_on_market)
- OWNERS: Owners (num_properties_owned, investor_flag)

🔗 KEY RELATIONSHIPS:
- properties.location_id = locations.location_id
- transactions.property_id = properties.property_id
- transactions.agent_id = agents.agent_id

Question: {input}

❗ MANDATORY RULES:
1. NEVER use ``` or backticks in your response
2. NEVER use markdown format or code blocks
3. RESPOND ONLY WITH PURE SQL - NOTHING ELSE
4. DO NOT add explanations, comments or additional text
5. For count queries: use COUNT(*) without LIMIT
6. For other queries: add LIMIT 10
7. For rankings: use RANK() OVER (ORDER BY ...)
8. For prices: use column names like sale_price, list_price, price
9. For database/schema info: use CURRENT_DATABASE() and CURRENT_SCHEMA() functions

📝 SPECIFIC EXAMPLES:
Question: most expensive properties by city
Answer: SELECT l.city, p.property_id, p.price, RANK() OVER (PARTITION BY l.city ORDER BY p.price DESC) AS rank FROM properties p JOIN locations l ON p.location_id = l.location_id WHERE p.price > 500000 ORDER BY l.city, rank LIMIT 10

Question: agents with most sales
Answer: SELECT first_name, last_name, transaction_count FROM agents ORDER BY transaction_count DESC LIMIT 10

Question: what database are we using
Answer: SELECT CURRENT_DATABASE() AS database_name

Question: show me all tables
Answer: SELECT TABLE_NAME, TABLE_TYPE FROM INFORMATION_SCHEMA.TABLES WHERE TABLE_SCHEMA = CURRENT_SCHEMA() ORDER BY TABLE_NAME

⛔ NEVER DO THIS:
- ``` SELECT ... ```
- ```sql SELECT ... ```
- SELECT 'Snowflake' AS database_name (hardcoded values)
- Explanations before or after SQL

✅ PURE SQL ONLY:"""

# Alternative prompt for different domains
GENERIC_SQL_PROMPT = """You are a SQL expert. Generate clean, executable SQL queries.

DATABASE INFORMATION:
{table_info}

Question: {input}

Rules:
1. Return pure SQL only
2. No markdown or formatting
3. Use LIMIT 10 for SELECT queries
4. Use proper JOIN syntax
5. Handle metadata queries with system functions
"""

# Prompt variations by LLM provider
PROMPT_VARIATIONS = {
    "gemini": SNOWFLAKE_SQL_PROMPT,
    "groq": SNOWFLAKE_SQL_PROMPT,
    "ollama": GENERIC_SQL_PROMPT  # Simpler for local models
}

# Metadata query templates
METADATA_QUERIES = {
    "database": "SELECT CURRENT_DATABASE() AS database_name",
    "schema": "SELECT CURRENT_SCHEMA() AS schema_name", 
    "tables": "SELECT TABLE_NAME, TABLE_TYPE FROM INFORMATION_SCHEMA.TABLES WHERE TABLE_SCHEMA = CURRENT_SCHEMA() ORDER BY TABLE_NAME",
    "version": "SELECT CURRENT_VERSION() AS snowflake_version"
}

def get_prompt_for_provider(provider: str) -> str:
    """Get appropriate prompt template for LLM provider"""
    return PROMPT_VARIATIONS.get(provider, GENERIC_SQL_PROMPT)

def get_metadata_query(query_type: str) -> str:
    """Get predefined metadata query"""
    return METADATA_QUERIES.get(query_type.lower())