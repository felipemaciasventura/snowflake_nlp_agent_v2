"""
Query type detection and response generation
"""


def is_database_query(user_input):
    """Detects if the query is about databases or out of context"""
    user_input_lower = user_input.lower()

    # Keywords that indicate database queries (English only)
    db_keywords = [
        "table",
        "data",
        "query",
        "how many",
        "show",
        "list",
        "display",
        "region",
        "customer",
        "client",
        "sale",
        "average",
        "sum",
        "total",
        "count",
        "select",
        "database",
        "schema",
        "records",
        "rows",
        "columns",
        "orders",
        "products",
        "categories",
        "revenue",
        "income",
        "billing",
        "analysis",
        "report",
        "statistics",
        "maximum",
        "minimum",
        "search",
        "filter",
        "group",
        "sort",
        "top",
        "highest",
        "lowest",
        "latest",
        "recent",
        # Additional keywords for complex queries
        "city",
        "cities",
        "properties",
        "property",
        "price",
        "prices",
        "ranking",
        "rank",
        "position",
        "positions",
        "each",
        "get",
        "obtain",
        "include",
        "only",
        "dollars",
        "values",
        "value",
        "transactions",
        "transaction",
        "locations",
        "location",
        "expensive",
        "cheap",
        "more",
        "less",
        "most",
        "least",
        "join",
        "inner",
        "left",
        "right",
        "where",
        "order by",
        "group by",
        "partition",
        "over",
        "window",
        "function",
        "functions",
        "aggregate",
        "aggregation",
        # Real estate specific vocabulary (based on SQL schema)
        "agent",
        "agents",
        "owner",
        "owners",
        "buyer",
        "buyers",
        "seller",
        "sellers",
        "real estate",
        "house",
        "houses",
        "home",
        "homes",
        "apartment",
        "apartments",
        "mortgage",
        "mortgages",
        "credit",
        "financing",
        "loan",
        "loans",
        "bedroom",
        "bedrooms",
        "bathroom",
        "bathrooms",
        "sqft",
        "square feet",
        "garage",
        "parking",
        "pool",
        "garden",
        "yard",
        "patio",
        "deck",
        "county",
        "state",
        "zip code",
        "zipcode",
        "msa",
        "area",
        "neighborhood",
        "appraisal",
        "assessment",
        "tax",
        "taxes",
        "commission",
        "commissions",
        "listing",
        "listings",
        "offer",
        "offers",
        "closing",
        "closings",
        "deed",
        "inspection",
        "evaluation",
        "market",
        "trend",
        "trends",
        "growth",
        "profitability",
        "roi",
        "investment",
        "investments",
        "portfolio",
    ]

    # Off-topic keywords (be specific to avoid conflicts)
    off_topic_keywords = [
        "weather",
        "climate",
        "news",
        "cooking recipe",
        "translate language",
        "how are you",
        "hello",
        "joke",
        "personal story",
        "movie",
        "music",
        "sports",
        "politics",
        "personal health",
        "medicine",
        "travel",
        "restaurant",
        "buy clothes",
        "shopping",
        "personal schedule",
        "postal address",
        "personal phone",
        "personal email",
        "schedule appointment",
        # Removed "price" and "code" as they can be part of DB queries
    ]

    # Help/information questions (special case)
    help_keywords = [
        "help",
        "what can you do",
        "how does it work",
        "what do you do",
        "what are you for",
        "how to use",
        "instructions",
        "commands",
        "examples",
        "capabilities",
        "functions",
    ]

    # Check if it's a help question
    if any(keyword in user_input_lower for keyword in help_keywords):
        return "help"

    # Check if it contains clearly off-topic keywords
    if any(keyword in user_input_lower for keyword in off_topic_keywords):
        return "off_topic"

    # Check if it contains database keywords
    if any(keyword in user_input_lower for keyword in db_keywords):
        return "database"

    # If not clear, analyze more deeply
    if len(user_input.split()) < 3:  # Too short, probably not a DB query
        return "unclear"

    # For long queries (>10 words), probably complex DB queries
    if len(user_input.split()) > 10:
        # Check if it has data query structure
        data_structure_indicators = [
            "for each",
            "get",
            "obtain",
            "show",
            "list",
            "find",
            "calculate",
            "sum",
            "count",
            "group by",
            "order by",
            "with price",
            "with value",
            "greater than",
            "less than",
            "equal to",
            "include",
            "exclude",
            "only",
            "just",
            "exclusively",
        ]

        if any(
            indicator in user_input_lower for indicator in data_structure_indicators
        ):
            return "database"

    return "database"  # By default, try as DB query


def get_help_response():
    """Returns educational response about system capabilities"""
    return {
        "type": "help",
        "message": """Hello! 👋 I'm your NLP assistant for real estate queries in Snowflake.

🔍 **I can help you with:**
• 🏠 **Properties:** "How many properties are there per city?"
• 💰 **Prices:** "What's the average price per square foot?"
• 👥 **Agents:** "Show me agents with most sales"
• 📈 **Transactions:** "List the last 10 transactions"
• 📊 **Analysis:** "Which city has the most expensive properties?"
• 🏦 **Locations:** "Show me statistics by county"

🎨 **Examples you can try:**
• "For each city, get the average sale price"
• "Which agent has sold the most properties this year?"
• "List properties with more than 3 bedrooms and a pool"
• "What's the average commission of agents?"
• "Show me the most expensive properties by city"
• "How many transactions were made last month?"

Ask me any question about real estate! 🏡🚀""",
    }


def get_redirect_response():
    """Returns redirect response for out-of-context queries"""
    return {
        "type": "redirect",
        "message": """🤖 I'm an assistant specialized in Snowflake database queries.

I can't help you with that query, but I can help you explore your data! 📋

🎨 **Try asking me something like:**
• "How many records are in the customers table?"
• "Show me the regions with highest revenue"
• "What tables are available?"

Is there any information from your database you'd like to know? 😊""",
    }













