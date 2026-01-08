#!/bin/bash
# Setup script for AI-Factories framework on MeluXina
# Run this script after allocating an interactive session with salloc
# Usage: source ./setup.sh  (must use 'source' to load module in current shell)

echo "Loading Python module..."
module load Python/3.12.3-GCCcore-13.3.0

echo "Installing Python dependencies..."
pip install -r requirements.txt

echo ""
echo "Setup complete!"
echo "You can now use the framework with: python3 -m src.<module> <command>"
