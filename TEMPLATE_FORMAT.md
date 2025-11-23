# Template Format Documentation

## Overview

The template system enables flexible, configuration-driven presentation and display without requiring code changes. This system supports adding new use cases and CSV formats by creating card and section configuration files with rich conditional logic and formatting.

The template format is inspired by [Terrence Parr's StringTemplate](https://github.com/antlr/stringtemplate4/blob/master/doc/motivation.md) and implements the four canonical operations necessary for expressive template-based rendering. Based on years of experience with a website templating system and eventually in the code-generation backend used by [ANTLR](https://pragprog.com/titles/tpantlr2/the-definitive-antlr-4-reference/) capable of creating compilers for modern programming languages and interpreters, Parr determined there are only four operations necessary:

1. **Attribute Reference** - Access data fields from JSON using JSON Path syntax
2. **Template Reference** - Templates can refer to other templates and pass arguments allowing reuse  of templates like function calls.
3. **Conditional Include** - Show/hide content based on conditions (IF and SWITCH statements)
4. **Template Application to Lists** - Apply a template to each item in an array



## Core Operations

### 1. Attribute Reference

Access data from the current context using JSONPath expressions.

**Example:**

```json
{
  ...Other Card or Card Collection Configuration
  "templates": {
    "root": {
      "title": "{$.medication_name}",
      "dosage": "{$.dosage} - {$.frequency}",
      "prescriber": "{$.prescriber.name}, {$.prescriber.specialty}",
      "refill_count": "{len($.refills)}",
      "days_until": "{days_from_now($.appointment_date)}",
      "days_overdue": "{days_after($.due_date)}"
    }
  }
}
```

**JSONPath Syntax:**

- `{$.field}` - Access top-level field
- `{$.nested.field}` - Access nested field
- `{$.array} - Access the full array of elements
- `{$.array[0]}` - Access array element by index
- `{$.array[-1]}` - Access last array element

NOTE: array slice syntax could be added as a future enhancement, but I couldnt' think of a use case for it.

**Supported Functions:**
- `len(array)` - Count items in an array
- `sum(array.numericField)` - Sum numeric values
- `format_date(date, format)` - Format dates (e.g., `'%b %d, %Y'`)
- `days_from_now(date)` - Calculate days until/since a date (returns string like "5 days from now")
- `days_after(date)` - Calculate days after a date (returns number: positive if overdue, negative if upcoming, 0 if today)

NOTE: could add other date-related functions that resolve to hours, weeks, months, years, etc. or a generic time_from_now('days', "01-01-1970")

### 2. Template Reference

The "templates" object always contains a least one "root" template which may reference additional named templates `@template_name`. The templates should form
a tree of references, however recursive references should be possible. There are use cases for recursion when generating code, but I haven't thought of use cases
for Praia card and card collection templates. Reference cycles must be avoided. We can check for this in code, but we don't want to do this every time we evaluate a template
so we should have some validation script when we check in card or card collection config files.

**Basic Template Reference:**

```json
{
  "templates": {
    "root": {
      "title": "{$.medication_name}",
      "description": "@prescriber_info\n@medication_status"
    },
    "prescriber_info": "Prescribed by {$.prescriber.name}, {$.prescriber.specialty}",
    "medication_status": "{$.status}"
  }
}
```

**Parameterized Templates:**

Templates can accept parameters. Here 'label' and 'amount' are template parameters:

```json
{
  "templates": {
    "root": {
      "copay": "@currency('Copay', $.costs.copay)",
      "deductible": "@currency('Deductible', $.costs.deductible)",
      "total": "@currency('Total', $.costs.total)"
    },
    "currency(label, amount)": "{label}: {format_currency(amount)}"
  }
}
```

**Nested Template References:**

Templates can reference other templates. Here "root" refers to "full_medication_info" which refers to "status_badge"

```json
{
  "templates": {
    "root": {
      "display": "@full_medication_info"
    },
    "full_medication_info": "{$.medication_name} - @status_badge",
    "status_badge": {
      "condition": "$.status == 'active'",
      "if_true": "✓ Active",
      "if_false": "✗ Inactive"
    }
  }
}
```

### 3. Conditional Include

Show different content based on conditions. Supports simple if/else and multi-condition (if/elif/else) patterns.

**Simple Conditional:**

```json
{
  "templates": {
    "root": {
      "title": "Payment Status",
      "description": "@payment_status" 
    },
    "payment_status": {
      "condition": "$.amount_due > 0",
      "if_true": "Amount due: ${$.amount_due}",
      "if_false": "All bills are paid ✓"
    }
  }
}
```

**Optional Conditional** (omit field if condition is false):

```json
{
  "templates": {
    "root": {
      "title": "{$.medication_name}",
      "warning": "@low_refill_warning"
    },
    "low_refill_warning": {
      "condition": "len($.refills) < 2",
      "if_true": "⚠️ Running low - call prescriber"
    }
  }
}
```

**Multi-Condition (switch/case or if/elif/else chains):**

```json
{
  "templates": {
    "root": {
      "risk_level": "@risk_indicator"
    },
    "risk_indicator": {
      "conditions": [
        {
          "when": "$.risk_score >= 8",
          "show": "🔴 High Risk - Score: {$.risk_score}/10"
        },
        {
          "when": "$.risk_score >= 5",
          "show": "🟡 Moderate Risk - Score: {$.risk_score}/10"
        },
        {
          "when": "$.risk_score >= 0",
          "show": "🟢 Low Risk - Score: {$.risk_score}/10"
        }
      ],
      "default": "Risk level unknown"
    }
  }
}
```

**Conditional Expressions:**

Conditions support standard comparison and logical operators:

- **Comparison:** `==`, `!=`, `>`, `<`, `>=`, `<=`
- **Logical:** `&&` (and), `||` (or), `!` (not)
- **Functions:** Can use any function like `len()`, `sum()`, `days_from_now()`

Examples:
```
"condition": "$.amount > 0"
"condition": "$.status == 'active'"
"condition": "len($.refills) < 2"
"condition": "days_from_now($.date) <= 7"
"condition": "$.amount_due > 0 && $.insurance_pending > 0"
```

### 4. Template Application to Lists

Apply a template to each element in an array using the pipe operator `|`.

**Basic List Application:**

```json
{
  "templates": {
    "root": {
      "title": "Procedures:",
      "description": "{$.procedures|@procedure_display}"
    },
    "procedure_display": "• {$.name} - {$.status}\n"
  }
}
```

This transforms:

```json
{
  "procedures": [
    {"name": "Blood Test", "status": "completed"},
    {"name": "X-Ray", "status": "scheduled"}
  ]
}
```

Into a rendered list:

```
Procedures:
• Blood Test - completed
• X-Ray - scheduled
```

**With Custom Separator:**

```json
{
  "templates": {
    "root": {
      "procedure_list": "{$.procedures|@procedure_line|separator=', '}"
    },
    "procedure_line": "{$.name}"
  }
}
```

Output: `Blood Test, X-Ray`

**With Line Breaks:**

```json
{
  "templates": {
    "root": {
      "billing_items": "{$.items|@line_item|separator='\n'}"
    },
    "line_item": "{$.description}: ${$.amount}"
  }
}
```

**Complex List Templates:**

List templates can use conditionals and nested references:

```json
{
  "templates": {
    "root": {
      "medications": "{$.medications|@medication_item}"
    },
    "medication_item": "{$.medication_name} - @refill_status",
    "refill_status": {
      "condition": "len($.refills) > 0",
      "if_true": "{len($.refills)} refills",
      "if_false": "No refills"
    }
  }
}
```

## Complete Examples

### Example 1: Medication Card

```json
{
  "attribute": "_EHR/prescriptions",
  "foreach": "$[*]",
  "filter_by": { "field": "status", "value": "active" },
  "templates": {
    "root": {
      "title": "{$.medication_name}",
      "subtitle": "{$.dosage} - {$.frequency}",
      "prescriber": "@prescriber_info",
      "status": "@medication_status",
      "refills": "@refill_message",
      "?last_refill_date": "{format_date($.refills[-1].refill_date, '%b %d, %Y')}"
    },
    "prescriber_info": "Prescribed by {$.prescriber.name}, {$.prescriber.specialty}",
    "medication_status": {
      "condition": "$.status == 'active'",
      "if_true": "✓ Active",
      "if_false": "Discontinued {format_date($.end_date, '%b %Y')}"
    },
    "refill_message": {
      "condition": "len($.refills) < 2",
      "if_true": "⚠️ Running low - call prescriber",
      "if_false": "{len($.refills)} refills remaining"
    }
  }
}
```

### Example 2: Billing Card with Parameterized Templates

```json
{
  "attribute": "_EHR/billing",
  "foreach": "$[*]",
  "templates": {
    "root": {
      "title": "Medical Bill - {$.provider_name}",
      "status": "@payment_status",
      "copay": "@currency($.costs.copay, 'Copay')",
      "deductible": "@currency($.costs.deductible, 'Deductible')",
      "total": "@currency($.costs.total, 'Total Estimate')",
      "line_items": "{$.items|@line_item|separator='\n'}",
      "?payment_plan": "@payment_plan_info"
    },
    "currency(amount, label)": "{label}: ${amount}",
    "payment_status": {
      "conditions": [
        {
          "when": "$.amount_due > 100",
          "show": "🔴 High balance - payment plan available"
        },
        {
          "when": "$.amount_due > 0",
          "show": "💵 Amount due: ${$.amount_due}"
        }
      ],
      "default": "✓ All bills paid"
    },
    "line_item": "{$.description}: ${$.amount}",
    "payment_plan_info": {
      "condition": "$.costs.total > 500",
      "if_true": "Payment plans available - speak to financial counselor"
    }
  }
}
```

### Example 3: Appointment Card with Date Logic

```json
{
  "attribute": "_EHR/appointments",
  "foreach": "$[*]",
  "templates": {
    "root": {
      "title": "{$.provider.name}",
      "subtitle": "{$.provider.specialty}",
      "datetime": "{format_date($.date, '%b %d')} at {$.time}",
      "location": "{$.location}",
      "status_message": "@appointment_status",
      "procedures": "{$.procedures|@procedure_display|separator=', '}",
      "?preparation": "@prep_instructions"
    },
    "appointment_status": {
      "conditions": [
        {
          "when": "days_from_now($.date) < 0",
          "show": "Past appointment"
        },
        {
          "when": "days_from_now($.date) == 0",
          "show": "🔔 Today!"
        },
        {
          "when": "days_from_now($.date) < 7",
          "show": "⏰ Upcoming in {days_from_now($.date)} days"
        }
      ],
      "default": "Scheduled for {format_date($.date, '%b %d')}"
    },
    "procedure_display": "{$.procedure_name}",
    "prep_instructions": {
      "condition": "$.requires_fasting == true",
      "if_true": "⚠️ Fasting required - no food 8 hours before"
    }
  }
}
```

## Syntax Reference

### Template Structure

```json
{
  "attribute": "_EHR/cohorts",
  "foreach": "...",
  "templates": {
    "root": { ... },
    "template_name": "...",
    "parameterized_template(param1, param2)": "..."
  }
}
```

### Key Syntax Elements

| Element | Syntax | Example |
|---------|--------|---------|
| **Attribute reference** | `{$.field}` or `{column}` | `{$.medication_name}` |
| **Template reference** | `@template_name` | `@prescriber_info` |
| **Parameterized call** | `@template(arg1, arg2)` | `@currency($.amount, 'Total')` |
| **List application** | `{$.array\|@template}` | `{$.items\|@line_item}` |
| **With separator** | `{$.array\|@template\|separator='x'}` | `{$.items\|@line\|separator='\n'}` |
| **Optional field** | `?field_name` | `?insurance_info` |
| **Function call** | `{function(arg)}` | `{format_date($.date, '%b %d')}` |
| **Parameter reference** | `{param_name}` | In template body: `{amount}` |

### Conditional Syntax

**Simple conditional:**
```json
"template_name": {
  "condition": "expression",
  "if_true": "template when true",
  "if_false": "template when false"
}
```

**Optional conditional** (no `if_false`):
```json
"template_name": {
  "condition": "expression",
  "if_true": "template when true"
}
```

**Multi-condition:**
```json
"template_name": {
  "conditions": [
    {"when": "expression1", "show": "template1"},
    {"when": "expression2", "show": "template2"}
  ],
  "default": "default template"
}
```

## Rules and Constraints

1. **Root Template:**
   - Must have exactly one template named `"root"`
   - Root template cannot have parameters
   - No other template can reference `@root`

2. **Template References:**
   - All `@template_name` references must exist in the templates object
   - Templates can reference other templates (nested references)
   - No circular references allowed

3. **Parameters:**
   - Defined in template name: `"template(param1, param2)"`
   - Referenced in template body without `$`: `{param1}`, `{param2}`
   - Passed when calling: `@template($.field, 'literal')`

4. **JSONPath:**
   - Use `$.` prefix to access current data context
   - Supports nested access: `$.field.subfield`
   - Supports array access: `$.array[0]`, `$.array[-1]`

5. **Optional Fields:**
   - Prefix field name with `?` in root/parent template
   - Field is omitted if value is falsy (empty, null, false, 0)
