"""Anthropic structured-output provider."""

import anthropic
from loguru import logger
from pydantic import ValidationError

from studio.providers.errors import ProviderRequestError
from studio.providers.interface import ILlmProvider
from studio.providers.prompting import SYSTEM_INSTRUCTION, build_user_prompt
from studio.types import ProposalDraft, ProviderName, ProviderResult

ANTHROPIC_MAX_RETRIES = 1
ANTHROPIC_TIMEOUT_SECONDS = 30.0
ANTHROPIC_RETRYABLE_STATUS_CODES = (408, 409, 429, 500, 502, 503, 504, 529)


class AnthropicLlmProvider(ILlmProvider):
    """Compose proposals with an Anthropic API key supplied at runtime."""

    def __init__(self, *, api_key: str, model_name: str) -> None:
        self.api_key = api_key
        self.model_name = model_name

    def compose(self, *, intent: str, ontology_context: str) -> ProviderResult:
        """Request a schema-constrained proposal from Claude."""
        try:
            with anthropic.Anthropic(
                api_key=self.api_key,
                max_retries=ANTHROPIC_MAX_RETRIES,
                timeout=ANTHROPIC_TIMEOUT_SECONDS,
            ) as client:
                response = client.messages.parse(
                    model=self.model_name,
                    max_tokens=4096,
                    system=SYSTEM_INSTRUCTION,
                    messages=[
                        {
                            "role": "user",
                            "content": build_user_prompt(
                                intent=intent,
                                ontology_context=ontology_context,
                            ),
                        }
                    ],
                    output_format=ProposalDraft,
                )
        except anthropic.APITimeoutError as exc:
            self._log_connection_failure(exc, reason="timeout")
            raise ProviderRequestError(
                "Anthropic did not respond before the request timeout after automatic "
                "retries. Wait briefly and submit the request again."
            ) from exc
        except anthropic.APIConnectionError as exc:
            self._log_connection_failure(exc, reason="connection")
            raise ProviderRequestError(
                "The server could not reach the Anthropic API after automatic retries. "
                "Check network access and try again."
            ) from exc
        except anthropic.APIStatusError as exc:
            attempts = (
                ANTHROPIC_MAX_RETRIES + 1
                if exc.status_code in ANTHROPIC_RETRYABLE_STATUS_CODES
                else 1
            )
            logger.bind(source="Model provider").warning(
                "Anthropic API request failed · model={} · status_code={} · attempts={} · "
                "request_id={}",
                self.model_name,
                exc.status_code,
                attempts,
                getattr(exc, "request_id", None) or "unavailable",
            )
            raise ProviderRequestError(self._public_error_message(exc.status_code)) from exc
        except anthropic.APIError as exc:
            logger.bind(source="Model provider").warning(
                "Anthropic API request failed · model={} · error_type={}",
                self.model_name,
                type(exc).__name__,
            )
            raise ProviderRequestError(
                "Anthropic could not complete the model request. Try again or use the "
                "deterministic demo route."
            ) from exc
        except ValidationError as exc:
            logger.bind(source="Model provider").warning(
                "Anthropic returned an invalid structured response · model={} · error_type={}",
                self.model_name,
                type(exc).__name__,
            )
            raise ProviderRequestError(
                "Anthropic returned a response that did not match the proposal schema. "
                "Try the request again or use the deterministic demo route."
            ) from exc

        draft = response.parsed_output
        if draft is None:
            raise ProviderRequestError(
                "Anthropic returned no structured proposal. Try again or use the "
                "deterministic demo route."
            )
        usage = getattr(response, "usage", None)
        return ProviderResult(
            draft=draft,
            provider=ProviderName.ANTHROPIC,
            model_name=self.model_name,
            model_used=True,
            request_id=response.id,
            input_tokens=getattr(usage, "input_tokens", 0) or 0,
            output_tokens=getattr(usage, "output_tokens", 0) or 0,
        )

    def _log_connection_failure(
        self,
        exc: anthropic.APIConnectionError,
        *,
        reason: str,
    ) -> None:
        """Record safe connection metadata without response bodies or credentials."""
        logger.bind(source="Model provider").warning(
            "Anthropic API connection failed · model={} · reason={} · attempts={} · error_type={}",
            self.model_name,
            reason,
            ANTHROPIC_MAX_RETRIES + 1,
            type(exc).__name__,
        )

    def _public_error_message(self, status_code: int) -> str:
        """Translate Anthropic status codes without exposing raw provider details."""
        if status_code == 401:
            return (
                "Anthropic rejected the API key. Confirm that it is an active key from "
                "the Anthropic Console."
            )
        if status_code == 403:
            return (
                "The Anthropic key is valid but does not have access to the requested "
                "model or workspace."
            )
        if status_code == 404:
            return (
                "Anthropic could not find the requested model. Use a current Claude API "
                "model ID such as claude-sonnet-5 or claude-opus-5."
            )
        if status_code == 429:
            return (
                "Anthropic rate-limited the request after automatic retries. Check the "
                "workspace usage limit or wait briefly before trying again."
            )
        if status_code in (400, 422):
            return (
                "Anthropic could not process this structured-output request. Confirm the "
                "Claude API model ID and that the key can use that model."
            )
        if status_code >= 500:
            return (
                "Anthropic remained temporarily unavailable after automatic retries. "
                "Wait briefly and submit the request again."
            )
        return (
            "Anthropic could not accept the request. Check the API key, model ID, and "
            "workspace access."
        )
