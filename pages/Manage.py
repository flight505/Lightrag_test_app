import os
import logging
from datetime import datetime
from pathlib import Path
import json
import threading

import streamlit as st
import pandas as pd
from streamlit.runtime.scriptrunner import add_script_run_ctx

from src.file_manager import create_store_directory, DB_ROOT
from src.file_processor import FileProcessor
from src.academic_metadata import AcademicMetadata
from src.config_manager import ConfigManager

logger = logging.getLogger(__name__)

# Initialize session state at the top of the script
if 'initialized' not in st.session_state:
    st.session_state['initialized'] = True

def init_session_state():
    """Initialize session state variables"""
    if 'file_processor' not in st.session_state:
        st.session_state['file_processor'] = None
    if 'current_store' not in st.session_state:
        st.session_state['current_store'] = None
    if 'config_manager' not in st.session_state:
        st.session_state['config_manager'] = ConfigManager()

def run_with_context(func, *args, **kwargs):
    """Run a function with proper Streamlit context"""
    thread = threading.current_thread()
    add_script_run_ctx(thread)
    return func(*args, **kwargs)

# Initialize session state
init_session_state()

def process_files(uploaded_files, file_processor, status):
    """Save uploaded files without processing"""
    try:
        if not file_processor or not file_processor.store_path:
            raise ValueError("File processor not properly initialized with store path")
            
        for uploaded_file in uploaded_files:
            status.update(label=f"Saving {uploaded_file.name}...")
            
            # Save uploaded file
            pdf_path = Path(file_processor.store_path) / uploaded_file.name
            with open(pdf_path, "wb") as f:
                f.write(uploaded_file.getbuffer())
            
        status.update(label="✅ All files saved successfully. Click 'Convert Pending' to process them.", state="complete")
        return True
        
    except Exception as e:
        status.update(label=f"❌ Error saving files: {str(e)}", state="error")
        logger.error(f"Error saving files: {str(e)}", exc_info=True)
        return False

def reinit_file_processor(store_path: str) -> FileProcessor:
    """Reinitialize the file processor with the current store path"""
    file_processor = FileProcessor(st.session_state["config_manager"])
    file_processor.set_store_path(store_path)
    st.session_state["file_processor"] = file_processor
    return file_processor

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
        help="Choose an existing document store or create a new one",
        key="store_select"
    )

with store_col2:
    if selected_store == "Create New...":
        new_store = st.text_input("Store Name", key="new_store")
        if st.button("Create Store", key="create_store", type="primary", use_container_width=True):
            if new_store:
                store_path = create_store_directory(new_store)
                if store_path:
                    st.session_state["active_store"] = new_store
                    file_processor = FileProcessor(st.session_state["config_manager"])
                    file_processor.set_store_path(store_path)
                    st.session_state["file_processor"] = file_processor
                    st.success(f"Created store: {new_store}")
                    st.rerun()
    else:
        # Only update if the store selection has changed
        if selected_store != st.session_state.get("active_store"):
            store_path = os.path.join(DB_ROOT, selected_store)
            st.session_state["active_store"] = selected_store
            file_processor = FileProcessor(st.session_state["config_manager"])
            file_processor.set_store_path(store_path)
            st.session_state["file_processor"] = file_processor
            st.rerun()

st.divider()

