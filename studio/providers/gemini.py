"""Google Gemini structured-output provider."""

from uuid import uuid4

import httpx
from google import genai
from google.genai import errors, types
from loguru import logger
from pydantic import ValidationError

from studio.providers.errors import ProviderRequestError
from studio.providers.interface import ILlmProvider
from studio.providers.prompting import SYSTEM_INSTRUCTION, build_user_prompt
from studio.types import ProposalDraft, ProviderName, ProviderResult

GEMINI_TIMEOUT_MILLISECONDS = 30_000
GEMINI_RETRY_ATTEMPTS = 2
GEMINI_RETRY_INITIAL_DELAY_SECONDS = 0.5
GEMINI_RETRY_MAX_DELAY_SECONDS = 2.0
GEMINI_RETRYABLE_STATUS_CODES = (408, 429, 500, 502, 503, 504)


class GeminiLlmProvider(ILlmProvider):
    """Compose proposals through the Gemini Developer API."""

    def __init__(
        self,
        *,
        api_key: str,
        model_name: str,
    ) -> None:
        self.api_key = api_key
        self.model_name = model_name

    def compose(self, *, intent: str, ontology_context: str) -> ProviderResult:
        """Request a schema-constrained proposal from Gemini."""
        try:
            with self._build_client() as client:
                response = client.models.generate_content(
                    model=self.model_name,
                    contents=build_user_prompt(
                        intent=intent,
                        ontology_context=ontology_context,
                    ),
                    config=types.GenerateContentConfig(
                        system_instruction=SYSTEM_INSTRUCTION,
                        response_mime_type="application/json",
                        response_schema=ProposalDraft,
                        automatic_function_calling=types.AutomaticFunctionCallingConfig(
                            disable=True
                        ),
                    ),
                )
        except errors.APIError as exc:
            attempts = GEMINI_RETRY_ATTEMPTS if exc.code in GEMINI_RETRYABLE_STATUS_CODES else 1
            logger.bind(source="Model provider").warning(
                "Gemini Developer API request failed · model={} · status_code={} · attempts={}",
                self.model_name,
                exc.code,
                attempts,
            )
            raise ProviderRequestError(self._public_error_message(exc.code)) from exc
        except httpx.TimeoutException as exc:
            logger.bind(source="Model provider").warning(
                "Gemini Developer API request timed out · model={} · timeout_ms={} · attempts={}",
                self.model_name,
                GEMINI_TIMEOUT_MILLISECONDS,
                GEMINI_RETRY_ATTEMPTS,
            )
            raise ProviderRequestError(
                "The Gemini Developer API did not respond within the one-minute request "
                "limit. Try again later or use the deterministic demo route."
            ) from exc

        try:
            draft = ProposalDraft.model_validate_json(response.text)
        except (TypeError, ValueError, ValidationError) as exc:
            logger.bind(source="Model provider").warning(
                "Gemini returned an invalid structured response · model={} · error_type={}",
                self.model_name,
                type(exc).__name__,
            )
            raise ProviderRequestError(
                "Google returned a response that did not match the proposal schema. "
                "Try the request again or use the deterministic demo route."
            ) from exc

        request_id = getattr(response, "response_id", None) or f"gemini-{uuid4().hex[:12]}"
        usage = getattr(response, "usage_metadata", None)
        return ProviderResult(
            draft=draft,
            provider=ProviderName.GEMINI,
            model_name=self.model_name,
            model_used=True,
            request_id=request_id,
            input_tokens=getattr(usage, "prompt_token_count", 0) or 0,
            output_tokens=getattr(usage, "candidates_token_count", 0) or 0,
        )

    def _build_client(self) -> genai.Client:
        """Create a request-scoped Gemini Developer API client."""
        return genai.Client(
            api_key=self.api_key,
            http_options=types.HttpOptions(
                timeout=GEMINI_TIMEOUT_MILLISECONDS,
                retry_options=types.HttpRetryOptions(
                    attempts=GEMINI_RETRY_ATTEMPTS,
                    initial_delay=GEMINI_RETRY_INITIAL_DELAY_SECONDS,
                    max_delay=GEMINI_RETRY_MAX_DELAY_SECONDS,
                    http_status_codes=list(GEMINI_RETRYABLE_STATUS_CODES),
                ),
            ),
        )

    def _public_error_message(self, status_code: int) -> str:
        """Translate Google status codes without exposing response bodies or credentials."""
        route = "Gemini Developer API"
        if status_code in (401, 403):
            return (
                f"Google rejected the credential for the {route}. Confirm that it is an active "
                "Google AI Studio key with access to the requested model."
            )
        if status_code == 404:
            return (
                f"The requested model is not available through the {route}. Check the model "
                "name and the key's project access."
            )
        if status_code == 429:
            return (
                f"Google rate-limited the {route}. Check project quota or try again after the "
                "quota window resets."
            )
        if status_code >= 500:
            return (
                f"The {route} remained temporarily unavailable after automatic retries. "
                "Your key was accepted; wait briefly and submit the request again."
            )
        return (
            f"Google could not accept the request through the {route}. Check the AI Studio key, "
            "model name, API restrictions, and project access."
        )
