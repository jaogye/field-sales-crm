"""
Rate limiter instance — shared across main.py and routes.py.
Uses slowapi (wraps the `limits` library).
"""
from slowapi import Limiter
from slowapi.util import get_remote_address

limiter = Limiter(key_func=get_remote_address)
