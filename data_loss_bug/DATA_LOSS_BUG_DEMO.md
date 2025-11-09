# Data Loss Bug Demonstration

## The Problem

When a template at the top level (after `group_by`) maps fields directly WITHOUT using `collect` or another `group_by`, the code in [batch_process.py:166](../batch_process.py#L166) only uses the **first row** from the grouped data to populate field values.

## Code Location

```python
# batch_process.py lines 165-170
result = {}
row = data_rows[0]  # ⚠️ ONLY USES FIRST ROW!
for key, value in tmpl.items():
    if key in ("group_by", "template"):
        continue
    result[key] = build(value, data_rows) if isinstance(value, dict) else pull(row, value)
```

## Input Data

**test_data_loss.csv:**
```csv
patient_id,visit_date,diagnosis,severity
PAT001,2025-11-01,Hypertension,Moderate
PAT001,2025-11-01,Diabetes,Severe
PAT001,2025-11-01,Arthritis,Mild
```

We have **3 rows** for patient PAT001 with different diagnoses.

---

## Scenario 1: Buggy Config (Data Loss)

**test_config_bad.json:**
```json
{
  "attribute": {
    "name": "medical_visit",
    "group_by": "patient_id"
  },
  "template": {
    "visit_date": "{visit_date}",
    "primary_diagnosis": "{diagnosis}",
    "severity_level": "{severity}"
  }
}
```

### What Happens:
1. Groups 3 rows by `patient_id` → all 3 rows go into PAT001 group
2. Applies template to the group
3. **Uses only row[0]** to populate `diagnosis` and `severity`
4. **Loses the other 2 diagnoses!**

### Actual Output:
**test_output/PAT001_medical_visit.json:**
```json
{
  "visit_date": "2025-11-01",
  "primary_diagnosis": "Hypertension",
  "severity_level": "Moderate"
}
```

### Missing Data:
- ❌ Diabetes (Severe) - LOST
- ❌ Arthritis (Mild) - LOST

---

## Scenario 2: Correct Config (No Data Loss)

**test_config_good.json:**
```json
{
  "attribute": {
    "name": "medical_visit_fixed",
    "group_by": "patient_id"
  },
  "template": {
    "visit_date": "{visit_date}",
    "diagnoses": {
      "collect": [
        {
          "name": "{diagnosis}",
          "severity": "{severity}"
        }
      ]
    }
  }
}
```

### What Happens:
1. Groups 3 rows by `patient_id`
2. Applies template with `collect` directive
3. **Collects ALL rows** into the diagnoses array
4. **No data loss!**

### Actual Output:
**test_output/PAT001_medical_visit_fixed.json:**
```json
{
  "visit_date": "2025-11-01",
  "diagnoses": [
    {
      "name": "Hypertension",
      "severity": "Moderate"
    },
    {
      "name": "Diabetes",
      "severity": "Severe"
    },
    {
      "name": "Arthritis",
      "severity": "Mild"
    }
  ]
}
```

### All Data Preserved:
- ✅ Hypertension (Moderate)
- ✅ Diabetes (Severe)
- ✅ Arthritis (Mild)

---

## Root Cause Analysis

The bug exists because the code assumes that after a `group_by`, if you're mapping fields directly (not using `collect` or another `group_by`), you want a **single object** with values from the group.

But which row's values? The code arbitrarily picks **the first row** (index 0).

This makes sense for fields that are **identical across all rows** in the group (like `visit_date` in our example - all 3 rows have "2025-11-01"), but causes **silent data loss** for fields that **vary** across rows (like `diagnosis` and `severity`).

## When Does This Bug Occur?

✅ **Bug occurs when:**
- You use `group_by` to group multiple rows
- The template directly maps column values (e.g., `"field": "{column}"`)
- The column values **differ** across the grouped rows
- You DON'T use `collect` or another `group_by`

✅ **Bug does NOT occur when:**
- You use `collect` to gather all rows as an array
- You use another `group_by` to further subdivide the data
- All rows in the group have identical values for that column
- You only have 1 row per group

## Impact on Current Project

Looking at the actual `csv_transform.json`:
```json
{
  "attribute": {
    "name": "_EHR/appointments",
    "group_by": "EPI"  // Groups by patient
  },
  "template": {
    "group_by": "appointment_id",  // Further groups by appointment
    "template": {
      "appointment_id": "{appointment_id}",  // ← Safe: unique per group
      "date": "{appointment_date}",          // ← Safe: same for all rows in appointment
      "provider": { ... },                   // ← Safe: same for all rows in appointment
      "procedures": {
        "collect": [ ... ]                   // ← Safe: uses collect
      }
    }
  }
}
```

**The current project is NOT affected** because:
1. After grouping by `EPI`, it immediately groups again by `appointment_id`
2. All appointment-level fields (date, provider, etc.) are identical across rows with the same appointment_id
3. Procedures use `collect` to preserve all rows

**But this is a latent bug** that could bite someone who tries to use a simpler template structure!

---

## Recommended Fixes

### Option 1: Throw an error
When multiple rows exist and template maps fields directly, raise an error:
```python
if len(data_rows) > 1:
    raise ValueError(f"Template maps fields directly but {len(data_rows)} rows with different values exist. Use 'collect' or 'group_by' to create a list with all of the values.")
```

### Option 2: Document the behavior
Add a comment explaining that only the first row is used, and update documentation.

### Option 3: Aggregate intelligently
- If all rows have the same value, use it
- If values differ, raise an error or return an array

### Option 4: Always require explicit directive
Don't allow direct field mapping after `group_by` - require either `collect` or another `group_by`.
