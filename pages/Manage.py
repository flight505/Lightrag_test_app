import os
# Set Marker environment variables
os.environ["PYTORCH_ENABLE_MPS_FALLBACK"] = "1"
os.environ["IN_STREAMLIT"] = "true"

import logging
from datetime import datetime
from pathlib import Path
import json
import threading
from termcolor import colored
import queue
import time

import streamlit as st
from streamlit_navigation_bar import st_navbar
import pandas as pd
from streamlit.runtime.scriptrunner import add_script_run_ctx

from src.file_manager import create_store_directory, DB_ROOT
from src.file_processor import FileProcessor
from src.academic_metadata import AcademicMetadata
from src.config_manager import ConfigManager


logger = logging.getLogger(__name__)

def show_manage():
    st.divider()

    # Initialize session state at the top of the script
    if 'initialized' not in st.session_state:
        st.session_state['initialized'] = True
        st.session_state['status_container'] = None
        st.session_state['file_processor'] = None
        st.session_state['current_store'] = None
        st.session_state['config_manager'] = ConfigManager()

    def init_session_state():
        """Initialize session state variables"""
        if 'file_processor' not in st.session_state:
            st.session_state['file_processor'] = None
        if 'current_store' not in st.session_state:
            st.session_state['current_store'] = None
        if 'config_manager' not in st.session_state:
            st.session_state['config_manager'] = ConfigManager()
        if 'status_container' not in st.session_state:
            st.session_state['status_container'] = None

    def process_files(uploaded_files, file_processor, status):
        """Save uploaded files without processing"""
        try:
            if not file_processor or not file_processor.store_path:
                raise ValueError("File processor not properly initialized with store path")
            
            results = []
            for uploaded_file in uploaded_files:
                try:
                    # Save uploaded file
                    pdf_path = Path(file_processor.store_path) / uploaded_file.name
                    with open(pdf_path, "wb") as f:
                        f.write(uploaded_file.getbuffer())
                    results.append({"success": True, "file": uploaded_file.name})
                except Exception as e:
                    results.append({"success": False, "file": uploaded_file.name, "error": str(e)})
            
            return results
            
        except Exception as e:
            logger.error(f"Error saving files: {str(e)}", exc_info=True)
            return [{"success": False, "file": "batch", "error": str(e)}]

    # Initialize session state
    init_session_state()


    # Hide filename display in file uploader
    st.markdown("""
    <style>
    /* Hide the filename text that appears after upload */
    .uploadedFile {
        display: none;
    }
    /* Hide the specific class for filename display */
    .st-emotion-cache-fis6aj {
        display: none;
    }
    </style>
    """, unsafe_allow_html=True)

    

    # Main interface
    main_col1, main_col2 = st.columns([1, 1])
    with main_col1:
        st.write("### 📁 Document Manager")
        
        # Store selection in main content
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

    with main_col2:
        if selected_store == "Create New...":
            st.write("## Create Store")
            new_store = st.text_input("Store Name", key="new_store")
            if st.button("Create Store", key="create_store", type="primary", use_container_width=True):
                if new_store:
                    store_path = create_store_directory(new_store)
                    if store_path:
                        st.session_state["active_store"] = new_store
                        file_processor = FileProcessor(st.session_state["config_manager"])
                        file_processor.set_store_path(store_path)
                        st.session_state["file_processor"] = file_processor
                        # Initialize status container
                        if 'status_container' not in st.session_state or st.session_state['status_container'] is None:
                            st.session_state['status_container'] = st.status("Ready", state="complete", expanded=False)
                        status = st.session_state['status_container']
                        status.update(label=f"✅ Created store: {new_store}", state="complete", expanded=False)
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
            # Show upload section when store is selected
            if "active_store" in st.session_state and st.session_state["active_store"]:
                st.write("### 📄 Upload Documents")
                uploaded_files = st.file_uploader(
                    "",
                    type=["pdf"],
                    accept_multiple_files=True,
                    help="Select one or more PDF files to upload. Files will be saved but not processed immediately.",
                    label_visibility="hidden"
                )

    st.divider()

    # Document management interface
    if "active_store" in st.session_state and st.session_state["active_store"]:
        store_path = os.path.join(DB_ROOT, st.session_state["active_store"])
        
        # Use cached file processor
        if not st.session_state["file_processor"]:
            file_processor = FileProcessor(st.session_state["config_manager"])
            file_processor.set_store_path(store_path)
            st.session_state["file_processor"] = file_processor
        elif not st.session_state["file_processor"].store_path:
            file_processor = FileProcessor(st.session_state["config_manager"])
            file_processor.set_store_path(store_path)
            st.session_state["file_processor"] = file_processor
        else:
            file_processor = st.session_state["file_processor"]
        
        # Centralized status container - all status updates will appear here
        status_container = st.empty()  # Placeholder for status messages
        
        if uploaded_files:
            with status_container.container():
                with st.status("Saving uploaded files...", expanded=True) as status:
                    results = process_files(uploaded_files, file_processor, status)
                    
                    # Handle results in main thread
                    success_count = 0
                    for result in results:
                        if result["success"]:
                            success_count += 1
                            status.write(f"✓ Saved: {result['file']}")
                        else:
                            status.write(f"❌ Failed to save {result['file']}: {result.get('error', 'Unknown error')}")
                    
                    if success_count == len(results):
                        status.update(
                            label="✅ All files saved successfully. Click 'Convert Pending' to process them.", 
                            state="complete"
                        )
                    else:
                        status.update(
                            label=f"⚠️ Saved {success_count} of {len(results)} files", 
                            state="error"
                        )
        
        # Document list section
        st.markdown("### Manage Documents")
        
        # Top action buttons (document management)
        doc_action_col1, doc_action_col2, doc_action_col3, doc_action_col4 = st.columns(4)
        with doc_action_col1:
            if st.button("🔄 Refresh Document List", key="refresh_btn", use_container_width=True):
                st.rerun()
        with doc_action_col2:
            if st.button("🧹 Clean Unused Files", key="clean_btn", use_container_width=True):
                if file_processor:
                    with status_container.container():
                        with st.status("Cleaning unused files...", expanded=True) as status:
                            removed = file_processor.clean_unused_files()
                            if removed:
                                for file in removed:
                                    status.write(f"✓ Removed: {Path(file).name}")
                                status.update(label=f"✅ Removed {len(removed)} unused files", state="complete")
                            else:
                                status.update(label="✓ No unused files found", state="complete")
                    st.rerun()
        with doc_action_col3:
            if st.button("⚡ Convert Pending", key="convert_pending", use_container_width=True):
                if file_processor:
                    # Reinitialize file processor to ensure it has the latest methods
                    file_processor = FileProcessor(st.session_state["config_manager"])
                    file_processor.set_store_path(store_path)
                    
                    with status_container.container():
                        status = st.status("Checking for pending documents...", expanded=False)
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
                        
                        try:
                            total_files = len(pending_files)
                            status.update(label=f"Converting {total_files} document(s)...")
                            
                            for idx, file_path in enumerate(pending_files, 1):
                                file_name = os.path.basename(file_path)
                                status.update(label=f"Converting {idx}/{total_files}: {file_name}")
                                
                                def update_status(msg: str):
                                    status.update(label=f"Converting {idx}/{total_files}: {file_name}")
                                
                                result = file_processor.process_file(
                                    file_path,
                                    progress_callback=update_status
                                )
                                
                                if "error" in result:
                                    status.update(label=f"Error processing {file_name}: {result['error']}", state="error")
                                    st.rerun()
                            
                            status.update(label=f"✅ Converted {total_files} document(s)", state="complete")
                        except Exception as e:
                            status.update(label=f"❌ Error during conversion: {str(e)}", state="error")
                            logger.error(f"Error during batch conversion: {str(e)}", exc_info=True)
                        
                        st.rerun()
        with doc_action_col4:
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
                if 'status_container' not in st.session_state or st.session_state['status_container'] is None:
                    st.session_state['status_container'] = st.status("Ready", state="complete", expanded=False)
                status = st.session_state['status_container']
                status.update(
                    label="ℹ️ No documents found in this store. Upload some PDF files to get started.",
                    state="running",
                    expanded=False
                )
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
                
                # Bottom action buttons (selected files operations)
                selected_files_col1, selected_files_col2 = st.columns(2)
                with selected_files_col1:
                    if st.button("🗑️ Delete Selected", use_container_width=True):
                        with status_container.container():
                            with st.status("Deleting selected files...", expanded=True) as status:
                                deleted_files = []
                                failed_files = []
                                
                                # Get current store path
                                store_path = Path(DB_ROOT) / st.session_state["active_store"]
                                if not store_path.exists():
                                    status.update(label="❌ Store path does not exist", state="error")
                                    st.stop()
                                
                                for file in selected_files:
                                    try:
                                        file_path = store_path / file
                                        txt_path = file_path.with_suffix(".txt")
                                        metadata_path = store_path / f"{file_path.stem}_metadata.json"
                                        
                                        # Log deletion attempt
                                        logger.info(f"Attempting to delete: {file}")
                                        status.write(f"Processing: {file}")
                                        
                                        deletion_success = False
                                        
                                        try:
                                            # Delete PDF if exists
                                            if file_path.exists():
                                                os.remove(str(file_path))
                                                logger.info(f"Deleted PDF: {file}")
                                                status.write(f"✓ Deleted PDF: {file}")
                                                deleted_files.append(str(file_path))
                                                deletion_success = True
                                            
                                            # Delete TXT if exists
                                            if txt_path.exists():
                                                os.remove(str(txt_path))
                                                logger.info(f"Deleted TXT: {txt_path.name}")
                                                status.write(f"✓ Deleted TXT: {txt_path.name}")
                                                deleted_files.append(str(txt_path))
                                                deletion_success = True
                                            
                                            # Delete metadata if exists
                                            if metadata_path.exists():
                                                os.remove(str(metadata_path))
                                                logger.info(f"Deleted metadata: {metadata_path.name}")
                                                status.write(f"✓ Deleted metadata: {metadata_path.name}")
                                                deleted_files.append(str(metadata_path))
                                                deletion_success = True
                                            
                                            if deletion_success:
                                                try:
                                                    print(colored(f"✓ Successfully deleted files for: {file}", "green"))
                                                    # Remove from DataFrame
                                                    edited_df.drop(edited_df[edited_df["name"] == file].index, inplace=True)
                                                except Exception as print_err:
                                                    logger.warning(f"Print formatting error: {print_err}")
                                                    print(f"✓ Successfully deleted files for: {file}")
                                            else:
                                                logger.warning(f"No files found to delete for: {file}")
                                                status.write(f"⚠️ No files found for: {file}")
                                            
                                        except Exception as e:
                                            error_msg = f"Error deleting {file}: {str(e)}"
                                            logger.error(error_msg)
                                            status.write(f"❌ {error_msg}")
                                            failed_files.append(file)
                                        
                                    except Exception as e:
                                        error_msg = f"Error processing {file}: {str(e)}"
                                        logger.error(error_msg)
                                        status.write(f"❌ {error_msg}")
                                        failed_files.append(file)
                                
                                # Show final status
                                if deleted_files:
                                    status.write("---")
                                    status.write("**Successfully deleted:**")
                                    for f in deleted_files:
                                        status.write(f"- {Path(f).name}")
                                
                                if failed_files:
                                    status.write("---")
                                    status.write("**Failed to delete:**")
                                    for f in failed_files:
                                        status.write(f"- {f}")
                                
                                final_status = f"Deleted {len(deleted_files)} files" + (f" ({len(failed_files)} failed)" if failed_files else "")
                                status.update(
                                    label=final_status,
                                    state="complete" if not failed_files else "error"
                                )
                        
                        # Clear the session state for the data editor to force a refresh
                        if "document_editor" in st.session_state:
                            del st.session_state["document_editor"]
                        
                        # Force refresh only if files were actually deleted
                        if deleted_files:
                            st.rerun()
                
                with selected_files_col2:
                    if st.button("🔄 Reprocess Selected", use_container_width=True):
                        # Reinitialize file processor to ensure it has the latest methods
                        file_processor = FileProcessor(st.session_state["config_manager"])
                        file_processor.set_store_path(store_path)
                        
                        with status_container.container():
                            with st.status("Reprocessing selected files...", expanded=True) as status:
                                pdf_files = [f for f in selected_files if f.lower().endswith(".pdf")]
                                if not pdf_files:
                                    status.update(label="No PDF files selected for reprocessing", state="complete")
                                    st.rerun()
                                
                                try:
                                    for idx, file in enumerate(pdf_files, 1):
                                        file_path = Path(store_path) / file
                                        status.write(f"Processing {idx}/{len(pdf_files)}: {file}")
                                        
                                        def update_status(msg: str):
                                            status.write(f"[{idx}/{len(pdf_files)}] {msg}")
                                        
                                        try:
                                            result = file_processor.process_file(
                                                str(file_path),
                                                progress_callback=update_status
                                            )
                                            
                                            if "error" not in result:
                                                status.write(f"✓ Successfully processed {file}")
                                            else:
                                                status.write(f"❌ Failed to process {file}: {result['error']}")
                                        except Exception as e:
                                            status.write(f"❌ Error processing {file}: {str(e)}")
                                    
                                    status.update(
                                        label=f"✅ Finished reprocessing {len(pdf_files)} document(s)", 
                                        state="complete"
                                    )
                                except Exception as e:
                                    status.update(
                                        label=f"❌ Error during reprocessing: {str(e)}", 
                                        state="error"
                                    )
                                    logger.error(f"Error during batch reprocessing: {str(e)}", exc_info=True)
                        
                        st.rerun()
        
        except Exception as e:
            if 'status_container' not in st.session_state or st.session_state['status_container'] is None:
                st.session_state['status_container'] = st.status("Ready", state="complete", expanded=False)
            status = st.session_state['status_container']
            status.update(
                label=f"❌ Error managing documents: {str(e)}", 
                state="error",
                expanded=True
            )
            logger.error(f"Error in document management: {str(e)}", exc_info=True) 