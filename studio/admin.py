"""Administrative views for catalog and proposal inspection."""

from django.contrib import admin

from studio.models import (
    AgentManifest,
    ControlCheck,
    EvaluationResult,
    EvidenceArtifact,
    InsuranceFinding,
    OntologyEdge,
    OntologyNode,
    ProofEvent,
    ProposalApproval,
    ProposalBinding,
    SandboxAgentInstance,
    ToolInvocation,
    WorkflowProposal,
)


class ReadOnlyEvidenceAdmin(admin.ModelAdmin):
    """Prevent administrative mutation of append-only sandbox proof."""

    def get_readonly_fields(self, request, obj=None):
        return tuple(field.name for field in self.model._meta.fields)

    def has_add_permission(self, request) -> bool:
        return False

    def has_change_permission(self, request, obj=None) -> bool:
        return False

    def has_delete_permission(self, request, obj=None) -> bool:
        return False


@admin.register(OntologyNode)
class OntologyNodeAdmin(admin.ModelAdmin):
    """Inspect and maintain registered ontology concepts."""

    list_display = (
        "id",
        "name",
        "node_type",
        "business_domain",
        "owner",
        "classification",
        "approval_state",
        "updated_at",
    )
    search_fields = ("name", "slug", "description", "search_terms", "owner")
    list_filter = (
        "node_type",
        "business_domain",
        "classification",
        "approval_state",
        "updated_at",
    )
    readonly_fields = ("id", "created_at", "updated_at")


@admin.register(OntologyEdge)
class OntologyEdgeAdmin(admin.ModelAdmin):
    """Inspect typed ontology relationships."""

    list_display = ("id", "source", "relation", "target", "created_at")
    list_select_related = ("source", "target")
    search_fields = ("source__name", "target__name", "rationale")
    list_filter = ("relation", "created_at")
    autocomplete_fields = ("source", "target")
    readonly_fields = ("id", "created_at")


@admin.register(WorkflowProposal)
class WorkflowProposalAdmin(admin.ModelAdmin):
    """Inspect persisted workflow proposals without provider secrets or payloads."""

    list_display = (
        "id",
        "title",
        "status",
        "risk_level",
        "agent_name",
        "model_provider",
        "model_name",
        "model_used",
        "created_at",
    )
    search_fields = ("title", "intent", "requester_role", "summary")
    list_filter = ("status", "risk_level", "model_provider", "model_used", "created_at")
    readonly_fields = ("id", "created_at", "updated_at")


@admin.register(ProposalBinding)
class ProposalBindingAdmin(admin.ModelAdmin):
    """Inspect proposal-to-ontology bindings."""

    list_display = ("id", "proposal", "node", "binding_kind", "access_mode", "created_at")
    list_select_related = ("proposal", "node")
    search_fields = ("proposal__title", "node__name", "purpose")
    list_filter = ("binding_kind", "access_mode", "created_at")
    autocomplete_fields = ("proposal", "node")
    readonly_fields = ("id", "created_at")


@admin.register(ControlCheck)
class ControlCheckAdmin(admin.ModelAdmin):
    """Inspect deterministic governance results."""

    list_display = ("id", "proposal", "name", "outcome", "control", "created_at")
    list_select_related = ("proposal", "control")
    search_fields = ("proposal__title", "name", "detail")
    list_filter = ("outcome", "created_at")
    autocomplete_fields = ("proposal", "control")
    readonly_fields = ("id", "created_at")


@admin.register(ProofEvent)
class ProofEventAdmin(admin.ModelAdmin):
    """Inspect append-only proposal proof events."""

    list_display = ("id", "proposal", "event_type", "actor", "evidence_reference", "created_at")
    list_select_related = ("proposal",)
    search_fields = ("proposal__title", "actor", "summary", "evidence_reference")
    list_filter = ("event_type", "created_at")
    autocomplete_fields = ("proposal",)
    readonly_fields = (
        "id",
        "proposal",
        "event_type",
        "actor",
        "summary",
        "evidence_reference",
        "created_at",
    )

    def has_add_permission(self, request) -> bool:
        return False

    def has_change_permission(self, request, obj=None) -> bool:
        return False

    def has_delete_permission(self, request, obj=None) -> bool:
        return False


@admin.register(ProposalApproval)
class ProposalApprovalAdmin(ReadOnlyEvidenceAdmin):
    """Inspect independent role-specific proposal decisions."""

    list_display = ("id", "proposal", "review_role", "decision", "approver", "created_at")
    list_select_related = ("proposal",)
    search_fields = ("proposal__title", "approver", "note")
    list_filter = ("review_role", "decision", "created_at")


@admin.register(AgentManifest)
class AgentManifestAdmin(ReadOnlyEvidenceAdmin):
    """Inspect immutable versioned agent manifest metadata."""

    list_display = ("id", "proposal", "version", "schema_version", "size_bytes", "created_at")
    list_select_related = ("proposal",)
    search_fields = ("proposal__title", "artifact_hash", "prompt_version")
    list_filter = ("schema_version", "created_at")


@admin.register(SandboxAgentInstance)
class SandboxAgentInstanceAdmin(ReadOnlyEvidenceAdmin):
    """Inspect mocked orchestration registrations and terminal sandbox status."""

    list_display = ("id", "external_id", "environment", "status", "created_at", "updated_at")
    list_select_related = ("manifest",)
    search_fields = ("external_id", "orchestration_request_id", "manifest__proposal__title")
    list_filter = ("environment", "status", "created_at")


@admin.register(ToolInvocation)
class ToolInvocationAdmin(ReadOnlyEvidenceAdmin):
    """Inspect dual-identity synthetic tool and policy traces."""

    list_display = ("id", "agent", "sequence", "tool", "resource", "decision", "latency_ms")
    list_select_related = ("agent", "tool")
    search_fields = ("agent__external_id", "tool__name", "resource", "policy_reason")
    list_filter = ("decision", "tool", "created_at")


@admin.register(InsuranceFinding)
class InsuranceFindingAdmin(ReadOnlyEvidenceAdmin):
    """Inspect synthetic cited findings retained for human review."""

    list_display = ("id", "agent", "title", "disposition", "created_at")
    list_select_related = ("agent",)
    search_fields = ("title", "finding", "citations", "agent__external_id")
    list_filter = ("disposition", "created_at")


@admin.register(EvaluationResult)
class EvaluationResultAdmin(ReadOnlyEvidenceAdmin):
    """Inspect deterministic sandbox evaluation outcomes."""

    list_display = ("id", "agent", "test_case", "outcome", "score", "latency_ms", "created_at")
    list_select_related = ("agent",)
    search_fields = ("agent__external_id", "expected", "observed", "artifact_hash")
    list_filter = ("test_case", "outcome", "created_at")


@admin.register(EvidenceArtifact)
class EvidenceArtifactAdmin(ReadOnlyEvidenceAdmin):
    """Inspect downloadable evaluation and evidence manifest artifacts."""

    list_display = ("id", "agent", "artifact_type", "version", "size_bytes", "created_at")
    list_select_related = ("agent",)
    search_fields = ("agent__external_id", "artifact_hash")
    list_filter = ("artifact_type", "version", "created_at")
