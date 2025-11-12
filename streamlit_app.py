import os

import streamlit as st
from dotenv import load_dotenv

from src.agent.nlp_agent import SnowflakeNLPAgent
from src.database.snowflake_conn import SnowflakeConnection
from src.ui.chat_interface import display_chat_messages, display_logs_panel, process_user_input
from src.ui.sidebar import setup_sidebar

# Load environment variables
load_dotenv()

# Page configuration
st.set_page_config(page_title="Snowflake NLP Agent", page_icon="🤖", layout="wide")


def initialize_session_state():
    """Initialize session state"""
    if "messages" not in st.session_state:
        st.session_state.messages = []
    if "processing_logs" not in st.session_state:
        st.session_state.processing_logs = []
    if "agent" not in st.session_state:
        st.session_state.agent = None
    if "db_connection" not in st.session_state:
        st.session_state.db_connection = None


def main():
    """Main Streamlit app function.

    Assembles UI and bootstrapping:
    - Initialize session state (messages, logs, connection, agent)
    - Manage Snowflake connection and create agent if credentials exist
    - Organize layout (chat on left, sidebar + logs on right)
    - Place chat_input at the end (outside columns) to comply with Streamlit rules
    """
    st.title("🤖 NLP Agent for Snowflake Queries")
    st.markdown("Ask questions in English and get answers from your Snowflake database")

    # Initialize state
    initialize_session_state()

    # Set up connection if it doesn't exist
    if not st.session_state.db_connection:
        with st.spinner("Connecting to Snowflake..."):
            db_conn = SnowflakeConnection()
            if db_conn.connect():
                st.session_state.db_connection = db_conn

                # Initialize agent (auto-detects LLM provider)
                google_api_key = os.getenv("GOOGLE_API_KEY")
                groq_api_key = os.getenv("GROQ_API_KEY")
                try:
                    st.session_state.agent = SnowflakeNLPAgent(
                        db_conn.get_connection_string(),
                        groq_api_key=groq_api_key,
                        google_api_key=google_api_key,
                    )
                    st.success("✅ Connection established successfully!")
                except Exception as e:
                    st.error(f"❌ Error initializing LLM: {e}")
                    st.stop()
            else:
                st.error("❌ Could not connect to Snowflake. Check your configuration.")
                st.stop()

    # Display active LLM model banner at top (after agent is initialized)
    if st.session_state.agent and hasattr(st.session_state.agent, 'active_provider'):
        provider_info = st.session_state.agent.active_provider
        if provider_info and provider_info.get("provider"):
            provider = provider_info["provider"].upper()
            model = provider_info.get("model", "Unknown")
            description = provider_info.get("description", "")
            provider_type = provider_info.get("type", "unknown")
            
            # Create a prominent banner with color coding
            if provider_type == "local":
                st.success(f"🏠 **Active Model: {provider} ({model})** - {description} | See sidebar for details")
            elif provider_type == "cloud":
                st.info(f"☁️ **Active Model: {provider} ({model})** - {description} | See sidebar for details")
            else:
                st.info(f"**Active Model: {provider} ({model})** | See sidebar for details")

    # Column layout
    col1, col2 = st.columns([2, 1])

    with col1:
        display_chat_messages()

    with col2:
        setup_sidebar()
        display_logs_panel()

    # User input (outside column layout)
    if prompt := st.chat_input("Ask in English (letters, numbers, basic punctuation only): What data do you need?"):
        process_user_input(prompt)


if __name__ == "__main__":
    main()
