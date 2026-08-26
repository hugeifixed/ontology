"""Thin server-rendered and HTMX entry points for the studio."""

import json

from django.conf import settings
from django.http import HttpRequest, HttpResponse
from django.shortcuts import get_object_or_404, render
from django.views.decorators.http import require_GET, require_POST
from django.views.decorators.vary import vary_on_headers
from loguru import logger

from studio.discovery import discover_catalog
from studio.forms import ApprovalForm, DiscoveryForm, ProposalForm
from studio.models import (
    EvidenceArtifact,
    NodeType,
    OntologyEdge,
    OntologyNode,
    SandboxAgentInstance,
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
SECTIONS = {"overview", "ontology", "catalog", "connections", "compose", "proposals"}
PROPOSAL_PARTIAL = "studio/partials/proposal_detail.html#proposal-detail"
PROPOSAL_ERROR_PARTIAL = "studio/partials/proposal_error.html#proposal-error"
DISCOVERY_PARTIAL = "studio/partials/discovery_results.html#discovery-results"


@require_GET
def dashboard(request: HttpRequest) -> HttpResponse:
    """Render the integrated catalog, ontology, and proposal workspace."""
    proposals = WorkflowProposal.objects.select_related("existing_workflow")[:8]
    requested_section = request.GET.get("section", "overview")
    context = {
        "initial_section": requested_section if requested_section in SECTIONS else "overview",
        "discovery_form": DiscoveryForm(),
        "proposal_form": ProposalForm(initial={"intent": REFERENCE_INTENT}),
        "proposals": proposals,
        "latest_proposal": proposals[0] if proposals else None,
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
    response = render(
        request,
        PROPOSAL_PARTIAL,
        _proposal_context(proposal),
    )
    response["HX-Trigger"] = "proposalCreated"
    return response


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
        _proposal_context(proposal),
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
    response = render(
        request,
        PROPOSAL_PARTIAL,
        _proposal_context(proposal),
    )
    response["HX-Trigger"] = "proposalApproved"
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
    response = render(request, PROPOSAL_PARTIAL, _proposal_context(proposal))
    response["HX-Trigger"] = "sandboxRegistered"
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
    response = render(request, PROPOSAL_PARTIAL, _proposal_context(proposal))
    response["HX-Trigger"] = "sandboxEvaluated"
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
        "sandbox_agent": sandbox_agent,
        "source_approval": approvals_by_role.get("source_owner"),
    }
