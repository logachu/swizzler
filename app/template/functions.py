"""
Compute functions for card templates.

Provides utility functions for formatting dates, currency, and computing
values from arrays.
"""

from datetime import datetime
from typing import Any, Callable

from dateutil import parser as date_parser


# Function to get current datetime - can be overridden in tests
_get_current_datetime: Callable[[], datetime] = lambda: datetime.now()


def java_to_strftime(java_pattern: str) -> str:
    """
    Convert Java SimpleDateFormat pattern to Python strftime format.

    ⚠️ POC-ONLY CONVERSION CODE - DO NOT PORT TO JAVA ⚠️

    This function exists ONLY to allow the Python POC to accept Java-style
    date format patterns (e.g., 'yyyy-MM-dd', 'MMM dd, yyyy') in configuration
    files. The production Java implementation will use these patterns directly
    with SimpleDateFormat/DateTimeFormatter and will NOT need this converter.

    Why Java patterns in configs?
    - Production LogicBridge (Java/Quarkus) can use them directly
    - Aligns with Spring Boot, Quarkus, Jackson conventions
    - Java developers already familiar with this syntax
    - No conversion code needed in production

    Java Pattern -> Python strftime mapping:
        yyyy -> %Y  (4-digit year)
        yy -> %y    (2-digit year)
        MMMM -> %B  (full month name)
        MMM -> %b   (abbreviated month name)
        MM -> %m    (2-digit month number)
        dd -> %d    (2-digit day)
        EEEE -> %A  (full weekday name)
        EEE -> %a   (abbreviated weekday name)
        HH -> %H    (hour 0-23)
        hh -> %I    (hour 1-12)
        mm -> %M    (minutes - NOTE: Java uses lowercase!)
        ss -> %S    (seconds)
        a -> %p     (AM/PM)
        Z -> %z     (UTC offset)
        z -> %Z     (timezone name)

    Args:
        java_pattern: Java SimpleDateFormat pattern string

    Returns:
        Python strftime format string

    Examples:
        >>> java_to_strftime('yyyy-MM-dd')
        '%Y-%m-%d'
        >>> java_to_strftime('MMM dd, yyyy')
        '%b %d, %Y'
        >>> java_to_strftime('EEEE, MMMM dd')
        '%A, %B %d'
    """
    # Mapping from Java SimpleDateFormat tokens to Python strftime codes
    # Order matters: process longer tokens first to avoid partial replacements
    mappings = {
        'yyyy': '%Y',
        'yy': '%y',
        'MMMM': '%B',  # Must come before MMM
        'MMM': '%b',
        'MM': '%m',
        'dd': '%d',
        'EEEE': '%A',  # Must come before EEE
        'EEE': '%a',
        'HH': '%H',
        'hh': '%I',
        'mm': '%M',    # NOTE: Java mm=minutes, but Java MM=months!
        'ss': '%S',
        'a': '%p',
        'Z': '%z',
        'z': '%Z'
    }

    result = java_pattern
    # Sort by length descending to handle MMMM before MMM, EEEE before EEE
    for java_token, strftime_code in sorted(mappings.items(), key=lambda x: -len(x[0])):
        result = result.replace(java_token, strftime_code)

    return result


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
        """
        Format a date string according to Java SimpleDateFormat pattern.

        Accepts Java-style date format patterns (e.g., 'yyyy-MM-dd', 'MMM dd, yyyy')
        which will be used directly in the production Java implementation.
        The POC converts these to Python strftime format internally.

        Args:
            date_str: ISO-8601 date string or parseable date
            format_str: Java SimpleDateFormat pattern (e.g., 'MMM dd, yyyy')

        Returns:
            Formatted date string

        Examples:
            >>> format_date('2025-12-01', 'MMM dd, yyyy')
            'Dec 01, 2025'
            >>> format_date('2025-12-01T00:00:00-05:00', 'MMM dd')
            'Dec 01'
        """
        try:
            dt = date_parser.parse(date_str)
            # Convert Java pattern to Python strftime (POC-only conversion)
            python_format = java_to_strftime(format_str)
            return dt.strftime(python_format)
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
                today = _get_current_datetime().replace(tzinfo=dt.tzinfo, hour=0, minute=0, second=0, microsecond=0)
                dt = dt.replace(hour=0, minute=0, second=0, microsecond=0)
            else:
                today = _get_current_datetime().replace(hour=0, minute=0, second=0, microsecond=0)
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
                today = _get_current_datetime().replace(tzinfo=dt.tzinfo, hour=0, minute=0, second=0, microsecond=0)
                dt = dt.replace(hour=0, minute=0, second=0, microsecond=0)
            else:
                today = _get_current_datetime().replace(hour=0, minute=0, second=0, microsecond=0)
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
