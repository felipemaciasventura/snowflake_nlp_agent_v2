"""
Chat interface and message rendering
"""

import io
from typing import Dict, Optional

import pandas as pd
import streamlit as st

from src.ui.query_detector import get_help_response, get_redirect_response
from src.ui.result_formatter import format_sql_result_to_dataframe

CHAT_HISTORY_MAX_ROWS = 200


def _render_single_message(message):
    """Render a single message from history."""
    with st.chat_message(message["role"]):
        is_assistant_with_data = message["role"] == "assistant" and "data" in message
        if not is_assistant_with_data:
            st.write(message["content"])
            return

        st.write(message["content"])
        
        # Show generated SQL query if available
        executed_sql_hist = message.get("sql", "").strip()
        if executed_sql_hist:
            with st.expander("🔍 **Generated SQL Query**", expanded=False):
                st.code(executed_sql_hist, language="sql")
                st.caption("💡 This is the SQL query that was automatically generated from your natural language question.")
        
        if not message["data"].empty:
            df_hist = message["data"]

            # Reuse intelligent column selection with persistent checkbox
            def _norm(name: str) -> str:
                return str(name).strip().lower().replace(" ", "_")

            key_candidates = [
                "id",
                "agent_id",
                "agent_uid",
                "property_id",
                "name",
                "first_name",
                "last_name",
                "full_name",
                "email",
                "phone",
                "agency",
                "city",
                "state",
                "license_number",
                "active_flag",
                "date_joined",
            ]
            key_norms = set(key_candidates)
            column_norm_map = {c: _norm(c) for c in df_hist.columns}
            selected_cols = [c for c, n in column_norm_map.items() if n in key_norms]

            df_to_show_hist = df_hist
            if df_hist.shape[1] > 12 and len(selected_cols) >= 3:
                show_all_key_hist = (
                    f"show_all_cols_{abs(hash(executed_sql_hist)) % (10**8)}"
                )
                show_all_hist = st.checkbox(
                    "Show all columns", value=False, key=show_all_key_hist
                )
                if not show_all_hist:
                    df_to_show_hist = df_hist[selected_cols]

            st.dataframe(df_to_show_hist, width='stretch')
            num_rows = len(df_hist)
            st.caption(f"📊 {num_rows} record{'s' if num_rows != 1 else ''} shown")


def display_chat_messages():
    """Display chat message history with tables and counters."""
    st.header("💬 Chat with your Database")

    # Show message history
    for message in st.session_state.messages:
        _render_single_message(message)


def _append_assistant_message(content, df=None, sql: str | None = None):
    """Add an assistant message to history with optional DataFrame and SQL string for stable UI keys."""
    if df is not None and isinstance(df, pd.DataFrame):
        df_to_store = df.head(CHAT_HISTORY_MAX_ROWS).copy()
    else:
        df_to_store = pd.DataFrame()

    st.session_state.messages.append(
        {
            "role": "assistant",
            "content": content,
            "data": df_to_store,
            "sql": sql or "",
        }
    )


