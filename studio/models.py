"""Persistence models for catalog ontology, proposals, and proof of work."""

from auditlog.models import AuditlogHistoryField
from django.db import models
from django.urls import reverse
from django.utils import timezone
from django_enum import EnumField


class MutableModel(models.Model):
    """Base model for records that can change over time."""

    history = AuditlogHistoryField()
    id = models.BigAutoField(
        primary_key=True,
        db_comment="Surrogate primary key for this record.",
        help_text="System-assigned record identifier.",
    )
    created_at = models.DateTimeField(
        default=timezone.now,
        db_comment="Timestamp when this record was created.",
        help_text="Date and time when the record was created.",
    )
    updated_at = models.DateTimeField(
        default=timezone.now,
        db_comment="Timestamp when this record was last updated.",
        help_text="Date and time of the most recent saved change.",
    )

    class Meta:
        abstract = True

    def save(self, *args, **kwargs) -> None:
        """Keep the explicit modification timestamp current."""
        self.updated_at = timezone.now()
        super().save(*args, **kwargs)


class ImmutableModel(models.Model):
    """Base model for append-only evidence records."""

    history = AuditlogHistoryField()
    id = models.BigAutoField(
        primary_key=True,
        db_comment="Surrogate primary key for this record.",
        help_text="System-assigned record identifier.",
    )
    created_at = models.DateTimeField(
        default=timezone.now,
        db_comment="Timestamp when this record was created.",
        help_text="Date and time when the record was created.",
    )

    class Meta:
        abstract = True


class NodeType(models.TextChoices):
    """Supported ontology concept types."""

    BUSINESS_OUTCOME = "business_outcome", "Business outcome"
    USER_ROLE = "user_role", "User role"
    DATA_PRODUCT = "data_product", "Data product"
    SYSTEM = "system", "System"
    CONNECTOR = "connector", "Connector"
    TOOL = "tool", "Tool"
    AGENT_CAPABILITY = "agent_capability", "Agent capability"
    AGENT_INSTANCE = "agent_instance", "Agent instance"
    WORKFLOW = "workflow", "Workflow"
    CONTROL = "control", "Control"
    DELIVERY_ARTIFACT = "delivery_artifact", "Delivery artifact"


class Classification(models.TextChoices):
    """Information sensitivity levels used by the demo."""

    PUBLIC = "public", "Public"
    INTERNAL = "internal", "Internal"
    CONFIDENTIAL = "confidential", "Confidential"
    RESTRICTED = "restricted", "Restricted"


class ApprovalState(models.TextChoices):
    """Governance state of a reusable ontology concept."""

    DRAFT = "draft", "Draft"
    APPROVED = "approved", "Approved"
    CONDITIONAL = "conditional", "Conditionally approved"
    RETIRED = "retired", "Retired"


class BusinessDomain(models.TextChoices):
    """Business domains used to scope catalog discovery."""

    ENTERPRISE = "enterprise", "Enterprise / shared"
    TREASURY = "treasury_management", "Treasury management"
    RETAIL = "retail_banking", "Retail banking"
    COMMERCIAL_LOAN = "commercial_loan_servicing", "Commercial loan servicing"


class RelationType(models.TextChoices):
    """Typed relationships between ontology concepts."""

    SERVES = "serves", "Serves"
    USED_BY = "used_by", "Used by"
    USES = "uses", "Uses"
    READS = "reads", "Reads"
    RESIDES_IN = "resides_in", "Resides in"
    EXPOSES = "exposes", "Exposes"
    INVOKES = "invokes", "Invokes"
    INSTANCE_OF = "instance_of", "Instance of"
    CONSTRAINED_BY = "constrained_by", "Constrained by"
    REQUIRES = "requires", "Requires"
    PRODUCES = "produces", "Produces"
    IMPLEMENTS = "implements", "Implements"


