"""Deterministic legal-document structure graphs; no LLM dependency."""

from .build import build_graph
from .models import GraphPayload

__all__ = ["build_graph", "GraphPayload"]
