"""Thin server-rendered and HTMX entry points for the studio."""

import json

from django.conf import settings
from django.db.models import Q
from django.http import HttpRequest, HttpResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_GET, require_POST
from django.views.decorators.vary import vary_on_headers
from loguru import logger

from studio.discovery import discover_catalog
from studio.forms import ApprovalForm, DiscoveryForm, ProposalForm
from studio.models import (
    ApprovalState,
    BusinessDomain,
    Classification,
    EvidenceArtifact,
    InsuranceFinding,
    NodeType,
    OntologyEdge,
    OntologyNode,
    ProposalStatus,
    ReviewRole,
    RiskLevel,
    SandboxAgentInstance,
    SandboxStatus,
    WorkflowProposal,
)
from studio.providers import ProviderConfigurationError
from studio.providers.errors import ProviderRequestError
from studio.sandbox_services import (
    SandboxWorkflowError,
    register_sandbox_agent,
    run_sandbox_evaluation,
)
from studio.services import (
    ProposalValidationError,
    approve_workflow_proposal,
    compose_workflow_proposal,
    ontology_layers,
)

REFERENCE_INTENT = (
    "Help commercial loan servicing analysts find the insurance requirements in a "
    "borrower's governed loan documents, compare them with the servicing profile and "
    "approved policy standards, and return cited findings for human review. Do not "
    "change any system of record or contact the customer."
)
SECTIONS = {"home", "start", "proposals", "knowledge", "connections", "search"}
SECTION_ALIASES = {
    "overview": "home",
    "compose": "start",
    "catalog": "knowledge",
    "ontology": "knowledge",
}
PROPOSAL_STAGES = {"define", "approve", "test", "evidence"}
PROPOSAL_PARTIAL = "studio/partials/proposal_detail.html#proposal-detail"
PROPOSAL_ERROR_PARTIAL = "studio/partials/proposal_error.html#proposal-error"
DISCOVERY_PARTIAL = "studio/partials/discovery_results.html#discovery-results"


