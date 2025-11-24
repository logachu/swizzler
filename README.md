# Price Estimation Demo - Prototype System

This project contains a proof-of-concept system for transforming CSV data into NoSQL-ready JSON documents and a prototype mobile app backend server.

## Goals

The primary high-level goal of this system is the ability for customers to upload arbitrary structured health data as CSV files and display that data in a mobile app UI in customized collections of cards without requiring code changes to deployed on client or server to support new use cases.

To accomplish this high-level goal any solution should support:

* Nested objects in the data to any depth
* Nested _lists_ of objects
* Importing typed data from CSV including dates and currency values
* Allow use of configuration to describe where in the UI to display specified fields from this arbitrarily structured data
  -flexible formatting of dates and currency
  -displaying count of items in a list e.g. "you have {person.prescriptions.active.count}" active prescriptions"
  -conditional templates
  -sums of values e.g. "total cost: ${sum(person.bills[*].amount)}"
* Sorting arrays of objects by field values including all support comparable types: strings dates, currencies
* Filtering arrays of objects e.g. filtering only future appointments or active prescriptions

## Proposed solution

1. CSVs with denormalized data are uploaded via FTP.
2. Praia or the customer prepares a schema file to describe data types of CSV columns and now to normalize the nested data.
3. The schema is used by Databricks to transform CSV to JSON objects to store as Person Store attributes for each patient.
4. To display the data in the correct front-end UI element, use JSON Path-like syntax in templates in card configuration files to reference the custom data.
5. Logic bridge resolves templates and serves the strings to populate cards in the mobile clients.

There are multiple solution for serving the data with different tradeoffs. We could fully render templates on server to keep client as simple and future-proof as possible, or send the data as key/value pairs with keys matching the references from templates. We could send sort order with hrefs for each card for the client to use to fetch card data. This allows finer-grained client-side caching and ability to fetch on-demand but more server calls to initially render a card collection.

## Proof of concept

This project demonstrates the feasibility of this solution with a working solution. This ensures proposed formats for the schema and JSONPath-like template references fulfill the project goals.

### Components

#### 1. batch_process.py - CSV to JSON Transformer

A CLI tool that transforms denormalized CSV data into JSON documents using a declarative configuration format. This emulates a Databricks batch process.

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

The transformation is controlled by `csv_transform.json`. See [CSV_TRANSFORM_SCHEMA.md](CSV_TRANSFORM_SCHEMA.md) for complete reference.

**Simple Example:**

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
      "@item": {
        "appointment_id": "{appointment_id}",
        "date": "{appointment_date}"
      }
    }
  }
}
```

**Key Concepts:**

* **`@attribute`** - Top-level container with metadata
* **`@array`** - Defines an array (use `group_by` or `collect`)
* **`@item`** - Template for each object in the array
* **`{column_name}`** - Substituted with CSV column value
* **`@` prefix** - Indicates processing directive (not an output field)
* **No `@` prefix** - Output field name

**Type Conversions:**

Supports 7 types: `string`, `int`, `float`, `bool`, `null`, `currency`, `date`. See [COLUMN_TYPES.md](COLUMN_TYPES.md) for details.

```json
{
  "column_types": {
    "age": "int",
    "is_active": "bool",
    "appointment_date": {
      "type": "date",
      "input_format": "YYYY-MM-DD"
    }
  }
}
```

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

**GET /section/{section_path}**
Returns cards for a section. Supports both simple and parameterized sections.

**Simple sections:**
```bash
# Get home section
curl -H "X-EPI: EPI123456" http://localhost:8000/section/home

# Get active medications section
curl -H "X-EPI: EPI123456" http://localhost:8000/section/active_medications
```

**Parameterized sections:**
```bash
# Get procedures for a specific appointment
curl -H "X-EPI: EPI123456" http://localhost:8000/section/procedures/APT001
```

The generic endpoint extracts path parameters based on the section configuration's `path_parameters` field. For example, `/section/procedures/APT001` looks at the `procedures.json` section config, reads `"path_parameters": ["appointment_id"]`, and extracts `appointment_id=APT001` which becomes available to card filters as `${appointment_id}`.

**Headers:**

`X-EPI`: Epic Patient identifier. In the real system, the JWT includes this information. For this POC we emulate that with a custom header rather than deal with JWTs.

##### Configuration System

**Section Config** (`configs/sections/*.json`):

```json
{
  "title": "Section Title",
  "description": "Section description",
  "path_parameters": ["param_name"],
  "cards": [
    "card_config_file.json"
  ]
}
```

**Fields:**
- `title`: Display title for the section
- `description`: Description text
- `path_parameters`: (Optional) Array of parameter names to extract from URL path segments. For example, `["appointment_id"]` extracts the value from `/section/procedures/APT001` as `appointment_id=APT001`
- `cards`: Array of card configuration filenames to render

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
   * `{currency($.amount)}` - Format as currency (e.g., "$1,089.99")
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
   # Get upcoming appointments (simple section)
   curl -H "X-EPI: EPI123456" http://localhost:8000/section/home

   # Get procedures for specific appointment (parameterized section)
   curl -H "X-EPI: EPI123456" http://localhost:8000/section/procedures/APT001

   # Get active medications (simple section)
   curl -H "X-EPI: EPI123456" http://localhost:8000/section/active_medications
   ```
