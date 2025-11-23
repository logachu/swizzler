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

---

## Notes

These enhancements would improve the flexibility of the system for handling real-world healthcare data where dates and currency values appear in various formats across different data sources.