@require_GET
def dashboard(request: HttpRequest) -> HttpResponse:
    """Render the integrated catalog, ontology, and proposal workspace."""
    raw_section = request.GET.get("section", "home")
    requested_section = SECTION_ALIASES.get(raw_section, raw_section)
    initial_section = requested_section if requested_section in SECTIONS else "home"
    knowledge_view = request.GET.get("view", "browse")
    if raw_section == "ontology":
        knowledge_view = "map"
    elif raw_section == "catalog":
        knowledge_view = "browse"
    if knowledge_view not in {"browse", "map"}:
        knowledge_view = "browse"
    knowledge_focus = request.GET.get("focus", "").strip()

    all_proposals = list(
        WorkflowProposal.objects.select_related("existing_workflow").prefetch_related(
            "approvals", "manifests__sandbox_instance"
        )[:50]
    )
    proposal_cards = [_proposal_navigation(proposal) for proposal in all_proposals]

    proposal_q = request.GET.get("proposal_q", "").strip()
    proposal_status = request.GET.get("proposal_status", "").strip()
    proposal_risk = request.GET.get("proposal_risk", "").strip()
    proposal_actor = request.GET.get("proposal_actor", "").strip()
    filtered_proposal_cards = proposal_cards
    if proposal_q:
        needle = proposal_q.casefold()
        filtered_proposal_cards = [
            item
            for item in filtered_proposal_cards
            if needle in item["proposal"].title.casefold()
            or needle in item["proposal"].intent.casefold()
            or needle in item["proposal"].requester_role.casefold()
        ]
    if proposal_status:
        filtered_proposal_cards = [
            item for item in filtered_proposal_cards if item["proposal"].status == proposal_status
        ]
    if proposal_risk:
        filtered_proposal_cards = [
            item for item in filtered_proposal_cards if item["proposal"].risk_level == proposal_risk
        ]
    actor_labels = {
        "business": "Business owner",
        "source": "Source owner",
        "sandbox": "Sandbox operator",
        "governance": "Governance reviewer",
    }
    if proposal_actor in actor_labels:
        filtered_proposal_cards = [
            item
            for item in filtered_proposal_cards
            if item["next_actor"] == actor_labels[proposal_actor]
        ]

    catalog_nodes = OntologyNode.objects.all()
    catalog_q = request.GET.get("catalog_q", "").strip()
    catalog_domain = request.GET.get("catalog_domain", "").strip()
    catalog_type = request.GET.get("catalog_type", "").strip()
    catalog_classification = request.GET.get("catalog_classification", "").strip()
    catalog_approval = request.GET.get("catalog_approval", "").strip()
    if catalog_q:
        catalog_nodes = catalog_nodes.filter(
            Q(name__icontains=catalog_q)
            | Q(description__icontains=catalog_q)
            | Q(owner__icontains=catalog_q)
            | Q(search_terms__icontains=catalog_q)
        )
    if catalog_domain:
        catalog_nodes = catalog_nodes.filter(business_domain=catalog_domain)
    if catalog_type:
        catalog_nodes = catalog_nodes.filter(node_type=catalog_type)
    if catalog_classification:
        catalog_nodes = catalog_nodes.filter(classification=catalog_classification)
    if catalog_approval:
        catalog_nodes = catalog_nodes.filter(approval_state=catalog_approval)

    focused_node = None
    focused_edges = OntologyEdge.objects.none()
    if knowledge_focus:
        focused_node = OntologyNode.objects.filter(slug=knowledge_focus).first()
        if focused_node is not None:
            focused_edges = OntologyEdge.objects.select_related("source", "target").filter(
                Q(source=focused_node) | Q(target=focused_node)
            )

    search_q = request.GET.get("q", "").strip()
    search_nodes = OntologyNode.objects.none()
    search_proposals = WorkflowProposal.objects.none()
    search_findings = InsuranceFinding.objects.none()
    if search_q:
        search_nodes = OntologyNode.objects.filter(
            Q(name__icontains=search_q)
            | Q(description__icontains=search_q)
            | Q(owner__icontains=search_q)
            | Q(search_terms__icontains=search_q)
        )[:8]
        search_proposals = WorkflowProposal.objects.filter(
            Q(title__icontains=search_q)
            | Q(intent__icontains=search_q)
            | Q(summary__icontains=search_q)
        )[:8]
        search_findings = InsuranceFinding.objects.select_related(
            "agent__manifest__proposal"
        ).filter(Q(title__icontains=search_q) | Q(finding__icontains=search_q))[:8]

    task_counts = {
        "business": sum(item["next_actor"] == "Business owner" for item in proposal_cards),
        "source": sum(item["next_actor"] == "Source owner" for item in proposal_cards),
        "sandbox": sum(item["recommended_stage"] == "test" for item in proposal_cards),
        "evidence": sum(item["recommended_stage"] == "evidence" for item in proposal_cards),
    }
    context = {
        "initial_section": initial_section,
        "knowledge_view": knowledge_view,
        "knowledge_focus": knowledge_focus,
        "focused_node": focused_node,
        "focused_edges": focused_edges,
        "discovery_form": DiscoveryForm(),
        "proposal_form": ProposalForm(initial={"intent": REFERENCE_INTENT}),
        "proposal_cards": filtered_proposal_cards,
        "recent_proposal_cards": proposal_cards[:4],
        "task_counts": task_counts,
        "proposal_q": proposal_q,
        "proposal_status": proposal_status,
        "proposal_risk": proposal_risk,
        "proposal_actor": proposal_actor,
        "proposal_status_choices": ProposalStatus.choices,
        "catalog_nodes": catalog_nodes,
        "catalog_q": catalog_q,
        "catalog_domain": catalog_domain,
        "catalog_type": catalog_type,
        "catalog_classification": catalog_classification,
        "catalog_approval": catalog_approval,
        "business_domain_choices": BusinessDomain.choices,
        "node_type_choices": NodeType.choices,
        "classification_choices": Classification.choices,
        "approval_state_choices": ApprovalState.choices,
        "risk_level_choices": RiskLevel.choices,
        "search_q": search_q,
        "search_nodes": search_nodes,
        "search_proposals": search_proposals,
        "search_findings": search_findings,
        "nodes": OntologyNode.objects.all(),
        "edges": OntologyEdge.objects.select_related("source", "target"),
        "ontology_layers": ontology_layers(),
        "node_type_count": len(NodeType),
        "provider_status": {
            "gemini": bool(settings.GOOGLE_API_KEY),
            "anthropic": bool(settings.ANTHROPIC_API_KEY),
        },
        "gemini_model": settings.GEMINI_MODEL,
        "anthropic_model": settings.ANTHROPIC_MODEL,
    }
    return render(request, "studio/dashboard.html", context)


