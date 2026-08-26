"""LLM provider contract for structured workflow composition."""

from abc import ABC, abstractmethod

from studio.types import ProviderResult


class ILlmProvider(ABC):
    """Interpret business intent into a typed proposal draft."""

    @abstractmethod
    def compose(self, *, intent: str, ontology_context: str) -> ProviderResult:
        """Return a normalized proposal without persisting provider payloads."""
