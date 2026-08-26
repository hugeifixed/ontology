"""Factory for ephemeral LLM provider connections."""

from django.conf import settings

from studio.providers.anthropic import AnthropicLlmProvider
from studio.providers.gemini import GeminiLlmProvider
from studio.providers.interface import ILlmProvider
from studio.providers.mock import DemoLlmProvider
from studio.types import ProviderName


class ProviderConfigurationError(ValueError):
    """Raised when an explicitly selected provider has no usable credential."""


def build_llm_provider(
    *,
    provider_name: ProviderName,
    ephemeral_api_key: str,
    requested_model: str,
) -> ILlmProvider:
    """Build a provider without caching or persisting an ephemeral secret."""
    if provider_name is ProviderName.DEMO:
        return DemoLlmProvider()
    if provider_name is ProviderName.GEMINI:
        api_key = ephemeral_api_key or settings.GOOGLE_API_KEY
        if not api_key:
            raise ProviderConfigurationError(
                "Provide a Google AI Studio API key or set GOOGLE_API_KEY."
            )
        return GeminiLlmProvider(
            api_key=api_key,
            model_name=requested_model or settings.GEMINI_MODEL,
        )
    if provider_name is ProviderName.ANTHROPIC:
        api_key = ephemeral_api_key or settings.ANTHROPIC_API_KEY
        if not api_key:
            raise ProviderConfigurationError(
                "Provide an Anthropic API key for this request or set ANTHROPIC_API_KEY."
            )
        return AnthropicLlmProvider(
            api_key=api_key,
            model_name=requested_model or settings.ANTHROPIC_MODEL,
        )
    raise ProviderConfigurationError(f"Unsupported provider: {provider_name}")
