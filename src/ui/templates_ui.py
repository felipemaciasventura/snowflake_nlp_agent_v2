"""
UI components for Query Templates and Saved Queries
"""

import streamlit as st
from src.utils.query_templates import get_template_manager
from src.utils.saved_queries import get_saved_query_manager


def render_templates_section():
    """Render query templates section in sidebar"""
    st.sidebar.header("📋 Query Templates")
    
    template_manager = get_template_manager()
    templates = template_manager.get_templates()
    
    if not templates:
        st.sidebar.info("No templates available")
        return
    
    # Template selector
    template_names = [t.name for t in templates]
    selected_template_name = st.sidebar.selectbox(
        "Select Template",
        options=template_names,
        help="Choose a query template to use"
    )
    
    if selected_template_name:
        template = template_manager.get_template(selected_template_name)
        if template:
            st.sidebar.markdown(f"**{template.description}**")
            
            # Show template SQL
            with st.sidebar.expander("View Template SQL", expanded=False):
                st.code(template.template, language="sql")
            
            # Parameter inputs
            if template.parameters:
                st.sidebar.subheader("Parameters")
                params = {}
                for param in template.parameters:
                    params[param] = st.sidebar.text_input(
                        param.replace("_", " ").title(),
                        key=f"template_param_{template.name}_{param}"
                    )
                
                # Fill template button
                if st.sidebar.button("Fill Template", key=f"fill_template_{template.name}"):
                    try:
                        filled_sql = template.fill(params)
                        # Store in session state for use
                        st.session_state["filled_template_sql"] = filled_sql
                        st.session_state["filled_template_name"] = template.name
                        st.sidebar.success("Template filled! Use it in your query.")
                    except ValueError as e:
                        st.sidebar.error(f"Error: {e}")


def render_saved_queries_section():
    """Render saved queries section in sidebar"""
    st.sidebar.header("💾 Saved Queries")
    
    saved_query_manager = get_saved_query_manager()
    saved_queries = saved_query_manager.get_queries()
    
    if not saved_queries:
        st.sidebar.info("No saved queries yet")
        if st.sidebar.button("Learn how to save queries"):
            st.sidebar.info("After executing a query, you can save it from the results panel.")
        return
    
    # Search saved queries
    search_query = st.sidebar.text_input(
        "Search saved queries",
        key="search_saved_queries",
        placeholder="Search by name, description, or SQL..."
    )
    
    # Filter queries
    filtered_queries = saved_query_manager.get_queries(search=search_query) if search_query else saved_queries
    
    if not filtered_queries:
        st.sidebar.info("No queries match your search")
        return
    
    # Category filter
    categories = saved_query_manager.get_categories()
    if categories:
        selected_category = st.sidebar.selectbox(
            "Category",
            options=["All"] + categories,
            key="saved_query_category"
        )
        if selected_category != "All":
            filtered_queries = [q for q in filtered_queries if q.category == selected_category]
    
    # Display saved queries
    for query in filtered_queries[:10]:  # Show first 10
        with st.sidebar.expander(f"📌 {query.name}", expanded=False):
            st.markdown(f"**Description:** {query.description}")
            if query.user_question:
                st.markdown(f"**Original question:** {query.user_question}")
            st.markdown(f"**Category:** {query.category}")
            if query.tags:
                st.markdown(f"**Tags:** {', '.join(query.tags)}")
            st.markdown(f"**Used:** {query.use_count} times")
            if query.last_used:
                st.markdown(f"**Last used:** {query.last_used[:10]}")
            
            # Show SQL
            with st.expander("View SQL", expanded=False):
                st.code(query.sql, language="sql")
            
            # Run query button
            col1, col2 = st.columns(2)
            with col1:
                if st.button("▶️ Run", key=f"run_saved_{query.name}"):
                    st.session_state["run_saved_query"] = query.name
                    st.rerun()
            
            with col2:
                if st.button("🗑️ Delete", key=f"delete_saved_{query.name}"):
                    if saved_query_manager.delete_query(query.name):
                        st.sidebar.success(f"Deleted: {query.name}")
                        st.rerun()


def render_cache_section():
    """Render cache management section"""
    st.sidebar.header("⚡ Cache Management")
    
    if st.session_state.agent and hasattr(st.session_state.agent, 'query_cache'):
        cache = st.session_state.agent.query_cache
        stats = cache.get_cache_stats()
        
        st.sidebar.info(
            f"**Cache Stats:**\n"
            f"- Entries: {stats['total_entries']}\n"
            f"- TTL: {stats['ttl_minutes']} minutes\n"
            f"- Size: {stats['cache_size_mb']} MB"
        )
        
        col1, col2 = st.sidebar.columns(2)
        with col1:
            if st.button("🔄 Refresh Cache"):
                cache._clean_expired_entries()
                st.sidebar.success("Cache refreshed")
                st.rerun()
        
        with col2:
            if st.button("🗑️ Clear Cache"):
                cache.invalidate_cache()
                st.sidebar.success("Cache cleared")
                st.rerun()
    else:
        st.sidebar.info("Cache not available")



