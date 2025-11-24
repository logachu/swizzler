# Technical Design Document
## Configuration-Driven Healthcare Data Platform

---

## Table of Contents

1. [Executive Summary](#1-executive-summary)
2. [Problem Statement & Requirements](#2-problem-statement--requirements)
3. [Solution Alternatives](#3-solution-alternatives)
4. [Architecture & Design](#4-architecture--design)
5. [Proof of Concept Validation](#5-proof-of-concept-validation)
6. [Technical Tradeoffs & Limitations](#6-technical-tradeoffs--limitations)
7. [Risks & Mitigation](#7-risks--mitigation)
8. [Production Roadmap](#8-production-roadmap)
9. [References & Appendices](#9-references--appendices)

---

## 1. Executive Summary

### 1.1 Purpose

This Technical Design Document proposes a configuration-driven architecture for displaying arbitrary structured healthcare data in mobile applications without requiring code changes to deployed systems. The goal is to allow customers to upload whatever data they need for a new use case and we can use that data within our mobile client SDK with only configuration changes without versioning the server or client SDK code. A proof-of-concept implementation has been completed to validate the feasibility of this approach.

Note this proposal to not include any thing about a server-side rule parser. We currently handle template substitution with some parsing code from the same cep-rule-parser repository that handles parsing and evaluating card visibility rules. While this proposal does replace the template engine, it does not replace the rules-engine.

### 1.2 Problem Overview

Current system limitations:
- New customer use cases often require code changes to mobile clients and backend servers or awkward fitting of square pegs into our existing round holes e.g. using cohorts for everything.
- High cost and slow time-to-market for customer-specific features
- Customers and even internal people often suprised at what our system can and cannot currently handle.

Current technical limitations addressed by this proposal:
- All data values imported from CSVs are strings so cannot do computations with dates, times, dollar amounts, etc
- No way to disambugate denormalized data from the CSV into nested JSON PersonStore attributes.
- Cannot have conditional templates (text that does not appear if a value does not exist or show different text for different cases.)
- Custom code (PEContextElement subclasses) for each use case
- Cannot have functions in templates e.g. to sum values or display a count or length
- Cannot format dates
- Cannot format currency (dollar amounts)
- Cannot sort lists

### 1.3 Proposed Solution

A two-stage configuration-driven system:

1. **Batch Transformation**: CSV files with denormalized data are transformed into nested JSON documents using a specially formated metadata file to describe the transformation using a Databricks pipeline. The resulting JSON is saved to PersonStore as a new attribute.
2. **Dynamic Rendering**: LogicBridge (Quarkus/Java) server renders card-based UI sections from JSON data using configuration files with new template format that can refer to individual data fields in a complex PersonStore attribute (attributes are stored as JSON documents)

**Note on POC Implementation:** The proof-of-concept uses a Python/FastAPI server for rapid prototyping and validation. A Production implementation would require implementing this functionality in the existing LogicBridge service (Quarkus/Java).
    The Databricks pipeline is simulated with a simple Python CLI script.

### 1.4 POC Results

The proof-of-concept successfully validates:
- ✅ Arbitrary nested data structures (objects and arrays to any depth)
- ✅ Type-safe data import (7 supported types including dates, currency)
- ✅ Configuration-driven UI rendering with enhanced template format conditional logic
- ✅ Data operations (filtering, sorting, aggregations)
- ✅ Template-based formatting (dates, currency, relative dates, item counts)
- ✅ Multiple real-world use cases implemented

## 2. Problem Statement & Requirements

### 2.1 Business Problem

**[TODO: Expand with specific business context]**

Healthcare customers need to upload arbitrary structured health data (CSV files) and display that data in mobile app UIs with customized layouts and formatting. Current solutions require:
- Custom code development for each new use case
- Deployment of new client and server versions
- Long lead times (weeks to months)
- High engineering costs per customer

**Business Impact:**
- Cost per custom use case
- Time-to-market delays
- Lost opportunities due to inflexibility

### 2.2 Current System Limitations

Key limitations:
- Requires customer data to follow a fixed format e.g. cohort files. While we do allow passing along "additionalFields" for extra CSV columns to the client, then custom code that recognizes the additionalField content is required per use case e.g. facilities.
- Hardcoded data models in mobile clients, e.g. PECohortsContext, PEOrdersContext
- Deployment required for many new customer use cases that do not fall into our existing NBA or cohorts cases.

### 2.3 Requirements

Any solution must support:

1. **Arbitrary Data Structures**
   + Nested objects to any depth
   + Nested lists/arrays of objects
   + Mixed object and array structures

2. **Type-Safe Data Import**
    Import typed data from CSV including:
     + Dates with timezone support
     + Currency values
     + Integers, floats, booleans, strings, nulls

3. **Flexible UI Configuration**
   + Display specified fields from arbitrarily structured data
   + Flexible formatting of dates and currency
   + Display counts of items in lists (e.g., "You have 3 active prescriptions")
   + Conditional templates (show/hide based on data)
   + Computed values (sums, aggregations)

4. **Data Operations**
   + Sort arrays of objects by field values (strings, dates, currencies)
   + Filter arrays of objects (e.g., only future appointments, active prescriptions)
   + Aggregate data (count, sum)

5. **Zero Code Changes for New Use Cases**
   + Add new use cases by creating configuration files only
   + No mobile client redeployment
   + No server redeployment

---


### 3.3 Alternative 3: Configuration-Driven Architecture (PROPOSED)

**Description:** Two-stage transformation with declarative JSON configuration

**Architecture:**
1. CSV → Declarative Transform Schema → JSON Documents (Databricks batch)
2. JSON Documents → Card/Section Configs with enhanced templates → REST API → Mobile App

**Pros:**
- ✅ Greatly increased flexibility
- ✅ Zero code changes for new use cases

**Cons:**
- Learning curve for configuration formats
- Need to develop validation tooling
- Configuration debugging requires expertise
- Initial development investment, although POC code provides the template most of the needed logic.

---

## 4. Architecture & Design

### 4.1 System Architecture Overview

```txt
CSV File (Customer)
        ↓ FTP Upload
Databricks Pipeline (PRODUCTION)
  • Load → Cleanse → Combine
  • Uses: csv_transform.json
  • POC: batch_process.py emulates this
        ↓ Writes JSON
PersonStore DB
        
LogicBridge Server - Quarkus/Java (PRODUCTION)
  • GET /section/{section_path}
  • SectionRenderer → CardRenderer → Template Engine
  • Config: sections/*.json, cards/*.json
        ↓ REST API
Mobile App Client
```

**POC vs Production:**
- **POC (This Repository):**
  + `batch_process.py` - Python script emulating Databricks pipeline
  + `server.py` - Python/FastAPI server validating configuration approach
  + `mock_personstore/` - Flat JSON files simulating PersonStore DB
- **Production Implementation:**
  + Databricks pipeline - Python notebooks implementing transformation logic
  + LogicBridge - Quarkus/Java service with template engine integrated
  + PersonStore - Real database with proper indexing and querying

---

### 4.2 Component Design

#### 4.2.1 CSV-to-JSON Transformer (Batch Process)

**Purpose:** Transform denormalized CSV data into nested JSON documents for NoSQL storage.

**Implementation:** `batch_process.py` (emulates Databricks pipeline)

**Three-Stage Pipeline:**

1. **Load Stage**
   - Reads CSV file and transformation configuration
   - Validates file existence and format
   - Returns raw data and config

2. **Cleanse Stage**
   - Type conversions based on `column_types` configuration
   - Validates and normalizes data values
   - Handles 7 data types:
     - `string`: Text values (default)
     - `int`: Integers
     - `float`: Floating-point numbers
     - `bool`: Boolean values (true/false, yes/no, 1/0)
     - `null`: Explicit nulls
     - `currency`: Dollar amounts with parsing (`$23.47` → `23.47`)
     - `date`: Date strings converted to ISO-8601 with timezone support

3. **Combine Stage**
   - Applies declarative schema to create nested structures
   - Groups data by specified columns
   - Creates arrays and objects according to template
   - Outputs one JSON file per unique identifier (EPI)

**Example Usage:**
```bash
python batch_process.py use_cases/price_estimation/price_estimates.csv \
                        use_cases/price_estimation/csv_transform.json
```

**Output:** JSON files in `mock_personstore/` (or PersonStore DB in production)

---

#### 4.2.2 Transform Schema Language

**Purpose:** Declarative format for describing CSV-to-JSON transformations.

**Key Design Principle:** `@`-prefix convention
- Keys with `@` prefix = processing directives (not in output)
- Keys without `@` prefix = output field names

**Schema Structure:**

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
      },
      "copay": {
        "type": "currency"
      },
      "age": "int"
    },
    "@array": {
      "group_by": "appointment_id",
      "@item": {
        "id": "{appointment_id}",
        "date": "{appointment_date}",
        "copay": "{copay}",
        "procedures": {
          "@array": {
            "collect": "procedure_*",
            "@item": {
              "name": "{procedure_name}",
              "cost": "{procedure_cost}"
            }
          }
        }
      }
    }
  }
}
```

**Processing Directives:**
- `@attribute`: Top-level container with metadata
- `@array`: Define array structures (use `group_by` or `collect`)
- `@item`: Template for each array element
- `@object`: Define object structures
- `{column_name}`: CSV column value substitution

**Array Creation Strategies:**
1. **`group_by`**: Group rows by column value (one item per unique value)
2. **`collect`**: Collect columns matching pattern into array items

**Sorting:**
```json
{
  "@array": {
    "group_by": "appointment_id",
    "sort_by": {
      "field": "date",
      "order": "asc"
    }
  }
}
```

**Reference:** See [CSV_TRANSFORM_SCHEMA.md](CSV_TRANSFORM_SCHEMA.md) for complete specification.

---

#### 4.2.3 Column Type System

**Purpose:** Type-safe conversion from CSV strings to typed JSON values.

**Supported Types:**

| Type | Description | Example Input | Example Output |
|------|-------------|---------------|----------------|
| `string` | Text (default) | `"John Doe"` | `"John Doe"` |
| `int` | Integer | `"42"` | `42` |
| `float` | Decimal number | `"3.14"` | `3.14` |
| `bool` | Boolean | `"true"`, `"yes"`, `"1"` | `true` |
| `null` | Explicit null | `"null"`, `""` | `null` |
| `currency` | Dollar amount | `"$1,234.56"`, `"23.47"` | `23.47` |
| `date` | ISO-8601 date | `"11/23/2025"` | `"2025-11-23T00:00:00-05:00"` |

**Date Type Configuration:**
```json
{
  "column_types": {
    "appointment_date": {
      "type": "date",
      "input_format": "MM/DD/YYYY",      // Optional: auto-detects if omitted
      "timezone": "America/New_York"      // Optional: omit for no timezone
    }
  }
}
```

**Supported Date Input Formats:**
- `YYYY-MM-DD` (ISO-8601)
- `MM/DD/YYYY`
- `DD/MM/YYYY`
- `MM/DD/YYYY ZZZ` (with timezone abbreviation)
- Auto-detection of common formats

**Currency Type Configuration:**
```json
{
  "column_types": {
    "copay_amount": {
      "type": "currency",
      "currency": "USD"    // Optional: default USD
    }
  }
}
```

**Reference:** See `COLUMN_TYPES.md` for complete specification.

---

#### 4.2.4 Mobile App Backend Server

**Purpose:** Configuration-driven REST API for serving card-based UI data.

**Implementation:** LogicBridge would implement the template engine logic in the POC's `server.py` which relies on a JSONPath library as its only dependency. 

**NOTE:** There may be a good library to handle more complex expressions, but while developing the POC, I didn't find a need for complex expressions in templates beyond what is supported in a small amount of code found in app/template/*.py. It turns out the combination of template references to other templates and conditional templates can handle a suprising number of cases. I added some more cases I did not implement to TODO.md

**Architecture:**
```txt
server.py (FastAPI endpoint)
  ↓
SectionRenderer (app/rendering/section_renderer.py)
  ↓
CardRenderer (app/rendering/card_renderer.py)
  ↓
TemplateEngine (app/template/engine.py)
  ├── JSONPathEngine: Query JSON data
  ├── ExpressionParser: Parse {expression} syntax
  ├── ComputeFunctions: len(), sum(), format_date(), etc.
  └── ConditionEvaluator: Conditional includes
```

**Module Breakdown:**
- **`app/config/loaders.py`**: ConfigLoader, AttributeLoader for JSON file loading
- **`app/rendering/card_renderer.py`**: Evaluates card templates against patient data
- **`app/rendering/section_renderer.py`**: Orchestrates card rendering for sections
- **`app/template/engine.py`**: JSONPath evaluation and expression parsing
- **`app/template/functions.py`**: Compute functions (formatting, aggregations)
- **`app/template/conditions.py`**: Conditional logic evaluation

**Key Characteristic:** Zero use-case-specific code - all logic driven by configurations.

---

#### 4.2.5 API Specifications

**Base URL:** `http://localhost:8000` (POC) / `https://api.praia.com` (production)

**Endpoint:** `GET /section/{section_path}`

**Headers:**
- `X-EPI`: Epic Patient Identifier (simulates JWT in POC)

**Simple Section Request:**
```bash
curl -H "X-EPI: EPI123456" \
     http://localhost:8000/section/home
```

**Parameterized Section Request:**
```bash
curl -H "X-EPI: EPI123456" \
     http://localhost:8000/section/procedures/APT001
```

**Path Parameter Extraction:**
- Section config defines: `"path_parameters": ["appointment_id"]`
- URL `/section/procedures/APT001` extracts `appointment_id=APT001`
- Available in card configs as `${appointment_id}` for filtering

**Response Format:**
```json
{
  "title": "Section Title",
  "description": "Section description",
  "cards": [
    {
      "title": "Appointment with Dr. Smith",
      "subtitle": "Cardiology",
      "date": "Dec 01",
      "copay": "$25.00"
    }
  ]
}
```

**Error Responses:**
- `404`: Section or attribute not found
- `500`: Template evaluation error

---

#### 4.2.6 Configuration System

**Section Configuration** (`configs/sections/*.json`):

```json
{
  "title": "Upcoming Appointments",
  "description": "Your scheduled appointments",
  "path_parameters": ["appointment_id"],
  "cards": [
    "appointment_card.json",
    "procedure_card.json"
  ]
}
```

**Fields:**
- `title`: Section display title
- `description`: Section description text
- `path_parameters`: (Optional) URL parameter names to extract
- `cards`: Array of card config filenames to render in order

**Card Configuration** (`configs/cards/*.json`):

```json
{
  "attribute": "_EHR/appointments",
  "foreach": "$[*]",
  "filter_by": {
    "field": "appointment_id",
    "value": "${appointment_id}"
  },
  "extract": "procedures",
  "templates": {
    "root": {
      "title": "{$.provider.name}",
      "subtitle": "{$.provider.specialty}",
      "date": "{format_date($.date, '%b %d')}",
      "days_until": "{days_from_now($.date)} days",
      "copay": "{currency($.costs.copay)}",
      "procedure_count": "{len($.procedures)} procedures",
      "?conditional_field": "Only shown if truthy"
    }
  }
}
```

**Fields:**
- `attribute`: PersonStore attribute name (e.g., `_EHR/appointments`)
- `foreach`: JSONPath expression to iterate over items (default: `$`)
- `filter_by`: (Optional) Filter items by field value
- `extract`: (Optional) Extract nested array after filtering
- `templates.root`: Template defining output fields

**Path Variables:**
Use `${variable_name}` to inject URL path parameters:
```json
{
  "filter_by": {
    "field": "appointment_id",
    "value": "${appointment_id}"
  }
}
```

---

#### 4.2.7 Template Engine

**Purpose:** Flexible, configuration-driven rendering

**Design Philosophy:** Conbines JSONPath expressions to refer to fields in PersonStore attributes with four canonical template operations based on Terrence Parr's StringTemplate 

> Language theory supports my premise that even a minimal StringTemplate engine with only these features is very powerful--such an engine can generate the context-free languages; see Enforcing Strict Model-View Separation in Template Engines. E.g., most programming languages are context-free as are any XML pages whose form can be expressed with a DTD.

1. **Attribute Reference** - Access nested data fields
2. **Template Reference** - templates can refer to other templates
3. **Conditional Include** - Show/hide content based on a condition
4. **Template Application to Lists** - Apply a template to each value in an array aka the map operation.

**Template Expression Types:**

**1. Simple Field Access:**
```json
{
  "title": "{$.medication_name}",
  "dosage": "{$.dosage}"
}
```

**2. Nested Field Access:**
```json
{
  "doctor": "{$.prescriber.name}",
  "specialty": "{$.prescriber.specialty}"
}
```

**3. String Formatting:**
```json
{
  "datetime": "{$.date} at {$.time}",
  "location": "Room {$.room_number}, Floor {$.floor}"
}
```

**4. Compute Functions:**

| Function | Description | Example | Output |
|----------|-------------|---------|--------|
| `len()` | Count items | `{len($.prescriptions)}` | `3` |
| `sum()` | Sum values | `{sum($.items[*].cost)}` | `156.99` |
| `format_date()` | Format date | `{format_date($.date, '%b %d')}` | `"Dec 01"` |
| `days_from_now()` | Relative days | `{days_from_now($.date)}` | `7` |
| `days_after()` | Days between dates | `{days_after($.start, $.end)}` | `14` |
| `currency()` | Format currency | `{currency($.amount)}` | `"$1,089.99"` |

**5. Conditional Fields:**
Prefix field name with `?` to omit if value is falsy:
```json
{
  "title": "{$.name}",
  "?warning": "{$.warning_message}",  // Omitted if warning_message is empty/null
  "?refills": "{$.refills_remaining}" // Omitted if refills_remaining is 0/null
}
```

**6. Path Variables:**
Inject URL parameters with `${variable}`:
```json
{
  "filter_by": {
    "field": "id",
    "value": "${appointment_id}"
  }
}
```

**JSONPath Support:**
Uses `jsonpath-ng` library with standard JSONPath syntax:
- `$`: Root object
- `$[*]`: All array items
- `$.field`: Object field
- `$.nested.field`: Nested field
- `$[*].field`: Field from all array items

**Reference:** See `TEMPLATE_FORMAT.md` for complete specification.

---

### 4.3 Data Model

**CSV Input Format (Denormalized):**
```csv
EPI,appointment_id,appointment_date,provider_name,provider_specialty,procedure_name,procedure_cost
EPI123456,APT001,2025-12-01,Dr. Smith,Cardiology,EKG,$150.00
EPI123456,APT001,2025-12-01,Dr. Smith,Cardiology,Blood Pressure,$50.00
EPI123456,APT002,2025-12-15,Dr. Jones,Orthopedics,X-Ray,$200.00
```

**PersonStore JSON Format (Normalized):**
```json
[
  {
    "appointment_id": "APT001",
    "date": "2025-12-01T00:00:00-05:00",
    "provider": {
      "name": "Dr. Smith",
      "specialty": "Cardiology"
    },
    "procedures": [
      {
        "name": "EKG",
        "cost": 150.00
      },
      {
        "name": "Blood Pressure",
        "cost": 50.00
      }
    ],
    "total_cost": 200.00
  },
  {
    "appointment_id": "APT002",
    "date": "2025-12-15T00:00:00-05:00",
    "provider": {
      "name": "Dr. Jones",
      "specialty": "Orthopedics"
    },
    "procedures": [
      {
        "name": "X-Ray",
        "cost": 200.00
      }
    ],
    "total_cost": 200.00
  }
]
```

**API Response Format (Rendered Cards):**
```json
{
  "title": "Upcoming Appointments",
  "description": "Your scheduled appointments",
  "cards": [
    {
      "title": "Dr. Smith",
      "subtitle": "Cardiology",
      "date": "Dec 01",
      "days_until": "7 days",
      "procedure_count": "2 procedures",
      "total": "$200.00"
    },
    {
      "title": "Dr. Jones",
      "subtitle": "Orthopedics",
      "date": "Dec 15",
      "days_until": "21 days",
      "procedure_count": "1 procedure",
      "total": "$200.00"
    }
  ]
}
```

---

### 4.4 Security & Compliance

**[TODO: Add organization-specific security requirements]**

**PHI Data Handling:**
- All patient data classified as Protected Health Information (PHI)
- End-to-end encryption for data in transit (TLS 1.3+)
- Encryption at rest for PersonStore database
- No PHI in logs or error messages

**HIPAA Compliance:**
- Architecture supports HIPAA requirements
- Audit logging of all data access (to be implemented)
- Access controls based on user roles and patient consent
- Data retention and deletion policies

**Authentication & Authorization:**
- **POC:** X-EPI header simulates authentication
- **Production:** JWT tokens with patient EPI claim
- Role-based access control (RBAC)
- Patient consent verification before data access

**Configuration Security:**
- Configuration files are non-executable (JSON only)
- No code execution in templates (expression evaluation only)
- Input validation on all template expressions
- Rate limiting on API endpoints

**Data Boundaries:**
- Clear separation between batch processing and API serving
- PersonStore DB as single source of truth for patient data
- No direct database access from mobile clients
- All data access mediated through API with authorization checks

---

## 5. Proof of Concept Validation

### 5.1 POC Objectives

The proof-of-concept aimed to validate:

1. **Feasibility:** Can configuration-driven approach handle arbitrary nested data?
2. **Expressiveness:** Are schema and template formats sufficient for real use cases?
3. **Performance:** Do transformation and rendering perform adequately?
4. **Completeness:** Can all stated requirements be met?

**Success Criteria:**
- ✅ Implement 3+ real-world use cases with only configuration changes
- ✅ Support all required data types and operations
- ✅ Demonstrate nested structures (3+ levels deep)
- ✅ Validate template engine expressiveness (conditional, computed fields)
- ✅ Automated test suite with expected output validation

---

### 5.2 POC Scope & Constraints

**POC Objectives:**
The proof-of-concept uses **Python/FastAPI** to rapidly validate:
1. Configuration format expressiveness and completeness
2. Template engine functionality and syntax
3. Feasibility of zero-code-change approach
4. End-to-end data transformation and rendering

**Important:** The POC is **not** the production implementation. It validates the approach and configuration formats only.

**In Scope:**
- Core transformation pipeline (CSV → JSON) in Python
- Complete template engine with all expression types
- REST API with parameterized sections
- Multiple use case examples
- Automated testing framework
- Configuration format validation

**Out of Scope:**
- Production authentication (used X-EPI header simulation)
- Real Databricks integration (emulated locally with Python script)
- Real PersonStore database (used flat JSON files)
- LogicBridge/Quarkus integration (used Python/FastAPI instead)
- Performance/scale testing
- Configuration validation tooling
- UI/UX for configuration management

**Simplifications Made:**
- **Python/FastAPI instead of LogicBridge/Quarkus** - Faster POC development, validates approach
- **batch_process.py instead of Databricks** - Local emulation of pipeline logic
- **X-EPI header instead of JWT** - Authentication simulation
- **mock_personstore/ directory instead of PersonStore DB** - Flat file storage
- **No audit logging or monitoring** - Not needed for validation
- **Limited error handling** - Focus on happy path validation

**Production Migration Path:**
1. **Databricks Pipeline:** Adapt `batch_process.py` logic to Databricks Python notebooks
2. **LogicBridge Integration:** Port template engine logic to Java/Quarkus (or use GraalVM for Python interop)
3. **PersonStore Integration:** Replace flat file reading with database queries
4. **Authentication:** Integrate existing JWT validation in LogicBridge

---

### 5.3 Use Cases Implemented

#### Use Case 1: Price Estimation

**Description:** Display upcoming appointments with procedure cost estimates.

**Data Complexity:**
- Nested objects: Appointment → Provider, Costs
- Nested arrays: Appointment → Procedures
- Multiple data types: dates, currency, strings

**Configuration Files:**
- `use_cases/price_estimation/csv_transform.json`
- `configs/sections/home.json`
- `configs/sections/procedures.json`
- `configs/cards/appointment_card.json`
- `configs/cards/procedure_card.json`

**Key Features Validated:**
- ✅ Date type conversion and formatting
- ✅ Currency type conversion and display formatting
- ✅ Nested object creation
- ✅ Nested array creation
- ✅ Parameterized sections (drill-down to procedures)
- ✅ Filtering by path parameter
- ✅ Compute functions (len, sum, currency)

---

#### Use Case 2: Prescriptions

**Description:** Display active medications and medication history.

**Data Complexity:**
- Nested objects: Medication → Prescriber
- Nested arrays: Medication → Refills
- Filtering: Active vs all medications

**Configuration Files:**
- `use_cases/prescriptions/csv_transform.json`
- `configs/sections/active_medications.json`
- `configs/sections/medication_history.json`
- `configs/cards/medication_card.json`
- `configs/cards/medication_history_card.json`

**Key Features Validated:**
- ✅ Multiple sections from same data source
- ✅ Array filtering (active medications)
- ✅ Date formatting variations
- ✅ Conditional fields
- ✅ Compute functions (len for refill count)

---

#### Use Case 3: Health Screenings

**Description:** Display health screening tests and results.

**Configuration Files:**
- `use_cases/health_screenings/csv_transform.json`
- `configs/cards/health_screening_card.json`

**Key Features Validated:**
- ✅ Simple array structures
- ✅ Date handling for past events
- ✅ Conditional display of results

---

#### Use Case 4: Sorted Arrays Example

**Description:** Lab results sorted by different criteria.

**Configuration Files:**
- `use_cases/sorted_arrays_example/csv_transform.json`
- `use_cases/sorted_arrays_example/csv_transform_by_cost.json`
- `use_cases/sorted_arrays_example/csv_transform_by_name.json`

**Key Features Validated:**
- ✅ Array sorting by field (ascending/descending)
- ✅ Sorting by different data types (strings, currency, dates)
- ✅ Same data source with different sort orders

---

### 5.4 Test Results

**Test Framework:** `test_use_cases.py`

**Test Approach:**
1. Start FastAPI server
2. Make HTTP requests to all endpoints for each use case
3. Save actual responses to `use_cases/{name}/output_actual/`
4. Compare with expected responses in `use_cases/{name}/output_expected/`
5. Report any differences with detailed diff output

**Test Coverage:**
- **Price Estimation:** 6 endpoints tested (3 EPIs × 2 sections + parameterized)
- **Prescriptions:** 6 endpoints tested (3 EPIs × 2 sections)
- **Total Tests:** 12+ endpoint validations

**Results:**
- ✅ All tests passing
- ✅ Output matches expected for all use cases
- ✅ No data loss in transformations
- ✅ Correct type conversions
- ✅ Accurate template rendering

**Example Test Execution:**
```bash
$ python test_use_cases.py

Testing use case: price_estimation
  ✓ section_home_EPI123456.json
  ✓ section_home_EPI345678.json
  ✓ section_home_EPI789012.json
  ✓ section_procedures_EPI123456_APT001.json
  ✓ section_procedures_EPI123456_APT002.json
  ✓ section_procedures_EPI789012_APT001.json

Testing use case: prescriptions
  ✓ section_active_medications_EPI123456.json
  ✓ section_active_medications_EPI345678.json
  ✓ section_active_medications_EPI789012.json
  ✓ section_medication_history_EPI123456.json
  ✓ section_medication_history_EPI345678.json
  ✓ section_medication_history_EPI789012.json

All tests passed! ✓
```

---

### 5.5 POC Findings & Learnings

**Successful Validations:**

1. **Configuration Expressiveness**
   - ✅ Schema format handles all tested nested structures
   - ✅ Template syntax is intuitive and readable
   - ✅ No use cases required code changes

2. **Type System**
   - ✅ 7 data types cover healthcare data requirements
   - ✅ Date timezone handling works correctly
   - ✅ Currency parsing handles various input formats

3. **Template Engine**
   - ✅ Compute functions are powerful and composable
   - ✅ Conditional logic works as expected
   - ✅ JSONPath provides necessary data access flexibility

4. **Developer Experience**
   - ✅ Configuration files are human-readable
   - ✅ Errors are traceable to configuration issues
   - ✅ Iteration time is fast (no compilation/deployment)

**Challenges Encountered:**

1. **Configuration Debugging**
   - **Issue:** Template errors can be cryptic without good tooling
   - **Mitigation:** Added detailed error messages with context
   - **Production Need:** Configuration validation tool with live preview

2. **Nested Structure Complexity**
   - **Issue:** Deep nesting (4+ levels) becomes hard to visualize
   - **Mitigation:** Created examples and documentation
   - **Production Need:** Interactive configuration tool with visual preview

3. **Type Inference**
   - **Issue:** CSV columns default to strings without explicit type declaration
   - **Mitigation:** Required explicit `column_types` in schema
   - **Production Need:** Type inference from sample data

4. **Performance (Not Tested at Scale)**
   - **Issue:** POC uses flat files, not optimized for large datasets
   - **Mitigation:** N/A in POC
   - **Production Need:** Performance testing with realistic data volumes

**Gaps Identified:**

1. **Configuration Validation**
   - Need: JSON schema validation for config files
   - Need: Pre-deployment validation tooling

2. **Error Handling**
   - Need: Better error messages for configuration issues
   - Need: Graceful degradation for missing data

3. **Monitoring & Observability**
   - Need: Template evaluation metrics
   - Need: Configuration usage tracking
   - Need: Performance monitoring

---

### 5.6 POC Conclusion

**Feasibility: ✅ VALIDATED**

The proof-of-concept successfully demonstrates that a configuration-driven architecture can handle arbitrary structured healthcare data with zero code changes for new use cases.

**Key Validations:**
- ✅ All stated requirements are achievable
- ✅ Configuration formats are expressive enough for real use cases
- ✅ Template engine provides necessary flexibility
- ✅ Architecture is sound and scalable
- ✅ Multiple real-world use cases implemented successfully

**Confidence Level: HIGH**

The POC provides high confidence that this approach will scale to production. The architecture is clean, modular, and extensible. No fundamental blockers were identified.

**Remaining Work for Production:**
1. Replace POC components with production systems (Databricks, PersonStore DB, JWT auth)
2. Add configuration validation and tooling
3. Implement comprehensive error handling and monitoring
4. Conduct performance and scale testing
5. Develop configuration management workflows

**Recommendation: PROCEED TO PRODUCTION DEVELOPMENT**

---

## 6. Technical Tradeoffs & Limitations

### 6.1 Known Limitations

**1. Configuration Complexity**

**Limitation:** Learning curve for configuration formats
**Impact:** New developers need training on schema and template syntax
**Mitigation:**
- Comprehensive documentation (CSV_TRANSFORM_SCHEMA.md, TEMPLATE_FORMAT.md)
- Tutorial examples planned (TODO.md item #6)
- Interactive configuration tool planned (TODO.md item #5)

---

**2. Configuration Validation**

**Limitation:** No automated validation of configuration files
**Impact:** Errors may not be caught until runtime
**Mitigation:**
- JSON schema validation (to be implemented)
- Pre-deployment validation checks
- Comprehensive test suite for each use case

---

**3. Template Debugging**

**Limitation:** Limited tooling for debugging template evaluation
**Impact:** Troubleshooting configuration issues can be time-consuming
**Mitigation:**
- Detailed error messages with context
- Test-driven approach with expected outputs
- Development of configuration preview tool

---

**4. Server-Side vs Client-Side Rendering**

**Limitation:** Current POC renders all templates server-side
**Impact:**
- More server load
- Less client flexibility
- Cannot leverage client-side caching for partial updates

**Future Enhancement:** Separate syntax for server vs client templates (TODO.md item #5)

**Tradeoff Analysis:**
- **Server-Side Rendering (Current):**
  - ✅ Simpler mobile client
  - ✅ Consistent rendering across platforms
  - ✅ Easier to update templates without client deployment
  - ❌ More server load
  - ❌ Entire card must be re-fetched for updates

- **Client-Side Rendering:**
  - ✅ Reduced server load
  - ✅ Client-side caching of data
  - ✅ Partial updates possible
  - ❌ More complex mobile client
  - ❌ Need to version template syntax
  - ❌ Harder to update templates (client deployment required)

**POC Decision:** Server-side rendering for simplicity and future-proofing
**Production Consideration:** Hybrid approach with configurable rendering location

---

**5. Performance with Large Datasets**

**Limitation:** No performance testing with realistic data volumes
**Impact:** Unknown performance characteristics at scale
**Mitigation:**
- Use PersonStore database with proper indexing
- Implement caching layer (Redis)
- Add pagination for large result sets
- Performance testing plan for production

---

**6. Limited Compute Functions**

**Limitation:** Fixed set of template functions
**Impact:** Complex calculations may not be supported
**Current Functions:** len, sum, format_date, days_from_now, days_after, currency
**Future:** Extension mechanism for custom functions

---

### 6.2 Technical Debt from POC

**1. Mock PersonStore**
- **POC:** Flat JSON files in `mock_personstore/`
- **Production:** Real PersonStore database with proper indexing
- **Migration Effort:** Low - same file format

---

**2. Simplified Authentication**
- **POC:** X-EPI header for patient identification
- **Production:** JWT token validation with claims
- **Migration Effort:** Medium - well-understood pattern

---

**3. Limited Error Handling**
- **POC:** Basic error responses
- **Production:** Comprehensive error taxonomy, graceful degradation
- **Migration Effort:** Medium

---

**4. No Configuration Management**
- **POC:** Manual file editing
- **Production:** Version control, deployment pipeline, validation
- **Migration Effort:** High - needs tooling development

---

**5. No Monitoring/Observability**
- **POC:** No metrics or logging
- **Production:** APM, logging, alerting, dashboards
- **Migration Effort:** Medium - standard infrastructure

---

**6. No Caching Layer**
- **POC:** Direct file reads
- **Production:** Redis cache for frequently accessed data
- **Migration Effort:** Low - add caching middleware

---

### 6.3 Scalability Analysis

**Data Volume Scaling:**

| Component | POC | Production Target | Scaling Strategy |
|-----------|-----|-------------------|------------------|
| CSV Transform | < 100K rows | Millions of rows | Databricks distributed processing |
| PersonStore | 10s of files | Millions of records | NoSQL database with sharding |
| API Requests | < 100 req/sec | 10K+ req/sec | Horizontal scaling, load balancing |
| Template Eval | Simple | Complex nested | Caching, pre-compilation |

---

**Number of Use Cases:**

| Metric | POC | Production Target | Scaling Strategy |
|--------|-----|-------------------|------------------|
| Use cases | 4 | 50+ | Configuration management system |
| Card configs | 8 | 200+ | Modular, reusable card templates |
| Transform schemas | 4 | 50+ | Schema library, validation tools |

---

**Configuration Complexity:**

| Aspect | POC | Production | Mitigation |
|--------|-----|------------|------------|
| Max nesting depth | 3 levels | 5+ levels | Visual configuration tool |
| Fields per card | 10 | 50+ | Template composition, inheritance |
| Conditional logic | Simple | Complex | Testing framework, validation |

---

**API Throughput:**

**POC Performance (Estimated):**
- 50-100 requests/second on single instance
- ~50ms response time for simple cards
- No caching or optimization

**Production Targets:**
- 10,000+ requests/second (across cluster)
- < 100ms p99 response time
- Redis caching for hot data
- CDN for static configurations

**Scaling Approach:**
1. Horizontal scaling of API servers
2. Redis cluster for caching
3. CDN for configuration files
4. PersonStore read replicas
5. Connection pooling and rate limiting

---

## 7. Risks & Mitigation

### 7.1 Technical Risks

**Risk 1: Configuration Errors Lead to Data Display Issues**

**Probability:** Medium
**Impact:** High (incorrect data shown to patients)
**Mitigation:**
- **Pre-deployment:**
  - JSON schema validation for all configs
  - Automated test suite with expected outputs
  - Staging environment testing before production
- **Runtime:**
  - Comprehensive error handling with safe defaults
  - Configuration version control with rollback capability
  - Audit logging of configuration changes
- **Detection:**
  - Monitoring for error rates by configuration file
  - Automated alerts on template evaluation failures

---

**Risk 2: Template Engine Bugs**

**Probability:** Low-Medium
**Impact:** High (incorrect rendering, security issues)
**Mitigation:**
- **Prevention:**
  - Comprehensive unit tests for template engine
  - Security review of expression evaluation (no code execution)
  - Fuzz testing for edge cases
- **Detection:**
  - Automated testing on each deployment
  - Canary deployments to catch issues early
- **Response:**
  - Fast rollback capability
  - Clear escalation path for template engine issues

---

**Risk 3: Performance Degradation at Scale**

**Probability:** Medium
**Impact:** Medium (slow response times, user frustration)
**Mitigation:**
- **Prevention:**
  - Performance testing with realistic data volumes
  - Caching strategy (Redis)
  - Database query optimization
  - Horizontal scaling architecture
- **Detection:**
  - APM monitoring (response time, throughput)
  - Automated alerts on performance degradation
- **Response:**
  - Auto-scaling rules
  - Performance optimization runbook

---

**Risk 4: Data Loss During CSV Transformation**

**Probability:** Low
**Impact:** Critical (patient data loss)
**Mitigation:**
- **Prevention:**
  - Comprehensive validation of transform schemas
  - Row count verification (input vs output)
  - Data integrity checks
  - Schema versioning
- **Detection:**
  - Automated validation after each transform
  - Alert on row count mismatches
  - Manual spot-checking for new schemas
- **Response:**
  - Immediate halt of pipeline on validation failure
  - Reprocessing from source CSV

**Note:** POC identified and fixed a data loss bug (see `data_loss_bug/DATA_LOSS_BUG_DEMO.md`)

---

### 7.2 Operational Risks

**Risk 5: Configuration Management Complexity**

**Probability:** High
**Impact:** Medium (errors, confusion, version conflicts)
**Mitigation:**
- **Prevention:**
  - Git-based configuration version control
  - Code review process for configuration changes
  - Configuration deployment pipeline with validation
  - Clear naming conventions and organization
- **Tooling:**
  - Interactive configuration tool (TODO.md item #5)
  - Configuration validation CLI
  - Automated documentation generation
- **Training:**
  - Tutorial series for developers (TODO.md item #6)
  - Configuration best practices guide
  - Regular training sessions

---

**Risk 6: Support and Troubleshooting Burden**

**Probability:** Medium
**Impact:** Medium (support team overwhelmed)
**Mitigation:**
- **Documentation:**
  - Comprehensive troubleshooting guide
  - Common configuration errors and fixes
  - Runbooks for common issues
- **Tooling:**
  - Configuration validation tool
  - Template preview/debugging tool
  - Centralized error tracking
- **Training:**
  - Support team training on configuration system
  - Escalation path to engineering
  - Self-service diagnostic tools

---

**Risk 7: Configuration Version Drift**

**Probability:** Medium
**Impact:** Medium (inconsistencies across environments)
**Mitigation:**
- **Process:**
  - Single source of truth (Git repository)
  - Automated deployment pipeline
  - Environment-specific configuration branches
  - Configuration promotion workflow (dev → staging → prod)
- **Validation:**
  - Automated tests run on all configuration changes
  - Staging environment mirrors production
  - Configuration diff tool before production deploy

---

### 7.3 Business Risks

**Risk 8: Customer Adoption Challenges**

**Probability:** Medium
**Impact:** High (slow revenue growth)
**Mitigation:**
- **Enable customers:**
  - Interactive configuration tool reduces barrier to entry
  - Professional services for initial implementations
  - Template library of common patterns
- **Support:**
  - Dedicated customer success team
  - Training materials and workshops
  - Partner ecosystem for implementation support

---

**Risk 9: Timeline/Budget Overruns**

**Probability:** Medium
**Impact:** High (delayed launch, cost overruns)
**Mitigation:**
- **Planning:**
  - Phased rollout approach (MVP → enhancements)
  - Buffer time for unknowns (20-30%)
  - Clear scope definition with must-have vs nice-to-have
- **Execution:**
  - Agile development with 2-week sprints
  - Regular stakeholder updates
  - Early identification of blockers
- **Monitoring:**
  - Weekly progress tracking
  - Monthly budget reviews
  - Risk register updates

**[TODO: Add organization-specific timeline and budget constraints]**

---

**Risk 10: Competitive Timing**

**Probability:** **[TODO: Assess]**
**Impact:** **[TODO: Assess]**
**Mitigation:** **[TODO: Add competitive analysis and go-to-market strategy]**

---

## 8. Production Roadmap

### 8.1 Phase 1: Core Platform (MVP)

**Objective:** Production-ready core system supporting initial use cases

**Duration:** **[TODO: Estimate timeline]**

**Key Deliverables:**

1. **Databricks Integration**
   - Migrate `batch_process.py` logic to Databricks notebooks
   - Implement scheduled batch jobs
   - Add data validation and quality checks
   - Error handling and alerting

2. **PersonStore Database Integration**
   - Replace flat files with real PersonStore DB
   - Implement efficient querying by EPI + attribute
   - Add database indexing strategy
   - Connection pooling and retry logic

3. **Authentication & Authorization**
   - Replace X-EPI header with JWT validation
   - Integrate with existing auth system
   - Implement RBAC for different user roles
   - Patient consent verification

4. **Production Infrastructure**
   - FastAPI deployment on Kubernetes
   - Load balancing and auto-scaling
   - Redis cache layer
   - Monitoring and alerting (APM, logs, metrics)

5. **Configuration Management**
   - Git-based configuration repository
   - Automated validation on commit
   - Deployment pipeline (dev → staging → prod)
   - Rollback capability

6. **Testing & Quality**
   - Expanded test suite for all components
   - Performance/load testing
   - Security testing and penetration testing
   - HIPAA compliance audit

**Success Criteria:**
- Support 3-5 use cases in production
- < 100ms p99 API response time
- 99.9% uptime SLA
- All security/compliance requirements met

---

### 8.2 Phase 2: Configuration Tooling

**Objective:** Enable customer self-service through tooling

**Duration:** **[TODO: Estimate timeline]**

**Key Deliverables:**

1. **Interactive Configuration Tool** (TODO.md item #5)
   - Web-based configuration editor
   - Live preview of transformations and templates
   - Syntax validation and error highlighting
   - Template library of common patterns

2. **Configuration Validation**
   - JSON schema validation for configs
   - Pre-deployment validation CLI
   - Automated testing framework for configs
   - Configuration lint rules

3. **Tutorial & Documentation** (TODO.md item #6)
   - Step-by-step tutorial series
   - Video walkthroughs
   - Configuration best practices guide
   - API reference documentation

4. **Developer Experience**
   - Local development environment setup
   - Configuration preview in development
   - Debugging tools for template evaluation
   - Hot-reload for rapid iteration

**Success Criteria:**
- New use case can be configured in < 1 day
- 90% of configuration errors caught pre-deployment
- Customer self-service rate > 50%

---

### 8.3 Phase 3: Advanced Features

**Objective:** Enhanced functionality and optimizations

**Duration:** **[TODO: Estimate timeline]**

**Key Deliverables:**

1. **Server-Side vs Client-Side Templates** (TODO.md item #5)
   - New syntax to differentiate rendering location
   - Client SDK for template evaluation
   - Caching strategy for client-side rendering
   - Migration path for existing templates

2. **Text Formatting in Templates** (TODO.md item #7)
   - Markdown-style formatting support
   - Links and rich text elements
   - Conditional formatting (colors, emphasis)
   - HTML sanitization for security

3. **Advanced Compute Functions**
   - Custom function extension mechanism
   - Statistical functions (avg, median, percentile)
   - String manipulation functions
   - Date/time calculations

4. **Performance Optimizations**
   - Template pre-compilation
   - Query optimization for PersonStore
   - CDN for configuration files
   - GraphQL API option for flexible queries

5. **Configuration Analytics**
   - Usage tracking for configurations
   - Performance metrics by config
   - Error rate monitoring
   - Recommendations for optimization

**Success Criteria:**
- 50% reduction in server load through client-side rendering
- Support for 20+ use cases
- Configuration error rate < 1%

---

### 8.4 Phase 4: Scale & Polish

**Objective:** Enterprise-grade platform

**Duration:** **[TODO: Estimate timeline]**

**Key Deliverables:**

1. **Multi-Tenancy**
   - Tenant isolation for configurations
   - Per-tenant customization
   - White-label support

2. **Internationalization**
   - Multi-language support in templates
   - Locale-aware formatting (dates, currency)
   - Right-to-left text support

3. **Advanced Analytics**
   - Usage dashboards for customers
   - Data insights and recommendations
   - A/B testing for card configurations

4. **Partner Ecosystem**
   - API for third-party integrations
   - Marketplace for configuration templates
   - Partner certification program

**Success Criteria:**
- Support 50+ use cases
- Multi-region deployment
- 99.99% uptime SLA
- Customer NPS > 40

---

### 8.5 Resource Requirements

**[TODO: Fill in with organization-specific estimates]**

**Team Structure:**

| Role | Phase 1 | Phase 2 | Phase 3 | Phase 4 |
|------|---------|---------|---------|---------|
| Backend Engineers | X | X | X | X |
| Frontend Engineers | X | X | X | X |
| DevOps Engineers | X | X | X | X |
| QA Engineers | X | X | X | X |
| Product Manager | X | X | X | X |
| **Total** | **X** | **X** | **X** | **X** |

**Infrastructure:**
- **[TODO: Specify]** Kubernetes cluster capacity
- **[TODO: Specify]** Databricks compute units
- **[TODO: Specify]** PersonStore database capacity
- **[TODO: Specify]** Redis cache cluster
- **[TODO: Specify]** CDN bandwidth

**Budget:**
- **[TODO: Estimate]** Development costs
- **[TODO: Estimate]** Infrastructure costs (annual)
- **[TODO: Estimate]** Third-party services
- **[TODO: Estimate]** Training and documentation

**Timeline:**
- **[TODO: Estimate]** Phase 1: X months
- **[TODO: Estimate]** Phase 2: X months
- **[TODO: Estimate]** Phase 3: X months
- **[TODO: Estimate]** Phase 4: X months
- **Total:** **[TODO]** months to full production

---

## 9. References & Appendices

### 9.1 Documentation References

- **[README.md](README.md)** - Comprehensive project overview and usage guide
- **[CLAUDE.md](CLAUDE.md)** - Architecture summary for AI-assisted development
- **[CSV_TRANSFORM_SCHEMA.md](CSV_TRANSFORM_SCHEMA.md)** - Complete transform schema reference
- **[COLUMN_TYPES.md](COLUMN_TYPES.md)** - Data type conversion specifications
- **[TEMPLATE_FORMAT.md](TEMPLATE_FORMAT.md)** - Template syntax and expression documentation
- **[TODO.md](TODO.md)** - Completed enhancements and future roadmap

### 9.2 Code Repository

**Repository:** **[TODO: Add repository URL]**

**Key Directories:**
- `batch_process.py` - CSV transformation script
- `server.py` - FastAPI backend server
- `app/` - Modular application code
  - `config/` - Configuration loaders
  - `rendering/` - Card and section renderers
  - `template/` - Template engine
- `configs/` - Section and card configurations
- `use_cases/` - Example implementations with test data
- `mock_personstore/` - Generated JSON files (POC)
- `tests/` - Test suites

**Running the POC:**

```bash
# Install dependencies
pip install -r requirements.txt

# Transform CSV to JSON
python batch_process.py use_cases/price_estimation/price_estimates.csv \
                        use_cases/price_estimation/csv_transform.json

# Start server
python server.py

# Run tests
python test_use_cases.py
```

### 9.3 Appendix A: Use Case Examples

#### Price Estimation Use Case

**Business Need:** Display upcoming appointments with procedure cost estimates

**Input CSV:**
```csv
EPI,appointment_id,appointment_date,provider_name,provider_specialty,procedure_name,procedure_cost
EPI123456,APT001,2025-12-01,Dr. Smith,Cardiology,EKG,$150.00
EPI123456,APT001,2025-12-01,Dr. Smith,Cardiology,Blood Pressure,$50.00
```

**Transform Schema:** `use_cases/price_estimation/csv_transform.json`

**API Endpoints:**
- `GET /section/home` - All upcoming appointments
- `GET /section/procedures/{appointment_id}` - Procedures for specific appointment

**Output Example:**
```json
{
  "title": "Upcoming Appointments",
  "cards": [
    {
      "title": "Dr. Smith",
      "subtitle": "Cardiology",
      "date": "Dec 01",
      "days_until": "7 days",
      "procedure_count": "2 procedures",
      "total": "$200.00"
    }
  ]
}
```

**Files:**
- CSV: `use_cases/price_estimation/price_estimates.csv`
- Transform: `use_cases/price_estimation/csv_transform.json`
- Section configs: `configs/sections/home.json`, `configs/sections/procedures.json`
- Card configs: `configs/cards/appointment_card.json`, `configs/cards/procedure_card.json`
- Expected outputs: `use_cases/price_estimation/output_expected/`

---

#### Prescriptions Use Case

**Business Need:** Display active medications and medication history

**Input CSV:**
```csv
EPI,medication_name,dosage,frequency,start_date,end_date,prescriber_name,prescriber_specialty
EPI123456,Lisinopril,10mg,Once daily,2025-01-01,2025-12-31,Dr. Smith,Cardiology
```

**Transform Schema:** `use_cases/prescriptions/csv_transform.json`

**API Endpoints:**
- `GET /section/active_medications` - Current medications only
- `GET /section/medication_history` - All medications

**Output Example:**
```json
{
  "title": "Active Medications",
  "cards": [
    {
      "title": "Lisinopril",
      "subtitle": "10mg, Once daily",
      "prescriber": "Dr. Smith - Cardiology",
      "start_date": "Jan 01, 2025"
    }
  ]
}
```

**Files:**
- CSV: `use_cases/prescriptions/prescriptions.csv`
- Transform: `use_cases/prescriptions/csv_transform.json`
- Section configs: `configs/sections/active_medications.json`, `configs/sections/medication_history.json`
- Card configs: `configs/cards/medication_card.json`
- Expected outputs: `use_cases/prescriptions/output_expected/`

---

### 9.4 Appendix B: Configuration Quick Reference

#### Transform Schema Syntax

```json
{
  "@attribute": {
    "name": "namespace/attribute_name",
    "group_by": "identifier_column",
    "column_types": {
      "date_col": {"type": "date", "input_format": "YYYY-MM-DD"},
      "amount_col": {"type": "currency"},
      "count_col": "int"
    },
    "@array": {
      "group_by": "group_column",
      "sort_by": {"field": "sort_field", "order": "asc"},
      "@item": {
        "output_field": "{csv_column}",
        "nested_object": {
          "field1": "{column1}",
          "field2": "{column2}"
        }
      }
    }
  }
}
```

#### Template Syntax

```json
{
  "templates": {
    "root": {
      "field": "{$.data_field}",
      "nested": "{$.object.nested_field}",
      "formatted": "{$.date} at {$.time}",
      "count": "{len($.items)} items",
      "sum": "Total: {currency(sum($.items[*].cost))}",
      "date": "{format_date($.date, '%b %d')}",
      "relative": "In {days_from_now($.date)} days",
      "?conditional": "Only shown if truthy"
    }
  }
}
```

#### Compute Functions

| Function | Syntax | Example | Output |
|----------|--------|---------|--------|
| Length | `len(path)` | `{len($.items)}` | `3` |
| Sum | `sum(path)` | `{sum($.items[*].cost)}` | `156.99` |
| Format Date | `format_date(path, format)` | `{format_date($.date, '%b %d')}` | `"Dec 01"` |
| Days From Now | `days_from_now(path)` | `{days_from_now($.date)}` | `7` |
| Days After | `days_after(path1, path2)` | `{days_after($.start, $.end)}` | `14` |
| Currency | `currency(path)` | `{currency($.amount)}` | `"$1,089.99"` |

---

### 9.5 Glossary

| Term | Definition |
|------|------------|
| **PersonStore** | NoSQL database storing patient attribute data as JSON documents |
| **EPI** | Epic Patient Identifier - unique identifier for patients in Epic systems |
| **Card** | UI component displaying patient data fields (title, subtitle, metadata) |
| **Section** | Collection of related cards displayed together in the mobile app |
| **Transform Schema** | Declarative JSON configuration describing CSV-to-JSON transformation |
| **Template** | Configuration defining how to render data fields in cards |
| **JSONPath** | Query language for extracting data from JSON structures |
| **Processing Directive** | Configuration key with `@` prefix (not included in output) |
| **Compute Function** | Template function for calculations (len, sum, format_date, etc.) |
| **Conditional Field** | Template field prefixed with `?` that is omitted if value is falsy |
| **Path Parameter** | URL segment extracted as variable (e.g., `appointment_id` from `/section/procedures/APT001`) |

---

## Document Revision History

| Version | Date | Author | Changes |
|---------|------|--------|---------|
| 1.0 Draft | 2025-11-24 | **[TODO]** | Initial draft for production approval |

---

**END OF DOCUMENT**