def _render_successful_result(result, prompt):
    """Render a successful agent result and update history."""
    response_content = "Query executed successfully:"
    st.write(response_content)

    # Debug logging for received result
    if hasattr(st, "session_state") and hasattr(st.session_state, "processing_logs"):
        st.session_state.processing_logs.append(
            {
                "step": "📥 Streamlit Data Reception",
                "content": f"Received result keys: {list(result.keys())}, "
                f"result['result'] type: {type(result.get('result'))}, "
                f"result['result'] is None: {result.get('result') is None}, "
                f"result['success']: {result.get('success')}, "
                f"result['result'] preview: {str(result.get('result'))[:200]}...",
                "timestamp": pd.Timestamp.now().strftime("%H:%M:%S"),
            }
        )

    actual_data = result.get("result")
    # Try to parse stringified list/tuple results into Python objects
    if isinstance(actual_data, str):
        import re as _re
        from ast import literal_eval
        from decimal import Decimal

        sanitized = actual_data
        try:
            # Step 1: Replace datetime.date(Y, M, D) with 'YYYY-MM-DD'
            def _date_repl(match):
                y, m, d = match.group(1), match.group(2), match.group(3)
                try:
                    y_i, m_i, d_i = int(y), int(m), int(d)
                    return f"'{y_i:04d}-{m_i:02d}-{d_i:02d}'"
                except Exception:
                    return match.group(0)

            sanitized = _re.sub(
                r"datetime\.date\(\s*(\d{1,4})\s*,\s*(\d{1,2})\s*,\s*(\d{1,2})\s*\)",
                _date_repl,
                sanitized,
            )
            
            # Step 2: Replace Decimal('...') with float value
            def _decimal_repl(match):
                decimal_str = match.group(1)
                try:
                    return str(float(decimal_str))
                except Exception:
                    return match.group(0)
            
            sanitized = _re.sub(
                r"Decimal\('([^']+)'\)",
                _decimal_repl,
                sanitized,
            )
            
            # Step 3: Try to parse with literal_eval
            actual_data = literal_eval(sanitized)
        except Exception as e:
            # Log the parsing error for debugging
            if hasattr(st, "session_state") and hasattr(st.session_state, "processing_logs"):
                st.session_state.processing_logs.append(
                    {
                        "step": "⚠️ String Parsing Failed",
                        "content": f"Error: {str(e)}, Original data preview: {str(result.get('result'))[:200]}",
                        "timestamp": pd.Timestamp.now().strftime("%H:%M:%S"),
                    }
                )
            # Keep as-is if parsing fails
            pass

    # Check for truly empty results
    if actual_data is None:
        st.warning("⚠️ No data received from query execution.")
        _append_assistant_message("No data received from query execution.")
        return
    elif isinstance(actual_data, list) and len(actual_data) == 0:
        st.info("Query executed successfully but returned no results.")
        _append_assistant_message(
            "Query executed successfully but returned no results."
        )
        return

    # Debug logging for data validation
    if hasattr(st, "session_state") and hasattr(st.session_state, "processing_logs"):
        st.session_state.processing_logs.append(
            {
                "step": "🔍 Data Validation",
                "content": f"Data type: {type(actual_data)}, Length: {len(actual_data) if hasattr(actual_data, '__len__') else 'N/A'}, Preview: {str(actual_data)[:200]}...",
                "timestamp": pd.Timestamp.now().strftime("%H:%M:%S"),
            }
        )

    try:
        # Check if we received SQL instead of data (indicates a problem)
        if isinstance(actual_data, str) and actual_data.strip().upper().startswith(
            "SELECT"
        ):
            st.error(
                "⚠️ Received SQL query instead of data results. This indicates a processing issue."
            )
            st.code(actual_data)
            _append_assistant_message(
                f"Processing issue - received SQL instead of results: {actual_data}"
            )
            return

        # Get the SQL that was executed for column name extraction
        executed_sql = result.get("sql_query", "")
        
        # Show the generated SQL query to the user for transparency
        if executed_sql.strip():
            with st.expander("🔍 **Generated SQL Query**", expanded=False):
                st.code(executed_sql, language="sql")
                st.caption("💡 This is the SQL query that was automatically generated from your natural language question.")
                
                # Phase 2: Show query explanation
                explanation = result.get("explanation")
                if explanation:
                    st.markdown("---")
                    st.markdown("**📖 Query Explanation:**")
                    st.info(explanation)
                
                # Phase 2: Show confidence score
                confidence = result.get("confidence")
                if confidence:
                    st.markdown("---")
                    st.markdown("**🎯 Confidence Score:**")
                    overall = confidence.get("overall", 0.0)
                    
                    # Color code based on confidence
                    if overall >= 0.8:
                        st.success(f"Overall: {overall:.2f} (High Confidence)")
                    elif overall >= 0.6:
                        st.warning(f"Overall: {overall:.2f} (Medium Confidence)")
                    else:
                        st.error(f"Overall: {overall:.2f} (Low Confidence)")
                    
                    # Show breakdown
                    with st.expander("View Confidence Breakdown", expanded=False):
                        st.write(f"**Syntax:** {confidence.get('syntax', 0.0):.2f}")
                        st.write(f"**Semantic:** {confidence.get('semantic', 0.0):.2f}")
                        st.write(f"**Context Match:** {confidence.get('context_match', 0.0):.2f}")
                        st.write(f"**Table Validation:** {confidence.get('table_validation', 0.0):.2f}")
                    
                    # Show warnings if any
                    warnings = confidence.get("warnings", [])
                    if warnings:
                        st.warning("**Warnings:** " + "; ".join(warnings[:3]))
                
                # Phase 2: Show step-by-step explanation
                explanation_steps = result.get("explanation_steps")
                if explanation_steps:
                    st.markdown("---")
                    st.markdown("**📋 Step-by-Step Explanation:**")
                    for step in explanation_steps:
                        st.write(f"**Step {step.get('step', '?')}: {step.get('action', 'N/A')}**")
                        st.caption(step.get('details', ''))
                
                # Phase 2: Show validation warnings
                validation = result.get("validation")
                if validation and validation.get("warnings"):
                    st.markdown("---")
                    st.markdown("**⚠️ Validation Warnings:**")
                    for warning in validation.get("warnings", [])[:3]:
                        st.warning(warning)
        
        row_limit_notice = result.get("row_limit")
        if row_limit_notice:
            limit_value = row_limit_notice.get("limit")
            limit_display = limit_value if limit_value is not None else "the configured number of"
            st.warning(
                f"Showing only the first {limit_display} rows to keep the app responsive. "
                "Refine your filters to see more data."
            )

        # Log the generated SQL query for transparency
        if hasattr(st, "session_state") and hasattr(st.session_state, "processing_logs"):
            if executed_sql.strip():
                st.session_state.processing_logs.append(
                    {
                        "step": "🔍 Generated SQL Query",
                        "content": executed_sql,
                        "timestamp": pd.Timestamp.now().strftime("%H:%M:%S"),
                    }
                )

        # Get database connection for column name extraction
        db_connection = None
        if hasattr(st, "session_state") and hasattr(st.session_state, "agent") and st.session_state.agent:
            db_connection = getattr(st.session_state.agent, "db", None)

        # Format the actual data into a DataFrame
        df = format_sql_result_to_dataframe(actual_data, executed_sql, prompt, db_connection)

        # Intelligent column selection when there are too many columns
        def _norm(name: str) -> str:
            return str(name).strip().lower().replace(" ", "_")

        key_candidates = [
            "id",
            "agent_id",
            "agent_uid",
            "property_id",
            "name",
            "first_name",
            "last_name",
            "full_name",
            "email",
            "phone",
            "agency",
            "city",
            "state",
            "license_number",
            "active_flag",
            "date_joined",
        ]
        key_norms = set(key_candidates)
        column_norm_map = {c: _norm(c) for c in df.columns}
        selected_cols = [c for c, n in column_norm_map.items() if n in key_norms]

        show_all_key = f"show_all_cols_{abs(hash(executed_sql)) % (10**8)}"
        df_to_show = df
        if df.shape[1] > 12:
            show_all = st.checkbox("Show all columns", value=False, key=show_all_key)
            if not show_all and len(selected_cols) >= 3:
                df_to_show = df[selected_cols]

        # Detect URL-like columns for link rendering
        url_cols = [
            c
            for c in df_to_show.columns
            if ("url" in c.lower() or "website" in c.lower())
        ]
        column_config = {}
        for uc in url_cols:
            try:
                column_config[uc] = st.column_config.LinkColumn(label=uc)
            except Exception:
                pass  # Fallback silently if not supported

        # Row display control
        st.dataframe(df_to_show, width='stretch', column_config=column_config)
        num_rows = len(df)
        st.caption(f"📊 {num_rows} record{'s' if num_rows != 1 else ''} found")
        
        # Pagination controls
        pagination = result.get("pagination")
        if pagination:
            st.markdown("---")
            col1, col2, col3, col4 = st.columns(4)
            with col1:
                if pagination["has_previous"]:
                    if st.button("◀️ Previous", key=f"prev_page_{hash(executed_sql)}"):
                        st.session_state[f"page_{hash(executed_sql)}"] = pagination["page"] - 1
                        st.rerun()
            with col2:
                st.write(f"Page {pagination['page']} of {pagination['total_pages']}")
            with col3:
                if pagination["has_next"]:
                    if st.button("Next ▶️", key=f"next_page_{hash(executed_sql)}"):
                        st.session_state[f"page_{hash(executed_sql)}"] = pagination["page"] + 1
                        st.rerun()
            with col4:
                st.write(f"Total: {pagination['total_count']} rows")
        
        # Save query button
        st.markdown("---")
        col1, col2 = st.columns(2)
        with col1:
            if st.button("💾 Save Query", key=f"save_query_{hash(executed_sql)}"):
                st.session_state["show_save_query"] = True
        
        # Save query dialog
        if st.session_state.get("show_save_query", False):
            with st.expander("💾 Save Query", expanded=True):
                from src.utils.saved_queries import get_saved_query_manager
                saved_query_manager = get_saved_query_manager()
                
                query_name = st.text_input("Query Name", key="save_query_name")
                query_description = st.text_area("Description", key="save_query_description")
                query_category = st.selectbox(
                    "Category",
                    options=["general", "analytics", "reporting", "search"],
                    key="save_query_category"
                )
                
                col1, col2 = st.columns(2)
                with col1:
                    if st.button("✅ Save", key="confirm_save_query"):
                        if query_name:
                            try:
                                saved_query_manager.save_query(
                                    name=query_name,
                                    sql=executed_sql,
                                    description=query_description or "",
                                    user_question=prompt,
                                    category=query_category
                                )
                                st.success(f"Query '{query_name}' saved!")
                                st.session_state["show_save_query"] = False
                                st.rerun()
                            except ValueError as e:
                                st.error(str(e))
                        else:
                            st.error("Please provide a query name")
                with col2:
                    if st.button("❌ Cancel", key="cancel_save_query"):
                        st.session_state["show_save_query"] = False
                        st.rerun()

        # Export buttons
        csv_data = df.to_csv(index=False).encode("utf-8")
        st.download_button(
            label="Download CSV",
            data=csv_data,
            file_name="results.csv",
            mime="text/csv",
        )
        try:
            buf = io.BytesIO()
            df.to_parquet(buf, index=False)
            st.download_button(
                label="Download Parquet",
                data=buf.getvalue(),
                file_name="results.parquet",
                mime="application/octet-stream",
            )
        except Exception:
            pass  # Parquet dependencies not installed; skip

        _append_assistant_message(response_content, df, executed_sql)

    except Exception as e:
        st.error(f"Error formatting results: {str(e)}")
        result_text = str(result.get("result"))
        st.code(result_text)
        _append_assistant_message(f"{response_content}\n{result_text}")


