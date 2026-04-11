import sys
import os

# Add api/ directory so `import api` resolves to api/api.py
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "api"))
