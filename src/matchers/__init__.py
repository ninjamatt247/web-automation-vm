"""Fuzzy matching modules for linking Freed and Osmind notes"""

from .name_matcher import NameMatcher
from .date_matcher import DateMatcher
from .note_matcher import NoteMatcher

__all__ = ['NameMatcher', 'DateMatcher', 'NoteMatcher']
