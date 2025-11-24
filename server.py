#!/usr/bin/env python3
"""
server.py - Prototype mobile app backend server

FastAPI-based server that renders card-based UI sections from patient attribute data
using declarative configuration files.

This server is fully configuration-driven with zero use-case-specific code.
"""

from fastapi import FastAPI, Header, HTTPException

from app.config import ConfigLoader, AttributeLoader
from app.rendering import CardRenderer, SectionRenderer

# Initialize FastAPI app
app = FastAPI(title="Patient Data API", version="1.0.0")

# Initialize components
config_loader = ConfigLoader()
attr_loader = AttributeLoader()
card_renderer = CardRenderer(config_loader, attr_loader)
section_renderer = SectionRenderer(config_loader, card_renderer)


@app.get("/section/{section_path:path}")
async def get_section(
    section_path: str,
    x_epi: str = Header(..., alias="X-EPI")
):
    """
    Get a section with rendered cards.

    Supports both simple sections and parameterized sections:
    - Simple: /section/home
    - Parameterized: /section/procedures/APT001

    For parameterized sections, the section configuration's "path_parameters"
    field defines the parameter names to extract from the URL path.

    Args:
        section_path: Section path, optionally with parameters (e.g., "home" or "procedures/APT001")
        x_epi: Patient identifier from X-EPI header

    Returns:
        Section data with title, description, and cards
    """
    try:
        # Parse the section path
        path_parts = section_path.split('/')
        section_name = path_parts[0]
        path_values = path_parts[1:]  # Remaining path segments

        # Load section config to get parameter names
        section_config = config_loader.load_section(section_name)
        path_parameters = section_config.get("path_parameters", [])

        # Extract variables from path segments using parameter names from config
        variables = {}
        for i, param_name in enumerate(path_parameters):
            if i < len(path_values):
                variables[param_name] = path_values[i]

        result = section_renderer.render_section(section_name, x_epi, variables)
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
