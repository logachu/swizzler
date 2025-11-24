# CSV Transform Schema Reference

This document provides the definitive reference for the `csv_transform.json` configuration format.

## Overview

The CSV transform schema uses an `@`-prefixed format to clearly distinguish processing directives from output field names.

**Key Principle:** Keys with `@` prefix are processing directives (not in output). Keys without `@` are output field names.

## Schema Structure

```jsonc
{
  "@attribute": {
    "name": "attribute_name",
    "group_by": "column_name",
    "column_types": { /* ... */ },
    "@array": { /* ... */ }  // OR "@object": { /* ... */ }
  }
}
```

## Top Level: `@attribute`

Contains metadata about the attribute and the root template.

| Field | Required | Description |
|-------|----------|-------------|
| `name` | Yes | PersonStore attribute name (format: `namespace/attribute`) |
| `group_by` | Yes | CSV column to group rows by. Creates one JSON file per unique value. |
| `column_types` | No | Type conversion specifications (see [Column Types](#column-types)) |
| `@array` | Either this or `@object` | Root template that produces an array |
| `@object` | Either this or `@array` | Root template that produces a single object |

**Example:**
```json
{
  "@attribute": {
    "name": "_EHR/appointments",
    "group_by": "EPI",
    "column_types": { /* ... */ },
    "@array": { /* ... */ }
  }
}
```

## Arrays: `@array`

Defines an array of objects. Must contain exactly one of: `group_by` or `collect`.

| Field | Required | Description |
|-------|----------|-------------|
| `group_by` | Either this or `collect` | Column to group by. Creates one object per unique value. |
| `collect` | Either this or `group_by` | Set to `true` to collect all rows as array items (no deduplication). |
| `sort_by` | No | Sorting configuration (see [Sorting](#sorting)) |
| `@item` | Yes | Template for each array item |

**Example - Group By:**
```json
{
  "@array": {
    "group_by": "appointment_id",
    "sort_by": {
      "field": "date",
      "order": "ascending"
    },
    "@item": {
      "id": "{appointment_id}",
      "date": "{appointment_date}"
    }
  }
}
```

**Example - Collect:**
```json
{
  "@array": {
    "collect": true,
    "sort_by": {
      "field": "procedure_name",
      "order": "ascending"
    },
    "@item": {
      "code": "{procedure_code}",
      "name": "{procedure_name}"
    }
  }
}
```

## Objects: `@item` and `@object`

Defines the structure of an object.

- **`@item`**: Used inside `@array` to define each array element
- **`@object`**: Used as root template when output is a single object

**Structure:**
- Keys without `@` prefix become output field names
- Values can be:
  - `"{column_name}"` - Template substitution (replaced with CSV column value)
  - Nested objects
  - Nested `@array` definitions

**Example:**
```json
{
  "@item": {
    "appointment_id": "{appointment_id}",
    "date": "{appointment_date}",
    "provider": {
      "name": "{provider_name}",
      "specialty": "{provider_specialty}"
    },
    "procedures": {
      "@array": {
        "collect": true,
        "@item": {
          "code": "{procedure_code}",
          "name": "{procedure_name}"
        }
      }
    }
  }
}
```

## Sorting

Optional sorting configuration for arrays.

| Field | Required | Description |
|-------|----------|-------------|
| `field` | Yes | Field name to sort by. Supports nested paths (e.g., `"result.value"`). |
| `order` | Yes | Sort order: `"ascending"` or `"descending"` (can use `"asc"` or `"desc"`) |

**Example:**
```json
{
  "sort_by": {
    "field": "appointment_date",
    "order": "ascending"
  }
}
```

**Nested Field Example:**
```json
{
  "sort_by": {
    "field": "result.value",
    "order": "desc"
  }
}
```

## Column Types

Specify type conversions for CSV columns. See [COLUMN_TYPES.md](COLUMN_TYPES.md) for complete details.

**Simple Format:**
```json
{
  "column_types": {
    "age": "int",
    "is_active": "bool",
    "height": "float"
  }
}
```

**Complex Format (with options):**
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

**Supported Types:**
- `string` - Keep as string (default)
- `int` - Convert to integer
- `float` - Convert to float
- `bool` - Convert to boolean
- `null` - Convert empty/N/A to JSON null
- `currency` - Remove $, commas, convert to number
- `date` - Convert to ISO-8601 (requires `input_format`, optional `timezone`)

## Template Substitution

Use `{column_name}` syntax to substitute CSV column values into the output.

**Rules:**
- Column name must match CSV header exactly (case-sensitive)
- Braces indicate substitution: `{column_name}` → value from that column
- Without braces: used as literal value or configuration directive

**Examples:**

| Template | CSV Value | Output |
|----------|-----------|--------|
| `"{patient_name}"` | `"John Doe"` | `"John Doe"` |
| `"{age}"` (with `"age": "int"` type) | `"42"` | `42` |
| `"{is_active}"` (with `"is_active": "bool"` type) | `"true"` | `true` |

## Complete Example

**CSV Input:**
```csv
EPI,appointment_id,appointment_date,provider_name,provider_specialty,procedure_code,procedure_name
EPI001,APT001,2025-11-15,Dr. Johnson,Cardiology,PROC001,EKG Test
EPI001,APT001,2025-11-15,Dr. Johnson,Cardiology,PROC002,Blood Test
EPI001,APT002,2025-11-20,Dr. Chen,Orthopedics,PROC003,X-Ray
```

**Transform Config:**
```json
{
  "@attribute": {
    "name": "_EHR/appointments",
    "group_by": "EPI",
    "column_types": {
      "appointment_date": {
        "type": "date",
        "input_format": "YYYY-MM-DD",
        "timezone": "America/New_York"
      }
    },
    "@array": {
      "group_by": "appointment_id",
      "sort_by": {
        "field": "appointment_date",
        "order": "ascending"
      },
      "@item": {
        "appointment_id": "{appointment_id}",
        "date": "{appointment_date}",
        "provider": {
          "name": "{provider_name}",
          "specialty": "{provider_specialty}"
        },
        "procedures": {
          "@array": {
            "collect": true,
            "@item": {
              "code": "{procedure_code}",
              "name": "{procedure_name}"
            }
          }
        }
      }
    }
  }
}
```

**JSON Output (`EPI001__EHR_appointments.json`):**
```json
[
  {
    "appointment_id": "APT001",
    "date": "2025-11-15T00:00:00-05:00",
    "provider": {
      "name": "Dr. Johnson",
      "specialty": "Cardiology"
    },
    "procedures": [
      {
        "code": "PROC001",
        "name": "EKG Test"
      },
      {
        "code": "PROC002",
        "name": "Blood Test"
      }
    ]
  },
  {
    "appointment_id": "APT002",
    "date": "2025-11-20T00:00:00-05:00",
    "provider": {
      "name": "Dr. Chen",
      "specialty": "Orthopedics"
    },
    "procedures": [
      {
        "code": "PROC003",
        "name": "X-Ray"
      }
    ]
  }
]
```

## How It Works

1. **Load & Cleanse**: CSV is loaded, type conversions applied per `column_types`
2. **Group by Attribute**: Rows grouped by `@attribute.group_by` (e.g., `EPI`)
3. **Apply Template**: For each group:
   - If `@array` with `group_by`: Subgroup rows and create array of objects
   - If `@array` with `collect`: Create array item for each row
   - If `@object`: Create single object
4. **Substitute Values**: Replace `{column_name}` with actual values
5. **Sort**: Apply `sort_by` if specified
6. **Output**: Write JSON file per top-level group

## Common Patterns

### Pattern 1: Array of Grouped Objects with Nested Arrays

**Use Case:** Appointments with multiple procedures

```json
{
  "@array": {
    "group_by": "appointment_id",
    "@item": {
      "appointment_id": "{appointment_id}",
      "procedures": {
        "@array": {
          "collect": true,
          "@item": {
            "name": "{procedure_name}"
          }
        }
      }
    }
  }
}
```

### Pattern 2: Single Object with Collected Array

**Use Case:** Patient profile with list of items

```json
{
  "@object": {
    "patient_name": "{patient_name}",
    "items": {
      "@array": {
        "collect": true,
        "@item": {
          "item": "{item}",
          "amount": "{amount}"
        }
      }
    }
  }
}
```

### Pattern 3: Sorted Array

**Use Case:** Lab results sorted by date

```json
{
  "@array": {
    "group_by": "lab_order_id",
    "sort_by": {
      "field": "order_date",
      "order": "descending"
    },
    "@item": {
      "order_date": "{order_date}",
      "test_name": "{test_name}"
    }
  }
}
```
