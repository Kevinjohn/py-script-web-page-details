# conftest.py
import sys
import os

# Add the 'src' directory to the Python path for test discovery
# This allows tests anywhere in the 'tests' directory to import from 'src'
# using absolute imports (e.g., from src.module import ...)
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__)))
src_path = os.path.join(project_root, "src")
if src_path not in sys.path:
    sys.path.insert(0, src_path)

# You can also add project_root to path if needed, depending on import styles
# if project_root not in sys.path:
#    sys.path.insert(0, project_root)

# Note: If you were using relative imports within src (e.g., from . import utils),
# ensuring the project root or src is in the path is usually sufficient.
# If you were running tests using 'python -m pytest', that often handles path issues too,
# but running 'pytest' directly is more common and requires path setup like this.