def _render_error_result(error_text, result: Optional[Dict] = None):
    """Render an agent error and update history."""
    st.error(error_text)
    
    # Phase 2: Show suggestions if available
    if result and result.get("suggestions"):
        suggestions = result.get("suggestions", [])
        if suggestions:
            st.markdown("---")
            st.markdown("**💡 Correction Suggestions:**")
            for i, suggestion in enumerate(suggestions[:3], 1):
                with st.expander(f"Suggestion {i} (Confidence: {suggestion.get('confidence', 0.0):.2f})", expanded=False):
                    st.markdown(f"**Original:** `{suggestion.get('original', 'N/A')}`")
                    st.markdown(f"**Corrected:** `{suggestion.get('corrected', 'N/A')}`")
                    st.info(f"**Reason:** {suggestion.get('reason', 'N/A')}")
                    
                    # Button to try corrected query
                    if st.button(f"Try Suggestion {i}", key=f"try_suggestion_{i}"):
                        st.session_state["try_corrected_query"] = suggestion.get("corrected")
                        st.rerun()
    
    # Phase 2: Show validation errors if available
    if result and result.get("validation"):
        validation = result.get("validation")
        if validation.get("errors"):
            st.markdown("---")
            st.markdown("**❌ Validation Errors:**")
            for error in validation.get("errors", []):
                st.error(error)
    
    _append_assistant_message(error_text)


