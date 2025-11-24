# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

A Python-based prototype system for transforming CSV healthcare data into NoSQL JSON documents and serving it through a configuration-driven FastAPI backend. The core innovation is enabling new use cases and data structures without code changes - only JSON configuration files need to be created.

**Key Components:**
- `batch_process.py`: CLI tool for CSV-to-JSON transformation using declarative schemas
- `server.py`: FastAPI backend serving card-based UI data via REST endpoints
- `app/`: Modular application code (config loaders, rendering, template engine)
- `configs/`: Section and card configurations for UI rendering
- `mock_personstore/`: Generated JSON files (simulates PersonStore database)
- `use_cases/`: Example implementations with test data and expected outputs

## Common Commands

### Development Setup
```bash
# Install dependencies
pip install -r requirements.txt

# Dependencies: fastapi, uvicorn, jsonpath-ng, python-dateutil
```

### Running the Application
```bash
# Transform CSV to JSON (batch processing)
python batch_process.py <csv_file> <transform_config.json> [-o output_dir]

# Example: Process price estimation use case
python batch_process.py use_cases/price_estimation/price_estimates.csv \
                        use_cases/price_estimation/csv_transform.json

# Start the FastAPI server
python server.py
# Server runs at http://localhost:8000

# Test all use cases (starts server, runs tests, compares outputs)
python test_use_cases.py

# Quick test script
./test.sh
```

### Testing Endpoints
```bash
# Simple section endpoint
curl -H "X-EPI: EPI123456" http://localhost:8000/section/home

# Parameterized section endpoint
curl -H "X-EPI: EPI123456" http://localhost:8000/section/procedures/APT001

# Health check
curl http://localhost:8000/health
```

## Architecture

### Data Flow Pipeline

1. **CSV Input** → `batch_process.py` → **JSON Output** (mock_personstore/)
2. **JSON Files** → `server.py` → **REST API** → Mobile App

### Batch Processing Architecture (`batch_process.py`)

Three-stage pipeline modeled after Databricks:
- **load()**: Read CSV and transformation config
- **cleanse()**: Validate and type-convert data (7 types: string, int, float, bool, null, currency, date)
- **combine()**: Apply declarative schema to create nested JSON structures

The transformation uses an `@`-prefix convention where `@` indicates processing directives (not output fields).

### Server Architecture (`server.py`)

Configuration-driven with zero use-case-specific code:

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
- `app/config/loaders.py`: ConfigLoader, AttributeLoader for loading JSON files
- `app/rendering/card_renderer.py`: Evaluates card templates against data
- `app/rendering/section_renderer.py`: Orchestrates card rendering for sections
- `app/template/engine.py`: JSONPath evaluation and expression parsing
- `app/template/functions.py`: Compute functions (date formatting, currency, etc.)
- `app/template/conditions.py`: Conditional logic evaluation

### Template System

Inspired by StringTemplate (Terrence Parr), supports four canonical operations:

1. **Attribute Reference**: JSONPath syntax `{$.field}`, `{$.nested.field}`
2. **Template Reference**: Reusable templates with arguments
3. **Conditional Include**: Show/hide based on conditions, prefix with `?`
4. **Template Application to Lists**: Apply templates to array items

**Template Expression Types:**
- Field access: `{$.medication_name}`
- String formatting: `{$.date} at {$.time}`
- Functions: `{len($.items)}`, `{sum($.costs)}`, `{format_date($.date, '%b %d')}`, `{currency($.amount)}`
- Conditionals: `?` prefix omits field if falsy
- Path variables: `${appointment_id}` for URL parameters

See TEMPLATE_FORMAT.md for complete documentation.

### Configuration System

**Section Config** (`configs/sections/*.json`):
```json
{
  "title": "Section Title",
  "description": "Description",
  "path_parameters": ["param_name"],  // Optional URL params
  "cards": ["card_file.json"]
}
```

**Card Config** (`configs/cards/*.json`):
```json
{
  "attribute": "_EHR/appointments",
  "foreach": "$[*]",
  "filter_by": {"field": "id", "value": "${param}"},
  "extract": "nested_field",
  "templates": {
    "root": {
      "title": "{$.name}",
      "count": "{len($.items)}"
    }
  }
}
```

### URL Routing and Path Parameters

The server extracts path parameters from URLs based on section configuration:

- Section config defines: `"path_parameters": ["appointment_id"]`
- URL `/section/procedures/APT001` extracts `appointment_id=APT001`
- Card configs reference via `${appointment_id}` for filtering

## CSV Transform Schema

Uses `@`-prefixed directives to distinguish processing instructions from output fields:

- `@attribute`: Top-level container with metadata
- `@array`: Define arrays (with `group_by` or `collect`)
- `@item`: Template for array elements
- `@object`: Define objects
- `{column_name}`: CSV column substitution
- Keys without `@`: Output field names

**Type Conversions:**
Defined in `column_types` field with 7 supported types:
- Simple: `"age": "int"`, `"active": "bool"`
- Complex: `"date": {"type": "date", "input_format": "YYYY-MM-DD", "timezone": "America/New_York"}`
- Currency: `"amount": {"type": "currency", "currency": "USD"}`

See CSV_TRANSFORM_SCHEMA.md and COLUMN_TYPES.md for complete reference.

## Key Design Principles

1. **Configuration-Driven**: New use cases require only JSON configs, no code changes
2. **Zero Use-Case-Specific Code**: Server and batch processor are completely generic
3. **Declarative Transformation**: CSV schema uses templates, not procedural code
4. **Modular Architecture**: Clear separation between config loading, rendering, and templating
5. **Test-Driven**: Each use case has expected outputs for validation

## Working with This Codebase

### Adding a New Use Case

1. Create CSV file in `use_cases/new_case/`
2. Create `csv_transform.json` schema
3. Run batch process to generate JSON in `mock_personstore/`
4. Create section configs in `configs/sections/`
5. Create card configs in `configs/cards/`
6. Create expected outputs in `use_cases/new_case/output_expected/`
7. Run `python test_use_cases.py` to validate

### Modifying the Template Engine

The template system is in `app/template/`:
- Add new functions to `functions.py` (ComputeFunctions class)
- Add new conditional logic to `conditions.py` (ConditionEvaluator class)
- Modify expression parsing in `engine.py` (ExpressionParser class)

### Understanding Data Flow

1. CSV → `batch_process.py` applies `csv_transform.json` → JSON files in `mock_personstore/`
2. API request → `server.py` → SectionRenderer loads section config
3. For each card in section → CardRenderer loads card config and patient data
4. TemplateEngine evaluates templates against data → Rendered cards returned

## Important Files for Reference

- `README.md`: Comprehensive system documentation with examples
- `CSV_TRANSFORM_SCHEMA.md`: Complete schema reference for transformations
- `COLUMN_TYPES.md`: Data type conversion specifications
- `TEMPLATE_FORMAT.md`: Template syntax and expression documentation
- `GEMINI.md`: Alternative overview (less detailed than README)

## Notes

- The project uses a virtual environment (`venv/`) - activate before running
- `mock_personstore/` directory simulates PersonStore database with flat JSON files
- File naming convention: `{EPI}_{attribute_name}.json` (e.g., `EPI123456__EHR_appointments.json`)
- X-EPI header simulates JWT authentication (contains Epic Patient Identifier)
- The system is a proof-of-concept to validate the feasibility of configuration-driven healthcare data rendering
