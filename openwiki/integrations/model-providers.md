---
type: integration guide
title: Model provider composition boundary
description: Typed, ephemeral Gemini, Anthropic, and deterministic provider adapters used only to draft governed workflow proposals.
tags: [integrations, llm, providers]
---

# Model provider composition boundary

`studio.providers` is the only implemented networked external integration surface. It transforms a business intent plus approved ontology metadata into a typed proposal draft. It neither persists provider credentials nor lets a provider authorize source access or approve its output. `compose_workflow_proposal()` is the upstream caller; catalog validation, manifest export, and approval persistence in [`workflows/proposal-lifecycle.md`](../workflows/proposal-lifecycle.md) are downstream. The deterministic sandbox uses only in-memory fixtures and a mocked orchestration client, as described in [`workflows/sandbox-runtime.md`](../workflows/sandbox-runtime.md), not another external adapter.

## Contract and factory

`ILlmProvider.compose(intent, ontology_context)` returns `ProviderResult`. The return contains:

- frozen `ProposalDraft`, consisting of `IntentDraft`, summary, optional existing-workflow slug, capability slug, agent name, binding drafts, control slugs, and delivery-artifact slugs;
- `ProviderName` (`demo`, `gemini`, `anthropic`), model name, `model_used`, and a non-sensitive request identifier.

Pydantic applies structural and length constraints before the result reaches services. It does not establish catalog existence or approval: `_resolve_draft_nodes()` does that after the provider call.

`build_llm_provider()` is the factory and complete registration point. It returns `DemoLlmProvider` for `demo`, otherwise selects a credential in this order: submitted `ephemeral_api_key`, then the corresponding settings value (`GOOGLE_API_KEY` or `ANTHROPIC_API_KEY`). A missing credential for an explicitly selected live provider raises `ProviderConfigurationError`. The requested model wins when nonempty; otherwise the factory falls back to `GEMINI_MODEL` or `ANTHROPIC_MODEL`.

## Adapters and prompt boundary

| Adapter | Call behavior | Typed output handling |
|---|---|---|
| `DemoLlmProvider` | No network call; returns the canonical commercial-loan draft and a generated `demo-...` request ID. | `model_used=False`; ignores supplied ontology context. |
| `GeminiLlmProvider` | Creates `genai.Client(api_key=...)`; calls `client.models.generate_content` with JSON mime type and `response_schema=ProposalDraft`. | Parses `response.text` with `ProposalDraft.model_validate_json`; uses provider response ID or generated fallback. |
| `AnthropicLlmProvider` | Creates `Anthropic(api_key=...)`; calls `messages.parse` with `output_format=ProposalDraft`. | Uses `parsed_output`; errors when it is absent; uses `response.id`. |

`SYSTEM_INSTRUCTION` in `studio/providers/prompting.py` says the model drafts but never authorizes or approves, must use supplied slugs, should reuse a workflow, must remain read-only, must not propose raw credentials, and must bind approved tools/controls. `build_user_prompt()` includes the user intent and only the catalog context. The source says catalog descriptions are metadata, not corpus content.

The prompt is a defense-in-depth constraint. The enforceable boundary is post-response validation: invented slugs, retired/draft slugs, unsupported access modes, mandatory-control omissions, and write/communication actions are handled by service code.

## Credential lifecycle

The HTML form accepts an optional password input. `compose_proposal` passes the cleaned value directly to the factory and catches configuration/validation failures as HTTP 422. It never writes the key to a model or event. Client script `studio/static/studio/js/app.js` clears the key input after every HTMX request, including errors. A settings-provided key is also only used to construct the request-scoped client.

The test `test_demo_provider_creates_controlled_proposal` posts `must-not-be-persisted` and asserts it is absent from proposal fields and proof summaries/references. `test_live_provider_requires_a_key_when_environment_is_empty` asserts selecting Gemini without a key yields 422 and creates no proposal. This does not test provider SDK network behavior.

## Add a provider safely

1. Add a `ProviderName` enum value in `studio/types.py` and a form choice in `studio/forms.py`.
2. Implement `ILlmProvider.compose`; construct a `ProposalDraft` through the provider's structured-output capability or explicit Pydantic validation.
3. Register the adapter and request/env credential/model fallback in `build_llm_provider`; add corresponding settings and placeholder-only `.env.example` values when required.
4. Preserve the no-payload/no-secret persistence rule. Do not log request content or credentials.
5. Update UI provider selection defaults in `dashboard.html`, then test missing-credential failure and a successful typed result.

A provider extension is not a source-connector extension. Catalog nodes named connector/tool represent target integrations; no provider adapter invokes them. The only implementation that invokes tool-shaped boundaries is the explicit in-memory synthetic runtime, whose fixture-only policy/evidence contract is documented in [`workflows/sandbox-runtime.md`](../workflows/sandbox-runtime.md).
