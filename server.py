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
from typing import Any, Dict, List, Optional, Match

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
        def replace_var(match: Match[str]) -> str:
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

    @staticmethod
    def days_after(date_str: str) -> int:
        """
        Return number of days after a given date.
        Positive if date is in the past (e.g., 5 days overdue).
        Negative if date is in the future (e.g., -5 means due in 5 days).
        Zero if date is today.
        """
        try:
            dt = date_parser.parse(date_str)
            today = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
            delta = (today - dt.replace(hour=0, minute=0, second=0, microsecond=0)).days
            return delta
        except Exception:
            return 0


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

    @staticmethod
    def split_function_args(arg_str: str) -> List[str]:
        """
        Split function arguments by comma, respecting quoted strings.

        Example: "$.field, 'value, with comma'" -> ["$.field", "'value, with comma'"]
        """
        args = []
        current_arg = []
        in_quote = False
        quote_char = None

        for char in arg_str:
            if char in ('"', "'") and not in_quote:
                in_quote = True
                quote_char = char
                current_arg.append(char)
            elif char == quote_char and in_quote:
                in_quote = False
                quote_char = None
                current_arg.append(char)
            elif char == ',' and not in_quote:
                args.append(''.join(current_arg).strip())
                current_arg = []
            else:
                current_arg.append(char)

        # Add the last argument
        if current_arg:
            args.append(''.join(current_arg).strip())

        return args

    def evaluate_pipe_expression(
        self,
        expr: str,
        data: Any,
        variables: Optional[Dict[str, str]] = None,
        templates: Optional[Dict[str, Any]] = None,
        card_renderer: Optional['CardRenderer'] = None
    ) -> str:
        """
        Evaluate a pipe expression: {$.array|@template|separator=', '}

        Args:
            expr: Pipe expression (e.g., "$.procedures|@procedure_item|separator=', '")
            data: Data context
            variables: Optional path variables
            templates: Templates dict
            card_renderer: CardRenderer for template application

        Returns:
            Joined string result
        """
        if not templates or not card_renderer:
            return str(expr)

        # Split by pipe, respecting quotes
        parts = [p.strip() for p in expr.split('|')]

        if len(parts) < 2:
            return str(expr)

        # First part is the array path
        array_path = parts[0]

        # Second part is the template reference
        template_ref = parts[1]
        if not template_ref.startswith('@'):
            return str(expr)  # Invalid format

        template_name = template_ref[1:]  # Remove @

        # Third part (optional) is separator
        separator = '\n'  # Default separator
        if len(parts) >= 3:
            separator_part = parts[2]
            # Parse separator='...'
            if '=' in separator_part:
                _, sep_value = separator_part.split('=', 1)
                separator = sep_value.strip().strip('"\'')
                # Handle escape sequences
                separator = separator.replace('\\n', '\n').replace('\\t', '\t')

        # Evaluate the array path to get the list
        array_results = self.jsonpath.evaluate(array_path, data, variables)
        array_data = array_results[0] if array_results else []

        if not isinstance(array_data, list):
            return str(array_data)

        # Apply template to each item
        rendered_items = []
        for item in array_data:
            # Get the template
            if template_name not in templates:
                rendered_items.append(str(item))
                continue

            template_def = templates[template_name]

            # Render the template for this item
            if isinstance(template_def, str):
                # String template - evaluate it
                rendered = card_renderer.evaluate_field_value(template_def, item, variables, templates)
                rendered_items.append(rendered)
            else:
                # Dict template (conditional) - evaluate it
                rendered = card_renderer.evaluate_conditional_template(template_def, item, variables, templates)
                rendered_items.append(rendered)

        # Join with separator
        return separator.join(rendered_items)

    def evaluate_expression(
        self,
        expr: str,
        data: Any,
        variables: Optional[Dict[str, str]] = None,
        templates: Optional[Dict[str, Any]] = None,
        card_renderer: Optional['CardRenderer'] = None
    ) -> Any:
        """
        Evaluate a single expression (content within {}).

        Args:
            expr: Expression string (e.g., "$.field" or "len($.array)")
            data: Data context
            variables: Optional path variables
            templates: Optional templates dict for pipe operator
            card_renderer: Optional CardRenderer for template application

        Returns:
            Evaluated value
        """
        expr = expr.strip()

        # Check if it's a pipe operator expression ($.array|@template)
        if '|' in expr and card_renderer:
            return self.evaluate_pipe_expression(expr, data, variables, templates, card_renderer)

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
                args = self.split_function_args(arg_expr)
                if len(args) == 2:
                    # First arg is JSONPath, second is format string
                    date_results = self.jsonpath.evaluate(args[0], data, variables)
                    date_val = date_results[0] if date_results else ""
                    # Strip quotes from format string
                    format_str = args[1].strip('"\'')
                    return self.compute.format_date(str(date_val), format_str)
                return arg_value
            elif func_name == "days_from_now":
                return self.compute.days_from_now(str(arg_value))
            elif func_name == "days_after":
                return self.compute.days_after(str(arg_value))

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

        # Check if it's a parameter reference (for parameterized templates)
        if variables and expr in variables:
            return variables[expr]

        # Literal value
        return expr

    def evaluate_template_string(
        self,
        template: str,
        data: Any,
        variables: Optional[Dict[str, str]] = None,
        templates: Optional[Dict[str, Any]] = None,
        card_renderer: Optional['CardRenderer'] = None
    ) -> str:
        """
        Evaluate a template string with embedded {expressions}.

        Args:
            template: Template string (e.g., "Date: {$.date} at {$.time}")
            data: Data context
            variables: Optional path variables
            templates: Optional templates dict for pipe operator
            card_renderer: Optional CardRenderer for template application

        Returns:
            String with all expressions evaluated and substituted
        """
        def replace_expr(match: Match[str]) -> str:
            expr = match.group(1)
            value = self.evaluate_expression(expr, data, variables, templates, card_renderer)
            return str(value) if value is not None else ""

        return self.EXPR_PATTERN.sub(replace_expr, template)


