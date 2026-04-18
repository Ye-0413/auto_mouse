"""Application entry point."""

import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent))

from gui.app import main

if __name__ == "__main__":
    main()
