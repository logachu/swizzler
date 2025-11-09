#!/usr/bin/env python3
"""
validate_csv.py - CSV and Configuration Validator

Validates that a CSV file can be successfully processed by batch_process.py
with a given csv_transform.json configuration.

Usage:
    python validate_csv.py <csv_file> [transform_file]
"""

import csv
import json
import sys
from collections import defaultdict
from pathlib import Path
from typing import Any, Dict, List, Set, Tuple


class ValidationResult:
    """Stores validation results with errors and warnings."""

    def __init__(self):
        self.errors: List[str] = []
        self.warnings: List[str] = []
        self.info: List[str] = []

    def add_error(self, message: str):
        """Add a critical error that prevents processing."""
        self.errors.append(f"❌ ERROR: {message}")

    def add_warning(self, message: str):
        """Add a warning about potential issues."""
        self.warnings.append(f"⚠️  WARNING: {message}")

    def add_info(self, message: str):
        """Add informational message."""
        self.info.append(f"ℹ️  INFO: {message}")

    def is_valid(self) -> bool:
        """Returns True if no errors exist."""
        return len(self.errors) == 0

    def print_report(self):
        """Print validation report to stdout."""
        print("\n" + "="*70)
        print("CSV VALIDATION REPORT")
        print("="*70 + "\n")

        if self.info:
            print("📊 Information:")
            for msg in self.info:
                print(f"  {msg}")
            print()

        if self.warnings:
            print("⚠️  Warnings:")
            for msg in self.warnings:
                print(f"  {msg}")
            print()

        if self.errors:
            print("❌ Errors:")
            for msg in self.errors:
                print(f"  {msg}")
            print()

        print("="*70)
        if self.is_valid():
            print("✅ VALIDATION PASSED - CSV can be processed")
        else:
            print(f"❌ VALIDATION FAILED - {len(self.errors)} error(s) found")
        print("="*70 + "\n")


