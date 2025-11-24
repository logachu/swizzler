"""
Template expression parsing and JSONPath evaluation.

Handles evaluation of template strings with {expressions}, JSONPath queries,
and template references.
"""

import re
from typing import Any, Dict, List, Optional, Match, TYPE_CHECKING

from jsonpath_ng import parse as jsonpath_parse

if TYPE_CHECKING:
    from ..rendering.card_renderer import CardRenderer


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


class ExpressionParser:
    """Parses and evaluates card template expressions."""

    # Pattern to match {expression} in template strings
    EXPR_PATTERN = re.compile(r'\{([^}]+)\}')

    # Pattern to match function calls like len(...), sum(...), etc.
    FUNC_PATTERN = re.compile(r'(\w+)\((.*?)\)')

    def __init__(self, jsonpath_engine: JSONPathEngine, compute_funcs: 'ComputeFunctions'):
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
            elif func_name == "currency":
                return self.compute.currency(arg_value)

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
