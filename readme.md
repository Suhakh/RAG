# 🔬 ScholarBot

**AI-Powered Local RAG Research Assistant**

ScholarBot is a fully local Retrieval-Augmented Generation (RAG) chatbot designed for research purposes. It runs entirely on your machine with no external API calls, ensuring complete privacy and control over your documents.

## ✨ Features

- **100% Local Processing** - No data leaves your machine
- **Multi-format Support** - PDF, TXT, and Markdown documents  
- **Intelligent Chunking** - Optimized text splitting for better retrieval
- **Semantic Search** - Advanced embedding-based document retrieval
- **Streaming Responses** - Real-time answer generation
- **Persistent Storage** - ChromaDB vector storage with chat history
- **Resource Optimized** - Designed for CPU-only inference on modest hardware
- **Clean UI** - Streamlit-based interface with document management

## 🖥️ System Requirements

**Minimum Specs:**
- CPU: Intel i5 or equivalent (4+ cores recommended)  
- RAM: 8GB (16GB recommended)
- Storage: 2GB free space
- OS: Windows 10/11, macOS, or Linux


## 🚀 Quick Setup

### 1. Install Ollama

**Windows:**
```bash
# Download and install from: https://ollama.com/download
# Or via command line:
winget install Ollama.Ollama
```

**macOS:**
```bash
# Download from: https://ollama.com/download
# Or via Homebrew:
brew install ollama
```

**Linux:**
```bash
curl -fsSL https://ollama.com/install.sh | sh
```

### 2. Start Ollama Service

```bash
ollama serve
```

### 3. Pull Required Models

```bash
# LLM for generation (quantized for low RAM usage)
ollama pull llama3.1:8b

# Embedding model for document retrieval
ollama pull nomic-embed-text
```

### 4. Install ScholarBot

```bash
# Clone or download ScholarBot
cd scholarbot

# Install Python dependencies
pip install -r requirements.txt
```

### 5. Run ScholarBot

```bash
streamlit run app.py
```

ScholarBot will automatically open in your browser at `http://localhost:8501`

## 📁 Project Structure

```
scholarbot/
├── app.py              # Main Streamlit application
├── rag_pipeline.py     # RAG processing pipeline  
├── ingest.py          # Document ingestion & validation
├── ui.py              # UI components & utilities
├── config.yaml        # Configuration settings
├── requirements.txt   # Python dependencies
├── README.md          # This file
├── data/              # Uploaded documents storage
├── vectordb/          # ChromaDB vector database
├── history/           # Chat history (JSON)
└── scholarbot.log     # Application logs
```

## ⚙️ Configuration

Edit `config.yaml` to customize ScholarBot:

**Key Settings:**
- `models.llm.name`: LLM model (default: `llama3.1:8b`)
- `models.embeddings.name`: Embedding model (default: `nomic-embed-text`)
- `chunking.chunk_size`: Document chunk size (default: 600 tokens)
- `retrieval.top_k`: Number of chunks to retrieve (default: 4)
- `models.llm.temperature`: Response creativity (0.0-2.0, default: 0.7)

**Performance Tuning:**
- Reduce `chunk_size` for faster processing
- Lower `top_k` to speed up retrieval
- Adjust `temperature` for more/less creative responses

## 📚 Usage Guide

### 1. Upload Documents

**Method 1 - File Upload:**
1. Go to "Upload Documents" tab
2. Select "Single/Multiple Files"  
3. Choose your PDF, TXT, or MD files
4. Wait for processing to complete

**Method 2 - Folder Ingest:**
1. Select "Folder Upload" 
2. Enter path to your documents folder
3. Click "Ingest Folder"

### 2. Ask Questions

1. Go to "Chat" tab
2. Type your question in natural language
3. Click "Ask ScholarBot"
4. Review the answer and source citations

### 3. Manage Documents

- View uploaded files in the sidebar "Document Manager"
- Delete individual files or clear all documents
- Monitor storage usage and document count

## 🔧 Performance Tips

### For Low-Spec CPUs:

**Optimize Model Settings:**
```yaml
models:
  llm:
    name: "llama3.1:8b"  # Use quantized model
    temperature: 0.5     # Lower for faster inference
    
chunking:
  chunk_size: 400       # Smaller chunks = less processing
  
retrieval:
  top_k: 3             # Fewer chunks = faster retrieval
```

**System-Level Optimizations:**
- Close unnecessary applications before running
- Use SSD storage for faster I/O
- Monitor RAM usage - restart if memory usage grows high
- Process documents in smaller batches

**Expected Performance:**
- **Cold Start:** ~30-60 seconds  
- **Document Processing:** ~1-3 seconds per page
- **Query Response:** ~3-8 seconds
- **Memory Usage:** ~2-6GB RAM depending on model and documents

## 🛠️ Troubleshooting

### Common Issues:

**"Cannot connect to Ollama"**
- Ensure Ollama is running: `ollama serve`
- Check if port 11434 is available
- Restart Ollama service

**"Missing required models"**  
- Pull models manually: `ollama pull llama3.1:8b`
- Check model names in `config.yaml`
- Verify models with: `ollama list`

**High Memory Usage**
- Restart ScholarBot application
- Reduce `chunk_size` and `top_k` in config
- Clear document database if too large

**Slow Performance**
- Use quantized models (q4_K_M format)
- Reduce document batch sizes
- Lower temperature setting
- Close other applications

### Model Alternatives:

**Smaller LLMs (< 8GB RAM):**
```bash
ollama pull llama3.1:3b    # Faster, less accurate
ollama pull phi3:mini      # Microsoft Phi-3
```

**Larger LLMs (16GB+ RAM):**
```bash
ollama pull llama3.1:13b   # Better quality, slower
```

**Alternative Embeddings:**
```bash
ollama pull mxbai-embed-large  # Alternative embedding model
```

## 📊 Monitoring

**System Resources:**
- Check CPU/RAM usage in sidebar "System Status"
- Monitor log file: `scholarbot.log`
- Document count and storage in "Document Manager"

**Performance Metrics:**
- Query response times shown after each answer  
- Document processing speed displayed during upload
- Memory cleanup occurs automatically every 100 queries

## 🔒 Privacy & Security

- **100% Local**: No internet connection required after setup
- **No Data Sharing**: Documents never leave your machine  
- **Encrypted Storage**: ChromaDB provides secure local storage
- **No Logging**: No personal data in logs (only system events)

## 🤝 Contributing

ScholarBot is designed as a research tool. Feel free to:
- Modify configurations for your specific use case
- Experiment with different models and settings
- Extend functionality for your research needs

## 📄 License

Open source - modify and use as needed for research purposes.

## 🆘 Support

For issues:
1. Check this README and troubleshooting section
2. Review `scholarbot.log` for error details  
3. Verify Ollama models and service status
4. Check system resource availability

---

**Happy Researching with ScholarBot! 