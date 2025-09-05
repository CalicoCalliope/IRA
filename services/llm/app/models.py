from typing import Optional, Tuple, Dict

"""
All prices are USD per 1M tokens in PRICE_DEFAULTS (API pricing is global; VAT may apply on invoices).
default_prices_for() converts to USD per 1K tokens to match the logger math.
Set COST_INPUT_PER_1K / COST_OUTPUT_PER_1K envs to override at runtime if needed.
"""

PRICE_DEFAULTS: Dict[str, Dict[str, float]] = {
    # GPT-5 family (placeholder values; override via env if needed)
    "gpt-5":       {"input": 1.250, "cached_input": 0.125, "output": 10.000},
    "gpt-5-mini":  {"input": 0.250, "cached_input": 0.025, "output": 2.000},
    "gpt-5-nano":  {"input": 0.050, "cached_input": 0.005, "output": 0.400},

    # 4o family
    "gpt-4o":      {"input": 2.500, "output": 10.000},
    "gpt-4o-mini": {"input": 0.600, "output": 2.400},

    # Back-compat aliases
    "gpt-4.1":      {"input": 2.000, "output": 8.000},
    "gpt-4.1-mini": {"input": 0.400, "output": 1.600},
}

def default_prices_for(model: str) -> Tuple[Optional[float], Optional[float]]:
    """
    Returns (input_price_per_1K, output_price_per_1K).
    Converts stored per-1M rates → per-1K to match cost math elsewhere.
    """
    p = PRICE_DEFAULTS.get(model)
    if not p:
        return None, None
    inp = p.get("input")
    out = p.get("output")
    if inp is None or out is None:
        return None, None
    return inp / 1000.0, out / 1000.0
