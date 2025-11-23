#!/usr/bin/env python3
"""
batch_process.py - CSV to NoSQL JSON transformation tool

A proof-of-concept CLI tool that transforms CSV files into nested JSON documents
for NoSQL database insertion. Uses a declarative configuration file to handle
denormalized data and create hierarchical structures.

Functions:
    load() - Read CSV file and configuration
    cleanse() - Clean and validate data
    combine() - Apply configuration and generate nested JSON output

These functions are meant to map to Databricks pipeline stages.
"""

import csv
import json
from collections import defaultdict
from pathlib import Path
from typing import Any, Dict, List, Optional
import argparse
from datetime import datetime
from zoneinfo import ZoneInfo


def load(csv_path: str, config_path: str) -> tuple[List[Dict[str, Any]], Dict[str, Any]]:
    """
    Load CSV data and transformation configuration.

    Args:
        csv_path: Path to the CSV file to process
        config_path: Path to the JSON configuration file

    Returns:
        Tuple of (csv_rows, config_dict)
    """
    csv_file = Path(csv_path)
    if not csv_file.exists():
        raise FileNotFoundError(f"CSV file not found: {csv_path}")

    with open(csv_file, 'r', encoding='utf-8-sig') as f:
        csv_rows = list(csv.DictReader(f))

    print(f"Loaded {len(csv_rows)} rows from {csv_path}")

    config_file = Path(config_path)
    if not config_file.exists():
        raise FileNotFoundError(f"Configuration file not found: {config_path}")

    with open(config_file, 'r') as f:
        config = json.load(f)

    print(f"Loaded configuration from {config_path}")
    return csv_rows, config


def user_format_to_strftime(user_format: str) -> str:
    """
    Convert user-friendly date format to Python strftime format.

    Args:
        user_format: User-friendly format like "MM/DD/YYYY" or "YYYY-MM-DD"

    Returns:
        Python strftime format string like "%m/%d/%Y" or "%Y-%m-%d"

    Examples:
        "MM/DD/YYYY" -> "%m/%d/%Y"
        "YYYY-MM-DD" -> "%Y-%m-%d"
        "DD/MM/YYYY" -> "%d/%m/%Y"
        "MM/DD/YYYY ZZZ" -> "%m/%d/%Y %Z"
    """
    # Map user-friendly tokens to strftime codes
    replacements = [
        ("YYYY", "%Y"),  # 4-digit year
        ("YY", "%y"),    # 2-digit year
        ("MM", "%m"),    # 2-digit month
        ("DD", "%d"),    # 2-digit day
        ("ZZZ", "%Z"),   # Timezone abbreviation (EST, PST, etc.)
    ]

    result = user_format
    for user_token, strftime_code in replacements:
        result = result.replace(user_token, strftime_code)

    return result


