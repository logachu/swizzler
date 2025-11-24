"""
Configuration and attribute data loaders.

Handles loading of section configs, card configs, and patient attribute data.
"""

import json
from pathlib import Path
from typing import Any, Dict, List


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
