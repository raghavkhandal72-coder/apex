import os
import sys

# Ensure current working directory is on sys.path for zipapp execution
if os.getcwd() not in sys.path:
    sys.path.insert(0, os.getcwd())

from .cli import main

if __name__ == "__main__":
    sys.exit(main())
