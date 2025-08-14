"""
ScholarBot RAG Pipeline
Handles document processing, embedding, retrieval, and generation
"""

import os
import yaml
import logging
from typing import List, Dict, Any, Optional, Generator
from pathlib import Path
import gc
import psutil

from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain_community.document_loaders import PyPDFLoader, TextLoader
from langchain_community.vectorstores import Chroma
from langchain_ollama import OllamaLLM, OllamaEmbeddings
from langchain.schema import Document
from langchain.chains import RetrievalQA
from langchain.callbacks.base import BaseCallbackHandler
from langchain.prompts import PromptTemplate

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class StreamingCallbackHandler(BaseCallbackHandler):
    """Callback handler for streaming responses"""
    def __init__(self):
        self.tokens = []
        
    def on_llm_new_token(self, token: str, **kwargs) -> None:
        self.tokens.append(token)
        
    def get_response(self) -> str:
        return "".join(self.tokens)
        
    def clear(self):
        self.tokens = []

class RAGPipeline:
    def __init__(self, config_path: str = "config.yaml"):
        """Initialize RAG pipeline with configuration"""
        self.config = self._load_config(config_path)
        self.vectorstore = None
        self.retriever = None
        self.llm = None
        self.embeddings = None
        self.qa_chain = None
        self.text_splitter = None
        self.streaming_handler = StreamingCallbackHandler()
        
        # Create directories
        self._create_directories()
        
        # Initialize components
        self._initialize_models()
        self._initialize_text_splitter()
        self._load_vectorstore()
        
    def _load_config(self, config_path: str) -> Dict[str, Any]:
        """Load configuration from YAML file"""
        try:
            with open(config_path, 'r') as f:
                config = yaml.safe_load(f)
            logger.info(f"✅ Configuration loaded from {config_path}")
            return config
        except Exception as e:
            logger.error(f"❌ Error loading config: {e}")
            raise
            
    def _create_directories(self):
        """Create necessary directories"""
        directories = [
            self.config['storage']['vectordb_path'],
            self.config['storage']['data_path'], 
            self.config['storage']['history_path']
        ]
        
        for directory in directories:
            Path(directory).mkdir(parents=True, exist_ok=True)
            
    def _initialize_models(self):
        """Initialize LLM and embedding models"""
        try:
            # Initialize embeddings
            self.embeddings = OllamaEmbeddings(
                model=self.config['models']['embeddings']['name'],
                base_url="http://localhost:11434"
            )
            
            # Initialize LLM
            self.llm = OllamaLLM(
                model=self.config['models']['llm']['name'],
                temperature=self.config['models']['llm']['temperature'],
                num_ctx=self.config['models']['llm']['context_window'],
                base_url="http://localhost:11434",
                callbacks=[self.streaming_handler] if self.config['performance']['streaming'] else None
            )
            
            logger.info("✅ Models initialized successfully")
            
        except Exception as e:
            logger.error(f"❌ Error initializing models: {e}")
            raise
            
    def _initialize_text_splitter(self):
        """Initialize text splitter for chunking"""
        self.text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=self.config['chunking']['chunk_size'],
            chunk_overlap=self.config['chunking']['chunk_overlap'],
            separators=self.config['chunking']['separators']
        )
        
    def _load_vectorstore(self):
        """Load or create vector store"""
        try:
            vectordb_path = self.config['storage']['vectordb_path']
            
            if os.path.exists(vectordb_path) and os.listdir(vectordb_path):
                # Load existing vectorstore
                self.vectorstore = Chroma(
                    persist_directory=vectordb_path,
                    embedding_function=self.embeddings
                )
                doc_count = self.vectorstore._collection.count()
                logger.info(f"✅ Loaded existing vectorstore with {doc_count} documents")
            else:
                # Create new vectorstore
                self.vectorstore = Chroma(
                    persist_directory=vectordb_path,
                    embedding_function=self.embeddings
                )
                logger.info("✅ Created new vectorstore")
                
            # Setup retriever
            self._setup_retriever()
            
        except Exception as e:
            logger.error(f"❌ Error loading vectorstore: {e}")
            raise
            
    def _setup_retriever(self):
        """Setup retriever with configured parameters"""
        search_kwargs = {"k": self.config['retrieval']['top_k']}
        
        if self.config['retrieval']['search_type'] == "mmr":
            search_kwargs["fetch_k"] = self.config['retrieval']['top_k'] * 2
            search_kwargs["lambda_mult"] = self.config['retrieval']['mmr_diversity']
            
        self.retriever = self.vectorstore.as_retriever(
            search_type=self.config['retrieval']['search_type'],
            search_kwargs=search_kwargs
        )
        
        # Setup QA chain
        self._setup_qa_chain()
        
    def _setup_qa_chain(self):
        """Setup question-answering chain"""
        prompt_template = """You are ScholarBot, a helpful research assistant. Use the following context to answer the question comprehensively and accurately.

Context from documents:
{context}

Question: {question}

Instructions:
- Provide a detailed, well-structured answer based on the context
- If the context doesn't contain enough information, say so clearly
- Include relevant details and cite specific information when possible
- Be concise but thorough
- If asked about sources, refer to the document content provided

Answer:"""

        prompt = PromptTemplate(
            template=prompt_template,
            input_variables=["context", "question"]
        )
        
        self.qa_chain = RetrievalQA.from_chain_type(
            llm=self.llm,
            chain_type="stuff",
            retriever=self.retriever,
            return_source_documents=True,
            chain_type_kwargs={"prompt": prompt}
        )
        
    def load_documents(self, file_paths: List[str]) -> List[Document]:
        """Load documents from file paths"""
        documents = []
        
        for file_path in file_paths:
            try:
                file_path = Path(file_path)
                
                if file_path.suffix.lower() == '.pdf':
                    loader = PyPDFLoader(str(file_path))
                    docs = loader.load()
                elif file_path.suffix.lower() in ['.txt', '.md']:
                    loader = TextLoader(str(file_path), encoding='utf-8')
                    docs = loader.load()
                else:
                    logger.warning(f"⚠️ Unsupported file type: {file_path}")
                    continue
                    
                # Add metadata
                for doc in docs:
                    doc.metadata.update({
                        'source': str(file_path),
                        'filename': file_path.name,
                        'file_type': file_path.suffix.lower()
                    })
                    
                documents.extend(docs)
                logger.info(f"✅ Loaded {len(docs)} documents from {file_path.name}")
                
            except Exception as e:
                logger.error(f"❌ Error loading {file_path}: {e}")
                
        return documents
        
    def process_documents(self, documents: List[Document]) -> List[Document]:
        """Process documents by chunking"""
        if not documents:
            return []
            
        chunks = self.text_splitter.split_documents(documents)
        logger.info(f"✅ Split documents into {len(chunks)} chunks")
        return chunks
        
    def add_documents(self, file_paths: List[str]) -> Dict[str, Any]:
        """Add documents to the vector store"""
        try:
            # Load documents
            documents = self.load_documents(file_paths)
            if not documents:
                return {"success": False, "message": "No valid documents to process"}
                
            # Process documents
            chunks = self.process_documents(documents)
            if not chunks:
                return {"success": False, "message": "No chunks created from documents"}
                
            # Add to vectorstore
            self.vectorstore.add_documents(chunks)
            self.vectorstore.persist()
            
            # Cleanup memory
            self._cleanup_memory()
            
            logger.info(f"✅ Added {len(chunks)} chunks from {len(documents)} documents")
            
            return {
                "success": True,
                "message": f"Successfully processed {len(documents)} documents into {len(chunks)} chunks",
                "document_count": len(documents),
                "chunk_count": len(chunks)
            }
            
        except Exception as e:
            logger.error(f"❌ Error adding documents: {e}")
            return {"success": False, "message": f"Error processing documents: {str(e)}"}
            
    def query(self, question: str) -> Dict[str, Any]:
        """Query the RAG system"""
        try:
            if not self.qa_chain:
                return {"success": False, "message": "System not initialized properly"}
                
            # Clear previous streaming tokens
            if self.config['performance']['streaming']:
                self.streaming_handler.clear()
                
            # Execute query
            result = self.qa_chain({"query": question})
            
            # Get streaming response if enabled
            if self.config['performance']['streaming']:
                response_text = self.streaming_handler.get_response()
                if not response_text:  # Fallback to result if streaming failed
                    response_text = result['result']
            else:
                response_text = result['result']
                
            # Process source documents
            sources = []
            if 'source_documents' in result and result['source_documents']:
                for i, doc in enumerate(result['source_documents']):
                    sources.append({
                        'content': doc.page_content[:200] + "..." if len(doc.page_content) > 200 else doc.page_content,
                        'metadata': doc.metadata,
                        'index': i
                    })
                    
            return {
                "success": True,
                "answer": response_text,
                "sources": sources,
                "query": question
            }
            
        except Exception as e:
            logger.error(f"❌ Error during query: {e}")
            return {
                "success": False,
                "message": f"Error processing query: {str(e)}",
                "query": question
            }
            
    def get_collection_info(self) -> Dict[str, Any]:
        """Get information about the current collection"""
        try:
            if not self.vectorstore:
                return {"document_count": 0, "collection_name": "none"}
                
            doc_count = self.vectorstore._collection.count()
            collection_name = self.vectorstore._collection.name
            
            return {
                "document_count": doc_count,
                "collection_name": collection_name,
                "vectorstore_path": self.config['storage']['vectordb_path']
            }
            
        except Exception as e:
            logger.error(f"❌ Error getting collection info: {e}")
            return {"document_count": 0, "collection_name": "error"}
            
    def clear_vectorstore(self) -> bool:
        """Clear the vector store"""
        try:
            if self.vectorstore:
                # Delete the collection
                self.vectorstore.delete_collection()
                
            # Recreate vectorstore
            self._load_vectorstore()
            
            logger.info("✅ Vectorstore cleared successfully")
            return True
            
        except Exception as e:
            logger.error(f"❌ Error clearing vectorstore: {e}")
            return False
            
    def _cleanup_memory(self):
        """Cleanup memory"""
        gc.collect()
        
        # Log memory usage
        memory_percent = psutil.virtual_memory().percent
        logger.info(f"🔧 Memory usage: {memory_percent:.1f}%")
        
    def get_system_stats(self) -> Dict[str, Any]:
        """Get system performance statistics"""
        try:
            memory = psutil.virtual_memory()
            cpu_percent = psutil.cpu_percent(interval=1)
            
            return {
                "memory_used_gb": memory.used / (1024**3),
                "memory_total_gb": memory.total / (1024**3), 
                "memory_percent": memory.percent,
                "cpu_percent": cpu_percent,
                "available_memory_gb": memory.available / (1024**3)
            }
        except Exception as e:
            logger.error(f"❌ Error getting system stats: {e}")
            return {}