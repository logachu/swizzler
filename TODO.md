# Project TODOs

## Completed Enhancements

### ✅ 1. Date Format Conversion in CSV-to-JSON Transform (COMPLETED)

Added support in our CSV-to-JSON transform format that allows us to describe CSV columns with arbitrary date formats that we will convert to ISO-8601 Dates with optional timezone offset in our simulated PersonStore DB.

**Implementation:**

- Added `column_types` section to csv_transform.json format
- Supports user-friendly date format notation (e.g., "YYYY-MM-DD", "MM/DD/YYYY", "MM/DD/YYYY ZZZ")
- `input_format` is optional - auto-detects common formats if not specified
- `timezone` is optional - if not provided and not in date string, outputs ISO-8601 without timezone
- Supports timezone abbreviations in date strings (EST, PST, etc.)
- Converts dates to ISO-8601 format with or without timezone (e.g., "2025-11-23T00:00:00-05:00" or "2025-11-23T00:00:00")
- Updated batch_process.py with `convert_date_to_iso8601()` and `user_format_to_strftime()` functions

**Example:**

- Input CSV has dates like "11/23/2025" or "2025-11-23"
- Transform config specifies the input format which could be either "ISO-8601" or a date format string, e.g. "MM/DD/YYYY ZZZ" where MM is two digits for month, DD is two digits for day, YYYY is four digits for year and ZZZ is three letters for a timezone abbreviation. Another example is "YYYY-MM-DD" where month and day could be one or two digits including a leading zero, e.g. "03" for March, the third month.
- Output JSON stores dates in standardized ISO-8601 format with timezone it available (e.g., "2025-11-23T00:00:00-05:00")

```json
{
  "column_types": {
    "appointment_date": {
      "type": "date",
      "input_format": "YYYY-MM-DD",
      "timezone": "America/New_York"
    }
  }
}
```

### ✅ 2. Date Display Format in Card Configuration (COMPLETED)

Added support for displaying dates in user-friendly formats in card UI. The `format_date()` function was already implemented and works with both simple date strings and ISO-8601 formatted dates.

**Implementation:**

- `format_date(date_field, format_string)` function available in card templates
- Updated server.py to handle timezone-aware ISO-8601 dates
- `days_from_now()` and `days_after()` functions updated to support timezone-aware dates

**Example:**

```json
{
  "template": {
    "datetime": "{format_date($.date, '%b %d')} at {$.time}",
    "days_until": "{days_from_now($.date)}"
  }
}
```

### ✅ 3. Currency Parsing in CSV-to-JSON Transform (COMPLETED)

Added support in our CSV-to-JSON transform format that allows us to describe CSV columns containing numbers as currency amounts in dollars accepting optional dollar signs and decimal points.

**Implementation:**

- Added `convert_currency_to_numeric()` function in batch_process.py
- Updated `cleanse()` function to apply currency type conversion
- Supports all specified input formats and converts to standardized numeric values
- Configuration example: `{"column_types": {"amount": {"type": "currency"}}}`

**Supported input formats:**

- `23.4700` → 23.47
- `$23.47` → 23.47
- `$23` → 23.0
- `23` → 23.0
- `23.` → 23.0
- `.47` → 0.47
- `0.47` → 0.47
- `$0.47` → 0.47

**Output:** Standardized numeric format stored in JSON document (e.g., 23.47)

**Example:**

```json
{
  "column_types": {
    "copay_amount": {
      "type": "currency"
    }
  }
}
```

### ✅ 4. Currency Display Format in Card Configuration (COMPLETED)

Added a way to specify a display format for currency amounts in dollars in our card configuration. Shows only two decimal places to right of decimal. Shows comma as thousands separator.

**Implementation:**

- Added `currency()` function to `ComputeFunctions` class in server.py
- Updated `ExpressionParser` to recognize currency() function calls
- Formats numeric values with dollar sign, comma thousands separator, and exactly two decimal places
- Template usage: `{currency($.amount)}`

**Example use case:**

- Database stores: `1089.99` (numeric)
- Card config template: `{currency($.amount)}`
- UI displays: "$1,089.99"

