# Price Estimation Demo - Prototype System

This project contains a proof-of-concept system for transforming CSV data into NoSQL-ready JSON documents and a prototype mobile app backend server.

## Goals

The primary high-level goas is the ability to handle arbitrary data uploaded from customers as CSV files with columns containing custom fields not known to our system.

To accomplish this high-level goal we have the following sub-goals:

* Allow nested objects in the data
* Allow nested _lists_ of objects
* Allow the display of this arbitrarily structured data in the front-end UI using templates

## Proposed solution

1. CSVs with denormalized data are uploaded
2. We prepare a schema file to describe data types and now to normalize the nested data. This is used by Databricks to transform CSV to JSON objects to store as Person Store attributes for each patient.
3. To display the data in in the correct front-end UI element, use JSON Path-like syntax in templates to reference the custom data.
4. Logic bridge serves this data to clients.

There are multiple solution for serving the data with different tradeoffs. We could fully render templates on server to keep client as simple and future-proof as possible, or send the data as key/value pairs with keys matching the references from templates. We could send sort order with hrefs for each card for the client to use to fetch card data. This allows finer-grained client-side caching and ability to fetch on-demand but more server calls to initially render a card collection.

## Proof of concept

To demonstrate the feasibility of this solution and workout the formats for the schema and JSONPath-like template references I've prepared a proof of concept demo.

### Components

#### 1. batch_process.py - CSV to JSON Transformer

A CLI tool that transforms denormalized CSV data into nested JSON documents using a declarative configuration format. This emulates a Databricks batch process.

##### Usage

```bash
python batch_process.py <csv_file> <transform_file> [-o output_dir]
```

**Example:**

```bash
python batch_process.py use_cases/price_estimation/price_estimates.csv \
                        use_cases/price_estimation/csv_transform.json
```

##### Configuration Format

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

* `group_by`: Groups rows by a column value to create unique objects
* `collect`: Gathers all rows as separate array items (allows duplicates)
* `{column_name}`: References CSV column values

#### 2. server.py - Prototype Mobile App Backend

A FastAPI-based server that renders card-based UI sections from patient attribute data.

##### Running the Server

```bash
# Install dependencies
pip install -r requirements.txt

# Start server
python server.py
```

Server runs on `http://localhost:8000`

##### API Endpoints

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

`X-EPI`: Epic Patient identifier. In the real system, the JWT includes this information. For this POC we emulate that with a custom header rather than deal with JWTs.

##### Configuration System

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
   * `{len($.array)}` - Count array items
   * `{sum($.array)}` - Sum numeric values
   * `{format_date($.date, '%b %d')}` - Format dates
   * `{days_from_now($.date)}` - Relative date display
4. **Conditional fields:** Prefix with `?` to omit if falsy

**Path Variables:**

Use `${variable_name}` in card configs to inject URL path parameters (e.g., `${appointment_id}`)

### Project Structure

```txt
.
├── batch_process.py          # CSV transformer
├── server.py                 # FastAPI backend server
├── test_use_cases.py         # Automated test suite
├── requirements.txt          # Python dependencies
├── configs/                  # Shared configurations for all use cases
│   ├── sections/            # Section configurations
│   └── cards/               # Card template configurations
├── mock_personstore/        # Generated JSON files (simulates PersonStore database)
│   ├── EPI123456__EHR_appointments.json
│   ├── EPI123456__EHR_prescriptions.json
│   ├── EPI789012__EHR_appointments.json
│   └── ...
└── use_cases/               # Use case examples
    ├── price_estimation/
    │   ├── price_estimates.csv
    │   ├── csv_transform.json
    │   ├── configs/         # Use case-specific configs
    │   ├── output_expected/ # Expected API responses
    │   └── output_actual/   # Actual API responses (for testing)
    └── prescriptions/
        ├── prescriptions.csv
        ├── csv_transform.json
        ├── configs/
        ├── output_expected/
        └── output_actual/
```

### Example Workflow

1. **Transform CSV to JSON:**

   ```bash
   # Process price estimation use case
   python batch_process.py use_cases/price_estimation/price_estimates.csv \
                           use_cases/price_estimation/csv_transform.json

   # Process prescriptions use case
   python batch_process.py use_cases/prescriptions/prescriptions.csv \
                           use_cases/prescriptions/csv_transform.json
   ```

2. **Start the server:**

   ```bash
   python server.py
   ```

3. **Test all use cases:**

   ```bash
   python test_use_cases.py
   ```

4. **Fetch patient data:**

   ```bash
   # Get upcoming appointments
   curl -H "X-EPI: EPI123456" http://localhost:8000/section/home

   # Get procedures for specific appointment
   curl -H "X-EPI: EPI123456" http://localhost:8000/section/procedures/APT001

   # Get active medications
   curl -H "X-EPI: EPI123456" http://localhost:8000/section/active_medications
   ```

### Key Design Decisions

* **CSV Transform:** Configuration-driven, format-agnostic transformation supporting nested structures and grouping
* **Server:** Declarative card configurations with JSONPath-based data extraction and template expressions
* **Modularity:** Card configs are self-contained, declaring their own data sources
* **Flexibility:** Supports multiple attributes per patient, computed fields, conditional rendering, and parameterized sections
