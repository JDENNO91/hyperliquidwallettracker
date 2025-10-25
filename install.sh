#!/bin/bash

# HyperLiquidWalletTracker Installation Script
# This script installs HyperLiquidWalletTracker and its dependencies

set -e

echo "🚀 HyperLiquidWalletTracker Installation Script"
echo "=============================================="

# Check if Python 3.9+ is installed
if ! command -v python3 &> /dev/null; then
    echo "❌ Python 3 is not installed. Please install Python 3.9 or higher."
    exit 1
fi

PYTHON_VERSION=$(python3 -c "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}')")
REQUIRED_VERSION="3.9"

if [ "$(printf '%s\n' "$REQUIRED_VERSION" "$PYTHON_VERSION" | sort -V | head -n1)" != "$REQUIRED_VERSION" ]; then
    echo "❌ Python $PYTHON_VERSION is installed, but Python $REQUIRED_VERSION or higher is required."
    exit 1
fi

echo "✅ Python $PYTHON_VERSION detected"

# Check if pip is installed
if ! command -v pip3 &> /dev/null; then
    echo "❌ pip3 is not installed. Please install pip3."
    exit 1
fi

echo "✅ pip3 detected"

# Create virtual environment (optional)
if [ "$1" = "--venv" ]; then
    echo "📦 Creating virtual environment..."
    python3 -m venv hyperliquidwallettracker-env
    source hyperliquidwallettracker-env/bin/activate
    echo "✅ Virtual environment created and activated"
fi

# Install dependencies
echo "📦 Installing dependencies..."
pip3 install -r requirements.txt

# Install the package in development mode
echo "📦 Installing HyperLiquidWalletTracker..."
pip3 install -e .

echo ""
echo "🎉 Installation complete!"
echo ""
echo "Quick start:"
echo "1. Generate configuration:"
echo "   python3 -m hyperliquidwallettracker.cli generate-config --format yaml > config.yaml"
echo ""
echo "2. Edit configuration:"
echo "   nano config.yaml"
echo ""
echo "3. Start monitoring:"
echo "   python3 -m hyperliquidwallettracker.cli start --wallets 0x1234... --discord-webhook https://..."
echo ""
echo "For more information, visit: https://github.com/JDENNO91/hyperliquidwallettracker"
echo ""

if [ "$1" = "--venv" ]; then
    echo "💡 To activate the virtual environment in the future, run:"
    echo "   source hyperliquidwallettracker-env/bin/activate"
fi