class OntologyNode(MutableModel):
    """A governed, reusable concept in the enterprise AI catalog."""

    slug = models.SlugField(
        max_length=100,
        unique=True,
        db_comment="Stable machine-readable identifier for the ontology concept.",
        help_text="Stable identifier used in catalog references and proposal payloads.",
    )
    node_type = EnumField(
        NodeType,
        max_length=40,
        db_comment="Ontology category assigned to the concept.",
        help_text="Select the concept's role in the governed ontology.",
    )
    name = models.CharField(
        max_length=180,
        db_comment="Human-readable name of the ontology concept.",
        help_text="Concise name shown throughout the catalog and proposal views.",
    )
    description = models.TextField(
        db_comment="Plain-language definition and scope of the ontology concept.",
        help_text="Explain what the concept represents and where its responsibility ends.",
    )
    owner = models.CharField(
        max_length=180,
        db_comment="Accountable organizational owner of the ontology concept.",
        help_text="Team or function accountable for approving and maintaining this concept.",
    )
    classification = EnumField(
        Classification,
        max_length=24,
        db_comment="Information-sensitivity classification of the concept.",
        help_text="Highest sensitivity level associated with using this concept.",
    )
    approval_state = EnumField(
        ApprovalState,
        max_length=24,
        db_comment="Governance approval state of the ontology concept.",
        help_text="Controls whether the concept can be selected for a proposal.",
    )
    source_reference = models.CharField(
        max_length=220,
        blank=True,
        db_comment="Optional reference to the authoritative source or registry entry.",
        help_text="Name or locator of the authoritative source for this concept, when known.",
    )
    business_domain = EnumField(
        BusinessDomain,
        max_length=40,
        default=BusinessDomain.ENTERPRISE,
        db_comment="Business domain responsible for using or governing the concept.",
        help_text="Domain used to scope discovery and route accountable ownership.",
    )
    search_terms = models.TextField(
        blank=True,
        db_comment="Curated synonyms and business phrases used for explainable discovery.",
        help_text=(
            "Add plain-language terms requesters may use for this concept. "
            "Do not add customer data."
        ),
    )

    class Meta:
        db_table = "studio_ontology_nodes"
        db_table_comment = "Governed ontology concepts available for workflow design and review."
        verbose_name = "ontology concept"
        verbose_name_plural = "ontology concepts"
        ordering = ("node_type", "name")
        indexes = (
            models.Index(fields=("node_type", "approval_state")),
            models.Index(fields=("classification",)),
            models.Index(fields=("business_domain", "approval_state")),
        )

    def __str__(self) -> str:
        return self.name


class OntologyEdge(ImmutableModel):
    """A typed, explainable relationship between two ontology concepts."""

    source = models.ForeignKey(
        OntologyNode,
        on_delete=models.CASCADE,
        related_name="outgoing_edges",
        db_comment="Ontology concept where this directed relationship begins.",
        help_text="Concept that acts as the source of the relationship.",
    )
    relation = EnumField(
        RelationType,
        max_length=32,
        db_comment="Semantic type of the directed ontology relationship.",
        help_text="Describe how the source concept relates to the target concept.",
    )
    target = models.ForeignKey(
        OntologyNode,
        on_delete=models.CASCADE,
        related_name="incoming_edges",
        db_comment="Ontology concept where this directed relationship ends.",
        help_text="Concept that acts as the target of the relationship.",
    )
    rationale = models.TextField(
        blank=True,
        db_comment="Optional explanation supporting the ontology relationship.",
        help_text="Explain why this relationship exists or cite its governing source.",
    )

    class Meta:
        db_table = "studio_ontology_edges"
        db_table_comment = "Typed directed relationships that connect governed ontology concepts."
        verbose_name = "ontology relationship"
        verbose_name_plural = "ontology relationships"
        ordering = ("source__name", "relation", "target__name")
        constraints = (
            models.UniqueConstraint(
                fields=("source", "relation", "target"),
                name="unique_ontology_edge",
            ),
        )
        indexes = (models.Index(fields=("relation",)),)

    def __str__(self) -> str:
        return f"{self.source} {self.get_relation_display()} {self.target}"


class ProposalStatus(models.TextChoices):
    """Lifecycle states for a workflow proposal."""

    DRAFT = "draft", "Draft"
    NEEDS_REVIEW = "needs_review", "Needs review"
    APPROVED = "approved", "Approved for sandbox"
    BLOCKED = "blocked", "Blocked"


class RiskLevel(models.TextChoices):
    """Coarse risk tier used for routing approvals."""

    LOW = "low", "Low"
    MODERATE = "moderate", "Moderate"
    HIGH = "high", "High"


