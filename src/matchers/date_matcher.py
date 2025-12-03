"""Date parsing and comparison module"""

import re
from datetime import datetime, timedelta
from typing import Optional
from dateutil import parser as date_parser
import logging

logger = logging.getLogger(__name__)


class DateMatcher:
    """Handles date parsing, normalization, and comparison"""

    def __init__(self):
        """Initialize date matcher"""
        pass

    def normalize(self, date_str: str) -> Optional[str]:
        """Convert various date formats to YYYY-MM-DD

        Args:
            date_str: Date string in various formats

        Returns:
            Normalized date as YYYY-MM-DD or None if parse fails

        Examples:
            "11/29/25 8:12pm (5 min)" -> "2025-11-29"
            "2025-11-18" -> "2025-11-18"
            "10/30/2025" -> "2025-10-30"
            "2025-10-30T14:22:00+00:00" -> "2025-10-30"
        """
        if not date_str:
            return None

        # Already normalized (YYYY-MM-DD format)
        if re.match(r'^\d{4}-\d{2}-\d{2}$', date_str):
            return date_str

        try:
            # Extract date portion if there's extra content
            # Handle: "11/29/25 8:12pm (5 min)" -> "11/29/25"
            date_part = date_str.split()[0] if ' ' in date_str else date_str

            # Use dateutil parser with fuzzy mode
            parsed = date_parser.parse(date_part, fuzzy=True)

            # Return as YYYY-MM-DD
            return parsed.strftime('%Y-%m-%d')

        except (ValueError, TypeError) as e:
            logger.warning(f"Could not parse date '{date_str}': {e}")
            return None

    def parse_to_datetime(self, date_str: str) -> Optional[datetime]:
        """Parse date string to datetime object

        Args:
            date_str: Date string in any format

        Returns:
            datetime object or None if parse fails
        """
        normalized = self.normalize(date_str)
        if not normalized:
            return None

        try:
            return datetime.strptime(normalized, '%Y-%m-%d')
        except ValueError:
            return None

    def calculate_diff_days(self, date1: str, date2: str) -> Optional[int]:
        """Calculate difference in days between two dates

        Args:
            date1: First date string
            date2: Second date string

        Returns:
            Absolute difference in days, or None if parsing fails
        """
        dt1 = self.parse_to_datetime(date1)
        dt2 = self.parse_to_datetime(date2)

        if not dt1 or not dt2:
            return None

        diff = abs((dt1 - dt2).days)
        return diff

    def is_same_date(self, date1: str, date2: str) -> bool:
        """Check if two dates are the same day

        Args:
            date1: First date string
            date2: Second date string

        Returns:
            True if same date after normalization
        """
        norm1 = self.normalize(date1)
        norm2 = self.normalize(date2)

        if not norm1 or not norm2:
            return False

        return norm1 == norm2

    def within_tolerance(self, date1: str, date2: str, days: int = 1) -> bool:
        """Check if dates are within tolerance (±N days)

        Args:
            date1: First date string
            date2: Second date string
            days: Tolerance in days (default: 1)

        Returns:
            True if dates within ±days tolerance

        Example:
            within_tolerance("2025-11-29", "2025-11-30", 1) -> True
            within_tolerance("2025-11-29", "2025-12-01", 1) -> False
        """
        diff = self.calculate_diff_days(date1, date2)

        if diff is None:
            return False

        return diff <= days
