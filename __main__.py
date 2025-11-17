"""
Main entry point for AI-Factories framework
Routes to client, server, or monitor modules
"""
import sys
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent))

from cli import main

if __name__ == '__main__':
    main()
