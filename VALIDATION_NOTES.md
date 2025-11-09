# CSV Validation Notes

## The Validator Script

The `validate_csv.py` script helps identify potential issues with CSV files before processing them with `batch_process.py`.

### Usage

```bash
# Validate CSV structure only
python validate_csv.py data.csv

# Validate CSV against a specific config
python validate_csv.py data.csv csv_transform.json
```

## Important Limitation: Hierarchical Grouping

The current validator has a limitation when dealing with **hierarchical grouping** where group keys are only unique within a parent group.

### Example: Non-Unique Appointment IDs

In `price_estimates.csv`, appointment IDs like `APT001` are **reused across different patients**:

```csv
EPI,appointment_id,appointment_date
EPI123456,APT001,2025-11-15   ← APT001 for patient 1
EPI789012,APT001,2025-11-25   ← APT001 for patient 2 (DIFFERENT appointment!)
EPI345678,APT001,2025-12-02   ← APT001 for patient 3 (ALSO different!)
```

### How batch_process.py Handles This

The `csv_transform.json` uses **nested grouping**:

```json
{
  "attribute": {
    "group_by": "EPI"              // Step 1: Group by patient
  },
  "template": {
    "group_by": "appointment_id",  // Step 2: Within each patient, group by appointment
    "template": {
      "date": "{appointment_date}" // Step 3: Map fields
    }
  }
}
```

**Processing flow:**
1. First groups rows by `EPI` → Creates 3 separate groups
2. **Within each EPI group**, groups by `appointment_id` → APT001 for EPI123456 is separate from APT001 for EPI789012
3. Maps fields within those sub-groups

This works correctly because appointment IDs are unique **within each patient**.

### Validator Limitation

The validator currently checks `appointment_id` grouping across **ALL rows**, not within the EPI groups:

```
❌ ERROR: Template field 'date' maps directly to column(s) {'appointment_date'},
but multiple rows within the same 'appointment_id' group have different values.
```

This is a **false positive** - the validator sees APT001 appearing with different dates, but it's not accounting for the fact that these APT001s belong to different patients.

### Why This Happens

The CSV data has **appointment IDs that are only unique per patient**, not globally unique. This is a valid data model (like how order numbers might be unique per customer, not globally).

## Data Patterns That Make Processing Impossible

Based on analysis of `batch_process.py`, here are the actual constraints:

### 1. **Missing group_by Column**

❌ **Problem:**
```json
{
  "attribute": {"group_by": "patient_id"}  // Config specifies this column
}
```

But CSV has: `EPI, name, date` (no `patient_id` column)

**Result:** All rows silently dropped

---

### 2. **Empty or Falsy Group Keys**

❌ **Problem:**
```csv
patient_id,diagnosis
,Hypertension        ← Empty string
0,Diabetes           ← Integer zero (falsy!)
```

**Result:** Both rows silently dropped during grouping

---

### 3. **Inconsistent Values Without collect**

❌ **Problem:**
```json
{
  "attribute": {"group_by": "patient_id"},
  "template": {
    "diagnosis": "{diagnosis}"  // Direct mapping, no collect
  }
}
```

CSV:
```csv
patient_id,diagnosis
PAT001,Hypertension
PAT001,Diabetes      ← Same patient, different diagnosis
```

**Result:** `ValueError` thrown (as of the recent fix)

**Fix:** Use `collect`:
```json
{
  "template": {
    "diagnoses": {
      "collect": [{"name": "{diagnosis}"}]
    }
  }
}
```

---

### 4. **Missing Column References**

❌ **Problem:**
Template references `{procedure_code}` but CSV column is named `code`

**Result:** Silent data loss - outputs empty string `""`

---

### 5. **Non-UTF-8 Encoding**

❌ **Problem:**
CSV file is encoded in UTF-16 or Latin-1

**Result:** Data corruption or decode errors

---

### 6. **Duplicate Column Names**

❌ **Problem:**
```csv
id,name,name,value
1,John,Smith,100
```

**Result:** Only one `name` column accessible, other is lost

---

### 7. **All-Zero Data Rows**

⚠️ **Warning:**
```csv
count,value,total
0,0,0
```

**Result:** Row might be considered empty and skipped (if using integer 0)

---

## Recommendations

### For Valid Processing

Your CSV should:

1. ✅ Use UTF-8 encoding
2. ✅ Have unique column names
3. ✅ Ensure group_by columns exist and have non-empty, truthy values
4. ✅ Structure data hierarchically if using nested group_by
5. ✅ Use consistent values for directly-mapped fields within each group, OR use `collect`
6. ✅ Match all template column references to actual CSV column names

### For Hierarchical Data

If your data has non-unique IDs at lower levels (like appointment IDs per patient):

✅ **Correct:** Use nested `group_by`
```json
{
  "attribute": {"group_by": "patient_id"},
  "template": {
    "group_by": "appointment_id",
    "template": { ... }
  }
}
```

❌ **Incorrect:** Try to group by non-unique ID directly
```json
{
  "attribute": {"group_by": "appointment_id"}  // Not unique across all patients!
}
```

## Future Validator Improvements

To properly validate hierarchical grouping, the validator would need to:

1. Build the actual grouping hierarchy (group by EPI first, then by appointment_id within each)
2. Check consistency only within the appropriate level of the hierarchy
3. Simulate the actual batch_process.py logic more closely

For now, if you see errors about inconsistent values when using nested `group_by`, verify manually that:
- The values ARE consistent within the innermost grouping level
- Your nested group_by column is unique within its parent group