def process_user_input(prompt):
    """Process user input with hybrid detection.

    Hybrid flow:
    1. Check for saved query or template
    2. Validate input for safety
    3. Detect query type (DB, help, out of context)
    4. Respond appropriately according to type
    5. For DB queries: invoke NLP agent → SQL → execution (with cache and pagination)
    6. For others: show educational/redirect responses
    """
    from src.ui.input_validator import validate_user_input
    from src.ui.query_detector import is_database_query
    
    # Check for saved query to run
    if "run_saved_query" in st.session_state:
        saved_query_name = st.session_state.pop("run_saved_query")
        from src.utils.saved_queries import get_saved_query_manager
        saved_query_manager = get_saved_query_manager()
        saved_query = saved_query_manager.get_query(saved_query_name)
        if saved_query:
            # Use saved query SQL as prompt (will be executed directly)
            prompt = f"Execute this SQL query: {saved_query.sql}"
            if saved_query.user_question:
                prompt = saved_query.user_question
    
    # Check for filled template
    if "filled_template_sql" in st.session_state:
        template_sql = st.session_state.pop("filled_template_sql")
        template_name = st.session_state.pop("filled_template_name", "Template")
        # Use template SQL as prompt
        prompt = f"Execute this SQL query from {template_name}: {template_sql}"
    
    # Check for corrected query to try
    if "try_corrected_query" in st.session_state:
        corrected_sql = st.session_state.pop("try_corrected_query")
        # Use corrected SQL as prompt
        prompt = f"Execute this SQL query: {corrected_sql}"

    # Validate user input first
    is_valid, cleaned_prompt, error_message = validate_user_input(prompt)
    
    if not is_valid:
        # Show validation error without adding to session state
        with st.chat_message("assistant"):
            st.error(error_message)
            # Add a helpful message
            st.info("💡 **Tip:** Use natural language like:\n- 'Show me the top 10 customers'\n- 'What are the sales for 2023?'\n- 'How many orders do we have?'")
        return
    
    # Use cleaned prompt for processing
    prompt = cleaned_prompt
    
    # Get pagination info from session state if available
    page = 1
    page_size = None
    if hasattr(st.session_state, 'current_query_hash'):
        page_key = f"page_{st.session_state.current_query_hash}"
        if page_key in st.session_state:
            page = st.session_state[page_key]
    
    # Add user message
    st.session_state.messages.append({"role": "user", "content": prompt})

    with st.chat_message("user"):
        st.write(prompt)

    # Detect query type
    query_type = is_database_query(prompt)

    # Single assistant response block
    with st.chat_message("assistant"):
        if query_type == "help":
            help_resp = get_help_response()
            st.markdown(help_resp["message"])
            _append_assistant_message(help_resp["message"])
            return

        if query_type == "off_topic":
            redirect_resp = get_redirect_response()
            st.markdown(redirect_resp["message"])
            _append_assistant_message(redirect_resp["message"])
            return

        if query_type == "unclear":
            st.info(
                "🤔 I'm not sure if you're asking about data. I'll try as a DB query..."
            )

        if not st.session_state.agent:
            _render_error_result("Error: No agent initialized")
            return

        with st.spinner("Processing query..."):
            # Store query hash for pagination
            import hashlib
            query_hash = hashlib.md5(prompt.encode()).hexdigest()
            st.session_state.current_query_hash = query_hash
            
            # Get page from session state
            page_key = f"page_{query_hash}"
            current_page = st.session_state.get(page_key, 1)
            
            # Process with cache and pagination
            result = st.session_state.agent.process_query(
                prompt,
                use_enhanced_context=True,
                use_cache=True,
                page=current_page,
                page_size=None  # Use default
            )

        if result.get("success"):
            _render_successful_result(result, prompt)
            return

        _render_error_result(f"Error: {result.get('error', 'Unknown error')}", result)


def display_logs_panel():
    """Show explanatory logs panel with special highlighting for SQL queries"""
    st.header("📋 Process Logs")

    if st.session_state.processing_logs:
        # Show logs in reverse order (most recent first)
        for log in reversed(st.session_state.processing_logs[-10:]):  # Last 10 logs
            # Special treatment for SQL queries - expand by default and use SQL highlighting
            if "Generated SQL Query" in log['step']:
                with st.expander(f"⏰ {log['timestamp']} - {log['step']}", expanded=True):
                    st.code(log["content"], language="sql")
                    st.caption("🔍 This SQL query was automatically generated by the AI model")
            else:
                with st.expander(f"⏰ {log['timestamp']} - {log['step']}", expanded=False):
                    st.code(log["content"])
    else:
        st.info("No logs available. Make a query to see the process.")


