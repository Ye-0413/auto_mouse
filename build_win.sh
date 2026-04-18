#!/bin/bash
# Build script for Windows (run on Windows with Git Bash or WSL)

set -e

echo "Building Auto Mouse for Windows..."

# Check if we're on Windows
if [[ "$OSTYPE" != "msys" && "$OSTYPE" != "cygwin" && "$OSTYPE" != "win32" ]]; then
    echo "Note: This script is designed for Windows. On macOS, use build_mac.sh"
fi

# Install dependencies
echo "Installing dependencies..."
pip install -r requirements.txt

# Create dist directory
mkdir -p dist/windows

# Build with PyInstaller (onefile for simpler distribution)
echo "Building with PyInstaller..."
pyinstaller auto_mouse.spec --clean --win-private-assemblies

# Move to dist folder
mv dist/AutoMouse dist/windows/

echo "Build complete: dist/windows/AutoMouse.exe"
