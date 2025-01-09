import streamlit as st

# from src.academic_metadata import MetadataExtractor, PDFMetadataExtractor

def show_home():
    # Add this near the top of your app, in the sidebar
    st.divider()
    st.write("### 🏠 Home")

    debug_mode = st.checkbox("Enable Debug Mode", value=False)

    # Modify where you create the MetadataExtractor
    # pdf_extractor = PDFMetadataExtractor(debug=debug_mode)
    # extractor = MetadataExtractor()

    # Main layout
    left_col, right_col = st.columns([2, 1], gap="large")

    with left_col:
        # Header and introduction
        st.title("🌟 Welcome to LightRAG")
        st.markdown("""
        ### Your Academic Paper Analysis Assistant
        LightRAG helps you analyze academic papers efficiently using state-of-the-art retrieval-augmented generation.
        """)
        
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
