"""
Section rendering from section configurations.

Handles rendering complete sections with multiple card types.
"""

from typing import Any, Dict, Optional

from ..config import ConfigLoader
from .card_renderer import CardRenderer


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
