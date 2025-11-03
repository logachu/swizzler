# Price Estimation Demo - Prototype System

This project contains a proof-of-concept system for transforming CSV data into NoSQL-ready JSON documents and a prototype mobile app backend server.

## Components

### 1. batch_process.py - CSV to JSON Transformer

A CLI tool that transforms denormalized CSV data into nested JSON documents using a declarative configuration format.

#### Usage

```bash
python batch_process.py <csv_file> <transform_file> [-o output_dir]
```

**Example:**
```bash
python batch_process.py price_estimates.csv csv_transform.json
```

#### Configuration Format

The transformation is controlled by `csv_transform.json`:

```json
{
  "attribute": {
    "name": "_EHR/appointments",
    "group_by": "EPI"
  },
  "template": {
    "group_by": "appointment_id",
    "template": {
      "field_name": "{column_name}",
      "nested_array": {
        "collect": [...]
      }
    }
  }
}
```

**Key concepts:**
- `group_by`: Groups rows by a column value to create unique objects
- `collect`: Gathers all rows as separate array items (allows duplicates)
- `{column_name}`: References CSV column values

### 2. server.py - Prototype Mobile App Backend

A FastAPI-based server that renders card-based UI sections from patient attribute data.

#### Running the Server

```bash
# Install dependencies
pip install -r requirements.txt

# Start server
python server.py
```

Server runs on `http://localhost:8000`

#### API Endpoints

**GET /section/{section_name}**
Returns cards for a section (e.g., "home")

```bash
curl -H "X-EPI: EPI123456" http://localhost:8000/section/home
```

**GET /section/procedures/{appointment_id}**
Returns procedure cards for a specific appointment

```bash
curl -H "X-EPI: EPI123456" http://localhost:8000/section/procedures/APT001
```

**Headers:**
- `X-EPI`: Required. Patient identifier for data access

#### Configuration System

**Section Config** (`configs/sections/*.json`):
```json
{
  "title": "Section Title",
  "description": "Section description",
  "cards": [
    "card_config_file.json"
  ]
}
```

**Card Config** (`configs/cards/*.json`):
```json
{
  "attribute": "_EHR/appointments",
  "foreach": "$[*]",
  "filter_by": {
    "field": "appointment_id",
    "value": "${appointment_id}"
  },
  "extract": "procedures",
  "template": {
    "title": "{$.name}",
    "subtitle": "{$.specialty}",
    "count": "{len($.procedures)} items",
    "formatted_date": "{format_date($.date, '%b %d')}",
    "days_until": "{days_from_now($.date)}",
    "conditional_field": "?Only shown if value exists"
  }
}
```

**Template Expression Types:**

1. **Simple field access:** `{$.field}` or `{$.nested.field}`
2. **String formatting:** `{$.date} at {$.time}`
3. **Compute functions:**
   - `{len($.array)}` - Count array items
   - `{sum($.array)}` - Sum numeric values
   - `{format_date($.date, '%b %d')}` - Format dates
   - `{days_from_now($.date)}` - Relative date display
4. **Conditional fields:** Prefix with `?` to omit if falsy

**Path Variables:**
Use `${variable_name}` in card configs to inject URL path parameters (e.g., `${appointment_id}`)

## Project Structure

```
.
├── batch_process.py          # CSV transformer
├── server.py                 # FastAPI backend server
├── requirements.txt          # Python dependencies
├── csv_transform.json        # Sample CSV transform config
├── price_estimates.csv       # Sample data
├── configs/
│   ├── sections/            # Section configurations
│   │   ├── home.json
│   │   └── procedures.json
│   └── cards/               # Card template configurations
│       ├── appointment_card.json
│       └── procedure_card.json
└── output/                  # Generated JSON files (patient attributes)
    ├── EPI123456__EHR_appointments.json
    ├── EPI789012__EHR_appointments.json
    └── EPI345678__EHR_appointments.json
```

## Example Workflow

1. **Transform CSV to JSON:**
   ```bash
   python batch_process.py price_estimates.csv csv_transform.json
   ```

2. **Start the server:**
   ```bash
   python server.py
   ```

3. **Fetch patient data:**
   ```bash
   # Get upcoming appointments
   curl -H "X-EPI: EPI123456" http://localhost:8000/section/home

   # Get procedures for specific appointment
   curl -H "X-EPI: EPI123456" http://localhost:8000/section/procedures/APT001
   ```

## Key Design Decisions

- **CSV Transform:** Configuration-driven, format-agnostic transformation supporting nested structures and grouping
- **Server:** Declarative card configurations with JSONPath-based data extraction and template expressions
- **Modularity:** Card configs are self-contained, declaring their own data sources
- **Flexibility:** Supports multiple attributes per patient, computed fields, conditional rendering, and parameterized sections
