# Sorted Arrays Example

This example demonstrates the new `sort_by` capability for nested arrays in csv_transform.json configurations.

## Purpose

When transforming CSV data to nested JSON, you often want arrays to be sorted by specific fields. This example shows how to:
1. Sort arrays by a simple field (e.g., dates)
2. Sort arrays by a nested field using dot notation (e.g., `result.value`)

## Files

- **input.csv** - Lab results data with intentionally unsorted rows
- **csv_transform.json** - Configuration demonstrating the new `sort_by` syntax
- **expected_output_EPI789012__EHR_lab_results.json** - Expected sorted output for patient EPI789012
- **expected_output_EPI456789__EHR_lab_results.json** - Expected sorted output for patient EPI456789

## New Configuration Syntax

The `sort_by` configuration is added at the same level as `group_by` or `collect`:

```json
{
  "group_by": "lab_order_id",
  "sort_by": {
    "field": "order_date",
    "order": "desc"
  },
  "template": { ... }
}
```

Or for arrays created with `collect`:

```json
{
  "collect": [ ... ],
  "sort_by": {
    "field": "result.value",
    "order": "asc"
  }
}
```

### Configuration Properties

- **field**: The field name to sort by. Supports dot notation for nested fields (e.g., `result.value`)
- **order**: Sort direction, either `"asc"` (ascending) or `"desc"` (descending)

## Example Transformation

### Input CSV (excerpt)
```csv
EPI,lab_order_id,order_date,provider_name,test_code,test_name,result_value,...
EPI789012,LAB003,2025-08-15,Dr. Emily Rodriguez,TEST007,Hemoglobin,14.2,...
EPI789012,LAB001,2025-10-20,Dr. Sarah Johnson,TEST002,Glucose,118,...
EPI789012,LAB001,2025-10-20,Dr. Sarah Johnson,TEST001,Cholesterol,220,...
EPI789012,LAB002,2025-09-10,Dr. Michael Chen,TEST004,Creatinine,0.9,...
```

### Sorting Applied

1. **Lab orders** sorted by `order_date` (descending - most recent first):
   - LAB001 (2025-10-20)
   - LAB002 (2025-09-10)
   - LAB003 (2025-08-15)

2. **Tests within each lab order** sorted by `result.value` (ascending - lowest to highest):
   - LAB001: TEST003 (95), TEST002 (118), TEST001 (220)
   - LAB002: TEST004 (0.9), TEST008 (4.2), TEST006 (140)
   - LAB003: TEST005 (7.8), TEST007 (14.2), TEST009 (245)

## Key Features Demonstrated

1. **Two-level sorting**: Outer array (lab orders) sorted by date, inner arrays (tests) sorted by numeric values
2. **Nested field access**: Using dot notation `result.value` to sort by a field inside a nested object
3. **Numeric sorting**: String values like "220" and "95" should be sorted numerically, not lexicographically
4. **Date sorting**: ISO date strings sorted chronologically
5. **Multiple patients**: Shows sorting works independently for each patient's data