@require_POST
def discover(request: HttpRequest) -> HttpResponse:
    """Return explainable catalog matches after deterministic scope filtering."""
    form = DiscoveryForm(request.POST)
    if not form.is_valid():
        return render(
            request,
            DISCOVERY_PARTIAL,
            {
                "discovery_error": (
                    "Describe the business need and choose a discovery access profile."
                )
            },
            status=422,
        )
    result = discover_catalog(
        intent=form.cleaned_data["intent"],
        access_profile=form.cleaned_data["access_profile"],
    )
    return render(request, DISCOVERY_PARTIAL, {"discovery_result": result})


@require_POST
def compose_proposal(request: HttpRequest) -> HttpResponse:
    """Validate the form and invoke the proposal composition service."""
    form = ProposalForm(request.POST)
    if not form.is_valid():
        return _compose_error_response(
            request,
            message="Please correct the highlighted request fields.",
            status=422,
            form=form,
        )
    try:
        proposal = compose_workflow_proposal(
            intent=form.cleaned_data["intent"],
            requester_role=form.cleaned_data["requester_role"],
            provider_name=form.cleaned_data["provider"],
            ephemeral_api_key=form.cleaned_data["api_key"],
            requested_model=form.cleaned_data["model_name"],
        )
    except (ProviderConfigurationError, ProposalValidationError, ValueError) as exc:
        return _compose_error_response(
            request,
            message=str(exc),
            status=422,
        )
    except ProviderRequestError as exc:
        return _compose_error_response(
            request,
            message=exc.public_message,
            status=502,
        )
    except Exception as exc:
        logger.bind(source="Model provider").error(
            "Unexpected proposal-provider failure · provider={} · error_type={}",
            form.cleaned_data["provider"],
            type(exc).__name__,
        )
        return _compose_error_response(
            request,
            message=(
                "The selected model provider could not complete the request. "
                "Verify the key, model access, and network connection. No key was stored."
            ),
            status=502,
        )
    destination = f"{proposal.get_absolute_url()}?stage=define"
    if request.htmx:
        response = HttpResponse(status=204)
        response["HX-Redirect"] = destination
        response["HX-Trigger"] = "proposalCreated"
        return response
    return redirect(destination)


def _compose_error_response(
    request: HttpRequest,
    *,
    message: str,
    status: int,
    form: ProposalForm | None = None,
) -> HttpResponse:
    """Render compose feedback beside its action without replacing prior work."""
    response = render(
        request,
        PROPOSAL_ERROR_PARTIAL,
        {"message": message, "form": form},
        status=status,
    )
    response["HX-Retarget"] = "#compose-feedback"
    response["HX-Reswap"] = "innerHTML swap:100ms settle:150ms"
    return response


@require_GET
@vary_on_headers("HX-Request")
def proposal_detail(request: HttpRequest, proposal_id: int) -> HttpResponse:
    """Render one proposal as an HTMX fragment or a complete detail page."""
    proposal = get_object_or_404(
        WorkflowProposal.objects.select_related("existing_workflow"),
        pk=proposal_id,
    )
    return render(
        request,
        PROPOSAL_PARTIAL if request.htmx else "studio/proposal_page.html",
        _proposal_context(proposal, requested_stage=request.GET.get("stage")),
    )