class CSVValidator:
    """Validates CSV files for batch_process.py compatibility."""

    def __init__(self, csv_path: str, config_path: str | None = None):
        self.csv_path = Path(csv_path)
        self.config_path = Path(config_path) if config_path else None
        self.result = ValidationResult()

    def validate(self) -> ValidationResult:
        """Run all validation checks."""
        # Check files exist
        if not self._check_file_exists():
            return self.result

        # Load CSV
        csv_rows, headers = self._load_csv()
        if csv_rows is None or headers is None:
            return self.result

        # Validate CSV structure
        self._validate_csv_structure(csv_rows, headers)

        # If config provided, validate against config
        if self.config_path:
            config = self._load_config()
            if config:
                self._validate_against_config(csv_rows, headers, config)
        else:
            self.result.add_info("No config file provided - skipping config-specific validation")
            self._suggest_config_structure(csv_rows, headers)

        return self.result

    def _check_file_exists(self) -> bool:
        """Check that required files exist."""
        if not self.csv_path.exists():
            self.result.add_error(f"CSV file not found: {self.csv_path}")
            return False

        if self.config_path and not self.config_path.exists():
            self.result.add_error(f"Config file not found: {self.config_path}")
            return False

        return True

    def _load_csv(self) -> Tuple[List[Dict[str, Any]] | None, List[str] | None]:
        """Load and parse CSV file."""
        try:
            with open(self.csv_path, 'r', encoding='utf-8-sig') as f:
                reader = csv.DictReader(f)
                headers = list(reader.fieldnames) if reader.fieldnames else []
                rows = list(reader)

            self.result.add_info(f"Loaded {len(rows)} rows from {self.csv_path.name}")
            self.result.add_info(f"Found {len(headers)} columns: {', '.join(headers)}")

            return rows, headers

        except UnicodeDecodeError as e:
            self.result.add_error(f"CSV encoding error - file must be UTF-8: {e}")
            return None, None
        except Exception as e:
            self.result.add_error(f"Failed to load CSV: {e}")
            return None, None

    def _load_config(self) -> Dict[str, Any] | None:
        """Load and parse config file."""
        if not self.config_path:
            return None

        try:
            with open(self.config_path, 'r') as f:
                config = json.load(f)

            self.result.add_info(f"Loaded config from {self.config_path.name}")
            return config

        except json.JSONDecodeError as e:
            self.result.add_error(f"Invalid JSON in config file: {e}")
            return None
        except Exception as e:
            self.result.add_error(f"Failed to load config: {e}")
            return None

    def _validate_csv_structure(self, rows: List[Dict], headers: List[str]):
        """Validate basic CSV structure."""
        # Check for empty CSV
        if not rows:
            self.result.add_error("CSV file has no data rows (only headers)")
            return

        # Check for duplicate column names
        if len(headers) != len(set(headers)):
            duplicates = [h for h in headers if headers.count(h) > 1]
            self.result.add_error(f"Duplicate column names found: {set(duplicates)}")

        # Check for empty column names
        if any(not h or h.strip() == "" for h in headers):
            self.result.add_error("CSV has columns with empty names")

        # Check for rows with all empty values
        empty_row_count = 0
        rows_with_zeros = []

        for i, row in enumerate(rows):
            # Strip whitespace from string values (like cleanse() does)
            cleaned = {k: v.strip() if isinstance(v, str) else v for k, v in row.items()}

            # Check if all values are falsy (potential issue)
            if all(not v for v in cleaned.values()):
                empty_row_count += 1

            # Check for integer zeros (potential grouping issue)
            for col, val in row.items():
                if val == "0" or val == 0:
                    rows_with_zeros.append(i + 2)  # +2 for 1-based indexing + header row
                    break

        if empty_row_count > 0:
            self.result.add_warning(f"{empty_row_count} row(s) will be skipped (all values are empty/falsy)")

        if rows_with_zeros:
            self.result.add_warning(
                f"Rows with zero values found (lines {rows_with_zeros[:5]}{'...' if len(rows_with_zeros) > 5 else ''}). "
                "Integer 0 used as group key will cause row to be silently dropped!"
            )

        # Check for whitespace-only values
        whitespace_found = False
        for i, row in enumerate(rows):
            for col, val in row.items():
                if isinstance(val, str) and val.strip() == "" and val != "":
                    whitespace_found = True
                    break
            if whitespace_found:
                break

        if whitespace_found:
            self.result.add_warning("Whitespace-only values found - they will become empty strings after cleansing")

    def _validate_against_config(self, rows: List[Dict], headers: List[str], config: Dict):
        """Validate CSV against configuration requirements."""
        # Extract config components
        attribute_config = config.get("attribute", {})
        group_by_column = attribute_config.get("group_by")
        template = config.get("template", {})

        if not group_by_column:
            self.result.add_error("Config missing 'attribute.group_by' field")
            return

        # Validate group_by column exists
        if group_by_column not in headers:
            self.result.add_error(
                f"Config specifies group_by column '{group_by_column}' but it doesn't exist in CSV. "
                f"Available columns: {', '.join(headers)}"
            )
            return

        # Check for empty or falsy group keys
        empty_keys = 0
        falsy_keys = 0
        group_key_values = set()

        for i, row in enumerate(rows):
            key = row.get(group_by_column)
            if key == "" or key is None:
                empty_keys += 1
            elif not key:  # Falsy but not empty string or None (e.g., 0)
                falsy_keys += 1
            else:
                group_key_values.add(key)

        if empty_keys > 0:
            self.result.add_error(
                f"{empty_keys} row(s) have empty/missing value for group_by column '{group_by_column}' "
                "- these rows will be silently dropped!"
            )

        if falsy_keys > 0:
            self.result.add_error(
                f"{falsy_keys} row(s) have falsy (e.g., 0) value for group_by column '{group_by_column}' "
                "- these rows will be silently dropped!"
            )

        self.result.add_info(f"Found {len(group_key_values)} unique group keys in '{group_by_column}'")

        # Validate template references
        self._validate_template_references(template, headers, rows, group_by_column)

    def _validate_template_references(self, template: Any, headers: List[str], rows: List[Dict], group_by_column: str):
        """Recursively validate template column references."""
        referenced_columns = self._extract_column_references(template)

        # Check if referenced columns exist
        missing_columns = referenced_columns - set(headers)
        if missing_columns:
            self.result.add_error(
                f"Template references columns that don't exist in CSV: {', '.join(missing_columns)}"
            )

        # Check for data consistency issues (multiple rows with different values for direct mappings)
        if isinstance(template, dict):
            # Check if this level has group_by or collect
            has_group_by = "group_by" in template
            has_collect = "collect" in template

            if has_group_by:
                # Validate nested group_by column exists
                nested_group_by = template["group_by"]
                if nested_group_by not in headers:
                    self.result.add_error(
                        f"Template specifies nested group_by column '{nested_group_by}' "
                        f"but it doesn't exist in CSV"
                    )

                # Recursively validate nested template
                # The nested template will be applied AFTER grouping by nested_group_by
                nested_template = template.get("template", {})
                self._validate_template_references(nested_template, headers, rows, nested_group_by)

            elif not has_collect:
                # This is a direct mapping - check for data consistency
                self._check_direct_mapping_consistency(template, headers, rows, group_by_column)

    def _extract_column_references(self, template: Any) -> Set[str]:
        """Extract all {column_name} references from template."""
        columns = set()

        if isinstance(template, dict):
            for key, value in template.items():
                if key in ("group_by", "template", "collect"):
                    if key != "group_by":  # group_by value is a column name, not a reference
                        columns.update(self._extract_column_references(value))
                else:
                    columns.update(self._extract_column_references(value))

        elif isinstance(template, list):
            for item in template:
                columns.update(self._extract_column_references(item))

        elif isinstance(template, str):
            # Extract {column_name} pattern
            if template.startswith("{") and template.endswith("}"):
                columns.add(template[1:-1])

        return columns

    def _check_direct_mapping_consistency(self, template: Dict, _headers: List[str], rows: List[Dict], group_by_column: str):
        """Check if direct field mappings have consistent values within groups."""
        # Group rows by the group_by column
        grouped = defaultdict(list)
        for row in rows:
            key = row.get(group_by_column)
            if key:
                grouped[key].append(row)

        # For each group, check if direct mappings have consistent values
        inconsistent_fields = defaultdict(set)

        for _group_key, group_rows in grouped.items():
            if len(group_rows) <= 1:
                continue  # Single row groups are always consistent

            for field_name, field_value in template.items():
                if field_name in ("group_by", "template", "collect"):
                    continue

                # Skip nested objects/dicts - they have their own structure
                if isinstance(field_value, dict):
                    continue

                # Only check direct column references
                if isinstance(field_value, str) and field_value.startswith("{") and field_value.endswith("}"):
                    column_name = field_value[1:-1]

                    # Get all values for this column in this group
                    values = [row.get(column_name) for row in group_rows]
                    unique_values = set(values)

                    if len(unique_values) > 1:
                        inconsistent_fields[field_name].add(column_name)

        if inconsistent_fields:
            for field_name, columns in inconsistent_fields.items():
                self.result.add_error(
                    f"Template field '{field_name}' maps directly to column(s) {columns}, "
                    f"but multiple rows within the same '{group_by_column}' group have different values. "
                    f"Use 'collect' or nested 'group_by' to handle varying values."
                )

    def _suggest_config_structure(self, rows: List[Dict], headers: List[str]):
        """Suggest a config structure based on CSV analysis."""
        self.result.add_info("\n📝 Suggested config structure based on CSV analysis:")

        # Try to identify potential grouping columns (columns with repeated values)
        potential_group_columns = []
        for col in headers:
            values = [row.get(col) for row in rows]
            unique_count = len(set(values))
            total_count = len(values)

            # If less than 50% unique, likely a grouping column
            if unique_count < total_count * 0.5:
                potential_group_columns.append((col, unique_count))

        if potential_group_columns:
            self.result.add_info(f"  Potential group_by columns: {', '.join([f'{col} ({count} unique)' for col, count in potential_group_columns])}")
        else:
            self.result.add_info(f"  No obvious grouping columns detected. Consider using: {headers[0]}")


def main():
    """Main CLI entry point."""
    if len(sys.argv) < 2:
        print("Usage: python validate_csv.py <csv_file> [transform_file]")
        print("\nExamples:")
        print("  python validate_csv.py data.csv")
        print("  python validate_csv.py data.csv csv_transform.json")
        return 1

    csv_file = sys.argv[1]
    config_file = sys.argv[2] if len(sys.argv) > 2 else None

    validator = CSVValidator(csv_file, config_file)
    result = validator.validate()
    result.print_report()

    return 0 if result.is_valid() else 1


if __name__ == "__main__":
    exit(main())