def convert_date_to_iso8601(date_str: str, input_format: Optional[str] = None, timezone: Optional[str] = None) -> str:
    """
    Convert a date string to ISO-8601 format with optional timezone offset.

    Args:
        date_str: The date string to convert
        input_format: Optional format string. Can be:
            - "ISO-8601" for ISO-8601 dates
            - User-friendly format like "MM/DD/YYYY" or "YYYY-MM-DD"
            - If None, auto-detect common formats
        timezone: Optional timezone name (e.g., "America/New_York").
                 If None and date string doesn't contain timezone, output date without timezone

    Returns:
        ISO-8601 formatted date string, with timezone if available (e.g., "2025-11-23T00:00:00-05:00")
        or without timezone if not available (e.g., "2025-11-23T00:00:00")
    """
    if not date_str or not date_str.strip():
        return date_str

    date_str = date_str.strip()
    parsed_dt = None
    has_timezone_info = False

    try:
        # Handle ISO-8601 format explicitly
        if input_format == "ISO-8601":
            from dateutil import parser as date_parser
            parsed_dt = date_parser.parse(date_str)
            has_timezone_info = parsed_dt.tzinfo is not None
        elif input_format:
            # Convert user-friendly format to strftime format
            strftime_format = user_format_to_strftime(input_format)

            # Try parsing with the converted format
            try:
                parsed_dt = datetime.strptime(date_str, strftime_format)
                # Check if format includes timezone
                has_timezone_info = "%Z" in strftime_format or "%z" in strftime_format
            except ValueError:
                # If parsing fails, might be because of timezone abbreviation handling
                # Try using dateutil parser instead
                from dateutil import parser as date_parser
                parsed_dt = date_parser.parse(date_str)
                has_timezone_info = parsed_dt.tzinfo is not None
        else:
            # Auto-detect format - try common formats
            formats = [
                "%Y-%m-%d",           # 2025-11-23
                "%m/%d/%Y",           # 11/23/2025
                "%m/%d/%y",           # 11/23/25
                "%d/%m/%Y",           # 23/11/2025 (European)
                "%b %d, %Y",          # Nov 23, 2025
                "%B %d, %Y",          # November 23, 2025
                "%Y-%m-%dT%H:%M:%S",  # 2025-11-23T00:00:00
                "%Y-%m-%d %H:%M:%S",  # 2025-11-23 00:00:00
            ]

            for fmt in formats:
                try:
                    parsed_dt = datetime.strptime(date_str, fmt)
                    break
                except ValueError:
                    continue

            if parsed_dt is None:
                # Try dateutil parser as last resort
                from dateutil import parser as date_parser
                parsed_dt = date_parser.parse(date_str)
                has_timezone_info = parsed_dt.tzinfo is not None

        if parsed_dt is None:
            print(f"Warning: Could not parse date '{date_str}', keeping original value")
            return date_str

        # Add timezone info if available and not already present
        if timezone and not has_timezone_info:
            tz = ZoneInfo(timezone)
            parsed_dt = parsed_dt.replace(tzinfo=tz)
        elif has_timezone_info and parsed_dt.tzinfo is None:
            # Edge case: format indicated timezone but parsing didn't capture it
            if timezone:
                tz = ZoneInfo(timezone)
                parsed_dt = parsed_dt.replace(tzinfo=tz)

        # Return ISO-8601 format
        return parsed_dt.isoformat()

    except Exception as e:
        print(f"Warning: Error converting date '{date_str}': {e}, keeping original value")
        return date_str


def convert_currency_to_numeric(currency_str: str) -> float:
    """
    Convert a currency string to a numeric value.

    Supports various input formats:
    - $23.47, $23, $0.47
    - 23.4700, 23, 0.47
    - .47, 23.

    Args:
        currency_str: The currency string to convert

    Returns:
        Numeric value as float

    Examples:
        "$23.47" -> 23.47
        "$23" -> 23.0
        "23.4700" -> 23.47
        ".47" -> 0.47
        "23." -> 23.0
    """
    if not currency_str or not isinstance(currency_str, str):
        return 0.0

    # Strip whitespace
    currency_str = currency_str.strip()

    if not currency_str:
        return 0.0

    try:
        # Remove dollar sign and commas
        cleaned = currency_str.replace("$", "").replace(",", "").strip()

        # Handle empty string after cleaning
        if not cleaned:
            return 0.0

        # Convert to float
        return float(cleaned)

    except ValueError as e:
        print(f"Warning: Could not parse currency '{currency_str}': {e}, returning 0.0")
        return 0.0


