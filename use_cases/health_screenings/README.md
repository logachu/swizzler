# Health Screenings Example

This example demonstrates the `days_after()` compute function for calculating overdue periods and upcoming due dates in card templates.

## Purpose

Healthcare applications often need to track preventive screenings and display whether they're overdue, upcoming, or due today. The `days_after()` function makes these calculations easy by returning:
- **Positive number** if the due date has passed (e.g., `5` = 5 days overdue)
- **Negative number** if the due date is in the future (e.g., `-5` = due in 5 days)
- **Zero** if the due date is today

## Files

- **input.csv** - Sample health screening data with various due dates
- **csv_transform.json** - Configuration to transform CSV to PersonStore format (sorted by due_date)
- **output/** - Generated JSON files for the PersonStore
- **health_screening_card.json** (in configs/cards/) - Card template demonstrating `days_after()`

## Sample Data

The example includes three types of screenings:

1. **Overdue** - Mammogram (due 2024-06-15, past due)
2. **Upcoming** - Blood Pressure Check (due 2025-11-25)
3. **Future** - Colonoscopy (due 2026-03-20)

## Card Template Usage

The `health_screening_card.json` template demonstrates several compute functions:

```json
{
  "title": "{$.screening_type}",
  "subtitle": "Due date: {format_date($.due_date, '%b %d, %Y')}",
  "status": "{$.status}",
  "?overdue_message": "You are {days_after($.due_date)} days overdue",
  "last_completed": "Last completed: {format_date($.last_completed_date, '%b %d, %Y')}"
}
```

### Key Features Demonstrated

1. **Date Formatting** - `format_date()` converts ISO dates to readable format
   ```
   "2024-06-15" → "Jun 15, 2024"
   ```

2. **Overdue Calculation** - `days_after()` calculates days since due date
   ```
   For due_date "2024-06-15" (if today is 2025-11-23):
   days_after($.due_date) → 526 days overdue
   ```

3. **Conditional Fields** - Fields prefixed with `?` only show when conditions are met
   - `?overdue_message` - Shows when screening is overdue
   - `?upcoming_message` - Shows when screening is upcoming
   - `?due_today` - Shows when screening is due today

## Example Output

For a **Mammogram overdue** screening, the card might display:

```
Title: Mammogram
Subtitle: Due date: Jun 15, 2024
Status: overdue
Overdue Message: You are 526 days overdue
Last Completed: Jun 10, 2023
Provider: Dr. Sarah Johnson
Notes: Breast cancer screening - age 45+
```

For a **Colonoscopy upcoming** screening:

```
Title: Colonoscopy
Subtitle: Due date: Mar 20, 2026
Status: scheduled
Last Completed: Mar 15, 2021
Provider: Dr. Michael Chen
Notes: Routine screening - next due 2026
```

## Running the Example

Generate the PersonStore data:
```bash
python3 batch_process.py use_cases/health_screenings/input.csv \
  use_cases/health_screenings/csv_transform.json \
  -o use_cases/health_screenings/output
```

The output will be sorted by due_date (ascending), so overdue screenings appear first.

## Use Cases

This pattern is useful for:
- Preventive health screenings (mammograms, colonoscopies, etc.)
- Vaccination reminders
- Medication refill due dates
- Annual checkup tracking
- Lab test scheduling
- Dental cleaning reminders

## Advanced Usage

You can combine `days_after()` with conditional logic in your application:

```javascript
const daysOverdue = days_after(screening.due_date);

if (daysOverdue > 0) {
  // Show urgent reminder - overdue
  displayMessage(`You are ${daysOverdue} days overdue`);
} else if (daysOverdue === 0) {
  // Show today reminder
  displayMessage("Due today!");
} else {
  // Show upcoming reminder
  displayMessage(`Due in ${Math.abs(daysOverdue)} days`);
}
```

## Compute Functions Summary

This example demonstrates these compute functions:

| Function | Purpose | Example |
|----------|---------|---------|
| `days_after(date)` | Days since a date | `days_after($.due_date)` → `526` |
| `format_date(date, format)` | Format date for display | `format_date($.due_date, '%b %d, %Y')` → `"Jun 15, 2024"` |
| `days_from_now(date)` | Relative date string | `days_from_now($.due_date)` → `"526 days ago"` |
