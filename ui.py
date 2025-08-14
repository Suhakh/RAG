"""
ScholarBot UI Components
Streamlit interface components and utilities
"""

import streamlit as st
import json
import logging
from datetime import datetime
from typing import Dict, Any, List
from pathlib import Path
import time

logger = logging.getLogger(__name__)

class ChatHistory:
    """Manages chat history persistence"""
    
    def __init__(self, history_path: str):
        self.history_file = Path(history_path)
        self.history_file.parent.mkdir(parents=True, exist_ok=True)
        
    def load_history(self) -> List[Dict[str, Any]]:
        """Load chat history from file"""
        try:
            if self.history_file.exists():
                with open(self.history_file, 'r', encoding='utf-8') as f:
                    history = json.load(f)
                return history
            return []
        except Exception as e:
            logger.error(f"❌ Error loading chat history: {e}")
            return []
            
    def save_history(self, history: List[Dict[str, Any]]):
        """Save chat history to file"""
        try:
            with open(self.history_file, 'w', encoding='utf-8') as f:
                json.dump(history, f, indent=2, ensure_ascii=False)
        except Exception as e:
            logger.error(f"❌ Error saving chat history: {e}")
            
    def add_exchange(self, question: str, answer: str, sources: List[Dict] = None):
        """Add a Q&A exchange to history"""
        history = self.load_history()
        
        exchange = {
            'timestamp': datetime.now().isoformat(),
            'question': question,
            'answer': answer,
            'sources': sources or []
        }
        
        history.append(exchange)
        
        # Keep only last N exchanges to prevent file from growing too large
        max_history = 100
        if len(history) > max_history:
            history = history[-max_history:]
            
        self.save_history(history)
        
    def clear_history(self):
        """Clear chat history"""
        try:
            if self.history_file.exists():
                self.history_file.unlink()
            logger.info("✅ Chat history cleared")
        except Exception as e:
            logger.error(f"❌ Error clearing chat history: {e}")

