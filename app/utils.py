# app/utils.py
from typing import Any, Optional

def safe_float(value: Any, default: float = 0.0) -> float:
    """Güvenli float dönüşümü"""
    try:
        if value is None:
            return default
        return float(value)
    except (ValueError, TypeError):
        return default

def safe_int(value: Any, default: int = 0) -> int:
    """Güvenli int dönüşümü"""
    try:
        if value is None:
            return default
        return int(value)
    except (ValueError, TypeError):
        return default
