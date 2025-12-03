"""Name matching and normalization module using rapidfuzz"""

import re
from typing import Dict, Tuple
from rapidfuzz import fuzz
import logging

logger = logging.getLogger(__name__)


class NameMatcher:
    """Handles patient name normalization and fuzzy matching"""

    # Common titles to remove
    TITLES = ['dr', 'mr', 'mrs', 'ms', 'miss', 'prof', 'rev']

    # Common suffixes to remove
    SUFFIXES = ['jr', 'sr', 'ii', 'iii', 'iv', 'esq', 'md', 'phd']

    def __init__(self):
        """Initialize name matcher"""
        pass

    def normalize(self, name: str) -> str:
        """Normalize patient name for comparison

        Args:
            name: Patient full name

        Returns:
            Normalized name (lowercase, no titles/suffixes/punctuation)

        Example:
            "Dr. John O'Brien, Jr." -> "john obrien"
        """
        if not name:
            return ""

        # Convert to lowercase
        normalized = name.lower()

        # Remove titles (with or without period)
        for title in self.TITLES:
            normalized = re.sub(rf'\b{title}\.?\s*', '', normalized)

        # Remove suffixes (with or without period)
        for suffix in self.SUFFIXES:
            normalized = re.sub(rf',?\s*\b{suffix}\.?\s*$', '', normalized)

        # Remove punctuation except hyphens (preserve hyphenated names)
        normalized = re.sub(r'[,.\'\"\(\)]', '', normalized)

        # Collapse multiple spaces to single space
        normalized = re.sub(r'\s+', ' ', normalized)

        # Strip leading/trailing whitespace
        normalized = normalized.strip()

        return normalized

    def extract_parts(self, name: str) -> Dict[str, str]:
        """Extract first, middle, and last name parts

        Args:
            name: Patient full name

        Returns:
            Dictionary with 'first', 'middle', 'last' keys

        Example:
            "John Michael Smith" -> {'first': 'john', 'middle': 'michael', 'last': 'smith'}
        """
        normalized = self.normalize(name)
        parts = normalized.split()

        if len(parts) == 0:
            return {'first': '', 'middle': '', 'last': ''}
        elif len(parts) == 1:
            return {'first': parts[0], 'middle': '', 'last': ''}
        elif len(parts) == 2:
            return {'first': parts[0], 'middle': '', 'last': parts[1]}
        else:
            # 3+ parts: first, middle(s), last
            return {
                'first': parts[0],
                'middle': ' '.join(parts[1:-1]),
                'last': parts[-1]
            }

    def calculate_similarity(self, name1: str, name2: str) -> float:
        """Calculate similarity score between two names using rapidfuzz

        Args:
            name1: First name
            name2: Second name

        Returns:
            Similarity score from 0.0 to 1.0

        Uses token_set_ratio which handles:
        - Word order: "John Smith" vs "Smith, John" -> high score
        - Extra words: "John Michael Smith" vs "John Smith" -> high score
        - Case insensitivity
        """
        norm1 = self.normalize(name1)
        norm2 = self.normalize(name2)

        if not norm1 or not norm2:
            return 0.0

        # Use token_set_ratio for best name matching
        # Returns 0-100, convert to 0.0-1.0
        score = fuzz.token_set_ratio(norm1, norm2) / 100.0

        return score

    def partial_match(self, name1: str, name2: str, match_type: str = 'first_or_last') -> Tuple[bool, float]:
        """Check if names partially match (first OR last name only)

        Args:
            name1: First name
            name2: Second name
            match_type: 'first_only', 'last_only', or 'first_or_last'

        Returns:
            Tuple of (matches, similarity_score)

        Example:
            partial_match("John Smith", "J Smith", "first_or_last")
            -> (True, 0.85) if "Smith" matches well
        """
        parts1 = self.extract_parts(name1)
        parts2 = self.extract_parts(name2)

        # Calculate first name similarity
        first_sim = 0.0
        if parts1['first'] and parts2['first']:
            first_sim = fuzz.ratio(parts1['first'], parts2['first']) / 100.0

        # Calculate last name similarity
        last_sim = 0.0
        if parts1['last'] and parts2['last']:
            last_sim = fuzz.ratio(parts1['last'], parts2['last']) / 100.0

        if match_type == 'first_only':
            return (first_sim > 0.85, first_sim)
        elif match_type == 'last_only':
            return (last_sim > 0.85, last_sim)
        else:  # first_or_last
            # Match if either first OR last is strong match
            max_sim = max(first_sim, last_sim)
            matches = first_sim > 0.85 or last_sim > 0.85
            return (matches, max_sim)

    def is_exact_match(self, name1: str, name2: str) -> bool:
        """Check if two names are exact matches after normalization

        Args:
            name1: First name
            name2: Second name

        Returns:
            True if exact match after normalization
        """
        return self.normalize(name1) == self.normalize(name2)
