#!/usr/bin/env python3
"""Test currency display formatting."""

import sys
import json
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from server import ConfigLoader, AttributeLoader, CardRenderer


def test_currency_display():
    """Test the currency() function in card templates."""
    # Setup
    config_loader = ConfigLoader(config_dir="tests/currency_test")
    attr_loader = AttributeLoader(output_dir="tests/currency_test/output")
    card_renderer = CardRenderer(config_loader, attr_loader)

    # Render cards
    try:
        cards = card_renderer.render_cards("test_currency_card.json", "EPI123")

        print("Currency Display Test Results:")
        print("=" * 60)
        print(json.dumps(cards, indent=2))
        print("=" * 60)

        # Verify formatting
        expected_formats = {
            "Service A": "$23.47",
            "Service B": "$1,089.99",
            "Service C": "$23.00",
            "Service D": "$0.47",
            "Service E": "$23.47",
            "Service F": "$0.47",
            "Service G": "$0.47",
            "Service H": "$23.00"
        }

        all_passed = True
        for card in cards:
            item = card.get("item")
            formatted = card.get("amount_formatted")
            expected = expected_formats.get(item)

            if formatted == expected:
                print(f"✓ {item}: {formatted}")
            else:
                print(f"✗ {item}: Expected {expected}, got {formatted}")
                all_passed = False

        if all_passed:
            print("\n✓ All currency formatting tests passed!")
            return 0
        else:
            print("\n✗ Some tests failed")
            return 1

    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(test_currency_display())