@require_POST
def approve_proposal(request: HttpRequest, proposal_id: int) -> HttpResponse:
    """Record the accountable human sandbox decision."""
    proposal = get_object_or_404(WorkflowProposal, pk=proposal_id)
    form = ApprovalForm(request.POST)
    if not form.is_valid():
        return render(
            request,
            PROPOSAL_ERROR_PARTIAL,
            {"message": "Provide an accountable approver before continuing."},
            status=422,
        )
    try:
        approve_workflow_proposal(
            proposal=proposal,
            review_role=form.cleaned_data["review_role"],
            approver=form.cleaned_data["approver"],
            note=form.cleaned_data["note"],
        )
    except ProposalValidationError as exc:
        return render(
            request,
            PROPOSAL_ERROR_PARTIAL,
            {"message": str(exc)},
            status=409,
        )
    proposal.refresh_from_db()
    context = _proposal_context(proposal)
    response = render(request, PROPOSAL_PARTIAL, context)
    response["HX-Trigger"] = "proposalApproved"
    response["HX-Push-Url"] = _proposal_stage_url(proposal, context)
    return response


@require_POST
def register_sandbox(request: HttpRequest, proposal_id: int) -> HttpResponse:
    """Register one approved manifest through the mocked orchestration boundary."""
    proposal = get_object_or_404(WorkflowProposal, pk=proposal_id)
    try:
        register_sandbox_agent(proposal=proposal)
    except SandboxWorkflowError as exc:
        return render(
            request,
            PROPOSAL_PARTIAL,
            _proposal_context(proposal, operation_error=str(exc)),
            status=409,
        )
    context = _proposal_context(proposal)
    response = render(request, PROPOSAL_PARTIAL, context)
    response["HX-Trigger"] = "sandboxRegistered"
    response["HX-Push-Url"] = _proposal_stage_url(proposal, context)
    return response


@require_POST
def evaluate_sandbox(request: HttpRequest, proposal_id: int) -> HttpResponse:
    """Execute the deterministic synthetic runtime and evaluation pack."""
    proposal = get_object_or_404(WorkflowProposal, pk=proposal_id)
    context = _proposal_context(proposal)
    agent = context["sandbox_agent"]
    if agent is None:
        return render(
            request,
            PROPOSAL_PARTIAL,
            _proposal_context(
                proposal,
                operation_error="Register the sandbox agent before running evaluations.",
            ),
            status=409,
        )
    try:
        run_sandbox_evaluation(agent=agent)
    except SandboxWorkflowError as exc:
        return render(
            request,
            PROPOSAL_PARTIAL,
            _proposal_context(proposal, operation_error=str(exc)),
            status=409,
        )
    context = _proposal_context(proposal)
    response = render(request, PROPOSAL_PARTIAL, context)
    response["HX-Trigger"] = "sandboxEvaluated"
    response["HX-Push-Url"] = _proposal_stage_url(proposal, context)
    return response


@require_GET
def download_manifest(request: HttpRequest, proposal_id: int) -> HttpResponse:
    """Download the exact canonical JSON manifest stored for a proposal."""
    proposal = get_object_or_404(WorkflowProposal, pk=proposal_id)
    manifest = proposal.manifests.order_by("-created_at").first()
    if manifest is None:
        return HttpResponse("No manifest is available for this proposal.", status=404)
    response = HttpResponse(manifest.content, content_type="application/json")
    response["Content-Disposition"] = (
        f'attachment; filename="agent-manifest-{proposal.pk}-v{manifest.version}.json"'
    )
    response["ETag"] = f'"{manifest.artifact_hash}"'
    return response


@require_GET
def download_evidence(
    request: HttpRequest,
    proposal_id: int,
    artifact_type: str,
) -> HttpResponse:
    """Download one exact JSON evidence artifact for the evaluated sandbox agent."""
    artifact = get_object_or_404(
        EvidenceArtifact,
        agent__manifest__proposal_id=proposal_id,
        artifact_type=artifact_type,
    )
    response = HttpResponse(artifact.content, content_type="application/json")
    response["Content-Disposition"] = (
        f'attachment; filename="{artifact.artifact_type}-{proposal_id}-v{artifact.version}.json"'
    )
    response["ETag"] = f'"{artifact.artifact_hash}"'
    return response


