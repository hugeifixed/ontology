"""Business services for ontology discovery and governed proposal lifecycle."""

from collections import defaultdict
from decimal import Decimal
from time import perf_counter

from django.db import transaction

from studio.models import (
    AccessMode,
    ApprovalState,
    BindingKind,
    CheckOutcome,
    Classification,
    ControlCheck,
    NodeType,
    OntologyEdge,
    OntologyNode,
    ProofEvent,
    ProofEventType,
    ProposalBinding,
    ProposalStatus,
    ReviewRole,
    RiskLevel,
    WorkflowProposal,
)
from studio.providers import build_llm_provider
from studio.providers.prompting import PROMPT_VERSION
from studio.sandbox_services import (
    SandboxWorkflowError,
    export_agent_manifest,
    record_proposal_approval,
)
from studio.types import (
    BindingAccessMode,
    IntentAction,
    ProposalDraft,
    ProviderName,
    ProviderResult,
)


class ProposalValidationError(ValueError):
    """Raised when a model draft violates the registered ontology contract."""


def compose_workflow_proposal(
    *,
    intent: str,
    requester_role: str,
    provider_name: ProviderName,
    ephemeral_api_key: str,
    requested_model: str,
) -> WorkflowProposal:
    """Interpret intent, validate ontology bindings, and persist a reviewable proposal."""
    ontology_context = build_ontology_context()
    provider = build_llm_provider(
        provider_name=provider_name,
        ephemeral_api_key=ephemeral_api_key,
        requested_model=requested_model,
    )
    composition_started = perf_counter()
    result = provider.compose(intent=intent, ontology_context=ontology_context)
    result = result.model_copy(
        update={"latency_ms": int((perf_counter() - composition_started) * 1000)}
    )
    resolved_nodes = _resolve_draft_nodes(result.draft)
    return _persist_proposal(
        intent=intent,
        requester_role=requester_role,
        result=result,
        resolved_nodes=resolved_nodes,
    )


def build_ontology_context() -> str:
    """Serialize approved catalog metadata into compact model grounding context."""
    nodes = OntologyNode.objects.filter(
        approval_state__in=(ApprovalState.APPROVED, ApprovalState.CONDITIONAL)
    ).order_by("node_type", "slug")
    edges = OntologyEdge.objects.filter(
        source__in=nodes,
        target__in=nodes,
    ).select_related("source", "target")
    node_lines = [
        (
            f"NODE slug={node.slug}; type={node.node_type}; name={node.name}; "
            f"classification={node.classification}; owner={node.owner}; "
            f"state={node.approval_state}; description={node.description}"
        )
        for node in nodes
    ]
    edge_lines = [
        f"EDGE {edge.source.slug} --{edge.relation}--> {edge.target.slug}" for edge in edges
    ]
    return "\n".join([*node_lines, *edge_lines])


def approve_workflow_proposal(
    *,
    proposal: WorkflowProposal,
    review_role: ReviewRole,
    approver: str,
    note: str,
) -> WorkflowProposal:
    """Record one role-specific decision for a policy-clean proposal."""
    if proposal.control_checks.filter(outcome=CheckOutcome.BLOCK).exists():
        raise ProposalValidationError("Blocked proposals cannot be approved.")
    try:
        record_proposal_approval(
            proposal=proposal,
            review_role=review_role,
            approver=approver,
            note=note,
        )
    except SandboxWorkflowError as exc:
        raise ProposalValidationError(str(exc)) from exc
    proposal.refresh_from_db()
    return proposal


