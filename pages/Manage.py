import os
import logging
from datetime import datetime
from pathlib import Path

import streamlit as st
import pandas as pd

from src.file_manager import create_store_directory, DB_ROOT
from src.file_processor import FileProcessor

# Page configuration
st.set_page_config(
    page_title="LightRAG Document Manager",
    page_icon="📁",
    layout="wide",
    initial_sidebar_state="collapsed",
    menu_items=None  # This hides the burger menu
)

# Navigation menu
nav_col1, nav_col2, nav_col3 = st.columns([1, 1, 1])
with nav_col1:
    if st.button("🏠 Home", use_container_width=True):
        st.switch_page("streamlit_app.py")
with nav_col2:
    if st.button("💬 Chat", use_container_width=True):
        st.switch_page("pages/Search.py")
with nav_col3:
    if st.button("📁 Manage Documents", use_container_width=True, type="primary"):
        st.switch_page("pages/Manage.py")

st.divider()

# Main interface
st.write("## 📁 Document Manager")

# Store selection in main content
store_col1, store_col2 = st.columns([3, 1])
with store_col1:
    # List existing stores
    stores = [d for d in os.listdir(DB_ROOT) if os.path.isdir(os.path.join(DB_ROOT, d))]
    
    # Calculate current store index
    current_index = 0
    if "active_store" in st.session_state and st.session_state["active_store"] in stores:
        current_index = stores.index(st.session_state["active_store"]) + 1
    
    # Store selection
    selected_store = st.selectbox(
        "Select Document Store",
        ["Create New..."] + stores,
        index=current_index,
        help="Choose an existing document store or create a new one"
    )

with store_col2:
    if selected_store == "Create New...":
        new_store = st.text_input("Store Name")
        if st.button("Create Store", type="primary", use_container_width=True):
            if new_store:
                store_path = create_store_directory(new_store)
                if store_path:
                    st.session_state["active_store"] = new_store
                    st.session_state["file_processor"] = FileProcessor(store_path)
                    st.success(f"Created store: {new_store}")
                    st.rerun()
    else:
        # Only update if the store selection has changed
        if selected_store != st.session_state.get("active_store"):
            store_path = os.path.join(DB_ROOT, selected_store)
            st.session_state["active_store"] = selected_store
            st.session_state["file_processor"] = FileProcessor(store_path)
            st.rerun()

st.divider()

# Document management interface
if "active_store" in st.session_state and st.session_state["active_store"]:
    store_path = os.path.join(DB_ROOT, st.session_state["active_store"])
    
    # File upload section
    st.markdown("### Upload Documents")
    uploaded_files = st.file_uploader(
        "Upload PDF documents",
        type=["pdf"],
        accept_multiple_files=True,
        help="Select one or more PDF files to upload"
    )
    
    if uploaded_files:
        for uploaded_file in uploaded_files:
            # Save the uploaded file
            file_path = os.path.join(store_path, uploaded_file.name)
            with open(file_path, "wb") as f:
                f.write(uploaded_file.getvalue())
            st.success(f"Uploaded: {uploaded_file.name}")
        
        # Process the new files
        if st.session_state["file_processor"]:
            with st.status("Processing uploaded files...", expanded=True):
                results = st.session_state["file_processor"].scan_and_convert_store()
                if results:
                    st.write("Processing Results:")
                    for filename, status in results.items():
                        if status == "converted":
                            st.success(f"✅ {filename}: Converted to text")
                        elif status == "skipped":
                            st.info(f"ℹ️ {filename}: Already processed")
                        else:
                            st.error(f"❌ {filename}: {status}")
    
    # Document list section
    st.markdown("### Manage Documents")
    
    # Create two columns for the action buttons
    action_col1, action_col2 = st.columns(2)
    with action_col1:
        if st.button("🔄 Refresh Document List", use_container_width=True):
            st.rerun()
    with action_col2:
        if st.button("🧹 Clean Unused Files", use_container_width=True):
            if st.session_state["file_processor"]:
                removed = st.session_state["file_processor"].cleanup_unused()
                if removed:
                    st.info(f"Removed {len(removed)} unused files")
                else:
                    st.info("No unused files found")
    
    try:
        # Get list of PDF and text files
        pdf_files = list(Path(store_path).glob("*.pdf"))
        txt_files = list(Path(store_path).glob("*.txt"))
        
        # Filter out system files
        system_files = ["graph_chunk_entity_relation.graphml", "graph_visualization.html", 
                       "kv_store_full_docs.json", "kv_store_llm_response_cache.json",
                       "kv_store_text_chunks.json", "metadata.json", "vdb_chunks.json",
                       "vdb_entities.json", "vdb_relationships.json"]
        
        txt_files = [f for f in txt_files if f.name not in system_files]
        
        if pdf_files or txt_files:
            # Create DataFrame with file information
            files_data = []
            
            # Add PDF files
            for file in pdf_files:
                file_stat = file.stat()
                txt_file = file.with_suffix(".txt")
                files_data.append({
                    "selected": False,
                    "name": file.name,
                    "type": "PDF",
                    "size": f"{file_stat.st_size / 1024:.1f} KB",
                    "modified": datetime.fromtimestamp(file_stat.st_mtime).strftime("%Y-%m-%d %H:%M"),
                    "status": "Processed" if txt_file.exists() else "Pending"
                })
            
            # Add text files
            for file in txt_files:
                file_stat = file.stat()
                pdf_file = file.with_suffix(".pdf")
                files_data.append({
                    "selected": False,
                    "name": file.name,
                    "type": "Text",
                    "size": f"{file_stat.st_size / 1024:.1f} KB",
                    "modified": datetime.fromtimestamp(file_stat.st_mtime).strftime("%Y-%m-%d %H:%M"),
                    "status": "Source" if pdf_file.exists() else "Standalone"
                })
            
            # Create DataFrame
            df = pd.DataFrame(files_data)
            
            # Display the DataFrame with data editor
            edited_df = st.data_editor(
                data=df,
                key="document_editor",
                column_config={
                    "selected": st.column_config.CheckboxColumn(
                        "Select",
                        default=False,
                        width="small"
                    ),
                    "name": st.column_config.TextColumn(
                        "File Name",
                        width="large"
                    ),
                    "type": st.column_config.TextColumn(
                        "Type",
                        width="small"
                    ),
                    "size": st.column_config.TextColumn(
                        "Size",
                        width="small"
                    ),
                    "modified": st.column_config.TextColumn(
                        "Modified",
                        width="medium"
                    ),
                    "status": st.column_config.TextColumn(
                        "Status",
                        width="small"
                    ),
                },
                hide_index=True,
                use_container_width=True,
            )
            
            # Add delete button for selected files
            if edited_df["selected"].any():
                if st.button("🗑️ Delete Selected Files", type="primary"):
                    selected_files = edited_df[edited_df["selected"]]["name"].tolist()
                    for file_name in selected_files:
                        file_path = os.path.join(store_path, file_name)
                        try:
                            # Remove PDF file
                            os.remove(file_path)
                            # Remove corresponding text file if it exists
                            txt_path = os.path.splitext(file_path)[0] + ".txt"
                            if os.path.exists(txt_path):
                                os.remove(txt_path)
                            st.success(f"Deleted: {file_name}")
                        except Exception as e:
                            st.error(f"Error deleting {file_name}: {str(e)}")
                    st.rerun()
        else:
            st.info("No documents found in this store. Upload some PDF files to get started.")
    except Exception as e:
        st.error(f"Error loading document list: {str(e)}")
        logger.error(f"Error in document list: {str(e)}", exc_info=True) 