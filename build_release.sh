#!/bin/bash
# Cross-platform build script

set -e

PLATFORM=$(uname -s)

case "$PLATFORM" in
    Darwin*)
        echo "Building Auto Mouse for macOS..."
        pip install -r requirements.txt
        pip install pyinstaller
        pyinstaller auto_mouse.spec --clean
        mkdir -p dist/release/macos
        cd dist
        zip -r release/macos/AutoMouse-macos.zip AutoMouse
        echo "Build complete: dist/release/macos/AutoMouse-macos.zip"
        ;;
    Linux*)
        echo "Building Auto Mouse for Linux..."
        pip install -r requirements.txt
        pip install pyinstaller
        pyinstaller auto_mouse.spec --clean
        mkdir -p dist/release/linux
        cd dist
        tar -czf release/linux/AutoMouse-linux.tar.gz AutoMouse
        echo "Build complete: dist/release/linux/AutoMouse-linux.tar.gz"
        ;;
    MINGW*|CYGWIN*|MSYS*)
        echo "Building Auto Mouse for Windows..."
        pip install -r requirements.txt
        pip install pyinstaller
        pyinstaller auto_mouse.spec --clean --win-private-assemblies
        mkdir -p dist/release/windows
        cd dist
        powershell -Command "Compress-Archive -Path AutoMouse -DestinationPath release/windows/AutoMouse-windows.zip -Force"
        echo "Build complete: dist/release/windows/AutoMouse-windows.zip"
        ;;
    *)
        echo "Unknown platform: $PLATFORM"
        exit 1
        ;;
esac