def cleanse(csv_rows: List[Dict[str, Any]], column_types: Optional[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
    """
    Cleanse and validate CSV data, applying type conversions as specified.

    Args:
        csv_rows: List of dictionaries representing CSV rows
        column_types: Optional dict mapping column names to type specifications

    Returns:
        List of cleansed dictionaries with type conversions applied
    """
    column_types = column_types or {}
    cleansed_rows = []

    for i, row in enumerate(csv_rows):
        cleaned_row = {k: v.strip() if isinstance(v, str) else v for k, v in row.items()}
        if all(not v for v in cleaned_row.values()):
            print(f"Skipping empty row at index {i}")
            continue

        # Apply type conversions
        for column_name, type_spec in column_types.items():
            if column_name in cleaned_row:
                value = cleaned_row[column_name]

                if isinstance(type_spec, dict) and type_spec.get("type") == "date":
                    # Convert date columns
                    input_format = type_spec.get("input_format")
                    timezone = type_spec.get("timezone")  # Optional, None if not specified
                    cleaned_row[column_name] = convert_date_to_iso8601(value, input_format, timezone)

                elif isinstance(type_spec, dict) and type_spec.get("type") == "currency":
                    # Convert currency columns to numeric
                    cleaned_row[column_name] = convert_currency_to_numeric(value)

        cleansed_rows.append(cleaned_row)

    print(f"Cleansed {len(cleansed_rows)} rows")
    return cleansed_rows


def combine(csv_rows: List[Dict[str, Any]], config: Dict[str, Any], output_dir: str = "mock_personstore") -> None:
    """
    Apply configuration template and generate nested JSON output files.

    Args:
        csv_rows: List of cleansed CSV row dictionaries
        config: Configuration dictionary with 'attribute' and 'template' keys
        output_dir: Directory where output JSON files will be written
    """
    output_path = Path(output_dir)
    output_path.mkdir(exist_ok=True)

    attribute_config = config.get("attribute", {})
    attribute_name = attribute_config.get("name", "data")
    group_by_column = attribute_config.get("group_by")
    template = config.get("template", {})

    if not group_by_column:
        raise ValueError("Configuration must specify 'attribute.group_by'")

    # Group rows by the top-level grouping column
    grouped_data = defaultdict(list)
    for row in csv_rows:
        key = row.get(group_by_column)
        if key:
            grouped_data[key].append(row)

    print(f"Grouped data into {len(grouped_data)} documents by '{group_by_column}'")

    # Process each group and create output files
    for key, rows in grouped_data.items():
        result = apply_template(rows, template)

        # Generate filename: {group_key}_{attribute_name}.json
        safe_attribute_name = attribute_name.replace("/", "_")
        filename = f"{key}_{safe_attribute_name}.json"
        output_file = output_path / filename

        with open(output_file, 'w') as f:
            json.dump(result, f, indent=2)

        print(f"Created {filename}")


def apply_template(rows: List[Dict[str, Any]], template: Any) -> Any:
    """
    Recursively apply template to rows to create nested structure.

    Args:
        rows: List of CSV row dictionaries to process
        template: Template configuration (dict, list, or string)

    Returns:
        Nested data structure
    """
    def pull(row, ref):
        """Extract value from row using {column_name} reference or return literal."""
        if isinstance(ref, str) and ref.startswith("{") and ref.endswith("}"):
            return row.get(ref[1:-1], "")
        return ref

    def get_nested_value(obj: Any, field_path: str) -> Any:
        """
        Extract a value from a nested object using dot notation.

        Args:
            obj: The object to extract from (dict or other)
            field_path: Dot-separated path (e.g., "result.value")

        Returns:
            The value at the specified path, or empty string if not found
        """
        if not isinstance(obj, dict):
            return ""

        parts = field_path.split(".")
        current = obj

        for part in parts:
            if isinstance(current, dict):
                current = current.get(part, "")
            else:
                return ""

        return current

    def parse_sort_value(value: str) -> Any:
        """
        Parse a string value into a sortable type.
        Handles: numbers, currency, dates, and strings.

        Args:
            value: String value to parse

        Returns:
            Tuple of (type_priority, parsed_value) for consistent sorting
        """
        if not isinstance(value, str):
            value = str(value) if value is not None else ""

        value = value.strip()

        if not value:
            return (3, "")  # Empty strings sort last

        # Try parsing as currency (e.g., "$89.99", "$125.00")
        if value.startswith("$"):
            try:
                numeric_value = float(value[1:].replace(",", ""))
                return (0, numeric_value)  # Currency sorts as numbers
            except ValueError:
                pass

        # Try parsing as number (including decimals)
        try:
            numeric_value = float(value)
            return (0, numeric_value)
        except ValueError:
            pass

        # Return as string (for dates and text)
        # ISO dates like "2025-10-20" will sort correctly as strings
        return (1, value)

    def apply_sort(items: List[Any], sort_config: Dict[str, str]) -> List[Any]:
        """
        Sort a list of items based on sort configuration.

        Args:
            items: List to sort
            sort_config: Dict with 'field' and 'order' keys

        Returns:
            Sorted list
        """
        if not sort_config or not items:
            return items

        field = sort_config.get("field")
        order = sort_config.get("order", "asc")

        if not field:
            return items

        # Normalize order to boolean (True = ascending, False = descending)
        # Accept: "asc", "ascending", "desc", "descending"
        ascending = order.lower() in ("asc", "ascending")

        # Create sort key function
        def sort_key(item):
            value = get_nested_value(item, field)
            return parse_sort_value(value)

        return sorted(items, key=sort_key, reverse=not ascending)

    def build(tmpl, data_rows):
        """Recursively build nested structure from template and rows."""
        if not data_rows:
            return {} if isinstance(tmpl, dict) else []

        if isinstance(tmpl, dict):
            # Handle special keys
            if "collect" in tmpl:
                # Collect all rows as array items
                collect_template = tmpl["collect"]
                if isinstance(collect_template, list) and collect_template:
                    result = [build(collect_template[0], [row]) for row in data_rows]

                    # Apply sorting if sort_by is specified
                    if "sort_by" in tmpl:
                        result = apply_sort(result, tmpl["sort_by"])

                    return result
                return []

            if "group_by" in tmpl:
                # Group rows and apply nested template
                group_key = tmpl["group_by"]
                nested_template = tmpl.get("template", {})

                grouped = defaultdict(list)
                for row in data_rows:
                    key = row.get(group_key)
                    if key:
                        grouped[key].append(row)

                result = [build(nested_template, group_rows) for group_rows in grouped.values()]

                # Apply sorting if sort_by is specified
                if "sort_by" in tmpl:
                    result = apply_sort(result, tmpl["sort_by"])

                return result

            # Regular object mapping
            # Check for potential data loss: if multiple rows exist and we're mapping fields directly,
            # we need to validate that all rows have the same values for non-nested fields
            if len(data_rows) > 1:
                # Check if any non-nested fields have different values across rows
                for key, value in tmpl.items():
                    if key in ("group_by", "template", "sort_by"):
                        continue
                    # Only check non-nested fields (strings with column references)
                    if isinstance(value, str) and value.startswith("{") and value.endswith("}"):
                        column_name = value[1:-1]
                        first_value = data_rows[0].get(column_name)
                        # Check if all rows have the same value for this column
                        if not all(row.get(column_name) == first_value for row in data_rows):
                            raise ValueError(
                                f"Template maps field '{key}' directly to column '{column_name}', "
                                f"but {len(data_rows)} rows exist with different values. "
                                f"Use 'collect' to create a list with all values, or 'group_by' to subdivide the data."
                            )

            result = {}
            row = data_rows[0]  # Use first row for field values
            for key, value in tmpl.items():
                if key in ("group_by", "template", "sort_by"):
                    continue
                result[key] = build(value, data_rows) if isinstance(value, dict) else pull(row, value)
            return result

        elif isinstance(tmpl, list):
            return [build(item, data_rows) for item in tmpl]

        else:
            # Primitive value or column reference
            return pull(data_rows[0] if data_rows else {}, tmpl)

    return build(template, rows)


def main():
    """Main CLI entry point."""
    parser = argparse.ArgumentParser(
        description="Transform CSV files into nested JSON documents for NoSQL databases"
    )
    parser.add_argument("csv_file", help="Path to the CSV file to process")
    parser.add_argument("transform_file", help="Path to the JSON transformation configuration file")
    parser.add_argument("-o", "--output", default="mock_personstore", help="Output directory for JSON files (default: mock_personstore)")

    args = parser.parse_args()

    try:
        csv_rows, config = load(args.csv_file, args.transform_file)
        column_types = config.get("column_types", {})
        cleansed_rows = cleanse(csv_rows, column_types)
        combine(cleansed_rows, config, args.output)
        print("\nProcessing complete!")
    except Exception as e:
        print(f"Error: {e}")
        return 1

    return 0


if __name__ == "__main__":
    exit(main())
