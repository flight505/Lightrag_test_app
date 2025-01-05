import streamlit as st
from pathlib import Path

# Page configuration
st.set_page_config(
    page_title="LightRAG Home",
    page_icon="🏠",
    layout="wide",
    initial_sidebar_state="collapsed",
    menu_items=None  # This hides the burger menu
)

# Main layout
left_col, right_col = st.columns([2, 1], gap="large")

with left_col:
    # Header and introduction
    st.title("🌟 Welcome to LightRAG")
    st.markdown("""
    ### Your Academic Paper Analysis Assistant
    LightRAG helps you analyze academic papers efficiently using state-of-the-art retrieval-augmented generation.
    """)
    
    # Navigation cards in sub-columns
    nav_col1, nav_col2, nav_col3 = st.columns(3, gap="medium")
    
    with nav_col1:
        st.markdown("### 📚 Manage Documents")
        st.markdown("Upload and organize your academic papers")
        manage_btn = st.button("Go to Document Manager", use_container_width=True)
        if manage_btn:
            st.switch_page("pages/Manage.py")
    
    with nav_col2:
        st.markdown("### 🔍 Search Papers")
        st.markdown("Search and analyze your documents")
        search_btn = st.button("Go to Search", use_container_width=True)
        if search_btn:
            st.switch_page("pages/Search.py")
    
    with nav_col3:
        st.markdown("### 📊 Academic Analysis")
        st.markdown("Analyze citations and equations")
        academic_btn = st.button("Go to Academic Analysis", use_container_width=True)
        if academic_btn:
            st.switch_page("pages/Academic.py")
    
    # System status
    st.divider()
    status_col1, status_col2 = st.columns(2)
    with status_col1:
        if "active_store" in st.session_state and st.session_state["active_store"]:
            st.success(f"🟢 Active Store: {st.session_state['active_store']}")
        else:
            st.warning("🟡 No active store selected")
    with status_col2:
        if "status_ready" in st.session_state and st.session_state["status_ready"]:
            st.success("🟢 LightRAG: Initialized")
        else:
            st.warning("🟡 LightRAG: Not initialized")

with right_col:
    # Features in an expander
    with st.expander("📚 Features", expanded=True):
        st.markdown("""
        **Document Management**
        - Upload and process PDF documents
        - Organize papers in separate stores
        - Track document processing status

        **Advanced Search**
        - Mix mode: Knowledge Graph + Vector Retrieval
        - Hybrid mode: Combined local and global search
        - Local mode: Context-focused search
        - Global mode: Broad relationship search

        **Academic Analysis**
        - Citation network visualization
        - Reference validation and DOI checking
        - Equation analysis and classification
        - Academic metadata extraction
        """)
    
    # Quick tips in an expander
    with st.expander("💡 Quick Tips", expanded=True):
        st.markdown("""
        1. Start by creating a document store in the **Document Manager**
        2. Upload your PDF papers and wait for processing
        3. Initialize LightRAG in the **Search** page
        4. Use different search modes for queries:
           - **Mix**: Complex relationships
           - **Hybrid**: General questions
           - **Local**: Specific details
           - **Global**: Broad themes
        5. Explore academic features:
           - View citation networks
           - Validate references
           - Analyze equations
        """)

# Footer
st.markdown("""
<div style='position: fixed; bottom: 0; width: 100%; text-align: center; padding: 10px; background: var(--background-color)'>
<small>LightRAG - Simple and Fast Retrieval-Augmented Generation</small>
</div>
""", unsafe_allow_html=True) 