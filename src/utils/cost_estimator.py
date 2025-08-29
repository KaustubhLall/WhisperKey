"""
Cost Estimation for WhisperKey

This module provides a simple cost estimator for OpenAI's transcription models.
"""

# Pricing for gpt-4o-mini (hypothetical, based on common models)
# Input: $0.15 / 1M tokens
# Output: $0.60 / 1M tokens

TOKEN_PRICING = {
    "input": 0.15 / 1_000_000,
    "output": 0.60 / 1_000_000,
}

def estimate_cost(input_tokens: int, output_tokens: int) -> float:
    """Estimate the cost of a transcription based on token usage."""
    input_cost = input_tokens * TOKEN_PRICING["input"]
    output_cost = output_tokens * TOKEN_PRICING["output"]
    return input_cost + output_cost
