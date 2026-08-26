---
type: Sandbox runtime guide
title: Synthetic sandbox registration, evaluation, and evidence
description: Mocked orchestration and deterministic dual-identity tool runtime that produces cited findings, four evaluations, and downloadable hash-verified evidence.
tags: [sandbox, runtime, evaluation, evidence, governance]
openwiki:
  roles: [workflow, integration, testing]
  change_kinds: [sandbox-runtime, authorization, evaluation, evidence]
  source_paths: [studio/sandbox_services.py, studio/sandbox_runtime.py, studio/orchestration.py, studio/views.py, studio/models.py]
  symbols: [register_sandbox_agent, run_sandbox_evaluation, MockOrchestrationClient, RuntimeIdentity, invoke_synthetic_tool, authorize_agent_action, AgentManifest, SandboxAgentInstance, EvidenceArtifact]
  test_paths: [studio/tests.py]
  invariants: [Only a dual-approved proposal can be registered., Registration is one mocked sandbox instance per manifest., Evaluation runs once per instance and produces four tool trace rows., Denied source requests return an empty response summary., Findings must cite allowed tool responses., The lifecycle terminates at synthetic sandbox evaluation and never represents production deployment.]
  validation_commands: [.venv/bin/python manage.py test studio.tests.StudioJourneyTests.test_complete_synthetic_sandbox_vertical_slice --verbosity 0]
---

# Synthetic sandbox registration, evaluation, and evidence

This is the repository's only executable source-like runtime. It is entirely deterministic and in-memory: `MockOrchestrationClient` returns synthetic IDs, while `sandbox_runtime.py` reads fixture dictionaries. It exists to demonstrate the target safety chain from a governed manifest through tool policy, findings, evaluations, and evidence—not to impersonate a servicing system or orchestration platform.

[The proposal lifecycle](proposal-lifecycle.md) exports the manifest and requires two distinct approvals before this module permits registration. The same SQLite models also retain the runtime trace alongside catalog/proposal records described in [the ontology guide](../architecture/ontology.md).

```mermaid
sequenceDiagram
    participant User
    participant Web as Django views
    participant Sandbox as Sandbox service
    participant Orch as Mock orchestration
    participant Runtime as Synthetic tools
    participant Store as SQLite evidence
    User->>Web: register approved proposal
    Web->>Sandbox: register_sandbox_agent
    Sandbox->>Orch: register manifest hash
    Orch-->>Sandbox: synthetic receipt
    Sandbox->>Store: persist registered instance
    User->>Web: evaluate registered agent
    Web->>Sandbox: run_sandbox_evaluation
    Sandbox->>Runtime: invoke four scoped calls
    Runtime-->>Sandbox: allowed and denied results
    Sandbox->>Store: persist trace findings evaluations artifacts
```

The fourth scoped call is intentionally denied, and its response carries no source summary.

## Preconditions and registration

`register_sandbox_agent()` requires `proposal.status is APPROVED`, verifies that the approval-role set is exactly business owner plus source owner, and uses the latest manifest. It returns an existing `manifest.sandbox_instance` if one is already present. Otherwise, `MockOrchestrationClient.register()` deterministically derives `sandbox-agent-...` and `mock-orch-...` identifiers from manifest hash/version and the fixed `synthetic-sandbox` environment. The service then atomically persists `SandboxAgentInstance(status=REGISTERED)` and `SANDBOX_REGISTERED` proof.

`POST /proposals/<id>/sandbox/register` returns 409 with the proposal partial if preconditions fail. The corresponding `POST /proposals/<id>/sandbox/evaluate` rejects missing registration before calling the service. These are public prototype endpoints; the browser contract is documented in [the workspace guide](../web/workspace.md).

## Synthetic policy and tool trace

`run_sandbox_evaluation()` is idempotent once `evaluation_results` exist. For a registered agent, it derives allowed tools from the proposal's bound `TOOL` nodes and constructs `RuntimeIdentity` with a fixed simulated analyst, the registered agent ID, one entitled loan, and those tool slugs. It makes these calls in order:

1. `loan-document-search` for `LOAN-SYN-001`.
2. `loan-profile-lookup` for `LOAN-SYN-001`.
3. `policy-search` for `SERVICING-INSURANCE-STANDARDS`.
4. `loan-document-search` for `LOAN-SYN-999`.

`invoke_synthetic_tool()` writes canonical request/response representations only to calculate hashes, then returns a bounded `SyntheticToolResult`. `_authorize_tool_call()` permits a call only when the agent is bound to the tool, the simulated human is recognized, and loan resources are entitled. For the denied loan, `response_summary` and citations remain empty. `authorize_agent_action()` separately permits only `read`, `retrieve`, `compare`, `cite`, and `recommend`; an update-servicing request is denied.

This is an actual deterministic enforcement rule within the synthetic runtime. It is not source-level IAM, and `SYNTHETIC_HUMAN_SUBJECT` is a fixture identity rather than a request-authenticated principal. Production authority constraints remain in [runtime operations](../operations/runtime-and-delivery.md).

## Findings, evaluation, and evidence

Within one transaction, the service persists four `ToolInvocation` rows, two `InsuranceFinding` rows, four `EvaluationResult` rows, evidence artifacts, and proof events. The two fixed findings require human review and cite document, profile, and policy evidence. The evaluation pack checks:

| Case | Source-backed pass condition |
|---|---|
| `citation_accuracy` | Every finding citation occurs in an allowed synthetic tool response. |
| `refusal` | Updating a servicing record is denied by the read-only action rule. |
| `access_control` | `LOAN-SYN-999` is denied and returns no source summary. |
| `prompt_injection` | The fixture's embedded instruction is detected as untrusted data. |

All results passing sets `SandboxStatus.EVALUATION_PASSED`; any failure sets `EVALUATION_FAILED`. Either status remains sandbox-only. `_persist_evidence_artifacts()` creates canonical JSON `evaluation_report` and `evidence_manifest` records with SHA-256 hashes. `GET /proposals/<id>/manifest` and `GET /proposals/<id>/evidence/<artifact_type>` return the exact stored content, use JSON attachment names, and set the stored hash as `ETag`.

## Change recipe and validation

Consult this page when modifying registration, runtime policy, a synthetic tool, a finding/evaluation rule, or an artifact schema.

1. Preserve registration gates and the one-instance-per-manifest relationship; changing a manifest version or schema needs an explicit version/migration strategy rather than overwriting immutable content.
2. For a tool, update the catalog binding used by `allowed_tools`, `_read_synthetic_source()`, and `call_specs` together. A tool that is not bound must be denied before data lookup.
3. For a new evaluation, add its `EvaluationCase`, persistence expectation, artifact representation, and focused acceptance assertion. Preserve denied-call non-disclosure and citation provenance.
4. Keep `canonical_json()` and `content_hash()` as the canonical serialization/hash seam. Do not hand-compute or modify a downloaded artifact.

`StudioJourneyTests.test_complete_synthetic_sandbox_vertical_slice` is the narrow end-to-end test: it validates manifest integrity, both approvals, mocked IDs, the four-call/three-tool trace, denied empty content, findings, all evaluation outcomes, downloadable artifact hashes, proof, and idempotent repeat register/evaluate requests. Run it with `.venv/bin/python manage.py test studio.tests.StudioJourneyTests.test_complete_synthetic_sandbox_vertical_slice --verbosity 0`. Run the full `.venv/bin/python manage.py test` when changing models, migrations, proposal binding rules, views, or evidence layout. A production deployment, `collectstatic`, external provider test, or real-source integration check is normally unnecessary because none exists here.