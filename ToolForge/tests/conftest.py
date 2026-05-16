"""Test configuration — ensures packages can be imported without editable install."""
import sys
from pathlib import Path

# Add ToolForge root to path so `from packages.core...` works in pytest
toolforge_root = Path(__file__).parent.parent
if str(toolforge_root) not in sys.path:
    sys.path.insert(0, str(toolforge_root))
