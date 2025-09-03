# Compatibility shim: re-export from app.adapter, including the private symbol.
from app.adapter import rank_items, _cosine

__all__ = ["rank_items", "_cosine"]