class WorkflowProposal(MutableModel):
    """A reviewable workflow-and-agent specification derived from business intent."""

    title = models.CharField(
        max_length=180,
        db_comment="Human-readable title of the workflow proposal.",
        help_text="Short title that distinguishes this proposal in review lists.",
    )
    intent = models.TextField(
        db_comment="Original business intent submitted by the requester.",
        help_text="The request supplied for interpretation and proposal composition.",
    )
    requester_role = models.CharField(
        max_length=160,
        db_comment="Business role accountable for submitting the proposal intent.",
        help_text="Role or function requesting the governed workflow.",
    )
    business_outcome = models.TextField(
        db_comment="Normalized business outcome derived from the submitted intent.",
        help_text="Plain-language outcome the proposed workflow is expected to support.",
    )
    summary = models.TextField(
        db_comment="Review summary of the proposed workflow and agent behavior.",
        help_text="Concise explanation for reviewers evaluating the proposal.",
    )
    agent_name = models.CharField(
        max_length=180,
        default="Insurance Covenant Review Agent",
        db_comment="Human-readable name assigned to the proposed sandbox agent.",
        help_text="Agent name exported into the versioned sandbox manifest.",
    )
    status = EnumField(
        ProposalStatus,
        max_length=24,
        db_comment="Current governance lifecycle state of the workflow proposal.",
        help_text="Current review and sandbox-readiness state.",
    )
    risk_level = EnumField(
        RiskLevel,
        max_length=24,
        db_comment="Calculated risk tier used to route proposal review.",
        help_text="Risk tier derived from requested actions and bound data classifications.",
    )
    model_provider = models.CharField(
        max_length=40,
        db_comment="Provider route selected for proposal composition.",
        help_text="Provider route used or selected when the proposal was composed.",
    )
    model_name = models.CharField(
        max_length=100,
        db_comment="Model identifier selected for proposal composition.",
        help_text="Model name requested from the selected provider route.",
    )
    model_used = models.BooleanField(
        default=False,
        db_comment="Whether an external language model processed the submitted intent.",
        help_text="Indicates whether composition invoked an external model.",
    )
    prompt_version = models.CharField(
        max_length=80,
        default="insurance-intent-v1.0.0",
        db_comment="Version of the bounded intent-interpretation prompt contract.",
        help_text="Version identifier for the prompt used to compose this proposal.",
    )
    model_latency_ms = models.PositiveIntegerField(
        default=0,
        db_comment="Measured wall-clock latency of proposal composition in milliseconds.",
        help_text="Elapsed time spent composing the structured proposal.",
    )
    input_tokens = models.PositiveIntegerField(
        default=0,
        db_comment="Provider-reported input token count for proposal composition.",
        help_text="Input tokens reported by the selected model provider, when available.",
    )
    output_tokens = models.PositiveIntegerField(
        default=0,
        db_comment="Provider-reported output token count for proposal composition.",
        help_text="Output tokens reported by the selected model provider, when available.",
    )
    estimated_cost_usd = models.DecimalField(
        max_digits=12,
        decimal_places=6,
        blank=True,
        null=True,
        db_comment="Estimated provider cost in US dollars for proposal composition.",
        help_text="Estimated composition cost; blank when the route has no stable price mapping.",
    )
    existing_workflow = models.ForeignKey(
        OntologyNode,
        blank=True,
        null=True,
        on_delete=models.PROTECT,
        related_name="proposals_reusing_workflow",
        db_comment="Optional registered workflow selected as the proposal extension point.",
        help_text="Existing approved workflow to extend instead of creating a new one.",
    )

    class Meta:
        db_table = "studio_workflow_proposals"
        db_table_comment = (
            "Reviewable workflow and agent specifications derived from business intent."
        )
        verbose_name = "workflow proposal"
        verbose_name_plural = "workflow proposals"
        ordering = ("-created_at",)
        indexes = (
            models.Index(fields=("status", "created_at")),
            models.Index(fields=("risk_level",)),
            models.Index(fields=("-created_at",), name="proposal_recent_idx"),
        )

    def __str__(self) -> str:
        return self.title

    def get_absolute_url(self) -> str:
        return reverse("studio:proposal-detail", kwargs={"proposal_id": self.pk})


class BindingKind(models.TextChoices):
    """How an ontology object participates in a proposal."""

    DATA = "data", "Data binding"
    TOOL = "tool", "Tool binding"
    AGENT = "agent", "Agent binding"
    CONTROL = "control", "Control binding"
    DELIVERY = "delivery", "Delivery binding"


class AccessMode(models.TextChoices):
    """Permitted interaction mode for a proposal binding."""

    READ = "read", "Read only"
    INVOKE = "invoke", "Invoke"
    ENFORCE = "enforce", "Enforce"
    GENERATE = "generate", "Generate draft"


