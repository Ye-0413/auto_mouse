#!/bin/bash
# Build script for macOS

set -e

echo "Building Auto Mouse for macOS..."

# Check if we're on macOS
if [[ "$OSTYPE" != "darwin"* ]]; then
    echo "Error: This script must be run on macOS"
    exit 1
fi

# Install dependencies
echo "Installing dependencies..."
pip install -r requirements.txt

# Create dist directory
mkdir -p dist/macos

# Build with PyInstaller
echo "Building with PyInstaller..."
pyinstaller auto_mouse.spec --clean

# Move to dist folder
mv dist/AutoMouse dist/macos/

echo "Build complete: dist/macos/AutoMouse.app"
