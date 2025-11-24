# Column Type Conversions

The `column_types` configuration allows you to specify how CSV columns should be converted during processing.

## Supported Types

### 1. **string** (default)
Keeps the value as a string. This is the default if no type is specified.

```json
{
  "column_types": {
    "patient_name": "string"
  }
}
```

**Examples:**
- `"John Doe"` → `"John Doe"`
- `"123"` → `"123"` (kept as string)

---

### 2. **int**
Converts string values to integers. Handles floating point strings by truncating.

```json
{
  "column_types": {
    "age": "int",
    "count": "int"
  }
}
```

**Examples:**
- `"42"` → `42`
- `"3.7"` → `3` (truncates decimal)
- `""` → `0` (empty becomes 0)
- `"abc"` → `0` (invalid values become 0 with warning)

---

### 3. **float**
Converts string values to floating point numbers.

```json
{
  "column_types": {
    "height": "float",
    "weight": "float"
  }
}
```

**Examples:**
- `"5.9"` → `5.9`
- `"42"` → `42.0`
- `""` → `0.0`
- `"abc"` → `0.0` (invalid values become 0.0 with warning)

---

### 4. **bool**
Converts string values to booleans.

```json
{
  "column_types": {
    "is_active": "bool",
    "has_insurance": "bool"
  }
}
```

**True values:** `"true"`, `"True"`, `"TRUE"`, `"yes"`, `"y"`, `"1"`
**False values:** `"false"`, `"False"`, `"FALSE"`, `"no"`, `"n"`, `"0"`, `""` (empty)

**Examples:**
- `"true"` → `true`
- `"yes"` → `true`
- `"1"` → `true`
- `"false"` → `false`
- `"no"` → `false`
- `""` → `false`

---

### 5. **null**
Converts empty or null-representing values to `null` in JSON. Non-empty values are kept as strings.

```json
{
  "column_types": {
    "notes": "null",
    "comments": "null"
  }
}
```

**Null representations:** `""` (empty), `"null"`, `"NULL"`, `"None"`, `"N/A"`, `"na"`

**Examples:**
- `""` → `null`
- `"N/A"` → `null`
- `"null"` → `null`
- `"Some notes"` → `"Some notes"` (kept as string)

---

### 6. **currency**
Converts currency strings to numeric float values. Removes dollar signs and commas.

```json
{
  "column_types": {
    "amount": {
      "type": "currency"
    }
  }
}
```

**Examples:**
- `"$23.47"` → `23.47`
- `"$1,089.99"` → `1089.99`
- `"23"` → `23.0`
- `".47"` → `0.47`
- `"$0.47"` → `0.47`

---

### 7. **date**
Converts date strings to ISO-8601 format. Supports custom input formats and optional timezones.

```json
{
  "column_types": {
    "appointment_date": {
      "type": "date",
      "input_format": "YYYY-MM-DD"
    },
    "birth_date": {
      "type": "date",
      "input_format": "MM/DD/YYYY"
    }
  }
}
```

**Supported input_format values:**
- `"YYYY-MM-DD"` - e.g., 2025-11-23
- `"MM/DD/YYYY"` - e.g., 11/23/2025
- `"DD/MM/YYYY"` - e.g., 23/11/2025
- `"ISO-8601"` - for ISO-8601 formatted dates
- `null` - auto-detect common formats

**Optional timezone parameter:**
- `"timezone"`: Timezone name (e.g., `"America/New_York"`)
- **Note**: Omit timezone unless you're certain all dates in the column are from the same timezone

**Examples:**
- Input: `"2025-11-23"` with format `"YYYY-MM-DD"` (no timezone)
  - Output: `"2025-11-23T00:00:00"`

- Input: `"2025-11-23"` with format `"YYYY-MM-DD"` and timezone `"America/New_York"`
  - Output: `"2025-11-23T00:00:00-05:00"`

- Input: `"11/23/2025"` with format `"MM/DD/YYYY"` (no timezone)
  - Output: `"2025-11-23T00:00:00"`

---

## Shorthand vs Object Format

Simple types can use shorthand:
```json
{
  "column_types": {
    "age": "int",
    "is_active": "bool"
  }
}
```

Complex types (like date, currency with options) use object format:
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

---

## Complete Example

```json
{
  "@attribute": {
    "name": "_EHR/patient_data",
    "group_by": "EPI",
    "column_types": {
      "patient_name": "string",
      "age": "int",
      "height": "float",
      "weight": "float",
      "is_smoker": "bool",
      "notes": "null",
      "copay": {
        "type": "currency"
      },
      "appointment_date": {
        "type": "date",
        "input_format": "YYYY-MM-DD",
        "timezone": "America/New_York"
      }
    },
    "@array": {
      "group_by": "visit_id",
      "@item": {
        "visit_id": "{visit_id}",
        "date": "{appointment_date}",
        "patient": "{patient_name}",
        "age": "{age}",
        "height": "{height}",
        "weight": "{weight}",
        "is_smoker": "{is_smoker}",
        "copay": "{copay}",
        "notes": "{notes}"
      }
    }
  }
}
```

**CSV Input:**
```csv
EPI,visit_id,patient_name,age,height,weight,is_smoker,copay,appointment_date,notes
EPI001,V001,John Doe,42,5.9,185.5,yes,$25.00,2025-11-23,Patient has allergies
EPI001,V002,John Doe,42,5.9,180.0,no,$30.50,2025-12-01,
```

**JSON Output:**
```json
[
  {
    "visit_id": "V001",
    "date": "2025-11-23T00:00:00-05:00",
    "patient": "John Doe",
    "age": 42,
    "height": 5.9,
    "weight": 185.5,
    "is_smoker": true,
    "copay": 25.0,
    "notes": "Patient has allergies"
  },
  {
    "visit_id": "V002",
    "date": "2025-12-01T00:00:00-05:00",
    "patient": "John Doe",
    "age": 42,
    "height": 5.9,
    "weight": 180.0,
    "is_smoker": false,
    "copay": 30.5,
    "notes": null
  }
]
```
