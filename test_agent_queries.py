import os
import pytest
from dotenv import load_dotenv

from src.agent.nlp_agent import SnowflakeNLPAgent
from src.database.snowflake_conn import SnowflakeConnection

# Cargar variables de entorno para la prueba
load_dotenv()

# --- Lista de Consultas para Pruebas Automatizadas ---
# Esta lista contiene preguntas que van desde simples a complejas para validar el agente.
QUERIES_TO_TEST = [
    # --- 1. Consultas de Metadatos (Manejo Directo) ---
    pytest.param("what database are we using", "metadata", id="Metadata - Current Database"),
    pytest.param("which schema are we using", "metadata", id="Metadata - Current Schema"),
    pytest.param("show me all the tables", "metadata", id="Metadata - List Tables"),
    pytest.param("what is the current role", "metadata", id="Metadata - Current Role"),

    # --- 2. Consultas de Vista Previa de Tablas (Manejo Directo) ---
    pytest.param("show me the agents table", "data_preview", id="Preview - Agents Table"),
    pytest.param("show the properties table", "data_preview", id="Preview - Properties Table"),

    # --- 3. Consultas de Conteo (Manejo Directo y LLM) ---
    pytest.param("how many agents are there?", "count", id="Count - Total Agents"),
    pytest.param("what is the total number of properties?", "llm_query", id="Count - Total Properties (LLM)"),
    pytest.param("count the number of transactions", "llm_query", id="Count - Total Transactions (LLM)"),

    # --- 4. Consultas Simples (LLM) ---
    pytest.param("list the first 5 agents by name", "llm_query", id="Simple - List 5 Agents"),
    pytest.param("show me the email for agent with id 10", "llm_query", id="Simple - Agent Email by ID"),
    pytest.param("what are the different property types available?", "llm_query", id="Simple - Distinct Property Types"),

    # --- 5. Consultas de Agregación y Agrupación (LLM - Complejidad Media) ---
    pytest.param("what is the average sale price of properties?", "llm_query", id="Aggregation - Average Sale Price"),
    pytest.param("how many properties are in each city?", "llm_query", id="GroupBy - Properties per City"),
    pytest.param("show the total number of sales for each agent", "llm_query", id="GroupBy - Sales per Agent"),
    pytest.param("what is the maximum price for a property in the 'Texas' state?", "llm_query", id="Aggregation - Max Price in State"),

    # --- 6. Consultas Complejas con Joins y Filtros (LLM - Alta Complejidad) ---
    pytest.param(
        "list the top 5 agents with the highest total sales value", "llm_query", id="Complex - Top 5 Agents by Sales Value"
    ),
    pytest.param(
        "what is the name of the agent who sold the most expensive property?", "llm_query", id="Complex - Agent for Most Expensive Property"
    ),
    pytest.param(
        "for each city, what is the average property price and the number of properties with more than 3 bedrooms?",
        "llm_query",
        id="Complex - Avg Price and Count by City with Filter",
    ),
    pytest.param(
        "show the names of buyers who purchased properties sold by the agent named 'Laura'",
        "llm_query",
        id="Complex - Buyers for a specific Agent",
    ),
]


@pytest.fixture(scope="module")
def agent():
    """
    Fixture para inicializar la conexión a la BD y el agente NLP una sola vez por módulo.
    Esto acelera las pruebas al no reconectar para cada consulta.
    """
    # Requerir que las variables de entorno estén presentes
    if not all(os.getenv(k) for k in ["SNOWFLAKE_USER", "SNOWFLAKE_PASSWORD", "SNOWFLAKE_ACCOUNT"]):
        pytest.skip("Faltan credenciales de Snowflake. Omitiendo pruebas de integración.")

    if not any(os.getenv(k) for k in ["GOOGLE_API_KEY", "GROQ_API_KEY"]) and not os.getenv("OLLAMA_BASE_URL"):
         pytest.skip("Faltan credenciales de LLM (Google/Groq) o URL de Ollama. Omitiendo pruebas.")

    db_conn = SnowflakeConnection()
    if not db_conn.connect():
        pytest.fail("No se pudo conectar a Snowflake.")

    connection_string = db_conn.get_connection_string()
    google_api_key = os.getenv("GOOGLE_API_KEY")
    groq_api_key = os.getenv("GROQ_API_KEY")

    try:
        nlp_agent = SnowflakeNLPAgent(
            connection_string,
            groq_api_key=groq_api_key,
            google_api_key=google_api_key,
        )
        return nlp_agent
    except Exception as e:
        pytest.fail(f"Error al inicializar SnowflakeNLPAgent: {e}")


@pytest.mark.integration
@pytest.mark.parametrize("query, query_type", QUERIES_TO_TEST)
def test_agent_query_processing(agent, query, query_type):
    """
    Prueba de integración que procesa una consulta y valida la respuesta.
    """
    assert agent is not None, "El agente no se inicializó correctamente."

    # Ejecutar la consulta a través del agente
    result = agent.process_query(query)

    # --- Aserciones Comunes para Todas las Consultas ---
    assert result is not None, "El resultado no puede ser nulo."
    assert result.get("success") is True, f"La consulta '{query}' falló. Error: {result.get('error', 'N/A')}"
    assert result.get("sql_query") is not None and result.get("sql_query") != "N/A", f"No se generó SQL para la consulta: '{query}'"

    # --- Aserciones Específicas del Resultado ---
    query_result_data = result.get("result")
    assert query_result_data is not None, f"Los datos del resultado son nulos para la consulta: '{query}'"

    # Para la mayoría de las consultas, esperamos una lista (de filas)
    if query_type != "metadata_scalar": # Podrías tener tipos que devuelven un solo valor
        assert isinstance(query_result_data, list), f"El resultado para '{query}' no es una lista, sino {type(query_result_data)}"
        assert len(query_result_data) > 0, f"La consulta '{query}' no devolvió resultados (lista vacía)."

    print(f"\n✅ Éxito para la consulta: '{query}'")
    print(f"   SQL Generado: {result['sql_query']}")
    print(f"   Resultado (primeros 100 chars): {str(query_result_data)[:100]}...")