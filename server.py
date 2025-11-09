#!/usr/bin/env python3
"""
server.py - Prototype mobile app backend server

FastAPI-based server that renders card-based UI sections from patient attribute data
using declarative configuration files.
"""

import json
import re
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Dict, List, Optional

from fastapi import FastAPI, Header, HTTPException, Path as PathParam
from jsonpath_ng import parse as jsonpath_parse
from dateutil import parser as date_parser


app = FastAPI(title="Patient Data API", version="1.0.0")


# ============================================================================
# Configuration Loader
# ============================================================================

class ConfigLoader:
    """Loads section and card configuration files."""

    def __init__(self, config_dir: str = "configs"):
        self.config_dir = Path(config_dir)
        self.sections_dir = self.config_dir / "sections"
        self.cards_dir = self.config_dir / "cards"

    def load_section(self, section_name: str) -> Dict[str, Any]:
        """Load a section configuration by name."""
        section_file = self.sections_dir / f"{section_name}.json"
        if not section_file.exists():
            raise FileNotFoundError(f"Section config not found: {section_name}")

        with open(section_file) as f:
            return json.load(f)

    def load_card(self, card_name: str) -> Dict[str, Any]:
        """Load a card configuration by filename."""
        card_file = self.cards_dir / card_name
        if not card_file.exists():
            raise FileNotFoundError(f"Card config not found: {card_name}")

        with open(card_file) as f:
            return json.load(f)


# ============================================================================
# Attribute Loader
# ============================================================================

class AttributeLoader:
    """Loads patient attribute data from JSON files."""

    def __init__(self, output_dir: str = "mock_personstore"):
        self.output_dir = Path(output_dir)

    def load_attribute(self, epi: str, attribute_name: str) -> Any:
        """
        Load a patient attribute by EPI and attribute name.

        Args:
            epi: Patient identifier
            attribute_name: Attribute name (e.g., "_EHR/appointments")

        Returns:
            Parsed JSON data from the attribute file
        """
        # Convert attribute name to filename format
        safe_attr_name = attribute_name.replace("/", "_")
        filename = f"{epi}_{safe_attr_name}.json"
        attr_file = self.output_dir / filename

        if not attr_file.exists():
            raise FileNotFoundError(f"Attribute not found: {attribute_name} for patient {epi}")

        with open(attr_file) as f:
            return json.load(f)

    def get_available_patients(self) -> List[str]:
        """Get list of all patient EPIs with available data."""
        epis = set()
        for file in self.output_dir.glob("*__*.json"):
            epi = file.stem.split("_")[0]
            epis.add(epi)
        return sorted(epis)


# ============================================================================
# JSONPath Engine with Variable Substitution
# ============================================================================

class JSONPathEngine:
    """Evaluates JSONPath expressions with variable substitution."""

    @staticmethod
    def substitute_variables(expression: str, variables: Dict[str, str]) -> str:
        """
        Replace ${var_name} placeholders with actual values.

        Args:
            expression: JSONPath expression with ${...} placeholders
            variables: Dict mapping variable names to values

        Returns:
            Expression with variables substituted
        """
        def replace_var(match):
            var_name = match.group(1)
            return variables.get(var_name, match.group(0))

        return re.sub(r'\$\{(\w+)\}', replace_var, expression)

    @staticmethod
    def evaluate(expression: str, data: Any, variables: Optional[Dict[str, str]] = None) -> List[Any]:
        """
        Evaluate a JSONPath expression against data.

        Args:
            expression: JSONPath expression
            data: Data to query
            variables: Optional variables for substitution

        Returns:
            List of matching values
        """
        if variables:
            expression = JSONPathEngine.substitute_variables(expression, variables)

        jsonpath_expr = jsonpath_parse(expression)
        matches = jsonpath_expr.find(data)
        return [match.value for match in matches]


# ============================================================================
# Compute Functions
# ============================================================================

class ComputeFunctions:
    """Implements compute functions for card templates."""

    @staticmethod
    def len(items: Any) -> int:
        """Return length of array or list."""
        if isinstance(items, list):
            return len(items)
        return 0

    @staticmethod
    def sum(items: Any) -> float:
        """Sum numeric values, handling currency strings."""
        if not isinstance(items, list):
            return 0.0

        total = 0.0
        for item in items:
            if isinstance(item, (int, float)):
                total += item
            elif isinstance(item, str):
                # Try to parse currency strings like "$42.20"
                cleaned = item.replace("$", "").replace(",", "").strip()
                try:
                    total += float(cleaned)
                except ValueError:
                    continue
        return total

    @staticmethod
    def format_date(date_str: str, format_str: str) -> str:
        """Format a date string according to format."""
        try:
            dt = date_parser.parse(date_str)
            return dt.strftime(format_str)
        except Exception:
            return date_str

    @staticmethod
    def days_from_now(date_str: str) -> str:
        """Return relative days from now."""
        try:
            dt = date_parser.parse(date_str)
            today = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
            delta = (dt.replace(hour=0, minute=0, second=0, microsecond=0) - today).days

            if delta == 0:
                return "today"
            elif delta == 1:
                return "tomorrow"
            elif delta == -1:
                return "yesterday"
            elif delta > 0:
                return f"{delta} days from now"
            else:
                return f"{abs(delta)} days ago"
        except Exception:
            return date_str


