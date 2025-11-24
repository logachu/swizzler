"""
Card rendering from patient data and card configurations.

Handles card template evaluation, field rendering, and conditional logic.
"""

import re
from typing import Any, Dict, List, Optional, Match

from ..config import ConfigLoader, AttributeLoader
from ..template import JSONPathEngine, ExpressionParser, ComputeFunctions, ConditionEvaluator


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
