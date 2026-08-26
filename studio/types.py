"""Validated transfer objects for intent interpretation and proposal composition."""

from enum import StrEnum, auto

from pydantic import BaseModel, ConfigDict, Field, field_validator


class ProviderName(StrEnum):
    """Available intent interpretation providers."""

    DEMO = auto()
    GEMINI = auto()
    ANTHROPIC = auto()


class IntentAction(StrEnum):
    """The highest-impact action requested by a business intent."""

    READ = auto()
    RECOMMEND = auto()
    COMMUNICATE = auto()
    WRITE = auto()


class BindingAccessMode(StrEnum):
    """Canonical access vocabulary accepted from model providers."""

    READ = auto()
    INVOKE = auto()
    ENFORCE = auto()
    GENERATE = auto()


class IntentDraft(BaseModel):
    """Structured interpretation of a free-form business request."""

    model_config = ConfigDict(frozen=True)

    title: str = Field(min_length=4, max_length=180)
    outcome: str = Field(min_length=12, max_length=600)
    actor: str = Field(min_length=3, max_length=160)
    action: IntentAction
    in_scope: list[str] = Field(min_length=1, max_length=6)
    out_of_scope: list[str] = Field(min_length=1, max_length=6)
    risk_signals: list[str] = Field(default_factory=list, max_length=8)


class BindingDraft(BaseModel):
    """A proposed binding to one approved ontology concept."""

    model_config = ConfigDict(frozen=True)

    node_slug: str
    purpose: str = Field(min_length=8, max_length=400)
    access_mode: BindingAccessMode

    @field_validator("access_mode", mode="before")
    @classmethod
    def normalize_read_only_alias(cls, value: object) -> object:
        """Accept common read-only spellings while retaining a closed vocabulary."""
        if isinstance(value, str) and value.strip().lower() in {
            "read_only",
            "read-only",
            "readonly",
        }:
            return BindingAccessMode.READ
        return value


class ProposalDraft(BaseModel):
    """LLM-produced draft that is validated before persistence."""

    model_config = ConfigDict(frozen=True)

    intent: IntentDraft
    summary: str = Field(min_length=20, max_length=900)
    existing_workflow_slug: str | None = None
    capability_slug: str
    agent_name: str = Field(min_length=4, max_length=180)
    bindings: list[BindingDraft] = Field(min_length=1, max_length=12)
    control_slugs: list[str] = Field(min_length=1, max_length=10)
    delivery_artifact_slugs: list[str] = Field(min_length=1, max_length=10)


class ProviderResult(BaseModel):
    """Normalized provider response with non-sensitive call metadata."""

    model_config = ConfigDict(frozen=True)

    draft: ProposalDraft
    provider: ProviderName
    model_name: str
    model_used: bool
    request_id: str
    latency_ms: int = Field(default=0, ge=0)
    input_tokens: int = Field(default=0, ge=0)
    output_tokens: int = Field(default=0, ge=0)
