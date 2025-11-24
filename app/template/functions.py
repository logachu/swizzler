"""
Compute functions for card templates.

Provides utility functions for formatting dates, currency, and computing
values from arrays.
"""

from datetime import datetime
from typing import Any

from dateutil import parser as date_parser


class ComputeFunctions:
    """Implements compute functions for card templates."""

    @staticmethod
    def len(items: Any) -> int:
        """Return length of array or list."""
        if isinstance(items, list):
            return len(items)
        return 0

    @staticmethod
    def sum(items: Any) -> float:
        """Sum numeric values, handling currency strings."""
        if not isinstance(items, list):
            return 0.0

        total = 0.0
        for item in items:
            if isinstance(item, (int, float)):
                total += item
            elif isinstance(item, str):
                # Try to parse currency strings like "$42.20"
                cleaned = item.replace("$", "").replace(",", "").strip()
                try:
                    total += float(cleaned)
                except ValueError:
                    continue
        return total

    @staticmethod
    def format_date(date_str: str, format_str: str) -> str:
        """Format a date string according to format."""
        try:
            dt = date_parser.parse(date_str)
            return dt.strftime(format_str)
        except Exception:
            return date_str

    @staticmethod
    def days_from_now(date_str: str) -> str:
        """Return relative days from now."""
        try:
            dt = date_parser.parse(date_str)
            # Handle timezone-aware datetimes
            if dt.tzinfo is not None:
                # Get current time in the same timezone as the parsed date
                today = datetime.now(dt.tzinfo).replace(hour=0, minute=0, second=0, microsecond=0)
                dt = dt.replace(hour=0, minute=0, second=0, microsecond=0)
            else:
                today = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
                dt = dt.replace(hour=0, minute=0, second=0, microsecond=0)

            delta = (dt - today).days

            if delta == 0:
                return "today"
            elif delta == 1:
                return "tomorrow"
            elif delta == -1:
                return "yesterday"
            elif delta > 0:
                return f"{delta} days from now"
            else:
                return f"{abs(delta)} days ago"
        except Exception:
            return date_str

    @staticmethod
    def days_after(date_str: str) -> int:
        """
        Return number of days after a given date.
        Positive if date is in the past (e.g., 5 days overdue).
        Negative if date is in the future (e.g., -5 means due in 5 days).
        Zero if date is today.
        """
        try:
            dt = date_parser.parse(date_str)
            # Handle timezone-aware datetimes
            if dt.tzinfo is not None:
                # Get current time in the same timezone as the parsed date
                today = datetime.now(dt.tzinfo).replace(hour=0, minute=0, second=0, microsecond=0)
                dt = dt.replace(hour=0, minute=0, second=0, microsecond=0)
            else:
                today = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
                dt = dt.replace(hour=0, minute=0, second=0, microsecond=0)

            delta = (today - dt).days
            return delta
        except Exception:
            return 0

    @staticmethod
    def currency(amount: Any) -> str:
        """
        Format a numeric value as currency with dollar sign, comma thousands separator,
        and exactly two decimal places.

        Args:
            amount: Numeric value or string to format

        Returns:
            Formatted currency string (e.g., "$1,089.99")

        Examples:
            1089.99 -> "$1,089.99"
            1089.99000 -> "$1,089.99"
            23 -> "$23.00"
            0.47 -> "$0.47"
        """
        try:
            # Convert to float if it's a string
            if isinstance(amount, str):
                # Remove existing currency symbols and commas
                cleaned = amount.replace("$", "").replace(",", "").strip()
                numeric_value = float(cleaned)
            elif isinstance(amount, (int, float)):
                numeric_value = float(amount)
            else:
                return "$0.00"

            # Format with comma thousands separator and 2 decimal places
            return f"${numeric_value:,.2f}"

        except (ValueError, TypeError):
            return "$0.00"