def ontology_layers() -> list[tuple[str, list[OntologyNode]]]:
    """Group ontology concepts into an easy-to-follow operating flow."""
    layer_definitions = (
        ("Intent", (NodeType.BUSINESS_OUTCOME, NodeType.USER_ROLE)),
        ("Work", (NodeType.WORKFLOW,)),
        ("Intelligence", (NodeType.AGENT_CAPABILITY, NodeType.AGENT_INSTANCE)),
        ("Access", (NodeType.TOOL, NodeType.CONNECTOR)),
        ("Enterprise", (NodeType.DATA_PRODUCT, NodeType.SYSTEM)),
        ("Guardrails & delivery", (NodeType.CONTROL, NodeType.DELIVERY_ARTIFACT)),
    )
    grouped: dict[NodeType, list[OntologyNode]] = defaultdict(list)
    for node in OntologyNode.objects.all():
        grouped[node.node_type].append(node)
    return [
        (label, [node for node_type in node_types for node in grouped[node_type]])
        for label, node_types in layer_definitions
    ]


def _resolve_draft_nodes(draft: ProposalDraft) -> dict[str, OntologyNode]:
    slugs = {
        draft.capability_slug,
        *draft.control_slugs,
        *draft.delivery_artifact_slugs,
        *(binding.node_slug for binding in draft.bindings),
    }
    if draft.existing_workflow_slug:
        slugs.add(draft.existing_workflow_slug)
    nodes = OntologyNode.objects.in_bulk(slugs, field_name="slug")
    unknown = sorted(slugs - nodes.keys())
    if unknown:
        raise ProposalValidationError(
            "The model referenced unregistered ontology objects: " + ", ".join(unknown)
        )
    unavailable = sorted(
        slug
        for slug, node in nodes.items()
        if node.approval_state not in (ApprovalState.APPROVED, ApprovalState.CONDITIONAL)
    )
    if unavailable:
        raise ProposalValidationError(
            "The model referenced unavailable ontology objects: " + ", ".join(unavailable)
        )
    return nodes


def _persist_proposal(
    *,
    intent: str,
    requester_role: str,
    result: ProviderResult,
    resolved_nodes: dict[str, OntologyNode],
) -> WorkflowProposal:
    draft = result.draft
    risk_level = _risk_level(draft=draft, resolved_nodes=resolved_nodes)
    checks = _evaluate_controls(draft=draft, resolved_nodes=resolved_nodes)
    status = (
        ProposalStatus.BLOCKED
        if any(outcome is CheckOutcome.BLOCK for _, outcome, _, _ in checks)
        else ProposalStatus.NEEDS_REVIEW
    )
    existing_workflow = (
        resolved_nodes[draft.existing_workflow_slug] if draft.existing_workflow_slug else None
    )

    with transaction.atomic():
        proposal = WorkflowProposal.objects.create(
            title=draft.intent.title,
            intent=intent,
            requester_role=requester_role,
            business_outcome=draft.intent.outcome,
            summary=draft.summary,
            agent_name=draft.agent_name,
            status=status,
            risk_level=risk_level,
            model_provider=result.provider.value,
            model_name=result.model_name,
            model_used=result.model_used,
            prompt_version=PROMPT_VERSION,
            model_latency_ms=result.latency_ms,
            input_tokens=result.input_tokens,
            output_tokens=result.output_tokens,
            estimated_cost_usd=_estimate_model_cost(result),
            existing_workflow=existing_workflow,
        )
        _create_bindings(
            proposal=proposal,
            draft=draft,
            resolved_nodes=resolved_nodes,
        )
        for name, outcome, detail, control_slug in checks:
            ControlCheck.objects.create(
                proposal=proposal,
                control=resolved_nodes.get(control_slug),
                name=name,
                outcome=outcome,
                detail=detail,
            )
        ProofEvent.objects.create(
            proposal=proposal,
            event_type=ProofEventType.INTENT_CAPTURED,
            actor=requester_role,
            summary="Business intent captured and bounded for proposal generation.",
            evidence_reference=f"proposal:{proposal.pk}:intent",
        )
        ProofEvent.objects.create(
            proposal=proposal,
            event_type=(
                ProofEventType.MODEL_INVOKED if result.model_used else ProofEventType.MODEL_BYPASSED
            ),
            actor=f"{result.provider.value}:{result.model_name}",
            summary=(
                "Structured proposal returned through the approved model route."
                if result.model_used
                else "Deterministic proposal used; no external model received the intent."
            ),
            evidence_reference=result.request_id,
        )
        ProofEvent.objects.create(
            proposal=proposal,
            event_type=ProofEventType.ONTOLOGY_MATCHED,
            actor="Catalog resolver",
            summary=f"Resolved {len(resolved_nodes)} registered ontology objects.",
            evidence_reference="ontology:commercial-loan-insurance:v1",
        )
        ProofEvent.objects.create(
            proposal=proposal,
            event_type=ProofEventType.POLICY_CHECKED,
            actor="Deterministic policy engine",
            summary=f"Evaluated {len(checks)} controls; model did not approve itself.",
            evidence_reference=f"proposal:{proposal.pk}:controls",
        )
        export_agent_manifest(proposal=proposal)
    return proposal


