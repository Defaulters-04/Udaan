import sys
from pathlib import Path

# Add project root to sys.path so engine and prism packages are discoverable by pytest
ROOT_DIR = Path(__file__).resolve().parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))
