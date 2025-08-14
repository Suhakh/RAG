#!/bin/bash

echo "========================================"
echo "      Starting ScholarBot..."
echo "========================================"

# Colors
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

print_status() {
    echo -e "${GREEN}✅ $1${NC}"
}

print_warning() {
    echo -e "${YELLOW}⚠️  $1${NC}"
}

print_error() {
    echo -e "${RED}❌ $1${NC}"
}

echo
echo "Checking Ollama service..."
if curl -s http://localhost:11434/api/tags > /dev/null 2>&1; then
    print_status "Ollama server is running"
else
    print_warning "Ollama server not responding"
    echo "Please start Ollama first: ollama serve"
    echo
    read -p "Would you like to start Ollama now? (y/n): " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        echo "Starting Ollama in background..."
        nohup ollama serve > ollama.log 2>&1 &
        echo "Waiting for Ollama to start..."
        sleep 5

        # Check again
        if curl -s http://localhost:11434/api/tags > /dev/null 2>&1; then
            print_status "Ollama started successfully"
        else
            print_error "Failed to start Ollama automatically"
            echo "Please start manually: ollama serve"
            exit 1
        fi
    else
        echo "Please start Ollama manually and run this script again"
        exit 1
    fi
fi

echo
echo "Activating Python environment..."
if [ ! -f "scholarbot_env/bin/activate" ]; then
    print_error "Virtual environment not found!"
    echo "Please run setup.sh first"
    exit 1
fi

source scholarbot_env/bin/activate

echo
print_status "Launching ScholarBot..."
echo "Access at: http://localhost:8501"
echo "Press Ctrl+C to stop"
echo

# Create desktop shortcut if requested
if [ ! -f "$HOME/Desktop/ScholarBot.desktop" ] && command -v desktop-file-install &> /dev/null; then
    read -p "Create desktop shortcut? (y/n): " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        cat > "$HOME/Desktop/ScholarBot.desktop" << EOF
[Desktop Entry]
Version=1.0
Type=Application
Name=ScholarBot
Comment=AI Research Assistant
Exec=$(pwd)/run_scholarbot.sh
Icon=$(pwd)/icon.png
Terminal=true
Categories=Education;Office;
EOF
        chmod +x "$HOME/Desktop/ScholarBot.desktop"
        print_status "Desktop shortcut created"
    fi
fi

streamlit run app.py