"""
ScholarBot - AI-Powered Local RAG Research Assistant
Main Streamlit Application
"""

import streamlit as st
import logging
import sys
import time
from pathlib import Path
import yaml

# Add project root to path
sys.path.append(str(Path(__file__).parent))

from rag_pipeline import RAGPipeline
from ingest import DocumentIngestor
from ui import UIComponents, ChatHistory

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('scholarbot.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

class ScholarBotApp:
    """Main application class"""
    
    def __init__(self):
        self.config = None
        self.rag_pipeline = None
        self.ingestor = None
        self.chat_history = None
        
    def load_config(self):
        """Load application configuration"""
        try:
            with open('config.yaml', 'r') as f:
                self.config = yaml.safe_load(f)
            logger.info("✅ Configuration loaded successfully")
        except Exception as e:
            st.error(f"❌ Failed to load config.yaml: {e}")
            logger.error(f"Failed to load configuration: {e}")
            st.stop()
            
    def initialize_components(self):
        """Initialize all application components"""
        try:
            # Initialize RAG pipeline
            with st.spinner("🔧 Initializing ScholarBot..."):
                self.rag_pipeline = RAGPipeline('config.yaml')
                
            # Initialize document ingestor
            self.ingestor = DocumentIngestor(self.config)
            
            # Initialize chat history
            history_path = Path(self.config['storage']['history_path']) / self.config['storage']['history_file']
            self.chat_history = ChatHistory(str(history_path))
            
            logger.info("✅ All components initialized successfully")
            
        except Exception as e:
            st.error(f"❌ Failed to initialize components: {e}")
            logger.error(f"Failed to initialize components: {e}")
            st.stop()
            
    def check_ollama_connection(self):
        """Check if Ollama is running and models are available"""
        try:
            import requests
            
            # Check Ollama server
            response = requests.get("http://localhost:11434/api/tags", timeout=5)
            
            if response.status_code != 200:
                st.error("❌ Ollama server not responding. Please start Ollama first.")
                st.code("ollama serve", language="bash")
                st.stop()
                
            # Check required models
            models = response.json().get('models', [])
            model_names = [model['name'] for model in models]
            
            required_models = [
                self.config['models']['llm']['name'],
                self.config['models']['embeddings']['name']
            ]
            
            missing_models = []
            for model in required_models:
                if not any(model in name for name in model_names):
                    missing_models.append(model)
                    
            if missing_models:
                st.error(f"❌ Missing required models: {', '.join(missing_models)}")
                st.write("Please pull the required models:")
                for model in missing_models:
                    st.code(f"ollama pull {model}", language="bash")
                st.stop()
                
            logger.info("✅ Ollama connection and models verified")
            
        except requests.exceptions.ConnectionError:
            st.error("""
            ❌ **Cannot connect to Ollama server.**
            
            Please make sure Ollama is running:
            1. Start Ollama: `ollama serve`
            2. Pull required models (see README)
            3. Refresh this page
            """)
            st.stop()
        except Exception as e:
            st.warning(f"⚠️ Could not verify Ollama connection: {e}")
            
    def render_main_interface(self):
        """Render the main application interface"""
        # Header
        UIComponents.render_header(self.config['app']['name'])
        
        # System status sidebar
        UIComponents.render_system_status(self.rag_pipeline)
        
        # Document manager
        UIComponents.render_document_manager(self.ingestor)
        
        # Settings
        UIComponents.render_settings(self.config)
        
        # Help
        UIComponents.render_help()
        
        # Welcome message
        UIComponents.show_welcome_message()
        
        # Main content tabs
        tab1, tab2 = st.tabs(["💬 Chat", "📁 Upload Documents"])
        
        with tab2:
            # File upload interface
            uploaded_files, folder_path, upload_method = UIComponents.render_file_uploader(self.ingestor)
            
            # Process uploads
            UIComponents.process_file_upload(
                uploaded_files, folder_path, upload_method, 
                self.ingestor, self.rag_pipeline
            )
            
        with tab1:
            # Chat interface
            question, ask_button = UIComponents.render_chat_interface(
                self.rag_pipeline, self.chat_history, self.config
            )
            
            # Process query
            if ask_button and question.strip():
                self.process_query(question.strip())
                
    def process_query(self, question: str):
        """Process a user query"""
        try:
            # Check if vectorstore has documents
            collection_info = self.rag_pipeline.get_collection_info()
            if collection_info.get('document_count', 0) == 0:
                st.warning("⚠️ No documents in the knowledge base. Please upload some documents first.")
                return
                
            # Show query being processed
            with st.spinner("🤔 ScholarBot is thinking..."):
                start_time = time.time()
                
                # Execute query
                response_data = self.rag_pipeline.query(question)
                
                query_time = time.time() - start_time
                
            # Render response
            UIComponents.render_response(response_data, self.config)
            
            # Save to history
            if response_data['success']:
                self.chat_history.add_exchange(
                    question=question,
                    answer=response_data['answer'],
                    sources=response_data.get('sources', [])
                )
                
            # Show performance info
            st.success(f"✅ Query completed in {query_time:.2f} seconds")
            
        except Exception as e:
            st.error(f"❌ Error processing query: {e}")
            logger.error(f"Error processing query: {e}")
            
    def run(self):
        """Run the main application"""
        try:
            # Load configuration
            self.load_config()
            
            # Check Ollama connection
            self.check_ollama_connection()
            
            # Initialize components (with caching)
            if 'components_initialized' not in st.session_state:
                self.initialize_components()
                st.session_state.components_initialized = True
                st.session_state.rag_pipeline = self.rag_pipeline
                st.session_state.ingestor = self.ingestor
                st.session_state.chat_history = self.chat_history
                st.session_state.config = self.config
            else:
                # Use cached components
                self.rag_pipeline = st.session_state.rag_pipeline
                self.ingestor = st.session_state.ingestor
                self.chat_history = st.session_state.chat_history
                self.config = st.session_state.config
                
            # Render main interface
            self.render_main_interface()
            
        except KeyboardInterrupt:
            logger.info("Application interrupted by user")
        except Exception as e:
            st.error(f"❌ Unexpected error: {e}")
            logger.error(f"Unexpected error: {e}")

def main():
    """Application entry point"""
    app = ScholarBotApp()
    app.run()

if __name__ == "__main__":
    main()