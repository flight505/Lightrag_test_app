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
from streamlit_navigation_bar import st_navbar
from termcolor import colored

import pages as pg

# Page configuration
st.set_page_config(
    page_title="LightRAG Home",
    page_icon="🏠",
    layout="wide",
    initial_sidebar_state="collapsed",
)

# Navigation bar
pages = ["Home", "Search", "Documents", "Academics", "GitHub"]
parent_dir = os.path.dirname(os.path.abspath(__file__))
print(colored(parent_dir, "red"))
urls = {
    "GitHub": "https://github.com/flight505/Lightrag_test_app",
}
logo_path = os.path.join(parent_dir, "lightning_icon2.svg")
styles = {
    "nav": {
        "background-color": "#44475a",
        "padding": "0.5rem 2rem",
        "height": "3.5rem",
        "display": "flex",
        "align-items": "center",
        "justify-content": "space-between"
    },
    "img": {
        "padding-right": "14px",
    },
    "span": {
        "color": "#f8f8f2",
        "padding": "0.5rem 1.5rem",
        "font-weight": "500",
        "border-radius": "0.5rem",
        "white-space": "nowrap",
        "text-align": "center",
        "min-width": "8.5rem"
    },
    "active": {
        "background-color": "#282a36",
        "color": "#bd93f9",
        "font-weight": "600"
    }
}
options = {
    "show_menu": False,
    "show_sidebar": False,
    "fix_shadow": True,
    "hide_nav": True
}

page = st_navbar(
    pages,
    urls=urls,
    logo_path=logo_path,
    styles=styles,
    options=options,
)

functions = {
    "Home": pg.show_home,
    "Search": pg.show_search,
    "Documents": pg.show_manage,
    "Academics": pg.show_academic,
}
go_to = functions.get(page)
if go_to:
    go_to()