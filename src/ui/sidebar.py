"""
Sidebar configuration and controls
"""

import os

import streamlit as st

from src.utils.config import config


def setup_sidebar():
    """Set up sidebar"""
    st.sidebar.header("🔧 Configuration")

    # Connection status
    if st.session_state.db_connection:
        st.sidebar.success("✅ Connected to Snowflake")
    else:
        st.sidebar.error("❌ Not connected")

    # Active LLM Provider Banner (prominent display)
    st.sidebar.header("🤖 Active LLM Model")
    if st.session_state.agent and hasattr(st.session_state.agent, 'active_provider'):
        provider_info = st.session_state.agent.active_provider
        if provider_info and provider_info.get("provider"):
            provider = provider_info["provider"]
            model = provider_info.get("model", "Unknown")
            description = provider_info.get("description", "")
            provider_type = provider_info.get("type", "unknown")
            
            # Color-coded banner based on provider type
            if provider_type == "local":
                st.sidebar.success(f"🏠 **{provider.upper()}**\n{model}\n_{description}_")
            elif provider_type == "cloud":
                st.sidebar.info(f"☁️ **{provider.upper()}**\n{model}\n_{description}_")
            else:
                st.sidebar.info(f"**{provider.upper()}**\n{model}")
            
            # Show server info for local models
            if provider_info.get("server"):
                st.sidebar.caption(f"📍 Server: {provider_info['server']}")
        else:
            st.sidebar.error("❌ No LLM provider active")
    else:
        st.sidebar.warning("⚠️ LLM not initialized")

    # System information + LLM controls
    st.sidebar.header("📊 System Information")

    # Helper: determine available providers based on .env, enable switches, and availability
    def _available_providers():
        options = []
        providers_status = config.get_all_providers_status()
        
        if providers_status["groq"]["available"]:
            options.append("groq")
        if providers_status["gemini"]["available"]:
            options.append("gemini")
        if providers_status["ollama"]["available"]:
            options.append("ollama")
        if providers_status["sqlcoder"]["available"]:
            options.append("sqlcoder")
        return options
    
    # Show providers status
    st.sidebar.subheader("📋 Providers Status")
    providers_status = config.get_all_providers_status()
    for provider_name, status in providers_status.items():
        if status["enabled"]:
            if status["available"]:
                st.sidebar.success(f"✅ {provider_name.upper()}: Available")
            else:
                st.sidebar.warning(f"⚠️ {provider_name.upper()}: Enabled but not available")
        else:
            st.sidebar.caption(f"⚪ {provider_name.upper()}: Disabled")

    current_provider = config.get_available_llm_provider() or "auto"
    providers = _available_providers()

    # Persist selection in session
    if "selected_llm_provider" not in st.session_state:
        st.session_state.selected_llm_provider = (
            current_provider
            if current_provider != "auto"
            else (providers[0] if providers else "")
        )

    # Provider selector (only if any available)
    if providers:
        sel = st.sidebar.selectbox(
            "LLM Provider",
            options=providers,
            index=(
                providers.index(st.session_state.selected_llm_provider)
                if st.session_state.selected_llm_provider in providers
                else 0
            ),
            help="Choose which LLM to use. Changing this will re-initialize the agent.",
        )
        st.session_state.selected_llm_provider = sel

        # Model editor per provider
        if sel == "groq":
            model_val = st.sidebar.text_input(
                "Groq model", value=str(config.MODEL_NAME or "")
            )
        elif sel == "gemini":
            model_val = st.sidebar.text_input(
                "Gemini model", value=str(config.GEMINI_MODEL or "")
            )
        elif sel == "ollama":
            model_val = st.sidebar.text_input(
                "Ollama model", value=str(config.OLLAMA_MODEL or "")
            )
            st.sidebar.caption(f"Server: {config.OLLAMA_BASE_URL}")
        elif sel == "sqlcoder":
            model_val = st.sidebar.text_input(
                "SQLCoder model", value=str(config.SQLCODER_MODEL or "")
            )
            st.sidebar.caption(f"🎯 SQL Specialized Server: {config.SQLCODER_BASE_URL}")
        else:
            model_val = ""

        # Apply changes button
        if st.sidebar.button("Apply LLM settings"):
            # Update config in-memory and re-create agent
            try:
                # Set provider
                config.LLM_PROVIDER = sel
                # Set model field accordingly
                if sel == "groq" and model_val:
                    config.MODEL_NAME = model_val
                elif sel == "gemini" and model_val:
                    config.GEMINI_MODEL = model_val
                elif sel == "ollama" and model_val:
                    config.OLLAMA_MODEL = model_val
                elif sel == "sqlcoder" and model_val:
                    config.SQLCODER_MODEL = model_val

                # Re-initialize agent if DB connection exists
                if st.session_state.db_connection:
                    from src.agent.nlp_agent import SnowflakeNLPAgent

                    google_api_key = os.getenv("GOOGLE_API_KEY")
                    groq_api_key = os.getenv("GROQ_API_KEY")
                    st.session_state.agent = SnowflakeNLPAgent(
                        st.session_state.db_connection.get_connection_string(),
                        groq_api_key=groq_api_key,
                        google_api_key=google_api_key,
                    )
                    st.sidebar.success("LLM updated and agent re-initialized ✅")
                else:
                    st.sidebar.warning(
                        "Connect to Snowflake first to initialize the agent."
                    )
            except Exception as e:
                st.sidebar.error(f"Failed to apply LLM settings: {e}")

    # Database and Schema info
    st.sidebar.subheader("🗄️ Database Info")
    st.sidebar.info(f"Database: {os.getenv('SNOWFLAKE_DATABASE', 'N/A')}")
    st.sidebar.info(f"Schema: {os.getenv('SNOWFLAKE_SCHEMA', 'PUBLIC')}")

    # Phase 1 Features: Templates, Saved Queries, Cache
    from src.ui.templates_ui import render_templates_section, render_saved_queries_section, render_cache_section
    
    st.sidebar.markdown("---")
    render_templates_section()
    
    st.sidebar.markdown("---")
    render_saved_queries_section()
    
    st.sidebar.markdown("---")
    render_cache_section()

    # Button to clear history
    st.sidebar.markdown("---")
    if st.sidebar.button("🗑️ Clear History"):
        st.session_state.messages = []
        st.session_state.processing_logs = []
        st.rerun()







