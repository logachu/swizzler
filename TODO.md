# Project TODOs

## Future Enhancements

### 1. Date Format Conversion in CSV-to-JSON Transform
Add support in our CSV-to-JSON transform format that allows us to describe CSV columns with arbitrary date formats that we will convert to ISO-8601 Dates with timezone offset in our simulated PersonStore DB.

**Example use case:**
- Input CSV has dates like "11/23/2025" or "Nov 23, 2025"
- Transform config specifies the input format
- Output JSON stores dates in standardized ISO-8601 format with timezone (e.g., "2025-11-23T00:00:00-05:00")

### 2. Date Display Format in Card Configuration
Add a way to specify a display format for dates in our card configuration to convert ISO-8601 Dates in our database to user-friendly formats for display in card UI.

**Example use case:**
- Database stores: "2025-11-23T00:00:00-05:00"
- Card config specifies format: "MMM DD, YYYY" or "11/23/2025"
- UI displays: "Nov 23, 2025" or "11/23/2025"

### 3. Currency Parsing in CSV-to-JSON Transform
Add support in our CSV-to-JSON transform format that allows us to describe CSV columns with numbers as currency amounts in dollars accepting optional dollar signs and decimal points.

**Supported input formats:**
- `23.47`
- `$23.47`
- `$23`
- `23`
- `23.`
- `.47`
- `0.47`
- `$0.47`

**Output:** Standardized numeric format or currency object in JSON

### 4. Currency Display Format in Card Configuration
Add a way to specify a display format for currency amounts in dollars in our card configuration.

**Example use case:**
- Database stores: `89.99` (numeric)
- Card config specifies format: "currency-usd"
- UI displays: "$89.99"

**Optional enhancements:**
- Support for different currency symbols
- Configurable decimal places
- Thousands separators
- Negative value formatting (e.g., "($10.00)" vs "-$10.00")

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
   - Compute functions: `len()`, `sum()`, `format_date()`, `days_from_now()`, `days_after()`
   - Counting items: "You have {len($.prescriptions)} active prescriptions"
   - Summing values: "Total copay: ${sum($.procedures[*].costs.copay)}"
   - Date calculations: "You are {days_after($.dueDate)} days overdue"
   - Date formatting and relative dates
   - Building complete card-based interfaces

**Benefits:**
- Reduces onboarding time for new developers
- Establishes best practices and patterns
- Serves as living documentation
- Provides reusable templates for common scenarios

---

## Notes

These enhancements would improve the flexibility of the system for handling real-world healthcare data where dates and currency values appear in various formats across different data sources.
