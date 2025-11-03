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
"""

import csv
import json
from collections import defaultdict
from pathlib import Path
from typing import Any, Dict, List
import argparse


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


def cleanse(csv_rows: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    Cleanse and validate CSV data.

    Args:
        csv_rows: List of dictionaries representing CSV rows

    Returns:
        List of cleansed dictionaries
    """
    cleansed_rows = []
    for i, row in enumerate(csv_rows):
        cleaned_row = {k: v.strip() if isinstance(v, str) else v for k, v in row.items()}
        if all(not v for v in cleaned_row.values()):
            print(f"Skipping empty row at index {i}")
            continue
        cleansed_rows.append(cleaned_row)

    print(f"Cleansed {len(cleansed_rows)} rows")
    return cleansed_rows


def combine(csv_rows: List[Dict[str, Any]], config: Dict[str, Any], output_dir: str = "output") -> None:
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
                    return [build(collect_template[0], [row]) for row in data_rows]
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

                return [build(nested_template, group_rows) for group_rows in grouped.values()]

            # Regular object mapping
            result = {}
            row = data_rows[0]  # Use first row for field values
            for key, value in tmpl.items():
                if key in ("group_by", "template"):
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
    parser.add_argument("-o", "--output", default="output", help="Output directory for JSON files (default: output)")

    args = parser.parse_args()

    try:
        csv_rows, config = load(args.csv_file, args.transform_file)
        cleansed_rows = cleanse(csv_rows)
        combine(cleansed_rows, config, args.output)
        print("\nProcessing complete!")
    except Exception as e:
        print(f"Error: {e}")
        return 1

    return 0


if __name__ == "__main__":
    exit(main())