def _estimate_model_cost(result: ProviderResult) -> Decimal | None:
    """Estimate supported model costs from provider-reported token counts."""
    if not result.model_used:
        return Decimal("0.000000")
    anthropic_rates = {
        "claude-sonnet-5": (Decimal("2"), Decimal("10")),
        "claude-opus-5": (Decimal("5"), Decimal("25")),
    }
    rates = anthropic_rates.get(result.model_name)
    if result.provider is not ProviderName.ANTHROPIC or rates is None:
        return None
    input_rate, output_rate = rates
    cost = (
        Decimal(result.input_tokens) * input_rate + Decimal(result.output_tokens) * output_rate
    ) / Decimal("1000000")
    return cost.quantize(Decimal("0.000001"))


def _create_bindings(
    *,
    proposal: WorkflowProposal,
    draft: ProposalDraft,
    resolved_nodes: dict[str, OntologyNode],
) -> None:
    binding_specs: list[tuple[OntologyNode, BindingKind, AccessMode, str]] = []
    capability = resolved_nodes[draft.capability_slug]
    binding_specs.append(
        (
            capability,
            BindingKind.AGENT,
            AccessMode.INVOKE,
            f"Instantiate this approved capability as {draft.agent_name}.",
        )
    )
    for binding in draft.bindings:
        node = resolved_nodes[binding.node_slug]
        binding_kind = _binding_kind_for_node(node)
        access_mode = _canonical_access_mode(
            node=node,
            binding_kind=binding_kind,
            proposed_mode=binding.access_mode,
        )
        binding_specs.append((node, binding_kind, access_mode, binding.purpose))
    binding_specs.extend(
        (
            resolved_nodes[slug],
            BindingKind.CONTROL,
            AccessMode.ENFORCE,
            "Required deterministic governance control.",
        )
        for slug in draft.control_slugs
    )
    binding_specs.extend(
        (
            resolved_nodes[slug],
            BindingKind.DELIVERY,
            AccessMode.GENERATE,
            "Required SDLC handoff artifact after approval.",
        )
        for slug in draft.delivery_artifact_slugs
    )
    seen: set[tuple[int, BindingKind]] = set()
    for node, kind, access_mode, purpose in binding_specs:
        identity = (node.pk, kind)
        if identity in seen:
            continue
        seen.add(identity)
        ProposalBinding.objects.create(
            proposal=proposal,
            node=node,
            binding_kind=kind,
            access_mode=access_mode,
            purpose=purpose,
        )


def _binding_kind_for_node(node: OntologyNode) -> BindingKind:
    if node.node_type is NodeType.DATA_PRODUCT:
        return BindingKind.DATA
    if node.node_type in (NodeType.TOOL, NodeType.CONNECTOR):
        return BindingKind.TOOL
    if node.node_type in (NodeType.AGENT_CAPABILITY, NodeType.AGENT_INSTANCE):
        return BindingKind.AGENT
    if node.node_type is NodeType.CONTROL:
        return BindingKind.CONTROL
    if node.node_type is NodeType.DELIVERY_ARTIFACT:
        return BindingKind.DELIVERY
    raise ProposalValidationError(f"{node.slug} cannot be bound directly to a proposal.")


