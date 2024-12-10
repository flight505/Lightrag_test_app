import streamlit as st

st.set_page_config(
    page_title="LightRAG Query Interface",
    page_icon="💡",
)

st.write("# Query your Knowledge Base with LightRAG! 💡")
st.sidebar.success("Select your search mode.")

st.markdown(
    """
    Use this app to query your documents using [LightRAG](https://github.com/HKU-LightRAG/LightRAG).
    
    👈 Get started by selecting your search mode on the left.

    ### About LightRAG Search

    LightRAG provides an efficient and powerful way to search through your documents using:
    
    - **Semantic Search**: Find relevant information based on meaning, not just keywords
    - **Hybrid Retrieval**: Combines multiple search strategies for better results
    - **Source Tracking**: Always know where your information comes from
    
    ### Getting Started
    
    1. Configure your API key and model settings
    2. Select your search mode
    3. Enter your query and get detailed responses with source citations
    
    👈 Select your search mode to begin!
"""
)
