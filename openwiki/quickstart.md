---
type: Wiki entrypoint
title: Governed AI Studio code wiki
description: Source-grounded navigation for safely changing the Django prototype that discovers governed catalog paths, drafts workflow proposals, and evaluates a synthetic sandbox.
tags: [quickstart, governed-ai, django, sandbox]
openwiki:
  roles: [repository, workflow]
  source_paths: [studio/urls.py, studio/views.py, studio/services.py, studio/discovery.py, studio/sandbox_services.py]
  test_paths: [studio/tests.py]
---

# Governed AI Studio code wiki

This is a Django 5.2 prototype for governed agent-work design. It discovers approved catalog metadata, optionally uses a model to draft a typed proposal, deterministically grounds and checks that draft, exports a sandbox-only manifest, requires distinct business/source-owner approvals, and runs one synthetic commercial-loan evaluation slice. It is not a deployed agent platform, a production identity system, or a live banking-source integration.

## Start here

- **System shape and boundaries:** [architecture overview](architecture/overview.md)
- **Ontology, migration-seeded catalog, and persistence model:** [ontology](architecture/ontology.md)
- **Explainable access-scoped catalog reuse and metadata gaps:** [catalog discovery](architecture/catalog-discovery.md)
- **Grounding, controls, manifest export, and dual approvals:** [proposal lifecycle](workflows/proposal-lifecycle.md)
- **Mocked registration, dual-identity synthetic tools, evaluations, and evidence:** [sandbox runtime](workflows/sandbox-runtime.md)
- **Gemini, Anthropic, and deterministic draft adapters:** [model providers](integrations/model-providers.md)
- **Django routes, forms, HTMX fragments, and accessibility:** [workspace](web/workspace.md)
- **Palette and generated CSS boundary:** [theme system](web/theme-system.md)
- **Settings, audit, static delivery, admin, and security limitations:** [runtime operations](operations/runtime-and-delivery.md)
- **Scheduled wiki automation:** [OpenWiki automation](operations/openwiki-automation.md)

## Task routing

| Change area or user intent | Relevant wiki page | Exact source entry points | Important symbols or types | Focused tests | Minimal validation command |
|---|---|---|---|---|---|
| Change discovery scope, ranking, reuse, or metadata-gap behavior | [catalog discovery](architecture/catalog-discovery.md) | `studio/discovery.py`; `studio/forms.py`; `studio/views.py:discover` | `discover_catalog`, `AccessProfile`, `DiscoveryDecision` | `StudioJourneyTests.test_catalog_discovery_resolves_each_registered_business_domain` | `.venv/bin/python manage.py test studio.tests.StudioJourneyTests.test_catalog_discovery_resolves_each_registered_business_domain --verbosity 0` |
| Add/change catalog concepts, edges, domain metadata, or eligibility | [ontology](architecture/ontology.md) | `studio/models.py`; new migration; `studio/migrations/0002_seed_reference_ontology.py` | `OntologyNode`, `OntologyEdge`, `BusinessDomain`, `ApprovalState` | Discovery and demo journey tests | `.venv/bin/python manage.py migrate` then `.venv/bin/python manage.py test` |
| Change proposal grounding, policy, manifest, or approvals | [proposal lifecycle](workflows/proposal-lifecycle.md) | `studio/services.py`; `studio/sandbox_services.py` | `compose_workflow_proposal`, `_resolve_draft_nodes`, `_evaluate_controls`, `record_proposal_approval` | `test_dual_approval_releases_sandbox_registration`; `test_approval_roles_enforce_separation_of_duties` | `.venv/bin/python manage.py test studio.tests.StudioJourneyTests.test_dual_approval_releases_sandbox_registration --verbosity 0` |
| Change mocked registration, source policy, findings, evaluations, or evidence | [sandbox runtime](workflows/sandbox-runtime.md) | `studio/sandbox_services.py`; `studio/sandbox_runtime.py`; `studio/orchestration.py` | `register_sandbox_agent`, `run_sandbox_evaluation`, `RuntimeIdentity`, `invoke_synthetic_tool` | `StudioJourneyTests.test_complete_synthetic_sandbox_vertical_slice` | `.venv/bin/python manage.py test studio.tests.StudioJourneyTests.test_complete_synthetic_sandbox_vertical_slice --verbosity 0` |
| Add or alter an LLM provider | [model providers](integrations/model-providers.md) | `studio/types.py`; `studio/providers/`; `studio/forms.py` | `ProposalDraft`, `ProviderResult`, `build_llm_provider` | `GeminiProviderTests`; `AnthropicProviderTests` | `.venv/bin/python manage.py test` |
| Change compose/discovery/sandbox HTTP behavior or workspace display | [workspace](web/workspace.md) | `studio/urls.py`; `studio/views.py`; `studio/templates/studio/partials/` | `discover`, `compose_proposal`, `register_sandbox`, `evaluate_sandbox` | `StudioJourneyTests.test_complete_synthetic_sandbox_vertical_slice` | `.venv/bin/python manage.py test` |
| Change CSS/theme/static assets | [theme system](web/theme-system.md) | `studio/assets/css/input.css`; `studio/static/favicon/studio-mark.svg` | `institutional`, semantic `--color-*` roles | No color-specific automated test | `npm run build:css` |
| Change settings, audit, admin, or static delivery | [runtime operations](operations/runtime-and-delivery.md) | `config/settings.py`; `config/logging.py`; `studio/admin.py` | `AUDITLOG_INCLUDE_TRACKING_MODELS`, `COMPONENTS` | `AuditTrailTests.test_authenticated_proposal_creation_is_audited_without_remote_address` | `.venv/bin/python manage.py check` |
| Change scheduled wiki updates | [OpenWiki automation](operations/openwiki-automation.md) | `.github/workflows/openwiki-update.yml` | workflow dispatch and PR path scope | workflow review | manual dispatch/review |

## Local commands

```bash
.venv/bin/python manage.py check
.venv/bin/python manage.py migrate
.venv/bin/python manage.py test
npm run build:css
```

Use `DJANGO_DEBUG=false .venv/bin/python manage.py collectstatic --noinput` only for production static-delivery changes, after building CSS.

## Safety-critical concepts

- **Models draft, code governs.** Typed output still must resolve to approved/conditional catalog slugs and pass deterministic controls.
- **Discovery is not authorization.** Profiles filter demonstration metadata; they do not represent real identities or source grants.
- **Synthetic enforcement is not production IAM.** The sandbox does enforce fixture identity/tool/loan constraints, while public workflow endpoints still lack institutional authorization.
- **Read-only is enforced twice.** Composition blocks write/communicate intent; the synthetic runtime denies action outside its fixed read-only vocabulary.
- **Approval is sandbox-only.** Two distinct submitted reviewer strings release mocked registration, not production deployment.
- **Evidence is application-level proof.** Canonical JSON and hashes support review; they do not provide immutable external retention.

## Backlog / explicit prototype boundaries

The README and `docs/architecture.md` identify deferred production work: enterprise model gateway/managed identities, authenticated source-level authorization, executable non-synthetic connectors, immutable external evidence retention, broader evaluations/threat modeling/cost controls/deployments, and institutional catalog ownership. These are boundaries, not partially implemented features. Begin any move toward them with [runtime operations](operations/runtime-and-delivery.md), [the ontology guide](architecture/ontology.md), and [the sandbox runtime](workflows/sandbox-runtime.md).