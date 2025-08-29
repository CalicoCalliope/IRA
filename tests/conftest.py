import sys
import os

# Add src/ to sys.path so tests can import modules
sys.path.insert(
    0, 
    os.path.abspath(os.path.join(os.path.dirname(__file__), "../src"))
)