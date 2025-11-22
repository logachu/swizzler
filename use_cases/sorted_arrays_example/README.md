# Sorted Arrays Example

This example demonstrates the new `sort_by` capability for nested arrays in csv_transform.json configurations.

## Purpose

When transforming CSV data to nested JSON, you often want arrays to be sorted by specific fields. This example shows how to:
1. Sort arrays by dates (ISO format strings)
2. Sort arrays by numeric values (with dot notation for nested fields)
3. Sort arrays by currency values (with $ symbols)
4. Sort arrays alphabetically by string fields

## Files

### Input Data
- **input.csv** - Lab results data with intentionally unsorted rows

### Configuration Variants
- **csv_transform.json** - Main example: sorts by date (descending) and numeric values (ascending)
- **csv_transform_by_cost.json** - Variant: sorts tests by cost (currency values, ascending)
- **csv_transform_by_name.json** - Variant: sorts tests by test name (alphabetically, ascending)

### Expected Outputs
- **expected_output_EPI789012__EHR_lab_results.json** - Main example output for patient EPI789012
- **expected_output_EPI456789__EHR_lab_results.json** - Main example output for patient EPI456789
- **expected_output_by_cost_EPI789012__EHR_lab_results.json** - Currency sorting output
- **expected_output_by_name_EPI789012__EHR_lab_results.json** - Alphabetical sorting output

## New Configuration Syntax

The `sort_by` configuration is added at the same level as `group_by` or `collect`:

```json
{
  "group_by": "lab_order_id",
  "sort_by": {
    "field": "order_date",
    "order": "descending"
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
- **order**: Sort direction. Accepts multiple formats:
  - Short form: `"asc"` (ascending) or `"desc"` (descending)
  - Long form: `"ascending"` or `"descending"`

## Example Transformations

### Input CSV (excerpt)
```csv
EPI,lab_order_id,order_date,provider_name,test_code,test_name,result_value,cost,...
EPI789012,LAB003,2025-08-15,Dr. Emily Rodriguez,TEST007,Hemoglobin,14.2,$45.00,...
EPI789012,LAB001,2025-10-20,Dr. Sarah Johnson,TEST002,Glucose,118,$125.00,...
EPI789012,LAB001,2025-10-20,Dr. Sarah Johnson,TEST001,Cholesterol,220,$89.99,...
EPI789012,LAB002,2025-09-10,Dr. Michael Chen,TEST004,Creatinine,0.9,$52.00,...
```

### Example 1: Date and Numeric Sorting (csv_transform.json)

**Configuration:**
```json
{
  "group_by": "lab_order_id",
  "sort_by": {
    "field": "order_date",
    "order": "descending"    // Long form - most recent first
  },
  "template": {
    "tests": {
      "collect": [...],
      "sort_by": {
        "field": "result.value",
        "order": "asc"         // Short form - lowest to highest
      }
    }
  }
}
```

**Sorting Applied:**
1. **Lab orders** sorted by `order_date` (descending - most recent first):
   - LAB001 (2025-10-20)
   - LAB002 (2025-09-10)
   - LAB003 (2025-08-15)

2. **Tests within each lab order** sorted by `result.value` (ascending - lowest to highest):
   - LAB001: TEST003 (95), TEST002 (118), TEST001 (220)
   - LAB002: TEST004 (0.9), TEST008 (4.2), TEST006 (140)
   - LAB003: TEST005 (7.8), TEST007 (14.2), TEST009 (245)

### Example 2: Currency Sorting (csv_transform_by_cost.json)

**Configuration:**
```json
{
  "tests": {
    "collect": [...],
    "sort_by": {
      "field": "cost",
      "order": "ascending"     // Long form - cheapest first
    }
  }
}
```

**Sorting Applied:**
Tests sorted by `cost` (ascending - cheapest to most expensive):
- LAB001: $89.99, $95.50, $125.00
- LAB002: $42.50, $44.25, $52.00
- LAB003: $35.50, $38.75, $45.00

### Example 3: Alphabetical Sorting (csv_transform_by_name.json)

**Configuration:**
```json
{
  "tests": {
    "collect": [...],
    "sort_by": {
      "field": "test_name",
      "order": "ascending"     // Long form - A to Z
    }
  }
}
```

**Sorting Applied:**
Tests sorted by `test_name` (alphabetically ascending):
- LAB001: Cholesterol, Glucose, Triglycerides
- LAB002: Creatinine, Potassium, Sodium
- LAB003: Hemoglobin, Platelet Count, White Blood Cell Count

## Key Features Demonstrated

1. **Two-level sorting**: Outer array (lab orders) sorted by date, inner arrays (tests) sorted by various criteria
2. **Nested field access**: Using dot notation `result.value` to sort by a field inside a nested object
3. **Multiple data types**:
   - **Dates**: ISO date strings sorted chronologically
   - **Numbers**: String values like "220" and "95" sorted numerically, not lexicographically
   - **Currency**: Values with $ symbols like "$89.99" sorted by numeric value
   - **Strings**: Test names sorted alphabetically
4. **Flexible syntax**: Both short forms (`"asc"`, `"desc"`) and long forms (`"ascending"`, `"descending"`) supported
5. **Multiple patients**: Shows sorting works independently for each patient's data
6. **Multiple sort configurations**: Different configuration files demonstrate various sorting approaches on the same dataset
