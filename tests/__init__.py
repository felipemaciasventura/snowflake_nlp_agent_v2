# Test configuration for Snowflake NLP Agent v2

# This file makes pytest recognize this directory as a package
import sys
from pathlib import Path

# Add src directory to Python path for imports
src_path = Path(__file__).parent.parent / "src"
sys.path.insert(0, str(src_path))