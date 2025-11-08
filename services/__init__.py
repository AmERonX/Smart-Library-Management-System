"""
Services module for SLMS.
Contains business logic separated from HTTP handling for testability.
"""

from .insertion import insert_pending_book

__all__ = ['insert_pending_book']
