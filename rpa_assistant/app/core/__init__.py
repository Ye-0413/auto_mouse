"""Execution core: variable substitution, flow validation."""

from rpa_assistant.app.core.variable_engine import (
    find_unresolved,
    substitute_structure,
    substitute_text,
)
from rpa_assistant.app.models.flow_dsl import validate_flow_definition

__all__ = [
    "find_unresolved",
    "substitute_structure",
    "substitute_text",
    "validate_flow_definition",
]
