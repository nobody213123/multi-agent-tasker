import env  # noqa: F401
import sys
from pathlib import Path

ROOT_DIR = Path(__file__).parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from entry.web import app, run_server

if __name__ == "__main__":
    run_server()
