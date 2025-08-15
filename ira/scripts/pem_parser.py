import sys
import os

# Ensure CuBERT is on the path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../..", "CuBERT")))

import PEM_matcher

if __name__ == "__main__":
    PEM_matcher.main()
