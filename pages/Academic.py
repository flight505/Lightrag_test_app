import streamlit as st
from pathlib import Path
from src.academic_metadata import (
    AcademicMetadata, CitationGraphAnalyzer, 
    ValidationLevel, ReferenceValidator
)

# Page configuration
st.set_page_config(
    page_title="Academic Analysis",
    page_icon="📚",
    layout="wide",
    initial_sidebar_state="collapsed"
)

def check_initialization():
    """Check if LightRAG is initialized"""
    if not st.session_state.get("status_ready", False):
        st.error("⚠️ Please initialize LightRAG in the Search page first")
        return False
    return True

def show_citation_network():
    """Show citation network analysis and visualization"""
    st.header("📊 Citation Network Analysis")
    
    # Get all metadata
    metadata_list = []
    for doc_info in st.session_state.file_processor.metadata["files"].values():
        if "academic_metadata" in doc_info:
            metadata = AcademicMetadata.from_dict(doc_info["academic_metadata"])
            metadata_list.append(metadata)
    
    if not metadata_list:
        st.warning("No academic metadata found. Process some documents first.")
        return
    
    # Initialize analyzer
    analyzer = CitationGraphAnalyzer()
    analyzer.build_graph(metadata_list)
    
    # Analysis results
    with st.spinner("Analyzing citation network..."):
        analysis = analyzer.analyze()
    
    # Display results in columns
    metrics_col, viz_col = st.columns([1, 2])
    
    with metrics_col:
        # Network metrics
        st.subheader("📈 Network Statistics")
        st.metric("Average Citations", f"{analysis.average_citations:.2f}")
        st.metric("Network Density", f"{analysis.network_density:.2f}")
        
        # Most cited papers
        st.subheader("🏆 Most Cited Papers")
        for paper, citations in analysis.most_cited:
            st.write(f"- **{paper}**: {citations} citations")
        
        # Influential papers
        st.subheader("⭐ Influential Papers")
        for paper in analysis.influential_papers:
            st.write(f"- {paper}")
    
    with viz_col:
        # Visualization
        st.subheader("🕸️ Citation Network Visualization")
        
        # Visualization options
        viz_options = st.columns(3)
        with viz_options[0]:
            node_size = st.slider("Node Size", 50, 500, 200)
        with viz_options[1]:
            font_size = st.slider("Font Size", 6, 16, 8)
        with viz_options[2]:
            alpha = st.slider("Transparency", 0.1, 1.0, 0.6)
        
        # Generate visualization
        viz_path = Path("temp_network.png")
        with st.spinner("Generating visualization..."):
            analyzer.visualize(
                output_path=viz_path,
                node_size=node_size,
                font_size=font_size,
                alpha=alpha
            )
        st.image(str(viz_path))
        
        # Export option
        if st.button("Export Network Data"):
            export_path = Path("citation_network.json")
            analyzer.export_graph(export_path)
            st.success(f"Network data exported to {export_path}")

def show_reference_validation():
    """Show reference validation interface"""
    st.header("🔍 Reference Validation")
    
    # Validation settings
    validation_level = st.selectbox(
        "Validation Level",
        options=[v.value for v in ValidationLevel],
        format_func=lambda x: x.title()
    )
    
    validator = ReferenceValidator(ValidationLevel(validation_level))
    
    # Process each document
    for doc_name, doc_info in st.session_state.file_processor.metadata["files"].items():
        if "academic_metadata" in doc_info:
            metadata = AcademicMetadata.from_dict(doc_info["academic_metadata"])
            
            with st.expander(f"📄 {doc_name}"):
                # Document overview
                st.write("Title:", metadata.title)
                st.write("Authors:", ", ".join(a.full_name for a in metadata.authors))
                
                # Reference validation
                st.subheader("References")
                for ref in metadata.references:
                    result = ref.validate(validator)
                    
                    # Reference details
                    ref_container = st.container()
                    ref_container.markdown(f"**{ref.title or 'Untitled Reference'}**")
                    
                    # Show validation results
                    if not result.is_valid:
                        ref_container.error("❌ " + ", ".join(result.errors))
                    if result.warnings:
                        ref_container.warning("⚠️ " + ", ".join(result.warnings))
                    
                    # Reference metadata
                    with ref_container.expander("Details"):
                        st.json({
                            "authors": [a.full_name for a in ref.authors],
                            "year": ref.year,
                            "venue": ref.venue,
                            "doi": ref.doi,
                            "citation_key": ref.citation_key
                        })