# ============================================================================
# Expression Parser
# ============================================================================

class ExpressionParser:
    """Parses and evaluates card template expressions."""

    # Pattern to match {expression} in template strings
    EXPR_PATTERN = re.compile(r'\{([^}]+)\}')

    # Pattern to match function calls like len(...), sum(...), etc.
    FUNC_PATTERN = re.compile(r'(\w+)\((.*?)\)')

    def __init__(self, jsonpath_engine: JSONPathEngine, compute_funcs: ComputeFunctions):
        self.jsonpath = jsonpath_engine
        self.compute = compute_funcs

    def evaluate_expression(self, expr: str, data: Any, variables: Optional[Dict[str, str]] = None) -> Any:
        """
        Evaluate a single expression (content within {}).

        Args:
            expr: Expression string (e.g., "$.field" or "len($.array)")
            data: Data context
            variables: Optional path variables

        Returns:
            Evaluated value
        """
        expr = expr.strip()

        # Check if it's a function call
        func_match = self.FUNC_PATTERN.match(expr)
        if func_match:
            func_name = func_match.group(1)
            arg_expr = func_match.group(2).strip()

            # Evaluate the argument (usually a JSONPath)
            if arg_expr.startswith('$'):
                results = self.jsonpath.evaluate(arg_expr, data, variables)
                arg_value = results[0] if results else None
            else:
                # Literal argument
                arg_value = arg_expr.strip('"\'')

            # Call the compute function
            if func_name == "len":
                return self.compute.len(arg_value)
            elif func_name == "sum":
                return self.compute.sum(arg_value)
            elif func_name == "format_date":
                # format_date takes two arguments
                args = [a.strip().strip('"\'') for a in arg_expr.split(',')]
                if len(args) == 2:
                    # First arg is JSONPath, second is format string
                    date_results = self.jsonpath.evaluate(args[0], data, variables)
                    date_val = date_results[0] if date_results else ""
                    return self.compute.format_date(str(date_val), args[1])
                return arg_value
            elif func_name == "days_from_now":
                return self.compute.days_from_now(str(arg_value))

        # Otherwise, it's a JSONPath expression
        if expr.startswith('$'):
            # For simple field access like $.field or $.nested.field, use direct dict access
            if expr.startswith('$.') and '[' not in expr and '(' not in expr:
                # Simple field path like $.name or $.costs.copay
                path_parts = expr[2:].split('.')  # Remove $. and split by .
                value = data
                for part in path_parts:
                    if isinstance(value, dict):
                        value = value.get(part, "")
                    else:
                        value = ""
                        break
                return value
            else:
                # Complex JSONPath expression
                results = self.jsonpath.evaluate(expr, data, variables)
                return results[0] if results else ""

        # Literal value
        return expr

    def evaluate_template_string(self, template: str, data: Any, variables: Optional[Dict[str, str]] = None) -> str:
        """
        Evaluate a template string with embedded {expressions}.

        Args:
            template: Template string (e.g., "Date: {$.date} at {$.time}")
            data: Data context
            variables: Optional path variables

        Returns:
            String with all expressions evaluated and substituted
        """
        def replace_expr(match):
            expr = match.group(1)
            value = self.evaluate_expression(expr, data, variables)
            return str(value) if value is not None else ""

        return self.EXPR_PATTERN.sub(replace_expr, template)


# ============================================================================
# Card Renderer
# ============================================================================

