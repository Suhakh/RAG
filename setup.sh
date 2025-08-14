#!/bin/bash

echo "========================================"
echo "   ScholarBot Setup Script (Linux/macOS)"
echo "========================================"
echo

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Function to print colored output
print_status() {
    echo -e "${GREEN}✅ $1${NC}"
}

print_warning() {
    echo -e "${YELLOW}⚠️  $1${NC}"
}

print_error() {
    echo -e "${RED}❌ $1${NC}"
}

# Check Python
echo "[1/5] Checking Python installation..."
if ! command -v python3 &> /dev/null; then
    print_error "Python 3 not found! Please install Python 3.8+"
    exit 1
fi

python_version=$(python3 --version | cut -d' ' -f2 | cut -d'.' -f1,2)
print_status "Python $python_version found"

# Create virtual environment
echo
echo "[2/5] Creating virtual environment..."
python3 -m venv scholarbot_env
if [ $? -ne 0 ]; then
    print_error "Failed to create virtual environment"
    exit 1
fi

# Activate and install dependencies
echo
echo "[3/5] Installing dependencies..."
source scholarbot_env/bin/activate
pip install --upgrade pip
pip install -r requirements.txt
if [ $? -ne 0 ]; then
    print_error "Failed to install dependencies"
    exit 1
fi
print_status "Dependencies installed"

# Create directories
echo
echo "[4/5] Creating directory structure..."
mkdir -p data vectordb history temp
print_status "Directories created"

# Check Ollama
echo
echo "[5/5] Checking Ollama installation..."
if ! command -v ollama &> /dev/null; then
    print_warning "Ollama not found in PATH"
    echo
    echo "Please install Ollama:"
    echo "  Linux: curl -fsSL https://ollama.com/install.sh | sh"
    echo "  macOS: brew install ollama"
    echo
    echo "Then run:"
    echo "  ollama serve"
    echo "  ollama pull llama3.1:8b"
    echo "  ollama pull nomic-embed-text"
else
    print_status "Ollama found"

    # Check if Ollama is running
    if curl -s http://localhost:11434/api/tags > /dev/null 2>&1; then
        print_status "Ollama server is running"

        # Offer to pull models
        echo
        read -p "Would you like to pull the required models now? (y/n): " -n 1 -r
        echo
        if [[ $REPLY =~ ^[Yy]$ ]]; then
            echo "Pulling models... (this may take several minutes)"
            ollama pull llama3.1:8b
            ollama pull nomic-embed-text
            print_status "Models downloaded"
        fi
    else
        print_warning "Ollama server not running"
        echo "Start Ollama with: ollama serve"
    fi
fi

echo
echo "========================================"
echo "        Setup Complete!"
echo "========================================"
echo
echo "Next steps:"
echo "1. Make sure Ollama is running: ollama serve"
echo "2. Start ScholarBot: ./run_scholarbot.sh"
echo
echo "Or manually:"
echo "  source scholarbot_env/bin/activate"
echo "  streamlit run app.py"
echo