def show_equation_analysis():
    """Show equation analysis interface"""
    st.header("📐 Equation Analysis")
    
    # Collect all equations
    all_equations = []
    for doc_info in st.session_state.file_processor.metadata["files"].values():
        if "academic_metadata" in doc_info:
            metadata = AcademicMetadata.from_dict(doc_info["academic_metadata"])
            all_equations.extend(metadata.equations)
    
    if not all_equations:
        st.warning("No equations found in the documents.")
        return
    
    # Statistics
    st.subheader("📊 Equation Statistics")
    eq_types = {}
    for eq in all_equations:
        eq_types[eq.equation_type] = eq_types.get(eq.equation_type, 0) + 1
    
    # Display statistics
    stats_cols = st.columns(len(eq_types))
    for col, (eq_type, count) in zip(stats_cols, eq_types.items()):
        col.metric(
            f"{eq_type.title()} Equations",
            count,
            help=f"Number of {eq_type} equations found"
        )
    
    # Equation browser
    st.subheader("🔍 Equation Browser")
    
    # Filters
    filter_cols = st.columns(3)
    with filter_cols[0]:
        selected_type = st.selectbox(
            "Equation Type",
            options=["All"] + list(eq_types.keys())
        )
    with filter_cols[1]:
        search_symbols = st.text_input(
            "Search Symbols",
            placeholder="e.g., sigma, alpha"
        )
    with filter_cols[2]:
        selected_sort = st.selectbox(
            "Sort By",
            options=["Type", "Complexity", "Document"]
        )
        if selected_sort:
            # Sort equations based on selection
            if selected_sort == "Type":
                all_equations.sort(key=lambda x: x.type)
            elif selected_sort == "Complexity":
                all_equations.sort(key=lambda x: x.complexity)
            elif selected_sort == "Document":
                all_equations.sort(key=lambda x: x.document_id)
    
    # Filter equations
    filtered_equations = all_equations
    if selected_type != "All":
        filtered_equations = [eq for eq in filtered_equations 
                            if eq.equation_type == selected_type]
    if search_symbols:
        symbols = [s.strip() for s in search_symbols.split(",")]
        filtered_equations = [eq for eq in filtered_equations 
                            if any(s in eq.symbols for s in symbols)]
    
    # Display equations
    for eq in filtered_equations:
        with st.expander(f"Equation {eq.equation_id}"):
            st.latex(eq.raw_text)
            st.write("**Context:**", eq.context)
            st.write("**Type:**", eq.equation_type)
            st.write("**Symbols:**", ", ".join(eq.symbols))

def main():
    """Main function for the academic analysis page"""
    st.title("📚 Academic Analysis")
    
    if not check_initialization():
        return
    
    # Feature selection
    feature = st.radio(
        "Select Analysis Feature",
        options=["Citation Network", "Reference Validation", "Equation Analysis"],
        format_func=lambda x: {
            "Citation Network": "🕸️ Citation Network",
            "Reference Validation": "🔍 Reference Validation",
            "Equation Analysis": "📐 Equation Analysis"
        }[x],
        horizontal=True
    )
    
    st.divider()
    
    # Show selected feature
    if feature == "Citation Network":
        show_citation_network()
    elif feature == "Reference Validation":
        show_reference_validation()
    else:
        show_equation_analysis()

if __name__ == "__main__":
    main() 