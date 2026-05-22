import asyncio
import sys
import os

# Ensure repository root is on sys.path so 'app' package imports work
ROOT = os.path.dirname(os.path.dirname(__file__))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from app.startup import startup_event

if __name__ == "__main__":
    asyncio.run(startup_event())
