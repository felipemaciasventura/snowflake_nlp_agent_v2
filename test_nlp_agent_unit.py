import pytest
from unittest.mock import MagicMock, patch

from src.agent.nlp_agent import SnowflakeNLPAgent


@pytest.fixture
def mock_db_connection():
    """
    Fixture que crea un mock de la conexión a la base de datos.
    No se conecta realmente a Snowflake, solo simula su comportamiento.
    """
    mock_conn = MagicMock()
    mock_conn.run.return_value = [("TABLE_1", "BASE TABLE"), ("TABLE_2", "VIEW")]
    return mock_conn


@pytest.fixture
@patch("src.agent.nlp_agent.config")
@patch("src.agent.nlp_agent.get_context_enhancer")
@patch("src.agent.nlp_agent.SQLDatabase")
@patch("src.agent.nlp_agent.ChatOllama")  # Mockeamos todos los LLMs
@patch("src.agent.nlp_agent.ChatGoogleGenerativeAI")
@patch("src.agent.nlp_agent.ChatGroq")
def unit_test_agent(
    mock_groq,
    mock_gemini,
    mock_ollama,
    mock_sqldatabase,
    mock_context_enhancer,
    mock_config,
    mock_db_connection,
):
    """
    Fixture para crear una instancia del agente para pruebas unitarias.
    Todas las dependencias externas (LLMs, DB) están mockeadas.
    """
    # Configuramos el mock para que simule que 'ollama' está disponible
    mock_config.get_available_llm_provider.return_value = "ollama"
    mock_config.OLLAMA_BASE_URL = "http://mock-url"
    mock_config.OLLAMA_MODEL = "mock-model"

    # Creamos una instancia del agente. No se conectará a nada real.
    agent = SnowflakeNLPAgent(db_connection="dummy_string")

    # Reemplazamos la conexión real a la BD con nuestro mock
    agent.db = mock_db_connection
    return agent


@pytest.mark.unit
def test_handle_metadata_query_for_tables(unit_test_agent):
    """
    Prueba unitaria para la función _handle_metadata_query.
    Verifica que una pregunta sobre tablas se maneje correctamente.
    """
    # 1. Arrange (Preparar)
    question = "show me all the tables"
    expected_sql = "SELECT TABLE_NAME, TABLE_TYPE FROM INFORMATION_SCHEMA.TABLES WHERE TABLE_SCHEMA = CURRENT_SCHEMA() ORDER BY TABLE_NAME"

    # 2. Act (Actuar)
    result = unit_test_agent._handle_metadata_query(question)

    # 3. Assert (Verificar)
    assert result is not None, "La función no debería devolver None para una consulta de metadatos"
    assert result["success"] is True
    assert result["query_type"] == "metadata"
    assert result["sql_query"] == expected_sql

    # Verificamos que se llamó al mock de la base de datos con el SQL correcto
    unit_test_agent.db.run.assert_called_once_with(expected_sql)

    # Verificamos que el resultado del mock se pasó correctamente
    assert result["result"] == [("TABLE_1", "BASE TABLE"), ("TABLE_2", "VIEW")]

    print(f"\n✅ Prueba unitaria para '{question}' pasó exitosamente.")