#!/bin/bash
# Setup script for AI-Factories framework on MeluXina
# Run this script after allocating an interactive session with salloc

echo "Loading Python module..."
module load Python/3.12.3-GCCcore-13.3.0

echo "Installing Python dependencies..."
pip install loguru

echo ""
echo "Setup complete!"
echo "You can now use the framework with: python -m src.<module> <command>"
