import streamlit as st

from pathlib import Path
from src.academic_metadata import (
    AcademicMetadata, Author, Reference, Citation
)
from src.equation_metadata import Equation
import json
from termcolor import colored
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from collections import Counter, defaultdict
import networkx as nx
import pyvis
from pyvis.network import Network
import tempfile

def show_academic():
    st.divider()
    st.write("### 📚 Academic Analysis")
    
    def load_metadata_files(store_path: Path) -> list[AcademicMetadata]:
        """Load all metadata files from the store"""
        metadata_files = list(store_path.glob("*_metadata.json"))
        metadata_list = []
        
        for file in metadata_files:
            try:
                with open(file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    metadata = AcademicMetadata.from_dict(data)
                    metadata_list.append(metadata)
            except Exception as e:
                st.error(f"Error loading {file.name}: {str(e)}")
        
        return metadata_list

    def create_citation_network(metadata_list: list[AcademicMetadata]) -> Network:
        """Create citation network visualization"""
        G = nx.DiGraph()
        
        # Add nodes and edges
        for doc in metadata_list:
            # Add document as node
            G.add_node(doc.doc_id, title=doc.title, type="document")
            
            # Add references and citations
            for ref in doc.references:
                ref_id = f"{ref.title}_{ref.year}" if ref.title and ref.year else str(ref)
                G.add_node(ref_id, title=ref.title or "Unknown", type="reference")
                G.add_edge(doc.doc_id, ref_id)
        
        # Create PyVis network
        net = Network(height="600px", width="100%", bgcolor="#222222", font_color="white")
        
        # Add nodes with different colors for documents and references
        for node in G.nodes(data=True):
            net.add_node(
                node[0],
                label=node[1]["title"][:30] + "..." if len(node[1]["title"]) > 30 else node[1]["title"],
                color="#00ff00" if node[1]["type"] == "document" else "#ff9999"
            )
        
        # Add edges
        for edge in G.edges():
            net.add_edge(edge[0], edge[1])
        
        net.set_options("""
        var options = {
            "physics": {
                "forceAtlas2Based": {
                    "gravitationalConstant": -100,
                    "centralGravity": 0.01,
                    "springLength": 100,
                    "springConstant": 0.08
                },
                "solver": "forceAtlas2Based",
                "minVelocity": 0.75,
                "timestep": 0.5
            }
        }
        """)
        
        return net

    def main():
        st.title("📚 Academic Analysis")
        
        # Get current store path
        if "active_store" not in st.session_state:
            st.error("Please select a store in the Manage page first")
            return
            
        store_path = Path("DB") / st.session_state["active_store"]
        if not store_path.exists():
            st.error(f"Store path {store_path} does not exist")
            return
        
        # Load metadata
        metadata_list = load_metadata_files(store_path)
        if not metadata_list:
            st.warning("No academic metadata found in the current store")
            return
        
        # Display summary statistics
        st.header("📊 Summary Statistics")
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            st.metric("Documents", len(metadata_list))
        
        total_refs = sum(len(doc.references) for doc in metadata_list)
        with col2:
            st.metric("References", total_refs)
        
        total_citations = sum(len(doc.citations) for doc in metadata_list)
        with col3:
            st.metric("Citations", total_citations)
        
        total_equations = sum(len(doc.equations) for doc in metadata_list)
        with col4:
            st.metric("Equations", total_equations)
        
        # Citation Network
        st.header("🕸️ Citation Network")
        net = create_citation_network(metadata_list)
        
        # Save and display network
        with tempfile.NamedTemporaryFile(delete=False, suffix='.html') as tmp:
            net.save_graph(tmp.name)
            with open(tmp.name, 'r', encoding='utf-8') as f:
                html = f.read()
            st.components.v1.html(html, height=600)
        
        # Reference Analysis
        st.header("📑 Reference Analysis")
        
        # Year distribution
        years = [ref.year for doc in metadata_list for ref in doc.references if ref.year]
        if years:
            fig = px.histogram(
                x=years,
                title="Reference Year Distribution",
                labels={"x": "Year", "y": "Count"},
                template="plotly_dark"
            )
            st.plotly_chart(fig, use_container_width=True)
        
        # Author Analysis
        st.header("👥 Author Analysis")
        
        # Count author appearances
        author_counts = Counter()
        for doc in metadata_list:
            for ref in doc.references:
                for author in ref.authors:
                    if author.full_name:
                        author_counts[author.full_name] += 1
        
        # Create author frequency chart
        top_authors = dict(sorted(author_counts.items(), key=lambda x: x[1], reverse=True)[:20])
        if top_authors:
            fig = px.bar(
                x=list(top_authors.keys()),
                y=list(top_authors.values()),
                title="Top 20 Most Cited Authors",
                labels={"x": "Author", "y": "Citations"},
                template="plotly_dark"
            )
            fig.update_layout(xaxis_tickangle=45)
            st.plotly_chart(fig, use_container_width=True)
        
        # Equation Analysis
        if any(doc.equations for doc in metadata_list):
            st.header("📐 Equation Analysis")
            
            # Count equation types
            eq_types = Counter()
            symbols = Counter()
            for doc in metadata_list:
                for eq in doc.equations:
                    eq_types[eq.equation_type] += 1
                    symbols.update(eq.symbols)
            
            col1, col2 = st.columns(2)
            
            with col1:
                # Equation types pie chart
                if eq_types:
                    fig = px.pie(
                        values=list(eq_types.values()),
                        names=list(eq_types.keys()),
                        title="Equation Types Distribution",
                        template="plotly_dark"
                    )
                    st.plotly_chart(fig, use_container_width=True)
            
            with col2:
                # Most common symbols
                if symbols:
                    top_symbols = dict(sorted(symbols.items(), key=lambda x: x[1], reverse=True)[:10])
                    fig = px.bar(
                        x=list(top_symbols.keys()),
                        y=list(top_symbols.values()),
                        title="Top 10 Mathematical Symbols",
                        labels={"x": "Symbol", "y": "Occurrences"},
                        template="plotly_dark"
                    )
                    st.plotly_chart(fig, use_container_width=True)

    if __name__ == "__main__":
        main() 