class CardRenderer:
    """Renders cards from data using card configuration templates."""

    def __init__(self, config_loader: ConfigLoader, attr_loader: AttributeLoader):
        self.config_loader = config_loader
        self.attr_loader = attr_loader
        self.jsonpath = JSONPathEngine()
        self.compute = ComputeFunctions()
        self.expr_parser = ExpressionParser(self.jsonpath, self.compute)

    def render_cards(
        self,
        card_config_name: str,
        epi: str,
        variables: Optional[Dict[str, str]] = None
    ) -> List[Dict[str, Any]]:
        """
        Render cards using a card configuration.

        Args:
            card_config_name: Name of card config file
            epi: Patient identifier
            variables: Optional path variables for substitution

        Returns:
            List of rendered card dictionaries
        """
        # Load card configuration
        card_config = self.config_loader.load_card(card_config_name)

        # Extract config components
        attribute_name = card_config.get("attribute")
        foreach_expr = card_config.get("foreach", "$")
        filter_by = card_config.get("filter_by")
        extract = card_config.get("extract")
        template = card_config.get("template", {})

        # Load patient attribute data
        attribute_data = self.attr_loader.load_attribute(epi, attribute_name)

        # Evaluate foreach to get list of items
        items = self.jsonpath.evaluate(foreach_expr, attribute_data, variables)

        # Apply filter if specified
        if filter_by:
            field = filter_by.get("field")
            value = filter_by.get("value")
            # Substitute variables in value
            if value and variables:
                value = self.jsonpath.substitute_variables(value, variables)
            # Filter items
            items = [item for item in items if item.get(field) == value]

        # Extract nested data if specified
        if extract:
            extracted_items = []
            for item in items:
                nested_data = item.get(extract, [])
                if isinstance(nested_data, list):
                    extracted_items.extend(nested_data)
                else:
                    extracted_items.append(nested_data)
            items = extracted_items

        # Render a card for each item
        cards = []
        for item in items:
            card = self.render_single_card(template, item, variables)
            if card:  # Only include if not empty (conditional fields might remove all)
                cards.append(card)

        return cards

    def render_single_card(
        self,
        template: Dict[str, Any],
        data: Any,
        variables: Optional[Dict[str, str]] = None
    ) -> Dict[str, Any]:
        """
        Render a single card from template and data.

        Args:
            template: Card template dictionary
            data: Data item
            variables: Optional path variables

        Returns:
            Rendered card dictionary
        """
        card = {}

        for field_name, field_value in template.items():
            # Check if field is conditional (prefixed with ?)
            is_conditional = False
            if isinstance(field_value, str) and field_value.startswith("?"):
                is_conditional = True
                field_value = field_value[1:]  # Remove ? prefix

            # Evaluate the field value
            if isinstance(field_value, str):
                rendered_value = self.expr_parser.evaluate_template_string(field_value, data, variables)
            else:
                rendered_value = field_value

            # For conditional fields, check if value is truthy
            if is_conditional:
                if not rendered_value or rendered_value == "" or rendered_value == "0":
                    continue  # Skip this field

            card[field_name] = rendered_value

        return card


# ============================================================================
# Section Renderer
# ============================================================================

class SectionRenderer:
    """Renders complete sections with multiple card types."""

    def __init__(self, config_loader: ConfigLoader, card_renderer: CardRenderer):
        self.config_loader = config_loader
        self.card_renderer = card_renderer

    def render_section(
        self,
        section_name: str,
        epi: str,
        variables: Optional[Dict[str, str]] = None
    ) -> Dict[str, Any]:
        """
        Render a complete section.

        Args:
            section_name: Name of section config
            epi: Patient identifier
            variables: Optional path variables

        Returns:
            Section response with title, description, and cards
        """
        # Load section configuration
        section_config = self.config_loader.load_section(section_name)

        # Extract section metadata
        title = section_config.get("title", "")
        description = section_config.get("description", "")
        card_configs = section_config.get("cards", [])

        # Render all cards in order
        all_cards = []
        for card_config_name in card_configs:
            try:
                cards = self.card_renderer.render_cards(card_config_name, epi, variables)
                all_cards.extend(cards)
            except FileNotFoundError as e:
                # Log and continue if a card config or attribute is missing
                print(f"Warning: {e}")
                continue

        return {
            "title": title,
            "description": description,
            "cards": all_cards
        }


# ============================================================================
# FastAPI Application
# ============================================================================

# Initialize components
config_loader = ConfigLoader()
attr_loader = AttributeLoader()
card_renderer = CardRenderer(config_loader, attr_loader)
section_renderer = SectionRenderer(config_loader, card_renderer)


@app.get("/section/{section_name}")
async def get_section(
    section_name: str,
    x_epi: str = Header(..., alias="X-EPI")
):
    """
    Get a section with rendered cards.

    Args:
        section_name: Name of the section (e.g., "home")
        x_epi: Patient identifier from X-EPI header

    Returns:
        Section data with title, description, and cards
    """
    try:
        result = section_renderer.render_section(section_name, x_epi)
        return result
    except FileNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error rendering section: {str(e)}")


@app.get("/section/procedures/{appointment_id}")
async def get_procedures_section(
    appointment_id: str = PathParam(...),
    x_epi: str = Header(..., alias="X-EPI")
):
    """
    Get procedures section for a specific appointment.

    Args:
        appointment_id: Appointment identifier from path
        x_epi: Patient identifier from X-EPI header

    Returns:
        Section data with procedure cards
    """
    try:
        variables = {"appointment_id": appointment_id}
        result = section_renderer.render_section("procedures", x_epi, variables)
        return result
    except FileNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error rendering section: {str(e)}")


@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {"status": "healthy", "version": "1.0.0"}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
