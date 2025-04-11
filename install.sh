#!/bin/bash
#
# Voice2Text Installation Script
#
# This script installs the Voice2Text tool and its dependencies.
#

set -e  # Exit on error

echo "========================================="
echo "Voice2Text Installer"
echo "========================================="

# Check Python version
python_version=$(python3 --version 2>&1 | awk '{print $2}')
echo "Detected Python $python_version"

# Check if Python version is sufficient
version_major=$(echo $python_version | cut -d. -f1)
version_minor=$(echo $python_version | cut -d. -f2)

if [ "$version_major" -lt 3 ] || ([ "$version_major" -eq 3 ] && [ "$version_minor" -lt 7 ]); then
    echo "Error: Python 3.7+ is required (found $python_version)"
    exit 1
fi

# Create a virtual environment if requested
read -p "Create a virtual environment for Voice2Text? [y/N] " create_venv
if [[ $create_venv =~ ^[Yy]$ ]]; then
    echo "Creating virtual environment..."
    python3 -m venv .venv
    
    # Activate virtual environment
    source .venv/bin/activate
    
    echo "Virtual environment created and activated"
fi

# Install base dependencies
echo "Installing core dependencies..."
pip install -r requirements.txt

# Ask about additional engines
echo ""
echo "Would you like to install additional speech recognition engines?"
echo "1. OpenAI Whisper (local - requires 1GB+ RAM)"
echo "2. faster-whisper (optimized Whisper - requires 1GB+ RAM)"
echo "3. Deepgram SDK (requires API key)"
echo "4. All of the above"
echo "5. None"
read -p "Enter your choice [1-5]: " engine_choice

case $engine_choice in
    1)
        echo "Installing OpenAI Whisper..."
        pip install openai-whisper
        ;;
    2)
        echo "Installing faster-whisper..."
        pip install faster-whisper
        ;;
    3)
        echo "Installing Deepgram SDK..."
        pip install deepgram-sdk
        ;;
    4)
        echo "Installing all additional engines..."
        pip install openai-whisper faster-whisper deepgram-sdk
        ;;
    5)
        echo "Skipping additional engines."
        ;;
    *)
        echo "Invalid choice. Skipping additional engines."
        ;;
esac

# Make the executable script executable
chmod +x voice2text

# Check for required system dependencies
echo ""
echo "Checking system dependencies..."

# Check for PortAudio (required for PyAudio)
if ! ldconfig -p | grep -q libportaudio; then
    echo "WARNING: libportaudio not found. PyAudio may not work correctly."
    echo "On Debian/Ubuntu, install with: sudo apt-get install portaudio19-dev"
    echo "On Fedora/RHEL: sudo dnf install portaudio-devel"
    echo "On Arch Linux: sudo pacman -S portaudio"
fi

# Final instructions
echo ""
echo "========================================="
echo "Installation complete!"
echo "========================================="
echo ""
echo "To use Voice2Text:"
echo "1. If you created a virtual environment, activate it with:"
echo "   source .venv/bin/activate"
echo ""
echo "2. Run the tool with:"
echo "   ./voice2text"
echo ""
echo "3. For configuration options, edit config.yaml"
echo ""
echo "4. If you want to install globally, create a symlink:"
echo "   sudo ln -s $(pwd)/voice2text /usr/local/bin/voice2text"
echo ""
echo "Enjoy Voice2Text!"