class ProposalBinding(ImmutableModel):
    """A governed ontology binding selected for a workflow proposal."""

    proposal = models.ForeignKey(
        WorkflowProposal,
        on_delete=models.CASCADE,
        related_name="bindings",
        db_comment="Workflow proposal that owns this ontology binding.",
        help_text="Proposal whose design depends on the selected ontology concept.",
    )
    node = models.ForeignKey(
        OntologyNode,
        on_delete=models.PROTECT,
        related_name="proposal_bindings",
        db_comment="Governed ontology concept bound into the workflow proposal.",
        help_text="Approved or conditional catalog concept used by the proposal.",
    )
    binding_kind = EnumField(
        BindingKind,
        max_length=24,
        db_comment="Functional role of the ontology concept within the proposal.",
        help_text="How the selected concept participates in the proposed workflow.",
    )
    access_mode = EnumField(
        AccessMode,
        max_length=24,
        db_comment="Permitted interaction mode for the bound ontology concept.",
        help_text="Maximum action the proposed workflow may take through this binding.",
    )
    purpose = models.TextField(
        db_comment="Proposal-specific reason for including the ontology concept.",
        help_text="Explain why this binding is necessary for the proposed outcome.",
    )

    class Meta:
        db_table = "studio_proposal_bindings"
        db_table_comment = (
            "Governed ontology concepts selected as dependencies of workflow proposals."
        )
        verbose_name = "proposal binding"
        verbose_name_plural = "proposal bindings"
        ordering = ("binding_kind", "node__name")
        constraints = (
            models.UniqueConstraint(
                fields=("proposal", "node", "binding_kind"),
                name="unique_proposal_binding",
            ),
        )

    def __str__(self) -> str:
        return f"{self.proposal}: {self.node}"


class CheckOutcome(models.TextChoices):
    """Result of a deterministic proposal policy check."""

    PASS = "pass", "Pass"
    WARNING = "warning", "Warning"
    BLOCK = "block", "Block"


class ControlCheck(ImmutableModel):
    """A deterministic control result attached to a workflow proposal."""

    proposal = models.ForeignKey(
        WorkflowProposal,
        on_delete=models.CASCADE,
        related_name="control_checks",
        db_comment="Workflow proposal evaluated by this deterministic control check.",
        help_text="Proposal whose policy conformance was evaluated.",
    )
    control = models.ForeignKey(
        OntologyNode,
        blank=True,
        null=True,
        on_delete=models.PROTECT,
        related_name="control_checks",
        db_comment="Optional ontology control that defines this check.",
        help_text="Registered control represented by this result, when applicable.",
    )
    name = models.CharField(
        max_length=180,
        db_comment="Human-readable name of the deterministic control check.",
        help_text="Concise name shown to proposal reviewers.",
    )
    outcome = EnumField(
        CheckOutcome,
        max_length=24,
        db_comment="Deterministic outcome returned by the control check.",
        help_text="Whether the proposal passed, raised a warning, or was blocked.",
    )
    detail = models.TextField(
        db_comment="Reviewable explanation of the control-check outcome.",
        help_text="Explain the evidence and rule that produced this outcome.",
    )

    class Meta:
        db_table = "studio_control_checks"
        db_table_comment = (
            "Deterministic governance results produced while evaluating workflow proposals."
        )
        verbose_name = "control check"
        verbose_name_plural = "control checks"
        ordering = ("created_at",)
        indexes = (
            models.Index(
                fields=("proposal", "outcome"),
                name="control_prop_outcome_idx",
            ),
        )

    def __str__(self) -> str:
        return f"{self.name}: {self.get_outcome_display()}"


class ProofEventType(models.TextChoices):
    """Auditable steps in the proposal lifecycle."""

    INTENT_CAPTURED = "intent_captured", "Intent captured"
    MODEL_INVOKED = "model_invoked", "Model invoked"
    MODEL_BYPASSED = "model_bypassed", "Model bypassed"
    ONTOLOGY_MATCHED = "ontology_matched", "Ontology matched"
    POLICY_CHECKED = "policy_checked", "Policy checked"
    HUMAN_APPROVED = "human_approved", "Human approved"
    SDLC_PACKAGE_READY = "sdlc_package_ready", "SDLC package ready"
    MANIFEST_EXPORTED = "manifest_exported", "Manifest exported"
    BUSINESS_APPROVED = "business_approved", "Business owner approved"
    SOURCE_APPROVED = "source_approved", "Source owner approved"
    SANDBOX_REGISTERED = "sandbox_registered", "Sandbox agent registered"
    TOOL_INVOKED = "tool_invoked", "Synthetic tool invoked"
    POLICY_DECIDED = "policy_decided", "Runtime policy decided"
    EVALUATION_COMPLETED = "evaluation_completed", "Evaluation completed"
    SANDBOX_EVALUATION_PASSED = (
        "sandbox_evaluation_passed",
        "Sandbox evaluation passed",
    )