# Document management interface
if "active_store" in st.session_state and st.session_state["active_store"]:
    store_path = os.path.join(DB_ROOT, st.session_state["active_store"])
    
    # Ensure file processor is initialized with store path
    if not st.session_state["file_processor"]:
        file_processor = reinit_file_processor(store_path)
    elif not st.session_state["file_processor"].store_path:
        file_processor = reinit_file_processor(store_path)
    else:
        file_processor = st.session_state["file_processor"]
    
    # File upload section
    st.markdown("### Upload Documents")
    st.info("Upload your PDF files here. After uploading, click 'Convert Pending' to process them.")
    uploaded_files = st.file_uploader(
        "Upload PDF documents",
        type=["pdf"],
        accept_multiple_files=True,
        help="Select one or more PDF files to upload. Files will be saved but not processed immediately."
    )
    
    if uploaded_files:
        status = st.status("Saving uploaded files...", expanded=True)
        process_files(uploaded_files, file_processor, status)
    
    # Document list section
    st.markdown("### Manage Documents")
    
    # Create three columns for the action buttons
    action_col1, action_col2, action_col3, action_col4 = st.columns(4)
    with action_col1:
        if st.button("🔄 Refresh Document List", key="refresh_btn", use_container_width=True):
            st.rerun()
    with action_col2:
        if st.button("🧹 Clean Unused Files", key="clean_btn", use_container_width=True):
            if file_processor:
                removed = file_processor.clean_unused_files()
                if removed:
                    st.info(f"Removed {len(removed)} unused files")
                else:
                    st.info("No unused files found")
    with action_col3:
        if st.button("⚡ Convert Pending", key="convert_pending", use_container_width=True):
            if file_processor:
                # Reinitialize file processor to ensure it has the latest methods
                file_processor = reinit_file_processor(store_path)
                
                status = st.status("Checking for pending documents...", expanded=True)
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
                
                status.update(label=f"Found {len(pending_files)} document(s) to process")
                progress_text = "Converting documents..."
                progress_bar = st.progress(0, text=progress_text)
                
                try:
                    for idx, file_path in enumerate(pending_files, 1):
                        file_name = os.path.basename(file_path)
                        
                        def update_status(msg: str):
                            status.update(label=f"[{idx}/{len(pending_files)}] {msg}")
                            progress = idx / len(pending_files)
                            progress_bar.progress(progress, text=f"{progress_text} ({idx}/{len(pending_files)})")
                        
                        result = file_processor.process_file(
                            file_path,
                            progress_callback=update_status
                        )
                        
                        if "error" not in result:
                            status.update(label=f"✅ Successfully processed {file_name}")
                        else:
                            status.update(label=f"❌ Failed to process {file_name}: {result['error']}", state="error")
                        
                        # Update progress
                        progress = idx / len(pending_files)
                        progress_bar.progress(progress, text=f"{progress_text} ({idx}/{len(pending_files)})")
                    
                    status.update(label=f"✅ Finished processing {len(pending_files)} document(s)", state="complete")
                except Exception as e:
                    status.update(label=f"❌ Error during conversion: {str(e)}", state="error")
                    logger.error(f"Error during batch conversion: {str(e)}", exc_info=True)
                
                st.rerun()
    with action_col4:
        if st.button("📊 View Academic Metadata", key="view_metadata", use_container_width=True):
            st.switch_page("pages/Academic.py")
    
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
            metadata_file = Path(store_path) / f"{file.stem}_metadata.json"
            
            # Get academic metadata if available
            academic_info = ""
            if metadata_file.exists():
                try:
                    with open(metadata_file, 'r', encoding='utf-8') as f:
                        metadata = AcademicMetadata.from_dict(json.load(f))
                        academic_info = f"📚 {len(metadata.references)} refs, {len(metadata.equations)} eqs"
                except Exception as e:
                    logger.error(f"Error loading metadata for {file.name}: {e}")
                    academic_info = "❌ Metadata error"
            
            files_data.append({
                "selected": False,
                "name": file.name,
                "type": "PDF",
                "size": f"{file_stat.st_size / 1024:.1f} KB",
                "modified": datetime.fromtimestamp(file_stat.st_mtime).strftime("%Y-%m-%d %H:%M"),
                "status": "Processed" if txt_file.exists() else "Pending",
                "academic": academic_info
            })
        
        # Add text files
        for file in txt_files:
            file_stat = file.stat()
            pdf_file = file.with_suffix(".pdf")
            metadata_file = Path(store_path) / f"{file.stem}_metadata.json"
            
            # Get academic metadata if available
            academic_info = ""
            if metadata_file.exists():
                try:
                    with open(metadata_file, 'r', encoding='utf-8') as f:
                        metadata = AcademicMetadata.from_dict(json.load(f))
                        academic_info = f"📚 {len(metadata.references)} refs, {len(metadata.equations)} eqs"
                except Exception as e:
                    logger.error(f"Error loading metadata for {file.name}: {e}")
                    academic_info = "❌ Metadata error"
            
            files_data.append({
                "selected": False,
                "name": file.name,
                "type": "Text",
                "size": f"{file_stat.st_size / 1024:.1f} KB",
                "modified": datetime.fromtimestamp(file_stat.st_mtime).strftime("%Y-%m-%d %H:%M"),
                "status": "Source" if pdf_file.exists() else "Standalone",
                "academic": academic_info
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
                "academic": st.column_config.TextColumn(
                    "Academic Info",
                    width="medium"
                )
            },
            hide_index=True
        )
        
        # Handle selected files
        selected_files = edited_df[edited_df["selected"]]["name"].tolist()
        if selected_files:
            st.markdown("### Selected Files")
            
            # Action buttons for selected files
            selected_col1, selected_col2 = st.columns(2)
            with selected_col1:
                if st.button("🗑️ Delete Selected", use_container_width=True):
                    for file in selected_files:
                        file_path = Path(store_path) / file
                        try:
                            # Remove the file and its associated files
                            if file_path.exists():
                                file_path.unlink()
                            txt_path = file_path.with_suffix(".txt")
                            if txt_path.exists():
                                txt_path.unlink()
                            metadata_path = Path(store_path) / f"{file_path.stem}_metadata.json"
                            if metadata_path.exists():
                                metadata_path.unlink()
                            st.success(f"Deleted {file}")
                        except Exception as e:
                            st.error(f"Error deleting {file}: {str(e)}")
                    st.rerun()
            
            with selected_col2:
                if st.button("🔄 Reprocess Selected", use_container_width=True):
                    # Reinitialize file processor to ensure it has the latest methods
                    file_processor = reinit_file_processor(store_path)
                    
                    status = st.status("Reprocessing selected files...", expanded=True)
                    progress_text = "Reprocessing documents..."
                    progress_bar = st.progress(0, text=progress_text)
                    
                    total = len([f for f in selected_files if f.lower().endswith(".pdf")])
                    current = 0
                    
                    for file in selected_files:
                        if file.lower().endswith(".pdf"):
                            current += 1
                            file_path = Path(store_path) / file
                            
                            def update_status(msg: str):
                                status.update(label=f"[{current}/{total}] {msg}")
                                progress = current / total
                                progress_bar.progress(progress, text=f"{progress_text} ({current}/{total})")
                            
                            try:
                                result = file_processor.process_file(
                                    str(file_path),
                                    progress_callback=update_status
                                )
                                if "error" not in result:
                                    status.update(label=f"✅ Successfully reprocessed {file}")
                                else:
                                    status.update(label=f"❌ Failed to reprocess {file}: {result['error']}", state="error")
                            except Exception as e:
                                status.update(label=f"❌ Error reprocessing {file}: {str(e)}", state="error")
                            
                            # Update progress
                            progress = current / total
                            progress_bar.progress(progress, text=f"{progress_text} ({current}/{total})")
                    
                    status.update(label="Reprocessing complete", state="complete")
                    st.rerun()
    
    except Exception as e:
        st.error(f"Error managing documents: {str(e)}")
        logger.error(f"Error in document management: {str(e)}", exc_info=True) 