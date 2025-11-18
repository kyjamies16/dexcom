import sys
from pathlib import Path


def pytest_configure(config):
    repo_root = Path(__file__).resolve().parent.parent
    sys.path.insert(0, str(repo_root))