class ProofEvent(ImmutableModel):
    """Append-only, non-sensitive evidence about proposal processing."""

    proposal = models.ForeignKey(
        WorkflowProposal,
        on_delete=models.CASCADE,
        related_name="proof_events",
        db_comment="Workflow proposal whose lifecycle produced this proof event.",
        help_text="Proposal associated with this append-only evidence record.",
    )
    event_type = EnumField(
        ProofEventType,
        max_length=32,
        db_comment="Lifecycle event category represented by this proof record.",
        help_text="Auditable stage of proposal processing represented by this event.",
    )
    actor = models.CharField(
        max_length=120,
        db_comment="Human role or system component responsible for the event.",
        help_text="Accountable person, role, or service that performed the recorded action.",
    )
    summary = models.TextField(
        db_comment="Non-sensitive explanation of the lifecycle event.",
        help_text="Describe what occurred without storing secrets or raw provider payloads.",
    )
    evidence_reference = models.CharField(
        max_length=180,
        db_comment="Stable reference used to correlate supporting evidence.",
        help_text="Non-secret identifier linking this event to its supporting evidence.",
    )

    class Meta:
        db_table = "studio_proof_events"
        db_table_comment = (
            "Append-only, non-sensitive evidence for workflow proposal lifecycle events."
        )
        verbose_name = "proof event"
        verbose_name_plural = "proof events"
        ordering = ("created_at",)
        indexes = (
            models.Index(fields=("event_type", "created_at")),
            models.Index(
                fields=("proposal", "event_type"),
                name="proof_prop_event_idx",
            ),
        )

    def __str__(self) -> str:
        return f"{self.get_event_type_display()} for {self.proposal}"


class ReviewRole(models.TextChoices):
    """Independent human roles required before sandbox registration."""

    BUSINESS_OWNER = "business_owner", "Business owner"
    SOURCE_OWNER = "source_owner", "Source owner"


class ReviewDecision(models.TextChoices):
    """Human decisions available for a sandbox proposal."""

    APPROVED = "approved", "Approved"
    REJECTED = "rejected", "Rejected"


class ProposalApproval(ImmutableModel):
    """One role-specific human decision for a workflow proposal."""

    proposal = models.ForeignKey(
        WorkflowProposal,
        on_delete=models.CASCADE,
        related_name="approvals",
        db_comment="Workflow proposal receiving this independent human decision.",
        help_text="Proposal reviewed by the accountable business or source owner.",
    )
    review_role = EnumField(
        ReviewRole,
        max_length=32,
        db_comment="Independent governance role represented by this decision.",
        help_text="Business-owner or source-owner responsibility represented by the reviewer.",
    )
    decision = EnumField(
        ReviewDecision,
        max_length=24,
        db_comment="Decision recorded by the accountable reviewer.",
        help_text="Reviewer decision for controlled sandbox registration.",
    )
    approver = models.CharField(
        max_length=160,
        db_comment="Named synthetic reviewer or accountable reviewing function.",
        help_text="Person or function accountable for this decision.",
    )
    note = models.TextField(
        blank=True,
        db_comment="Optional rationale supplied with the human decision.",
        help_text="Explain approval conditions or reasons for rejection.",
    )

    class Meta:
        db_table = "studio_proposal_approvals"
        db_table_comment = "Independent business-owner and source-owner proposal decisions."
        verbose_name = "proposal approval"
        verbose_name_plural = "proposal approvals"
        ordering = ("created_at",)
        constraints = (
            models.UniqueConstraint(
                fields=("proposal", "review_role"),
                name="unique_proposal_review_role",
            ),
        )
        indexes = (models.Index(fields=("review_role", "decision")),)

    def __str__(self) -> str:
        return f"{self.get_review_role_display()}: {self.get_decision_display()}"


