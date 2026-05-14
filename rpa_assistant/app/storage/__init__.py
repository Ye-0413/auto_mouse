"""Persistence layer."""

from rpa_assistant.app.storage.config_repo import ConfigRepository
from rpa_assistant.app.storage.database import CURRENT_SCHEMA_VERSION, connect, init_database
from rpa_assistant.app.storage.execution_repo import ExecutionRepository
from rpa_assistant.app.storage.flow_repo import FlowRepository

__all__ = [
    "CURRENT_SCHEMA_VERSION",
    "ConfigRepository",
    "ExecutionRepository",
    "FlowRepository",
    "connect",
    "init_database",
]
