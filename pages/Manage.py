import os
import logging
from datetime import datetime
from pathlib import Path

import streamlit as st
import pandas as pd
from stqdm import stqdm

from src.file_manager import create_store_directory, DB_ROOT
from src.file_processor import FileProcessor

logger = logging.getLogger(__name__)

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
        status = st.status("Processing uploaded files...", expanded=True)
        for uploaded_file in stqdm(
            uploaded_files, 
            desc="Uploading files",
            total=len(uploaded_files),
            unit="file",
            bar_format="{desc}: {percentage:3.0f}%|{bar}| {n_fmt}/{total_fmt} [{elapsed}<{remaining}]"
        ):
            try:
                # Save the uploaded file
                file_path = os.path.join(store_path, uploaded_file.name)
                with open(file_path, "wb") as f:
                    f.write(uploaded_file.getvalue())
                status.update(label=f"Uploaded: {uploaded_file.name}")
                
                # Process the file with Marker
                try:
                    if st.session_state["file_processor"]:
                        # Check if file is already processed
                        txt_path = Path(store_path) / f"{Path(file_path).stem}.txt"
                        if txt_path.exists():
                            status.update(label=f"✓ {uploaded_file.name}: Already converted", state="complete")
                            continue
                            
                        result = st.session_state["file_processor"].process_pdf_with_marker(file_path)
                        if result:
                            status.update(label=f"✅ {uploaded_file.name}: Converted and indexed")
                        else:
                            status.update(label=f"❌ {uploaded_file.name}: Conversion failed", state="error")
                except Exception as e:
                    status.update(label=f"❌ {uploaded_file.name}: Processing error - {str(e)}", state="error")
                    logger.error(f"Error processing {uploaded_file.name}: {str(e)}", exc_info=True)
                    
            except Exception as e:
                status.update(label=f"❌ {uploaded_file.name}: Upload error - {str(e)}", state="error")
                logger.error(f"Error uploading {uploaded_file.name}: {str(e)}", exc_info=True)
        
        status.update(label="File processing complete!", state="complete")
    
    # Document list section
    st.markdown("### Manage Documents")
    
    # Create three columns for the action buttons
    action_col1, action_col2, action_col3 = st.columns(3)
    with action_col1:
        if st.button("🔄 Refresh Document List", use_container_width=True):
            st.rerun()
    with action_col2:
        if st.button("🧹 Clean Unused Files", use_container_width=True):
            if st.session_state["file_processor"]:
                removed = st.session_state["file_processor"].clean_unused_files()
                if removed:
                    st.info(f"Removed {len(removed)} unused files")
                else:
                    st.info("No unused files found")
    with action_col3:
        if st.button("⚡ Convert Pending", use_container_width=True):
            if st.session_state["file_processor"]:
                status = st.status("Converting pending documents...", expanded=True)
                # Get list of pending PDFs (those without corresponding txt files)
                pdf_files = list(Path(store_path).glob("*.pdf"))
                pending_files = []
                
                for pdf_file in pdf_files:
                    txt_path = pdf_file.with_suffix(".txt")
                    if not txt_path.exists():
                        pending_files.append(str(pdf_file))
                
                if not pending_files:
                    status.update(label="No pending documents to convert", state="complete")
                    st.rerun()
                
                def update_progress(message: str):
                    status.update(label=message)
                
                try:
                    results = st.session_state["file_processor"].process_pdf_with_marker(
                        pending_files,
                        progress_callback=update_progress
                    )
                    if results:
                        status.update(label=f"✅ Successfully converted {len(results)} documents", state="complete")
                    else:
                        status.update(label="No documents were converted successfully", state="error")
                except Exception as e:
                    status.update(label=f"❌ Error during conversion: {str(e)}", state="error")
                    logger.error(f"Error during batch conversion: {str(e)}", exc_info=True)
                
                st.rerun()
    
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
        
        if not pdf_files and not txt_files:
            st.info("No documents found in this store. Upload some PDF files to get started.")
            st.stop()
        
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
                
                # Initialize RAG if needed
                if "rag" not in st.session_state or st.session_state.rag is None:
                    st.error("Please initialize LightRAG in the Search page first.")
                    st.stop()
                
                for file_name in selected_files:
                    file_path = os.path.join(store_path, file_name)
                    try:
                        # Get document ID (using file name without extension as ID)
                        doc_id = Path(file_name).stem
                        
                        # Delete from LightRAG first
                        try:
                            st.session_state.rag.delete_by_doc_id(doc_id)
                            logger.info(f"Deleted document {doc_id} from LightRAG")
                        except Exception as e:
                            logger.error(f"Error deleting document {doc_id} from LightRAG: {str(e)}")
                            st.warning(f"Could not delete {file_name} from LightRAG: {str(e)}")
                        
                        # Remove the file
                        os.remove(file_path)
                        
                        # Remove corresponding files based on type
                        base_path = os.path.splitext(file_path)[0]
                        
                        # If it's a PDF, remove corresponding .txt and .json
                        if file_name.lower().endswith('.pdf'):
                            txt_path = base_path + ".txt"
                            json_path = base_path + ".json"
                            if os.path.exists(txt_path):
                                os.remove(txt_path)
                            if os.path.exists(json_path):
                                os.remove(json_path)
                        
                        # If it's a text file, remove corresponding .json and check PDF
                        elif file_name.lower().endswith('.txt'):
                            json_path = base_path + ".json"
                            pdf_path = base_path + ".pdf"
                            if os.path.exists(json_path):
                                os.remove(json_path)
                            # Only remove PDF if it exists and is selected
                            if os.path.exists(pdf_path) and os.path.basename(pdf_path) in selected_files:
                                os.remove(pdf_path)
                        
                        st.success(f"Deleted: {file_name}")
                        
                    except Exception as e:
                        st.error(f"Error deleting {file_name}: {str(e)}")
                        logger.error(f"Error deleting {file_name}: {str(e)}", exc_info=True)
                
                # Run cleanup to ensure no orphaned files
                if st.session_state["file_processor"]:
                    removed = st.session_state["file_processor"].clean_unused_files()
                    if any(removed.values()):
                        st.info("Cleaned up associated files")
                
                st.rerun()
                
    except Exception as e:
        st.error(f"Error loading document list: {str(e)}")
        logger.error(f"Error in document list: {str(e)}", exc_info=True) 