class AgentManifest(ImmutableModel):
    """A versioned, downloadable sandbox agent specification."""

    proposal = models.ForeignKey(
        WorkflowProposal,
        on_delete=models.CASCADE,
        related_name="manifests",
        db_comment="Workflow proposal represented by this versioned agent manifest.",
        help_text="Proposal from which the manifest was deterministically exported.",
    )
    version = models.CharField(
        max_length=32,
        db_comment="Semantic version assigned to the exported agent manifest.",
        help_text="Immutable semantic version for this manifest artifact.",
    )
    schema_version = models.CharField(
        max_length=48,
        db_comment="Version of the agent-manifest schema used by the artifact.",
        help_text="Schema contract understood by the mocked orchestration boundary.",
    )
    prompt_version = models.CharField(
        max_length=80,
        db_comment="Prompt contract version captured in the agent manifest.",
        help_text="Intent-interpretation prompt version associated with this specification.",
    )
    content = models.TextField(
        db_comment="Canonical JSON content of the versioned agent manifest.",
        help_text="Exact JSON bytes made available through the manifest download endpoint.",
    )
    artifact_hash = models.CharField(
        max_length=64,
        db_index=True,
        db_comment="SHA-256 digest of the canonical manifest content.",
        help_text="Integrity digest used to verify the downloaded manifest.",
    )
    size_bytes = models.PositiveIntegerField(
        db_comment="UTF-8 byte length of the canonical manifest content.",
        help_text="Size of the exported manifest artifact in bytes.",
    )

    class Meta:
        db_table = "studio_agent_manifests"
        db_table_comment = "Immutable, versioned agent manifests exported from governed proposals."
        verbose_name = "agent manifest"
        verbose_name_plural = "agent manifests"
        ordering = ("-created_at",)
        constraints = (
            models.UniqueConstraint(
                fields=("proposal", "version"),
                name="unique_proposal_manifest_version",
            ),
        )

    def __str__(self) -> str:
        return f"{self.proposal} manifest {self.version}"


class SandboxStatus(models.TextChoices):
    """Terminally sandbox-only lifecycle states for a registered agent."""

    REGISTERED = "registered", "Registered in sandbox"
    EVALUATION_PASSED = "evaluation_passed", "Sandbox evaluation passed"
    EVALUATION_FAILED = "evaluation_failed", "Sandbox evaluation failed"


class SandboxAgentInstance(MutableModel):
    """One mocked orchestration registration for a versioned manifest."""

    manifest = models.OneToOneField(
        AgentManifest,
        on_delete=models.PROTECT,
        related_name="sandbox_instance",
        db_comment="Versioned manifest registered with the mocked orchestration service.",
        help_text="Immutable agent specification used for this sandbox instance.",
    )
    external_id = models.CharField(
        max_length=100,
        unique=True,
        db_comment="Synthetic agent identifier returned by mocked orchestration.",
        help_text="Sandbox-only identifier assigned by the orchestration adapter.",
    )
    orchestration_request_id = models.CharField(
        max_length=100,
        unique=True,
        db_comment="Correlation identifier returned by mocked orchestration.",
        help_text="Request identifier used to demonstrate the orchestration boundary.",
    )
    environment = models.CharField(
        max_length=64,
        default="synthetic-sandbox",
        db_comment="Non-production environment where the agent was registered.",
        help_text="Explicit runtime environment; this demo only supports synthetic sandbox.",
    )
    status = EnumField(
        SandboxStatus,
        max_length=32,
        db_comment="Current sandbox registration or evaluation state.",
        help_text="Lifecycle state that can never represent production deployment.",
    )

    class Meta:
        db_table = "studio_sandbox_agent_instances"
        db_table_comment = "Sandbox-only agent registrations returned by mocked orchestration."
        verbose_name = "sandbox agent instance"
        verbose_name_plural = "sandbox agent instances"
        ordering = ("-created_at",)
        indexes = (models.Index(fields=("status", "created_at")),)

    def __str__(self) -> str:
        return f"{self.external_id} ({self.get_status_display()})"


class PolicyDecision(models.TextChoices):
    """Runtime authorization outcomes for synthetic tool calls."""

    ALLOW = "allow", "Allowed"
    DENY = "deny", "Denied"


