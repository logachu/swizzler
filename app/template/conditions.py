"""
Condition evaluation for template logic.

Supports comparison operators, logical operators, and function calls in conditions.
"""

from typing import Any, Dict, Optional, TYPE_CHECKING

if TYPE_CHECKING:
    from .engine import JSONPathEngine, ExpressionParser
    from .functions import ComputeFunctions


class ConditionEvaluator:
    """Evaluates conditional expressions for template logic."""

    def __init__(
        self,
        jsonpath: 'JSONPathEngine',
        compute: 'ComputeFunctions',
        expr_parser: 'ExpressionParser'
    ):
        self.jsonpath = jsonpath
        self.compute = compute
        self.expr_parser = expr_parser

    def evaluate_condition(
        self,
        condition: str,
        data: Any,
        variables: Optional[Dict[str, str]] = None
    ) -> bool:
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

    def evaluate_value(
        self,
        expr: str,
        data: Any,
        variables: Optional[Dict[str, str]] = None
    ) -> Any:
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