def _proposal_context(
    proposal: WorkflowProposal,
    *,
    operation_error: str = "",
    requested_stage: str | None = None,
) -> dict[str, object]:
    """Build one complete hypermedia representation of the vertical slice."""
    approvals = list(proposal.approvals.all())
    approvals_by_role = {approval.review_role.value: approval for approval in approvals}
    manifest = proposal.manifests.order_by("-created_at").first()
    sandbox_agent = None
    if manifest is not None:
        try:
            sandbox_agent = manifest.sandbox_instance
        except SandboxAgentInstance.DoesNotExist:
            sandbox_agent = None
    finding_evidence = []
    if sandbox_agent is not None:
        finding_evidence = [
            {"finding": finding, "citations": json.loads(finding.citations)}
            for finding in sandbox_agent.findings.all()
        ]
    navigation = _proposal_navigation(
        proposal,
        approvals=approvals,
        manifest=manifest,
        sandbox_agent=sandbox_agent,
    )
    initial_stage = (
        requested_stage if requested_stage in PROPOSAL_STAGES else navigation["recommended_stage"]
    )
    return {
        "approval_form": ApprovalForm(),
        "business_approval": approvals_by_role.get("business_owner"),
        "evidence_artifacts": (
            list(sandbox_agent.evidence_artifacts.all()) if sandbox_agent else []
        ),
        "finding_evidence": finding_evidence,
        "manifest": manifest,
        "operation_error": operation_error,
        "proposal": proposal,
        "proposal_navigation": navigation,
        "initial_proposal_stage": initial_stage,
        "sandbox_agent": sandbox_agent,
        "source_approval": approvals_by_role.get("source_owner"),
    }


def _proposal_navigation(
    proposal: WorkflowProposal,
    *,
    approvals: list | None = None,
    manifest=None,
    sandbox_agent: SandboxAgentInstance | None = None,
) -> dict[str, object]:
    """Return the plain-language current state and one recommended next action."""
    if approvals is None:
        approvals = list(proposal.approvals.all())
    approval_roles = {approval.review_role.value for approval in approvals}
    if manifest is None:
        manifest = proposal.manifests.order_by("-created_at").first()
    if sandbox_agent is None and manifest is not None:
        try:
            sandbox_agent = manifest.sandbox_instance
        except SandboxAgentInstance.DoesNotExist:
            sandbox_agent = None

    if proposal.status == ProposalStatus.BLOCKED:
        stage, action, actor = "define", "Resolve blocking controls", "Design owner"
    elif manifest is None:
        stage, action, actor = "define", "Complete the versioned definition", "Requester"
    elif ReviewRole.BUSINESS_OWNER not in approval_roles:
        stage, action, actor = "approve", "Approve the business outcome", "Business owner"
    elif ReviewRole.SOURCE_OWNER not in approval_roles:
        stage, action, actor = "approve", "Approve the source scope", "Source owner"
    elif sandbox_agent is None:
        stage, action, actor = "test", "Register the sandbox agent", "Sandbox operator"
    elif sandbox_agent.status == SandboxStatus.REGISTERED:
        stage, action, actor = "test", "Run the sandbox evaluation", "Sandbox operator"
    else:
        stage, action, actor = "evidence", "Review findings and evidence", "Governance reviewer"

    return {
        "proposal": proposal,
        "recommended_stage": stage,
        "stage_label": {
            "define": "Define",
            "approve": "Approve",
            "test": "Test",
            "evidence": "Evidence",
        }[stage],
        "next_action": action,
        "next_actor": actor,
        "url": f"{proposal.get_absolute_url()}?stage={stage}",
    }


def _proposal_stage_url(proposal: WorkflowProposal, context: dict[str, object]) -> str:
    """Build the canonical URL for the proposal's recommended stage."""
    return (
        f"{proposal.get_absolute_url()}?stage={context['proposal_navigation']['recommended_stage']}"
    )