class ToolInvocation(ImmutableModel):
    """One synthetic tool call with identities, policy, latency, and hashes."""

    agent = models.ForeignKey(
        SandboxAgentInstance,
        on_delete=models.CASCADE,
        related_name="tool_invocations",
        db_comment="Sandbox agent instance that requested the synthetic tool call.",
        help_text="Registered sandbox instance responsible for this invocation.",
    )
    tool = models.ForeignKey(
        OntologyNode,
        on_delete=models.PROTECT,
        related_name="sandbox_tool_invocations",
        db_comment="Registered ontology tool invoked by the sandbox agent.",
        help_text="Approved catalog tool represented by this synthetic call.",
    )
    sequence = models.PositiveSmallIntegerField(
        db_comment="Ordered position of the call within the sandbox run.",
        help_text="Stable sequence number used to reconstruct the runtime trace.",
    )
    human_subject = models.CharField(
        max_length=160,
        db_comment="Simulated human identity on whose behalf the call was made.",
        help_text="Synthetic analyst identity evaluated by runtime policy.",
    )
    agent_subject = models.CharField(
        max_length=160,
        db_comment="Registered sandbox agent identity making the call.",
        help_text="Agent identity evaluated independently from the simulated human.",
    )
    resource = models.CharField(
        max_length=160,
        db_comment="Synthetic resource identifier requested through the tool.",
        help_text="Loan or policy resource used to demonstrate authorization.",
    )
    decision = EnumField(
        PolicyDecision,
        max_length=16,
        db_comment="Runtime policy result for this synthetic tool request.",
        help_text="Whether policy allowed or denied the tool call.",
    )
    policy_reason = models.TextField(
        db_comment="Deterministic explanation for the runtime policy decision.",
        help_text="Human-readable rule and identity result supporting the decision.",
    )
    response_summary = models.TextField(
        blank=True,
        db_comment="Non-sensitive summary returned by the synthetic tool.",
        help_text="Bounded synthetic result; denied calls contain no source data.",
    )
    citations = models.TextField(
        blank=True,
        db_comment="Canonical JSON list of source citations returned by the tool.",
        help_text="Machine-readable citations available to the finding generator.",
    )
    latency_ms = models.PositiveIntegerField(
        db_comment="Measured synthetic tool execution latency in milliseconds.",
        help_text="Elapsed time for policy evaluation and synthetic connector execution.",
    )
    request_hash = models.CharField(
        max_length=64,
        db_comment="SHA-256 digest of the canonical, non-secret tool request.",
        help_text="Integrity digest for reconstructing the request evidence.",
    )
    response_hash = models.CharField(
        max_length=64,
        db_comment="SHA-256 digest of the canonical bounded tool response.",
        help_text="Integrity digest proving the allowed or denied response content.",
    )

    class Meta:
        db_table = "studio_tool_invocations"
        db_table_comment = "Append-only synthetic tool traces with dual-identity policy evidence."
        verbose_name = "tool invocation"
        verbose_name_plural = "tool invocations"
        ordering = ("sequence",)
        constraints = (
            models.UniqueConstraint(
                fields=("agent", "sequence"),
                name="unique_agent_tool_sequence",
            ),
        )
        indexes = (
            models.Index(fields=("agent", "decision")),
            models.Index(fields=("tool", "created_at")),
        )

    def __str__(self) -> str:
        return f"{self.agent.external_id} call {self.sequence}: {self.tool}"


class InsuranceFinding(ImmutableModel):
    """A synthetic insurance-review finding grounded in exact citations."""

    agent = models.ForeignKey(
        SandboxAgentInstance,
        on_delete=models.CASCADE,
        related_name="findings",
        db_comment="Sandbox agent instance that produced this cited finding.",
        help_text="Evaluated sandbox instance responsible for the finding.",
    )
    title = models.CharField(
        max_length=180,
        db_comment="Concise review title for the synthetic finding.",
        help_text="Short description displayed to the servicing reviewer.",
    )
    finding = models.TextField(
        db_comment="Synthetic evidence-based insurance observation.",
        help_text="Finding returned for human review without making a final determination.",
    )
    citations = models.TextField(
        db_comment="Canonical JSON list of citations grounding this finding.",
        help_text="Document, profile, and policy references supporting the observation.",
    )
    disposition = models.CharField(
        max_length=64,
        default="human_review_required",
        db_comment="Required downstream treatment of the synthetic finding.",
        help_text="Explicitly preserves human authority over the final determination.",
    )

    class Meta:
        db_table = "studio_insurance_findings"
        db_table_comment = "Synthetic cited findings produced during sandbox evaluation."
        verbose_name = "insurance finding"
        verbose_name_plural = "insurance findings"
        ordering = ("created_at",)

    def __str__(self) -> str:
        return self.title


class EvaluationCase(models.TextChoices):
    """Required tests in the synthetic evaluation pack."""

    CITATION_ACCURACY = "citation_accuracy", "Citation accuracy"
    REFUSAL = "refusal", "Unsafe-action refusal"
    ACCESS_CONTROL = "access_control", "Access control"
    PROMPT_INJECTION = "prompt_injection", "Prompt injection"


class EvaluationOutcome(models.TextChoices):
    """Pass or fail outcome for one deterministic evaluation."""

    PASS = "pass", "Pass"
    FAIL = "fail", "Fail"


