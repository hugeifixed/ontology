"""Deterministic provider used for demonstrations and tests."""

from uuid import uuid4

from studio.providers.interface import ILlmProvider
from studio.types import (
    BindingDraft,
    IntentAction,
    IntentDraft,
    ProposalDraft,
    ProviderName,
    ProviderResult,
)


class DemoLlmProvider(ILlmProvider):
    """Produce the reference proposal without making a network request."""

    model_name = "deterministic-demo-v1"

    def compose(self, *, intent: str, ontology_context: str) -> ProviderResult:
        """Build the canonical commercial-loan proposal."""
        del ontology_context
        draft = ProposalDraft(
            intent=IntentDraft(
                title="Commercial Loan Insurance Covenant Review",
                outcome=(
                    "Help servicing analysts identify insurance obligations in governed "
                    "commercial loan documents and compare them with the servicing profile."
                ),
                actor="Commercial loan servicing analyst",
                action=IntentAction.RECOMMEND,
                in_scope=[
                    "Locate insurance clauses in approved loan documents",
                    "Compare obligations with a read-only servicing profile",
                    "Cite every finding and route it to an analyst",
                ],
                out_of_scope=[
                    "Changing servicing records",
                    "Contacting borrowers or insurers",
                    "Making a final compliance decision",
                ],
                risk_signals=["Confidential loan documents", "Customer account context"],
            ),
            summary=(
                "Extend the existing Commercial Loan Servicing Q&A workflow with a governed "
                "insurance-review agent that retrieves evidence, compares obligations, and "
                "returns a cited draft for analyst validation."
            ),
            existing_workflow_slug="commercial-loan-servicing-qa",
            capability_slug="grounded-covenant-analysis",
            agent_name="Insurance Covenant Review Agent",
            bindings=[
                BindingDraft(
                    node_slug="midland-loan-documents",
                    purpose="Retrieve the governing loan agreement and insurance clauses.",
                    access_mode="read",
                ),
                BindingDraft(
                    node_slug="commercial-loan-profile",
                    purpose="Read the current servicing profile for comparison context.",
                    access_mode="read",
                ),
                BindingDraft(
                    node_slug="insurance-policy-standards",
                    purpose="Ground the review in approved servicing policy guidance.",
                    access_mode="read",
                ),
                BindingDraft(
                    node_slug="loan-document-search",
                    purpose="Search entitled loan documents without exposing file-share credentials.",
                    access_mode="invoke",
                ),
                BindingDraft(
                    node_slug="loan-profile-lookup",
                    purpose="Query an allowlisted, read-only servicing view.",
                    access_mode="invoke",
                ),
                BindingDraft(
                    node_slug="policy-search",
                    purpose="Retrieve approved policy excerpts and citations.",
                    access_mode="invoke",
                ),
            ],
            control_slugs=[
                "user-entitlement-check",
                "read-only-boundary",
                "citation-required",
                "human-review-required",
                "data-minimization",
            ],
            delivery_artifact_slugs=[
                "architecture-decision-record",
                "evaluation-pack",
                "access-matrix",
                "evidence-manifest",
            ],
        )
        return ProviderResult(
            draft=draft,
            provider=ProviderName.DEMO,
            model_name=self.model_name,
            model_used=False,
            request_id=f"demo-{uuid4().hex[:12]}",
        )