**Example:**

```json
{
  "template": {
    "copay": "{currency($.costs.copay)}",
    "total": "{currency($.costs.total)}"
  }
}
```

## Future Enhancements

### 5. Interactive CSV Transform Configuration Tool

Create an interactive tool for creating the csv_transform.json files by showing an example input CSV, a csv_transform.json editor TextBox and the resulting JSON document Array output.

**Features:**

- **Input CSV viewer/editor**: Display or paste example CSV data
- **Transform config editor**: TextBox for editing csv_transform.json with syntax highlighting
- **Live output preview**: Real-time display of the resulting JSON output as the config is edited
- **Validation**: Highlight errors in the configuration or transformation process
- **Templates**: Provide common configuration patterns as starting points

**Benefits:**

- Reduces trial-and-error when creating new transformations
- Provides immediate feedback on configuration changes
- Helps users understand the relationship between CSV structure, config, and JSON output
- Makes the system more accessible to non-technical users

### 6. Tutorial Examples for Developer Onboarding

Create a comprehensive tutorial series that teaches the system to new developers through progressive, step-by-step examples.

**Tutorial Structure:**

- Start with simple examples and gradually introduce complexity
- Each tutorial builds on concepts from previous ones
- Cover both csv_transform.json format and JSON card configuration format
- Include working code, sample data, and expected outputs

**Proposed Tutorial Sequence:**

1. **Hello World**: Basic CSV to flat JSON
   - Simple one-to-one field mapping
   - Introduction to `{column_name}` syntax

2. **Nested Objects**: Creating hierarchical structures
   - Grouping related fields into nested objects
   - Understanding template structure

3. **Simple Arrays**: Using `collect` for one-to-many relationships
   - Collecting multiple rows into an array
   - When and why to use `collect`

4. **Grouping Data**: Using `group_by` for data organization
   - Creating separate objects from grouped rows
   - Understanding multi-level grouping

5. **Sorting Arrays**: Introducing the `sort_by` feature
   - Sorting by simple fields
   - Sorting by nested fields with dot notation
   - Different data types (numbers, dates, currency, strings)

6. **Complex Nested Structures**: Combining concepts
   - Multiple levels of nesting
   - Mixed arrays and objects
   - Real-world healthcare data example

7. **Card Configuration Basics**: Displaying data in UI
   - JSONPath expressions for data extraction
   - Card templates and sections
   - Linking PersonStore data to UI components

8. **Advanced Card Features**: Dynamic UI rendering
   - Conditional rendering
   - Compute functions: `len()`, `sum()`, `format_date()`, `days_from_now()`
   - Counting items: "You have {len($.prescriptions)} active prescriptions"
   - Summing values: "Total copay: ${sum($.procedures[*].costs.copay)}"
   - Date formatting and relative dates
   - Building complete card-based interfaces

**Benefits:**

- Reduces onboarding time for new developers
- Establishes best practices and patterns
- Serves as living documentation
- Provides reusable templates for common scenarios

### 7. Text Formatting in Templates

Add support for text formatting in card configuration templates to enable richer UI displays with bold text, links, and other formatting.

**Example use cases:**

- **Bold text**: Emphasize important information like warnings, status badges, or key values
- **Links**: Add clickable links to phone numbers, websites, or internal navigation
- **Other formatting**: Italics, underlines, colors for status indicators

**Potential syntax options:**

- Markdown-style: `**bold text**`, `[link text](url)`
- HTML-style: `<b>bold text</b>`, `<a href="url">link text</a>`
- Template functions: `{bold('text')}`, `{link('text', 'url')}`

**Example in templates:**

```json
{
  "templates": {
    "root": {
      "title": "**{$.medication_name}**",
      "pharmacy_contact": "[Call Pharmacy]({$.pharmacy.phone})",
      "warning": "**⚠️ Refill Needed**"
    }
  }
}
```

**Benefits:**

- Richer, more informative UI displays
- Better visual hierarchy in card layouts
- Actionable elements (clickable phone numbers, links)
- Consistent formatting across different data sources