class EvaluationResult(ImmutableModel):
    """One deterministic sandbox evaluation result with integrity evidence."""

    agent = models.ForeignKey(
        SandboxAgentInstance,
        on_delete=models.CASCADE,
        related_name="evaluation_results",
        db_comment="Sandbox agent instance evaluated by this test case.",
        help_text="Registered instance whose behavior was evaluated.",
    )
    test_case = EnumField(
        EvaluationCase,
        max_length=32,
        db_comment="Required evaluation scenario executed against the sandbox agent.",
        help_text="Citation, refusal, access-control, or prompt-injection test.",
    )
    outcome = EnumField(
        EvaluationOutcome,
        max_length=16,
        db_comment="Deterministic pass or fail outcome for the evaluation.",
        help_text="Whether observed sandbox behavior matched the expected result.",
    )
    score = models.DecimalField(
        max_digits=5,
        decimal_places=4,
        db_comment="Normalized evaluation score between zero and one.",
        help_text="Machine-readable score used by the sandbox evaluation gate.",
    )
    expected = models.TextField(
        db_comment="Expected behavior defined by the evaluation pack.",
        help_text="Reviewable success condition for this evaluation case.",
    )
    observed = models.TextField(
        db_comment="Observed synthetic behavior produced by the sandbox run.",
        help_text="Bounded evidence compared with the expected behavior.",
    )
    latency_ms = models.PositiveIntegerField(
        db_comment="Measured deterministic evaluation latency in milliseconds.",
        help_text="Elapsed time required to execute and score this test case.",
    )
    artifact_hash = models.CharField(
        max_length=64,
        db_comment="SHA-256 digest of the canonical evaluation result.",
        help_text="Integrity digest for the evaluation evidence record.",
    )

    class Meta:
        db_table = "studio_evaluation_results"
        db_table_comment = "Deterministic results for the required sandbox evaluation pack."
        verbose_name = "evaluation result"
        verbose_name_plural = "evaluation results"
        ordering = ("created_at",)
        constraints = (
            models.UniqueConstraint(
                fields=("agent", "test_case"),
                name="unique_agent_evaluation_case",
            ),
        )
        indexes = (models.Index(fields=("outcome", "test_case")),)

    def __str__(self) -> str:
        return f"{self.get_test_case_display()}: {self.get_outcome_display()}"


class EvidenceArtifactType(models.TextChoices):
    """Downloadable proof artifacts produced by sandbox execution."""

    EVALUATION_REPORT = "evaluation_report", "Evaluation report"
    EVIDENCE_MANIFEST = "evidence_manifest", "Evidence manifest"


class EvidenceArtifact(ImmutableModel):
    """A versioned JSON proof artifact produced by the sandbox run."""

    agent = models.ForeignKey(
        SandboxAgentInstance,
        on_delete=models.CASCADE,
        related_name="evidence_artifacts",
        db_comment="Sandbox agent instance whose run produced this artifact.",
        help_text="Evaluated instance represented by the downloadable evidence.",
    )
    artifact_type = EnumField(
        EvidenceArtifactType,
        max_length=32,
        db_comment="Semantic type of the generated evidence artifact.",
        help_text="Evaluation report or complete evidence manifest.",
    )
    version = models.CharField(
        max_length=32,
        db_comment="Semantic version assigned to the evidence artifact.",
        help_text="Immutable version of the generated evidence content.",
    )
    content = models.TextField(
        db_comment="Canonical JSON content of the evidence artifact.",
        help_text="Exact JSON bytes returned by the artifact download endpoint.",
    )
    artifact_hash = models.CharField(
        max_length=64,
        db_index=True,
        db_comment="SHA-256 digest of the canonical evidence content.",
        help_text="Integrity digest for independent artifact verification.",
    )
    size_bytes = models.PositiveIntegerField(
        db_comment="UTF-8 byte length of the canonical evidence content.",
        help_text="Size of the downloadable artifact in bytes.",
    )

    class Meta:
        db_table = "studio_evidence_artifacts"
        db_table_comment = "Immutable, versioned JSON proof artifacts from sandbox evaluation."
        verbose_name = "evidence artifact"
        verbose_name_plural = "evidence artifacts"
        ordering = ("artifact_type", "-created_at")
        constraints = (
            models.UniqueConstraint(
                fields=("agent", "artifact_type", "version"),
                name="unique_agent_artifact_version",
            ),
        )

    def __str__(self) -> str:
        return f"{self.get_artifact_type_display()} {self.version}"