class UIComponents:
    """Reusable UI components"""
    
    @staticmethod
    def render_header(app_name: str):
        """Render application header"""
        st.set_page_config(
            page_title=app_name,
            page_icon="🔬",
            layout="wide",
            initial_sidebar_state="expanded"
        )
        
        st.title(f"🔬 {app_name}")
        st.markdown("*AI-Powered Research Assistant with Local RAG*")
        
    @staticmethod
    def render_system_status(rag_pipeline):
        """Render system status in sidebar"""
        with st.sidebar:
            st.header("📊 System Status")
            
            try:
                # Collection info
                collection_info = rag_pipeline.get_collection_info()
                doc_count = collection_info.get('document_count', 0)
                
                col1, col2 = st.columns(2)
                with col1:
                    st.metric("Documents", doc_count)
                    
                # System stats
                stats = rag_pipeline.get_system_stats()
                if stats:
                    with col2:
                        st.metric("Memory", f"{stats.get('memory_percent', 0):.1f}%")
                        
                    # Memory details in expander
                    with st.expander("📈 System Details"):
                        st.write(f"**CPU Usage:** {stats.get('cpu_percent', 0):.1f}%")
                        st.write(f"**Memory Used:** {stats.get('memory_used_gb', 0):.1f} GB")
                        st.write(f"**Memory Available:** {stats.get('available_memory_gb', 0):.1f} GB")
                        
            except Exception as e:
                st.error(f"❌ Error getting system status: {e}")
                
    @staticmethod
    def render_file_uploader(ingestor):
        """Render file upload interface"""
        st.header("📁 Document Upload")
        
        # Upload method selection
        upload_method = st.radio(
            "Choose upload method:",
            ["Single/Multiple Files", "Folder Upload"],
            horizontal=True
        )
        
        uploaded_files = None
        folder_path = None
        
        if upload_method == "Single/Multiple Files":
            uploaded_files = st.file_uploader(
                "Choose files",
                type=['pdf', 'txt', 'md'],
                accept_multiple_files=True,
                help=f"Supported formats: PDF, TXT, MD (Max: {ingestor.max_file_size_mb}MB total)"
            )
            
        else:  # Folder upload
            folder_path = st.text_input(
                "Enter folder path:",
                placeholder=r"C:\path\to\your\documents",
                help="Path to folder containing documents to ingest"
            )
            
        return uploaded_files, folder_path, upload_method
        
    @staticmethod
    def process_file_upload(uploaded_files, folder_path, upload_method, ingestor, rag_pipeline):
        """Process file uploads and add to RAG system"""
        if upload_method == "Single/Multiple Files" and uploaded_files:
            # Save uploaded files temporarily
            temp_paths = []
            try:
                for uploaded_file in uploaded_files:
                    temp_path = Path("temp") / uploaded_file.name
                    temp_path.parent.mkdir(exist_ok=True)
                    
                    with open(temp_path, "wb") as f:
                        f.write(uploaded_file.getbuffer())
                    temp_paths.append(str(temp_path))
                    
                # Ingest files
                with st.spinner("Processing uploaded files..."):
                    ingest_result = ingestor.ingest_files(temp_paths)
                    
                if ingest_result['success']:
                    # Add to RAG pipeline
                    rag_result = rag_pipeline.add_documents(ingest_result['file_paths'])
                    
                    if rag_result['success']:
                        st.success(f"✅ {rag_result['message']}")
                    else:
                        st.error(f"❌ RAG Error: {rag_result['message']}")
                else:
                    st.error(f"❌ Ingestion Error: {ingest_result['message']}")
                    
                # Show validation details
                if 'validation_result' in ingest_result:
                    validation = ingest_result['validation_result']
                    if validation.get('invalid_files'):
                        with st.expander("⚠️ Invalid Files"):
                            for invalid_file in validation['invalid_files']:
                                st.write(f"**{invalid_file['name']}**: {invalid_file['error']}")
                                
            finally:
                # Cleanup temp files
                for temp_path in temp_paths:
                    try:
                        Path(temp_path).unlink(missing_ok=True)
                    except:
                        pass
                        
        elif upload_method == "Folder Upload" and folder_path:
            if st.button("📂 Ingest Folder", type="primary"):
                with st.spinner(f"Ingesting files from {folder_path}..."):
                    ingest_result = ingestor.ingest_from_folder(folder_path)
                    
                if ingest_result['success']:
                    # Add to RAG pipeline
                    rag_result = rag_pipeline.add_documents(ingest_result['file_paths'])
                    
                    if rag_result['success']:
                        st.success(f"✅ {rag_result['message']}")
                    else:
                        st.error(f"❌ RAG Error: {rag_result['message']}")
                else:
                    st.error(f"❌ {ingest_result['message']}")
                    
    @staticmethod
    def render_document_manager(ingestor):
        """Render document management interface"""
        with st.sidebar:
            with st.expander("📋 Document Manager"):
                files = ingestor.get_ingested_files()
                
                if files:
                    st.write(f"**Total Files:** {len(files)}")
                    total_size = sum(f['size_mb'] for f in files)
                    st.write(f"**Total Size:** {total_size:.1f} MB")
                    
                    # Show file list
                    for i, file_info in enumerate(files[:10]):  # Show first 10
                        col1, col2 = st.columns([3, 1])
                        with col1:
                            st.write(f"{file_info['name']} ({file_info['size_mb']:.1f}MB)")
                        with col2:
                            if st.button("🗑️", key=f"delete_{i}", help="Delete file"):
                                if ingestor.remove_file(file_info['path']):
                                    st.success("File deleted")
                                    st.rerun()
                                    
                    if len(files) > 10:
                        st.write(f"... and {len(files) - 10} more files")
                        
                    # Clear all button
                    if st.button("🗑️ Clear All Files", type="secondary"):
                        if ingestor.clear_all_files():
                            st.success("All files cleared")
                            st.rerun()
                else:
                    st.write("No documents ingested yet")
                    
    @staticmethod
    def render_chat_interface(rag_pipeline, chat_history, config):
        """Render main chat interface"""
        st.header("💬 Ask ScholarBot")
        
        # Chat history display
        history = chat_history.load_history()
        
        if history:
            with st.expander(f"📜 Chat History ({len(history)} conversations)", expanded=False):
                # Show last N conversations
                display_count = min(config['ui']['max_chat_history_display'], len(history))
                for exchange in history[-display_count:]:
                    timestamp = datetime.fromisoformat(exchange['timestamp']).strftime("%H:%M:%S")
                    st.write(f"**[{timestamp}] Q:** {exchange['question']}")
                    st.write(f"**A:** {exchange['answer'][:200]}...")
                    if exchange.get('sources'):
                        st.write(f"*({len(exchange['sources'])} sources)*")
                    st.divider()
                    
        # Query input
        question = st.text_area(
            "Enter your question:",
            height=100,
            placeholder="Ask me anything about your documents...",
            help="Type your research question here. I'll search through your documents to provide an answer."
        )
        
        col1, col2, col3 = st.columns([2, 1, 1])
        
        with col1:
            ask_button = st.button("🔍 Ask ScholarBot", type="primary", disabled=not question.strip())
            
        with col2:
            if st.button("🗑️ Clear History"):
                chat_history.clear_history()
                st.success("Chat history cleared!")
                st.rerun()
                
        return question, ask_button
        
    @staticmethod
    def render_response(response_data, config):
        """Render query response with sources"""
        if not response_data['success']:
            st.error(f"❌ {response_data['message']}")
            return
            
        # Main answer
        st.subheader("📝 Answer")
        st.write(response_data['answer'])
        
        # Sources section
        if config['ui']['show_sources'] and response_data.get('sources'):
            st.subheader("📚 Sources")
            
            for i, source in enumerate(response_data['sources'], 1):
                with st.expander(f"Source {i}: {source['metadata'].get('filename', 'Unknown')}"):
                    st.write(f"**File:** {source['metadata'].get('filename', 'N/A')}")
                    st.write(f"**Type:** {source['metadata'].get('file_type', 'N/A')}")
                    
                    if config['ui']['show_citations']:
                        st.write("**Content Preview:**")
                        st.text(source['content'])
                        
        # Performance info
        with st.expander("⚡ Query Info"):
            st.write(f"**Query:** {response_data['query']}")
            if response_data.get('sources'):
                st.write(f"**Sources Found:** {len(response_data['sources'])}")
                
    @staticmethod 
    def render_settings(config):
        """Render settings panel"""
        with st.sidebar:
            with st.expander("⚙️ Settings"):
                st.write("**Current Configuration:**")
                st.write(f"LLM: {config['models']['llm']['name']}")
                st.write(f"Embeddings: {config['models']['embeddings']['name']}")
                st.write(f"Chunk Size: {config['chunking']['chunk_size']}")
                st.write(f"Top-K: {config['retrieval']['top_k']}")
                st.write(f"Temperature: {config['models']['llm']['temperature']}")
                
                st.info("💡 Modify config.yaml to change settings, then restart the app")
                
    @staticmethod
    def render_help():
        """Render help information"""
        with st.sidebar:
            with st.expander("❓ Help"):
                st.markdown("""
                **Quick Start:**
                1. Upload documents (PDF, TXT, MD)
                2. Wait for processing to complete
                3. Ask questions about your documents
                
                **Tips:**
                - Be specific in your questions
                - Use natural language
                - Check sources for context
                
                **Performance:**
                - First query may be slower
                - Large documents take time to process
                - Monitor memory usage above
                """)
                
    @staticmethod
    def show_welcome_message():
        """Show welcome message for new users"""
        if 'welcomed' not in st.session_state:
            st.info("""
            👋 **Welcome to ScholarBot!**
            
            Get started by uploading some documents using the upload section below, 
            then ask questions about them in the chat interface.
            
            Your documents are processed locally and never leave your machine.
            """)
            st.session_state.welcomed = True