# ============================================================================
# Condition Evaluator
# ============================================================================

class ConditionEvaluator:
    """Evaluates conditional expressions for template logic."""

    def __init__(self, jsonpath: JSONPathEngine, compute: ComputeFunctions, expr_parser: 'ExpressionParser'):
        self.jsonpath = jsonpath
        self.compute = compute
        self.expr_parser = expr_parser

    def evaluate_condition(self, condition: str, data: Any, variables: Optional[Dict[str, str]] = None) -> bool:
        """
        Evaluate a condition expression.

        Supports:
        - Comparisons: ==, !=, >, <, >=, <=
        - Logical: &&, ||, !
        - Functions: len(), sum(), days_from_now(), etc.

        Args:
            condition: Condition expression (e.g., "$.amount > 0", "len($.items) < 2")
            data: Data context
            variables: Optional path variables

        Returns:
            Boolean result
        """
        condition = condition.strip()

        # Handle logical OR (||)
        if "||" in condition:
            parts = condition.split("||")
            return any(self.evaluate_condition(part.strip(), data, variables) for part in parts)

        # Handle logical AND (&&)
        if "&&" in condition:
            parts = condition.split("&&")
            return all(self.evaluate_condition(part.strip(), data, variables) for part in parts)

        # Handle logical NOT (!)
        if condition.startswith("!"):
            return not self.evaluate_condition(condition[1:].strip(), data, variables)

        # Handle comparison operators
        for op in ["==", "!=", ">=", "<=", ">", "<"]:
            if op in condition:
                parts = condition.split(op, 1)
                if len(parts) == 2:
                    left_val = self.evaluate_value(parts[0].strip(), data, variables)
                    right_val = self.evaluate_value(parts[1].strip(), data, variables)

                    # Compare
                    if op == "==":
                        return left_val == right_val
                    elif op == "!=":
                        return left_val != right_val
                    elif op == ">":
                        return float(left_val) > float(right_val)
                    elif op == "<":
                        return float(left_val) < float(right_val)
                    elif op == ">=":
                        return float(left_val) >= float(right_val)
                    elif op == "<=":
                        return float(left_val) <= float(right_val)

        # Simple boolean expression - evaluate and check truthiness
        val = self.evaluate_value(condition, data, variables)
        return bool(val)

    def evaluate_value(self, expr: str, data: Any, variables: Optional[Dict[str, str]] = None) -> Any:
        """
        Evaluate an expression to get its value.

        Args:
            expr: Expression (e.g., "$.field", "len($.items)", "42", "'text'")
            data: Data context
            variables: Optional path variables

        Returns:
            Evaluated value
        """
        expr = expr.strip()

        # String literal
        if (expr.startswith("'") and expr.endswith("'")) or (expr.startswith('"') and expr.endswith('"')):
            return expr[1:-1]

        # Numeric literal
        try:
            if "." in expr:
                return float(expr)
            else:
                return int(expr)
        except ValueError:
            pass

        # Boolean literals
        if expr.lower() == "true":
            return True
        if expr.lower() == "false":
            return False

        # Otherwise, evaluate as an expression (JSONPath or function call)
        return self.expr_parser.evaluate_expression(expr, data, variables)


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
        self.condition_evaluator = ConditionEvaluator(self.jsonpath, self.compute, self.expr_parser)

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
        if not attribute_name or not isinstance(attribute_name, str):
            raise ValueError(f"Card config '{card_config_name}' missing required 'attribute' field")

        foreach_expr = card_config.get("foreach", "$")
        filter_by = card_config.get("filter_by")
        extract = card_config.get("extract")

        # Support both old "template" and new "templates.root" format
        if "templates" in card_config:
            templates = card_config["templates"]
            if "root" not in templates:
                raise ValueError(f"Card config '{card_config_name}' has 'templates' but missing 'root' template")
            template = templates["root"]
        else:
            # Backward compatibility with old "template" format
            template = card_config.get("template", {})
            templates = {}  # Empty templates dict for old format

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
            card = self.render_single_card(template, item, variables, templates)
            if card:  # Only include if not empty (conditional fields might remove all)
                cards.append(card)

        return cards

    def render_single_card(
        self,
        template: Dict[str, Any],
        data: Any,
        variables: Optional[Dict[str, str]] = None,
        templates: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Render a single card from template and data.

        Args:
            template: Card template dictionary
            data: Data item
            variables: Optional path variables
            templates: Optional templates dict for template references

        Returns:
            Rendered card dictionary
        """
        if templates is None:
            templates = {}

        card = {}

        for field_name, field_value in template.items():
            # Check if field name is conditional (prefixed with ?)
            is_conditional = False
            actual_field_name = field_name
            if field_name.startswith("?"):
                is_conditional = True
                actual_field_name = field_name[1:]  # Remove ? prefix from field name

            # Evaluate the field value
            if isinstance(field_value, str):
                rendered_value = self.evaluate_field_value(field_value, data, variables, templates)
            else:
                rendered_value = field_value

            # For conditional fields, check if value is truthy
            if is_conditional:
                if not rendered_value or rendered_value == "" or rendered_value == "0":
                    continue  # Skip this field

            card[actual_field_name] = rendered_value

        return card

    def evaluate_field_value(
        self,
        field_value: str,
        data: Any,
        variables: Optional[Dict[str, str]] = None,
        templates: Optional[Dict[str, Any]] = None
    ) -> str:
        """
        Evaluate a field value, handling template references.

        Args:
            field_value: The template string or template reference
            data: Data context
            variables: Optional path variables
            templates: Templates dict for resolving references

        Returns:
            Evaluated value
        """
        if templates is None:
            templates = {}

        # Check if it's a pure template reference (@template_name with no other content)
        if field_value.startswith("@") and " " not in field_value and "\n" not in field_value:
            template_name = field_value[1:]  # Remove @ prefix

            # Look up the template
            if template_name not in templates:
                raise ValueError(f"Template reference '@{template_name}' not found in templates")

            referenced_template = templates[template_name]

            # Recursively evaluate the referenced template
            if isinstance(referenced_template, str):
                # It's a string template, evaluate it
                return self.evaluate_field_value(referenced_template, data, variables, templates)
            elif isinstance(referenced_template, dict):
                # It's a dict (conditional template)
                return self.evaluate_conditional_template(referenced_template, data, variables, templates)
            else:
                return str(referenced_template)

        # Otherwise, expand any @template_name references in the string, then evaluate
        expanded_value = self.expand_template_references(field_value, data, variables, templates)
        return self.expr_parser.evaluate_template_string(expanded_value, data, variables, templates, self)

    def expand_template_references(
        self,
        text: str,
        data: Any,
        variables: Optional[Dict[str, str]] = None,
        templates: Optional[Dict[str, Any]] = None
    ) -> str:
        """
        Expand all @template_name references in a string.

        Args:
            text: Text containing possible template references
            data: Data context
            variables: Optional path variables
            templates: Templates dict

        Returns:
            Text with all @template_name references expanded
        """
        if templates is None:
            templates = {}

        # Pattern to match @template_name or @template_name(args)
        # But NOT when preceded by | (pipe operator for list application)
        import re
        template_ref_pattern = re.compile(r'(?<!\|)@(\w+)(?:\((.*?)\))?')

        def replace_template_ref(match: Match[str]) -> str:
            template_name = match.group(1)
            args_str = match.group(2)  # May be None if no arguments

            # Look up the template - check both with and without parameters
            referenced_template = None
            template_key = None
            param_names = []

            # First, try to find a parameterized version
            if args_str is not None:
                # Look for "template_name(param1, param2, ...)" in templates
                for key in templates.keys():
                    if key.startswith(f"{template_name}(") and key.endswith(")"):
                        # Extract parameter names from key
                        param_part = key[len(template_name)+1:-1]  # Remove "template_name(" and ")"
                        param_names = [p.strip() for p in param_part.split(',')]
                        referenced_template = templates[key]
                        template_key = key
                        break

            # If not found, try non-parameterized version
            if referenced_template is None and template_name in templates:
                referenced_template = templates[template_name]
                template_key = template_name

            if referenced_template is None:
                raise ValueError(f"Template reference '@{template_name}' not found in templates")

            # If we have arguments, bind them to parameters
            param_values = {}
            if args_str and param_names:
                # Parse and evaluate arguments
                arg_exprs = self.expr_parser.split_function_args(args_str)

                if len(arg_exprs) != len(param_names):
                    raise ValueError(f"Template '{template_key}' expects {len(param_names)} arguments, got {len(arg_exprs)}")

                for param_name, arg_expr in zip(param_names, arg_exprs):
                    # Evaluate the argument expression
                    arg_value = self.evaluate_argument(arg_expr, data, variables)
                    param_values[param_name] = str(arg_value)

            # Recursively evaluate the referenced template with bound parameters
            if isinstance(referenced_template, str):
                return self.evaluate_field_value(referenced_template, data, param_values if param_values else variables, templates)
            elif isinstance(referenced_template, dict):
                # Dict template (conditional)
                return self.evaluate_conditional_template(referenced_template, data, param_values if param_values else variables, templates)
            else:
                return str(referenced_template)

        return template_ref_pattern.sub(replace_template_ref, text)

    def evaluate_argument(
        self,
        arg_expr: str,
        data: Any,
        variables: Optional[Dict[str, str]] = None
    ) -> Any:
        """
        Evaluate an argument expression for parameterized templates.

        Args:
            arg_expr: Argument expression (e.g., "$.field" or "'literal'")
            data: Data context
            variables: Optional path variables

        Returns:
            Evaluated value
        """
        arg_expr = arg_expr.strip()

        # String literal
        if (arg_expr.startswith("'") and arg_expr.endswith("'")) or \
           (arg_expr.startswith('"') and arg_expr.endswith('"')):
            return arg_expr[1:-1]

        # Numeric literal
        try:
            if "." in arg_expr:
                return float(arg_expr)
            else:
                return int(arg_expr)
        except ValueError:
            pass

        # JSONPath or expression
        if arg_expr.startswith("$"):
            results = self.jsonpath.evaluate(arg_expr, data, variables)
            return results[0] if results else ""

        # Otherwise, treat as literal
        return arg_expr

    def evaluate_conditional_template(
        self,
        conditional: Dict[str, Any],
        data: Any,
        variables: Optional[Dict[str, str]] = None,
        templates: Optional[Dict[str, Any]] = None
    ) -> str:
        """
        Evaluate a conditional template.

        Supports:
        - Simple conditional: {"condition": "...", "if_true": "...", "if_false": "..."}
        - Optional conditional: {"condition": "...", "if_true": "..."}
        - Multi-condition: {"conditions": [{when: "...", show: "..."}], "default": "..."}

        Args:
            conditional: Conditional template dict
            data: Data context
            variables: Optional path variables
            templates: Templates dict

        Returns:
            Evaluated string result
        """
        if templates is None:
            templates = {}

        # Multi-condition format
        if "conditions" in conditional:
            conditions_list = conditional["conditions"]
            for cond_item in conditions_list:
                when_expr = cond_item.get("when")
                show_template = cond_item.get("show")

                if when_expr and self.condition_evaluator.evaluate_condition(when_expr, data, variables):
                    # This condition matches, evaluate its template
                    return self.evaluate_field_value(show_template, data, variables, templates)

            # No condition matched, use default if provided
            default_template = conditional.get("default", "")
            return self.evaluate_field_value(default_template, data, variables, templates)

        # Simple conditional format
        elif "condition" in conditional:
            condition_expr = conditional["condition"]
            if_true_template = conditional.get("if_true", "")
            if_false_template = conditional.get("if_false", "")

            if self.condition_evaluator.evaluate_condition(condition_expr, data, variables):
                return self.evaluate_field_value(if_true_template, data, variables, templates)
            else:
                # if_false might be omitted for optional conditionals
                if if_false_template:
                    return self.evaluate_field_value(if_false_template, data, variables, templates)
                else:
                    return ""  # Return empty string if no if_false

        # Invalid conditional format
        else:
            raise ValueError(f"Invalid conditional template: must have 'condition' or 'conditions' field")


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
