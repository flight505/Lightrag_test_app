# //A script
# requires-python = ">=3.11"|
# dependencies = [
#    # Core packages
#    "streamlit",
#    "streamlit-navigation-bar",
#    "watchdog",
#    "termcolor",
#    "networkx",
#    "openai",
#    "pandas",
#    "numpy",
#    "plotly",
#    "marker-pdf>=1.2.3",    
#    "matplotlib",
#    "requests",
#    "stqdm",
#    "uv",
#    "xxhash",
#    "pyvis",
#    "aioboto3",
#    "ruff",
#    "ollama",
#    "tiktoken",
#    "nano-vectordb",
#    
#    # PDF processing
#    "PyMuPDF",
#    "PyPDF2",
#    "pdf2doi",
#    "crossrefapi",
#    "scholarly",
#    
#    # RAG packages
#    "lightrag-hku>=1.1.0",
#    
#    # Development
#    "python-dotenv",
#    "python-docx",
#    "pytest"
#]
#///



import os
import streamlit as st
from src.academic_metadata import MetadataExtractor, PDFMetadataExtractor
from streamlit_navigation_bar import st_navbar

import pages as pg

# Page configuration
st.set_page_config(
    page_title="LightRAG Home",
    page_icon="🏠",
    layout="wide",
    initial_sidebar_state="collapsed",
    menu_items=None  # This hides the burger menu
)

# Navigation bar
pages = ["Home", "Search", "Manage Documents", "Academic Analysis", "GitHub"]
parent_dir = os.path.dirname(os.path.abspath(__file__))
urls = {"GitHub": "https://github.com/flight505/Lightrag_test_app"}
styles = {
    "nav": {
        "background-color": "royalblue",
        "justify-content": "left",
    },
    "img": {
        "padding-right": "14px",
    },
    "span": {
        "color": "white",
        "padding": "14px",
    },
    "active": {
        "background-color": "white",
        "color": "var(--text-color)",
        "font-weight": "normal",
        "padding": "14px",
    }
}
options = {
    "show_menu": False,
    "show_sidebar": False,
}

page = st_navbar(
    pages,
    urls=urls,
    styles=styles,
    options=options,
)

functions = {
    "Home": pg.show_home,
    "Search": pg.show_search,
    "Manage Documents": pg.show_manage,
    "Academic Analysis": pg.show_academic,
}
go_to = functions.get(page)
if go_to:
    go_to()