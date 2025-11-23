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

## Compute Functions

| Function | Purpose | Example |
|----------|---------|---------|
| `days_after(date)` | Days since a date | `days_after($.due_date)` → `526` |
| `format_date(date, format)` | Format date for display | `format_date($.due_date, '%b %d, %Y')` → `"Jun 15, 2024"` |
| `days_from_now(date)` | Relative date string | `days_from_now($.due_date)` → `"526 days ago"` |
