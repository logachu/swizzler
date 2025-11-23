#!/usr/bin/env python3
"""
test_templates.py - Unit tests for template format operations

Tests each of the 4 core template operations incrementally:
1. Attribute Reference
2. Template Reference
3. Conditional Include
4. Template Application to Lists
"""

import json
import pytest
from pathlib import Path
from server import (
    ConfigLoader,
    AttributeLoader,
    CardRenderer,
    JSONPathEngine,
    ComputeFunctions,
    ExpressionParser
)


# Test fixtures
@pytest.fixture
def test_data_dir():
    """Path to test data directory."""
    return Path("tests/template_tests/test_data")


@pytest.fixture
def config_loader(test_data_dir):
    """ConfigLoader instance for tests."""
    # For this test, we'll load configs directly from test_data_dir
    loader = ConfigLoader()
    # Override paths for testing
    loader.cards_dir = test_data_dir
    return loader


@pytest.fixture
def attr_loader(test_data_dir):
    """AttributeLoader instance for tests."""
    return AttributeLoader(output_dir=str(test_data_dir))


@pytest.fixture
def card_renderer(config_loader, attr_loader):
    """CardRenderer instance for tests."""
    return CardRenderer(config_loader, attr_loader)


# ============================================================================
# Operation 1: Attribute Reference Tests
# ============================================================================

class TestOperation1AttributeReference:
    """Test attribute reference with the new templates structure."""

    def test_templates_root_structure(self, card_renderer):
        """Test that cards can use templates.root structure."""
        cards = card_renderer.render_cards(
            "operation1_card.json",
            "TEST001"
        )

        assert len(cards) == 2  # Two active prescriptions

        # Check first card
        card1 = cards[0]
        assert card1["title"] == "Lisinopril"
        assert card1["subtitle"] == "10mg - Once daily"
        assert card1["status"] == "active"

    def test_simple_field_access(self, card_renderer):
        """Test simple {$.field} attribute references."""
        cards = card_renderer.render_cards(
            "operation1_card.json",
            "TEST001"
        )

        card1 = cards[0]
        assert card1["title"] == "Lisinopril"
        assert "status" in card1
        assert card1["status"] == "active"

    def test_nested_field_access(self, card_renderer):
        """Test nested {$.field.subfield} attribute references."""
        cards = card_renderer.render_cards(
            "operation1_card.json",
            "TEST001"
        )

        card1 = cards[0]
        assert card1["prescriber"] == "Dr. Sarah Johnson, Cardiology"

    def test_array_indexing(self, card_renderer):
        """Test array indexing {$.array[-1].field}."""
        cards = card_renderer.render_cards(
            "operation1_card.json",
            "TEST001"
        )

        card1 = cards[0]
        # Should have last_refill field since array exists
        assert "last_refill" in card1
        assert "Jan" in card1["last_refill"]  # Jan 15, 2025

    def test_len_function(self, card_renderer):
        """Test len() function on arrays."""
        cards = card_renderer.render_cards(
            "operation1_card.json",
            "TEST001"
        )

        card1 = cards[0]
        assert card1["refill_count"] == "2"  # Lisinopril has 2 refills

        card2 = cards[1]
        assert card2["refill_count"] == "1"  # Metformin has 1 refill

    def test_format_date_function(self, card_renderer):
        """Test format_date() function."""
        cards = card_renderer.render_cards(
            "operation1_card.json",
            "TEST001"
        )

        card1 = cards[0]
        # Format is '%b %d, %Y' which should be like "Jan 15, 2025"
        assert card1["last_refill"] == "Jan 15, 2025"

    def test_optional_field_with_question_mark(self, card_renderer):
        """Test that ?field_name works as optional field."""
        # The ?last_refill field should be included since refills exist
        cards = card_renderer.render_cards(
            "operation1_card.json",
            "TEST001"
        )

        card1 = cards[0]
        assert "last_refill" in card1

        # If we had a card with no refills, the field should be omitted
        # (We'll test this when we have conditional logic)


# ============================================================================
# Unit Tests for Core Components
# ============================================================================

class TestJSONPathEngine:
    """Test JSONPath evaluation."""

    def test_simple_path(self):
        """Test simple $.field path."""
        engine = JSONPathEngine()
        data = {"name": "John", "age": 30}

        result = engine.evaluate("$.name", data)
        assert result == ["John"]

    def test_nested_path(self):
        """Test nested $.field.subfield path."""
        engine = JSONPathEngine()
        data = {
            "person": {
                "name": "John",
                "address": {
                    "city": "Boston"
                }
            }
        }

        result = engine.evaluate("$.person.address.city", data)
        assert result == ["Boston"]

    def test_array_index(self):
        """Test array indexing."""
        engine = JSONPathEngine()
        data = {"items": ["a", "b", "c"]}

        result = engine.evaluate("$.items[0]", data)
        assert result == ["a"]

        result = engine.evaluate("$.items[-1]", data)
        assert result == ["c"]


class TestComputeFunctions:
    """Test compute functions."""

    def test_len_function(self):
        """Test len() function."""
        compute = ComputeFunctions()

        assert compute.len([1, 2, 3]) == 3
        assert compute.len([]) == 0
        assert compute.len("not a list") == 0

    def test_sum_function(self):
        """Test sum() function."""
        compute = ComputeFunctions()

        assert compute.sum([1, 2, 3]) == 6.0
        assert compute.sum([1.5, 2.5]) == 4.0
        assert compute.sum(["$10.00", "$20.50"]) == 30.50

    def test_format_date(self):
        """Test format_date() function."""
        compute = ComputeFunctions()

        result = compute.format_date("2025-01-15T00:00:00-05:00", "%b %d, %Y")
        assert result == "Jan 15, 2025"

        result = compute.format_date("2025-01-15", "%Y-%m-%d")
        assert result == "2025-01-15"


class TestExpressionParser:
    """Test expression parsing and evaluation."""

    def test_simple_expression(self):
        """Test simple {$.field} expression."""
        parser = ExpressionParser(JSONPathEngine(), ComputeFunctions())
        data = {"name": "Alice"}

        result = parser.evaluate_template_string("Hello {$.name}", data)
        assert result == "Hello Alice"

    def test_multiple_expressions(self):
        """Test multiple expressions in one template."""
        parser = ExpressionParser(JSONPathEngine(), ComputeFunctions())
        data = {"first": "John", "last": "Doe"}

        result = parser.evaluate_template_string("{$.first} {$.last}", data)
        assert result == "John Doe"

    def test_function_in_expression(self):
        """Test function call in expression."""
        parser = ExpressionParser(JSONPathEngine(), ComputeFunctions())
        data = {"items": [1, 2, 3]}

        result = parser.evaluate_template_string("Count: {len($.items)}", data)
        assert result == "Count: 3"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