def _canonical_access_mode(
    *,
    node: OntologyNode,
    binding_kind: BindingKind,
    proposed_mode: BindingAccessMode,
) -> AccessMode:
    """Resolve model vocabulary to the catalog's node-specific access semantics."""
    expected_modes = {
        BindingKind.DATA: AccessMode.READ,
        BindingKind.TOOL: AccessMode.INVOKE,
        BindingKind.AGENT: AccessMode.INVOKE,
        BindingKind.CONTROL: AccessMode.ENFORCE,
        BindingKind.DELIVERY: AccessMode.GENERATE,
    }
    expected_mode = expected_modes[binding_kind]
    proposed_access_mode = AccessMode(proposed_mode.value)
    if proposed_access_mode is expected_mode:
        return expected_mode
    if binding_kind is BindingKind.TOOL and proposed_access_mode is AccessMode.READ:
        return AccessMode.INVOKE
    raise ProposalValidationError(
        f"Access mode '{proposed_access_mode.value}' is not valid for {node.slug}; "
        f"expected '{expected_mode.value}'."
    )


def _risk_level(
    *,
    draft: ProposalDraft,
    resolved_nodes: dict[str, OntologyNode],
) -> RiskLevel:
    if draft.intent.action in (IntentAction.WRITE, IntentAction.COMMUNICATE):
        return RiskLevel.HIGH
    if any(
        node.classification in (Classification.CONFIDENTIAL, Classification.RESTRICTED)
        for node in resolved_nodes.values()
    ):
        return RiskLevel.MODERATE
    return RiskLevel.LOW


def _evaluate_controls(
    *,
    draft: ProposalDraft,
    resolved_nodes: dict[str, OntologyNode],
) -> list[tuple[str, CheckOutcome, str, str]]:
    controls = set(draft.control_slugs)
    checks: list[tuple[str, CheckOutcome, str, str]] = []
    checks.append(
        (
            "Registered and approved assets",
            CheckOutcome.PASS,
            f"All {len(resolved_nodes)} referenced objects resolved to the governed catalog.",
            "user-entitlement-check",
        )
    )
    checks.append(
        _required_control_check(
            controls=controls,
            slug="user-entitlement-check",
            name="Entitlement before retrieval",
            pass_detail="User and agent identities must both be authorized before retrieval.",
        )
    )
    checks.append(
        _required_control_check(
            controls=controls,
            slug="citation-required",
            name="Evidence and citations",
            pass_detail="Every recommendation must link to retrieved source evidence.",
        )
    )
    checks.append(
        _required_control_check(
            controls=controls,
            slug="human-review-required",
            name="Human authority",
            pass_detail="A servicing analyst remains accountable for the final determination.",
        )
    )
    write_requested = draft.intent.action in (IntentAction.WRITE, IntentAction.COMMUNICATE)
    checks.append(
        (
            "Read-only action boundary",
            CheckOutcome.BLOCK if write_requested else CheckOutcome.PASS,
            (
                "The draft requests a write or communication action and cannot proceed."
                if write_requested
                else "No database update, external communication, or autonomous decision is allowed."
            ),
            "read-only-boundary",
        )
    )
    checks.append(
        (
            "Reuse before build",
            CheckOutcome.PASS if draft.existing_workflow_slug else CheckOutcome.WARNING,
            (
                "The proposal extends a registered servicing workflow."
                if draft.existing_workflow_slug
                else "No existing workflow was selected; architecture review must confirm the gap."
            ),
            "human-review-required",
        )
    )
    return checks


def _required_control_check(
    *,
    controls: set[str],
    slug: str,
    name: str,
    pass_detail: str,
) -> tuple[str, CheckOutcome, str, str]:
    if slug in controls:
        return name, CheckOutcome.PASS, pass_detail, slug
    return (
        name,
        CheckOutcome.BLOCK,
        f"Required control '{slug}' was omitted by the model draft.",
        slug,
    )
