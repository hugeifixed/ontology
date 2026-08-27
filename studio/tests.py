"""Integration tests for the reference governed-workflow journey."""

import hashlib
import json
from types import SimpleNamespace
from unittest.mock import Mock, patch

import anthropic
import httpx
from auditlog.models import LogEntry
from django.contrib.auth import get_user_model
from django.test import SimpleTestCase, TestCase, override_settings
from django.urls import reverse
from google.genai import errors

from studio.discovery import DiscoveryDecision, discover_catalog
from studio.models import (
    AccessMode,
    BusinessDomain,
    EvaluationCase,
    EvaluationOutcome,
    EvidenceArtifactType,
    OntologyEdge,
    OntologyNode,
    PolicyDecision,
    ProofEventType,
    ProposalStatus,
    ReviewRole,
    SandboxStatus,
    WorkflowProposal,
)
from studio.providers import build_llm_provider
from studio.providers.anthropic import (
    ANTHROPIC_MAX_RETRIES,
    ANTHROPIC_TIMEOUT_SECONDS,
    AnthropicLlmProvider,
)
from studio.providers.errors import ProviderRequestError
from studio.providers.gemini import (
    GEMINI_RETRY_ATTEMPTS,
    GEMINI_RETRYABLE_STATUS_CODES,
    GEMINI_TIMEOUT_MILLISECONDS,
    GeminiLlmProvider,
)
from studio.providers.mock import DemoLlmProvider
from studio.services import compose_workflow_proposal
from studio.types import BindingAccessMode, ProposalDraft, ProviderName


class StudioJourneyTests(TestCase):
    """Exercise dashboard, proposal creation, and human approval."""

    def test_dashboard_explains_reference_use_case(self) -> None:
        response = self.client.get(reverse("studio:dashboard"))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Commercial loan insurance covenant review")
        self.assertContains(
            response,
            "Move one business need from discovery to defensible evidence.",
        )
        self.assertContains(response, "Midland loan documents")

    def test_legacy_navigation_aliases_open_the_new_knowledge_model(self) -> None:
        ontology_response = self.client.get(
            reverse("studio:dashboard"),
            {"section": "ontology"},
        )
        catalog_response = self.client.get(
            reverse("studio:dashboard"),
            {"section": "catalog"},
        )

        self.assertContains(ontology_response, "section: 'knowledge'")
        self.assertContains(ontology_response, "knowledgeView: 'map'")
        self.assertContains(catalog_response, "section: 'knowledge'")
        self.assertContains(catalog_response, "knowledgeView: 'browse'")

    def test_knowledge_filters_and_workspace_search_have_distinct_jobs(self) -> None:
        filtered_response = self.client.get(
            reverse("studio:dashboard"),
            {
                "section": "knowledge",
                "view": "browse",
                "catalog_q": "Midland",
            },
        )
        search_response = self.client.get(
            reverse("studio:dashboard"),
            {"section": "search", "q": "insurance"},
        )

        self.assertContains(filtered_response, "Midland loan documents")
        self.assertContains(filtered_response, "View relationships")
        self.assertContains(search_response, "Search catalog, proposals, and findings")
        self.assertContains(search_response, "Catalog objects")
        self.assertContains(search_response, "Evidence findings")

    def test_catalog_discovery_resolves_each_registered_business_domain(self) -> None:
        cases = (
            (
                "Help a treasury seller answer a cash-management RFP using approved content.",
                BusinessDomain.TREASURY,
                "treasury-sales-assistant",
            ),
            (
                "Find the retail care-center procedure for a fee reversal question.",
                BusinessDomain.RETAIL,
                "retail-care-center-assist",
            ),
            (
                "Find commercial loan insurance covenants with citations for review.",
                BusinessDomain.COMMERCIAL_LOAN,
                "commercial-loan-servicing-qa",
            ),
        )

        for intent, expected_domain, expected_workflow in cases:
            with self.subTest(domain=expected_domain):
                result = discover_catalog(
                    intent=intent,
                    access_profile="enterprise_architect",
                )
                self.assertEqual(result.decision, DiscoveryDecision.REUSE)
                self.assertEqual(result.inferred_domain, expected_domain)
                self.assertEqual(result.workflow.node.slug, expected_workflow)
                self.assertIsNotNone(result.agent)
                self.assertTrue(result.products)
                self.assertTrue(result.capabilities)

    def test_discovery_stops_when_access_profile_excludes_the_domain(self) -> None:
        result = discover_catalog(
            intent="Answer a treasury cash-management RFP from approved proposal content.",
            access_profile="retail_specialist",
        )

        self.assertEqual(result.decision, DiscoveryDecision.ACCESS_MISMATCH)
        self.assertIsNone(result.workflow)
        self.assertFalse(result.can_continue)

    def test_discovery_does_not_force_a_weak_match_into_an_existing_workflow(self) -> None:
        result = discover_catalog(
            intent="Use foot-traffic and local weather data to plan branch staffing.",
            access_profile="enterprise_architect",
        )

        self.assertEqual(result.decision, DiscoveryDecision.METADATA_GAP)
        self.assertIsNone(result.workflow)
        self.assertIn("workflow", result.recommendation.lower())

    def test_discovery_endpoint_explains_path_and_execution_boundary(self) -> None:
        initial_node_count = OntologyNode.objects.count()
        initial_edge_count = OntologyEdge.objects.count()

        response = self.client.post(
            reverse("studio:discover"),
            {
                "intent": (
                    "Help commercial loan servicing analysts find insurance requirements "
                    "and return cited findings for human review."
                ),
                "access_profile": "enterprise_architect",
            },
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Reuse an existing governed workflow")
        self.assertContains(response, "Commercial Loan Servicing Q&amp;A")
        self.assertContains(response, "Typed relationship trace")
        self.assertContains(response, "Use this catalog path")
        self.assertEqual(OntologyNode.objects.count(), initial_node_count)
        self.assertEqual(OntologyEdge.objects.count(), initial_edge_count)
        self.assertFalse(WorkflowProposal.objects.exists())

    def test_dashboard_has_accessible_structure_and_labels(self) -> None:
        response = self.client.get(reverse("studio:dashboard"))

        self.assertContains(response, 'href="#main-content"')
        self.assertContains(response, 'id="main-content"')
        self.assertContains(response, 'role="status"')
        self.assertContains(response, 'aria-label="Primary"')
        self.assertContains(response, "data-menu-icon=", count=5)
        self.assertContains(response, 'class="menu-icon size-5 shrink-0"', count=5)
        self.assertContains(response, 'aria-hidden="true"')
        self.assertContains(response, 'for="id_intent"')
        self.assertContains(response, 'for="id_requester_role"')
        self.assertContains(response, 'for="provider"')
        self.assertContains(response, 'value="gemini"')
        self.assertContains(response, "Google Gemini — AI Studio")
        self.assertNotContains(
            response,
            "Google requests use the Gemini Developer API with an AI Studio key.",
        )
        self.assertContains(response, "studio/js/app.js?v=20260827-1")
        self.assertContains(response, '<caption class="sr-only">', html=False)
        self.assertContains(response, 'class="fragment-transition min-w-0"')
        self.assertContains(response, "collapse collapse-arrow")
        self.assertContains(response, "hx-disabled-elt=\"find button[type='submit']\"")
        self.assertContains(response, "x-transition.opacity.duration.150ms")
        self.assertContains(response, "Draft proposal")
        self.assertContains(response, 'data-loading-label="Drafting proposal"')
        self.assertContains(response, 'id="compose-feedback"')
        self.assertContains(response, "data-compose-progress")
        self.assertContains(response, "Draft request started")
        self.assertContains(response, "Preparing the request")
        self.assertContains(response, 'id="discovery-results"')
        self.assertContains(response, "Begin with the business need, not an agent.")
        self.assertContains(
            response,
            "Help commercial loan servicing analysts find insurance requirements and return cited findings for human review.",
        )
        self.assertContains(response, "Sample needs")
        self.assertContains(response, "Treasury RFP")
        self.assertContains(response, "Retail fee reversal")
        self.assertContains(response, "Loan insurance")
        self.assertContains(response, "Reuse in this browser tab")
        self.assertContains(response, "a git-ignored <code>.env</code> file is recommended")
        self.assertContains(response, "window.scrollTo({ top: 0, left: 0, behavior: 'auto' })")
        self.assertContains(response, "history.scrollRestoration = 'manual'")
        self.assertContains(response, "badge-info")
        self.assertContains(response, "badge-warning")
        self.assertContains(response, "badge-error")
        self.assertContains(response, 'data-provider-route="gemini"')
        self.assertContains(response, 'data-provider-route="anthropic"')
        self.assertContains(response, "data-provider-route-status", count=4)
        self.assertNotContains(response, "key at request")
        self.assertContains(
            response,
            'aria-describedby="compose-safety-note compose-feedback"',
        )

    @override_settings(GOOGLE_API_KEY="configured", ANTHROPIC_API_KEY="")
    def test_dashboard_reports_environment_key_availability(self) -> None:
        response = self.client.get(reverse("studio:dashboard"))

        self.assertContains(response, "Environment key available")
        self.assertContains(response, "No key configured")
        self.assertContains(response, 'data-environment-key="true"')
        self.assertContains(response, 'data-environment-key="false"')

    def test_dashboard_is_platform_neutral(self) -> None:
        response = self.client.get(reverse("studio:dashboard"))
        page = response.content.decode().lower()

        prohibited_terms = (
            "".join(("z", "afin")),
            "".join(("a", "ios")),
            "".join(("p", "nc")),
        )
        for term in prohibited_terms:
            self.assertNotIn(term, page)

    def test_demo_provider_creates_controlled_proposal(self) -> None:
        response = self.client.post(
            reverse("studio:compose-proposal"),
            {
                "intent": (
                    "Help servicing analysts find insurance requirements in commercial "
                    "loan files and return citations for human review only."
                ),
                "requester_role": "Loan servicing product owner",
                "provider": "demo",
                "model_name": "deterministic-demo-v1",
                "api_key": "must-not-be-persisted",
            },
        )

        self.assertEqual(response.status_code, 302)
        proposal = WorkflowProposal.objects.get()
        self.assertEqual(
            response.url,
            f"{proposal.get_absolute_url()}?stage=define",
        )
        response = self.client.get(response.url)
        self.assertContains(response, "badge-warning badge-soft")
        self.assertContains(response, 'class="proposal-transition space-y-5"')
        self.assertContains(
            response,
            'hx-swap="outerHTML swap:100ms settle:150ms"',
        )
        self.assertContains(response, 'data-loading-label="Recording business approval"')
        self.assertContains(response, "Download JSON manifest")
        self.assertContains(response, 'role="tablist"')
        self.assertContains(response, 'role="tabpanel"', count=4)
        self.assertContains(response, "proposalStage: 'define'")
        self.assertContains(response, "Connected catalog objects")
        self.assertContains(
            response,
            '<th scope="col">Allowed action</th>',
        )
        self.assertContains(response, 'class="whitespace-nowrap text-sm font-medium"')
        self.assertEqual(proposal.status, ProposalStatus.NEEDS_REVIEW)
        self.assertFalse(proposal.model_used)
        self.assertEqual(proposal.estimated_cost_usd, 0)
        self.assertEqual(proposal.manifests.count(), 1)
        self.assertGreaterEqual(proposal.bindings.count(), 10)
        self.assertFalse(proposal.control_checks.filter(outcome="block").exists())
        self.assertTrue(
            proposal.proof_events.filter(event_type=ProofEventType.MODEL_BYPASSED).exists()
        )
        persisted_text = " ".join(
            [
                proposal.title,
                proposal.intent,
                proposal.requester_role,
                proposal.summary,
                *proposal.proof_events.values_list("summary", flat=True),
                *proposal.proof_events.values_list("evidence_reference", flat=True),
            ]
        )
        self.assertNotIn("must-not-be-persisted", persisted_text)

    def test_htmx_composition_redirects_to_the_canonical_proposal_workspace(self) -> None:
        response = self.client.post(
            reverse("studio:compose-proposal"),
            {
                "intent": (
                    "Help servicing analysts find insurance requirements in commercial "
                    "loan files and return citations for human review only."
                ),
                "requester_role": "Loan servicing product owner",
                "provider": "demo",
                "model_name": "deterministic-demo-v1",
                "api_key": "",
            },
            HTTP_HX_REQUEST="true",
        )

        proposal = WorkflowProposal.objects.get()
        self.assertEqual(response.status_code, 204)
        self.assertEqual(
            response["HX-Redirect"],
            f"{proposal.get_absolute_url()}?stage=define",
        )

    def test_proposal_stage_is_addressable_and_refresh_safe(self) -> None:
        proposal = compose_workflow_proposal(
            intent=(
                "Help servicing analysts find insurance requirements in commercial loan "
                "files and return citations for human review only."
            ),
            requester_role="Loan servicing product owner",
            provider_name=ProviderName.DEMO,
            ephemeral_api_key="",
            requested_model="deterministic-demo-v1",
        )

        response = self.client.get(
            reverse("studio:proposal-detail", kwargs={"proposal_id": proposal.pk}),
            {"stage": "test"},
        )

        self.assertContains(response, "proposalStage: 'test'")
        self.assertContains(response, "3 · Test")

    @patch("studio.services.build_llm_provider")
    def test_read_only_model_alias_is_canonicalized_for_a_tool(self, provider_factory) -> None:
        base_result = DemoLlmProvider().compose(
            intent="Reference intent",
            ontology_context="",
        )
        draft_payload = base_result.draft.model_dump(mode="json")
        tool_binding = next(
            binding
            for binding in draft_payload["bindings"]
            if binding["node_slug"] == "loan-document-search"
        )
        tool_binding["access_mode"] = "read_only"
        normalized_draft = ProposalDraft.model_validate(draft_payload)
        normalized_binding = next(
            binding
            for binding in normalized_draft.bindings
            if binding.node_slug == "loan-document-search"
        )
        self.assertEqual(normalized_binding.access_mode, BindingAccessMode.READ)
        provider_factory.return_value.compose.return_value = base_result.model_copy(
            update={"draft": normalized_draft}
        )

        proposal = compose_workflow_proposal(
            intent=(
                "Help servicing analysts find insurance requirements in commercial loan "
                "files and return citations for human review only."
            ),
            requester_role="Loan servicing product owner",
            provider_name=ProviderName.GEMINI,
            ephemeral_api_key="",
            requested_model="gemini-flash-latest",
        )

        persisted_binding = proposal.bindings.get(node__slug="loan-document-search")
        self.assertEqual(persisted_binding.access_mode, AccessMode.INVOKE)

    def test_dual_approval_releases_sandbox_registration(self) -> None:
        self.client.post(
            reverse("studio:compose-proposal"),
            {
                "intent": (
                    "Help servicing analysts find insurance requirements in commercial "
                    "loan files and return citations for human review only."
                ),
                "requester_role": "Loan servicing product owner",
                "provider": "demo",
                "model_name": "deterministic-demo-v1",
                "api_key": "",
            },
        )
        proposal = WorkflowProposal.objects.get()

        business_response = self.client.post(
            reverse("studio:approve-proposal", kwargs={"proposal_id": proposal.pk}),
            {
                "review_role": ReviewRole.BUSINESS_OWNER,
                "approver": "Commercial servicing product owner",
                "note": "Business boundary accepted.",
            },
        )

        self.assertEqual(business_response.status_code, 200)
        proposal.refresh_from_db()
        self.assertEqual(proposal.status, ProposalStatus.NEEDS_REVIEW)
        self.assertEqual(proposal.approvals.count(), 1)

        source_response = self.client.post(
            reverse("studio:approve-proposal", kwargs={"proposal_id": proposal.pk}),
            {
                "review_role": ReviewRole.SOURCE_OWNER,
                "approver": "Commercial loan data owner",
                "note": "Synthetic source access accepted.",
            },
        )

        self.assertEqual(source_response.status_code, 200)
        self.assertContains(
            source_response,
            "btn btn-secondary btn-sm w-full whitespace-nowrap px-4 sm:w-auto",
        )
        self.assertContains(source_response, "Registering agent")
        self.assertContains(source_response, "proposalStage: 'test'")
        proposal.refresh_from_db()
        self.assertEqual(proposal.status, ProposalStatus.APPROVED)
        self.assertEqual(proposal.approvals.count(), 2)
        self.assertTrue(
            proposal.proof_events.filter(event_type=ProofEventType.BUSINESS_APPROVED).exists()
        )
        self.assertTrue(
            proposal.proof_events.filter(event_type=ProofEventType.SOURCE_APPROVED).exists()
        )
        self.assertTrue(
            proposal.proof_events.filter(event_type=ProofEventType.SDLC_PACKAGE_READY).exists()
        )

    def test_approval_roles_enforce_separation_of_duties(self) -> None:
        self.client.post(
            reverse("studio:compose-proposal"),
            {
                "intent": (
                    "Help servicing analysts find insurance requirements in commercial "
                    "loan files and return citations for human review only."
                ),
                "requester_role": "Loan servicing product owner",
                "provider": "demo",
                "model_name": "deterministic-demo-v1",
                "api_key": "",
            },
        )
        proposal = WorkflowProposal.objects.get()
        business_response = self.client.post(
            reverse("studio:approve-proposal", kwargs={"proposal_id": proposal.pk}),
            {
                "review_role": ReviewRole.BUSINESS_OWNER,
                "approver": "Same accountable reviewer",
                "note": "Business boundary accepted.",
            },
        )
        source_response = self.client.post(
            reverse("studio:approve-proposal", kwargs={"proposal_id": proposal.pk}),
            {
                "review_role": ReviewRole.SOURCE_OWNER,
                "approver": "same accountable reviewer",
                "note": "Synthetic source scope accepted.",
            },
        )

        self.assertEqual(business_response.status_code, 200)
        self.assertContains(
            source_response,
            "approvals require different reviewers",
            status_code=409,
        )
        proposal.refresh_from_db()
        self.assertEqual(proposal.status, ProposalStatus.NEEDS_REVIEW)
        self.assertEqual(proposal.approvals.count(), 1)

    def test_complete_synthetic_sandbox_vertical_slice(self) -> None:
        compose_response = self.client.post(
            reverse("studio:compose-proposal"),
            {
                "intent": (
                    "Help servicing analysts find insurance requirements in commercial "
                    "loan files and return citations for human review only."
                ),
                "requester_role": "Loan servicing product owner",
                "provider": "demo",
                "model_name": "deterministic-demo-v1",
                "api_key": "",
            },
        )
        self.assertEqual(compose_response.status_code, 302)
        proposal = WorkflowProposal.objects.get()
        manifest = proposal.manifests.get(version="1.0.0")
        manifest_payload = json.loads(manifest.content)
        self.assertTrue(manifest_payload["boundaries"]["sandbox_only"])
        self.assertFalse(manifest_payload["boundaries"]["production_eligible"])
        self.assertEqual(len(manifest_payload["tools"]), 3)
        manifest_download = self.client.get(
            reverse("studio:download-manifest", kwargs={"proposal_id": proposal.pk})
        )
        self.assertEqual(manifest_download.status_code, 200)
        self.assertEqual(
            hashlib.sha256(manifest_download.content).hexdigest(),
            manifest.artifact_hash,
        )

        for review_role, approver in (
            (ReviewRole.BUSINESS_OWNER, "Commercial servicing product owner"),
            (ReviewRole.SOURCE_OWNER, "Commercial loan data owner"),
        ):
            approval_response = self.client.post(
                reverse("studio:approve-proposal", kwargs={"proposal_id": proposal.pk}),
                {
                    "review_role": review_role,
                    "approver": approver,
                    "note": "Approved for synthetic evaluation only.",
                },
            )
            self.assertEqual(approval_response.status_code, 200)

        register_response = self.client.post(
            reverse("studio:register-sandbox", kwargs={"proposal_id": proposal.pk})
        )
        self.assertEqual(register_response.status_code, 200)
        self.assertContains(
            register_response,
            'class="card card-border bg-base-100 shadow-sm"',
        )
        self.assertContains(register_response, "Ready for synthetic evaluation")
        self.assertContains(register_response, "Run evaluation")
        self.assertContains(
            register_response,
            "btn btn-primary btn-sm w-full whitespace-nowrap px-4 sm:w-auto",
        )
        agent = manifest.sandbox_instance
        self.assertEqual(agent.status, SandboxStatus.REGISTERED)
        self.assertTrue(agent.external_id.startswith("sandbox-agent-"))
        self.assertTrue(agent.orchestration_request_id.startswith("mock-orch-"))

        evaluation_response = self.client.post(
            reverse("studio:evaluate-sandbox", kwargs={"proposal_id": proposal.pk})
        )
        self.assertContains(evaluation_response, "Sandbox evaluation passed")
        self.assertContains(evaluation_response, "proposalStage: 'evidence'")
        self.assertContains(evaluation_response, "Activity history")
        agent.refresh_from_db()
        self.assertEqual(agent.status, SandboxStatus.EVALUATION_PASSED)
        self.assertEqual(agent.tool_invocations.count(), 4)
        self.assertEqual(
            agent.tool_invocations.values("tool_id").distinct().count(),
            3,
        )
        self.assertEqual(
            agent.tool_invocations.filter(decision=PolicyDecision.ALLOW).count(),
            3,
        )
        denied_call = agent.tool_invocations.get(decision=PolicyDecision.DENY)
        self.assertEqual(denied_call.resource, "LOAN-SYN-999")
        self.assertEqual(denied_call.response_summary, "")
        self.assertEqual(agent.findings.count(), 2)
        self.assertEqual(agent.evaluation_results.count(), len(EvaluationCase))
        self.assertFalse(agent.evaluation_results.exclude(outcome=EvaluationOutcome.PASS).exists())
        refusal_result = agent.evaluation_results.get(test_case=EvaluationCase.REFUSAL)
        self.assertIn("Deny:", refusal_result.observed)
        citation_result = agent.evaluation_results.get(test_case=EvaluationCase.CITATION_ACCURACY)
        self.assertIn("Matched 6 of 6", citation_result.observed)
        self.assertEqual(agent.evidence_artifacts.count(), 2)

        evidence_artifact = agent.evidence_artifacts.get(
            artifact_type=EvidenceArtifactType.EVIDENCE_MANIFEST
        )
        evidence_payload = json.loads(evidence_artifact.content)
        self.assertEqual(
            evidence_payload["boundary"],
            "sandbox evaluation passed; production not requested",
        )
        self.assertEqual(len(evidence_payload["policy_decisions"]), 4)
        evidence_download = self.client.get(
            reverse(
                "studio:download-evidence",
                kwargs={
                    "proposal_id": proposal.pk,
                    "artifact_type": EvidenceArtifactType.EVIDENCE_MANIFEST,
                },
            )
        )
        self.assertEqual(evidence_download.status_code, 200)
        self.assertEqual(
            hashlib.sha256(evidence_download.content).hexdigest(),
            evidence_artifact.artifact_hash,
        )
        self.assertTrue(
            proposal.proof_events.filter(
                event_type=ProofEventType.SANDBOX_EVALUATION_PASSED
            ).exists()
        )

        second_register = self.client.post(
            reverse("studio:register-sandbox", kwargs={"proposal_id": proposal.pk})
        )
        second_evaluation = self.client.post(
            reverse("studio:evaluate-sandbox", kwargs={"proposal_id": proposal.pk})
        )
        self.assertEqual(second_register.status_code, 200)
        self.assertEqual(second_evaluation.status_code, 200)
        self.assertEqual(agent.tool_invocations.count(), 4)

    @override_settings(GOOGLE_API_KEY="")
    def test_gemini_provider_requires_an_ai_studio_key(self) -> None:
        response = self.client.post(
            reverse("studio:compose-proposal"),
            {
                "intent": (
                    "Help servicing analysts find insurance requirements in commercial "
                    "loan files and return citations for human review only."
                ),
                "requester_role": "Loan servicing product owner",
                "provider": "gemini",
                "model_name": "gemini-flash-latest",
                "api_key": "",
            },
        )

        self.assertEqual(response.status_code, 422)
        self.assertContains(response, "Google AI Studio API key", status_code=422)
        self.assertEqual(WorkflowProposal.objects.count(), 0)

    @override_settings(ANTHROPIC_API_KEY="")
    def test_anthropic_provider_requires_a_key(self) -> None:
        response = self.client.post(
            reverse("studio:compose-proposal"),
            {
                "intent": (
                    "Help servicing analysts find insurance requirements in commercial "
                    "loan files and return citations for human review only."
                ),
                "requester_role": "Loan servicing product owner",
                "provider": "anthropic",
                "model_name": "claude-opus-5",
                "api_key": "",
            },
        )

        self.assertEqual(response.status_code, 422)
        self.assertContains(response, "Anthropic API key", status_code=422)
        self.assertEqual(WorkflowProposal.objects.count(), 0)

    @patch("studio.views.compose_workflow_proposal")
    def test_provider_failure_returns_a_safe_actionable_fragment(self, compose_mock) -> None:
        compose_mock.side_effect = ProviderRequestError(
            "Google rejected the credential for the Gemini Developer API."
        )

        response = self.client.post(
            reverse("studio:compose-proposal"),
            {
                "intent": (
                    "Help servicing analysts find insurance requirements in commercial "
                    "loan files and return citations for human review only."
                ),
                "requester_role": "Loan servicing product owner",
                "provider": "gemini",
                "model_name": "gemini-flash-latest",
                "api_key": "replacement-key-must-not-render",
            },
        )

        self.assertContains(
            response,
            "Google rejected the credential for the Gemini Developer API.",
            status_code=502,
        )
        self.assertEqual(response["HX-Retarget"], "#compose-feedback")
        self.assertEqual(
            response["HX-Reswap"],
            "innerHTML swap:100ms settle:150ms",
        )
        self.assertContains(response, "alert-error alert-soft", status_code=502)
        self.assertNotContains(
            response,
            "replacement-key-must-not-render",
            status_code=502,
        )
        self.assertEqual(WorkflowProposal.objects.count(), 0)


class GeminiProviderTests(SimpleTestCase):
    """Verify Gemini Developer API routing and sanitized provider errors."""

    def setUp(self) -> None:
        self.draft_json = (
            DemoLlmProvider()
            .compose(intent="Reference intent", ontology_context="")
            .draft.model_dump_json()
        )

    def test_developer_api_uses_the_ai_studio_client(self) -> None:
        with patch("studio.providers.gemini.genai.Client") as client_class:
            client = client_class.return_value.__enter__.return_value
            client.models.generate_content.return_value = SimpleNamespace(
                text=self.draft_json,
                response_id="developer-response",
            )
            provider = GeminiLlmProvider(
                api_key="replacement-developer-key",
                model_name="gemini-flash-latest",
            )

            result = provider.compose(intent="Reference intent", ontology_context="catalog")

        client_class.assert_called_once()
        client_options = client_class.call_args.kwargs
        self.assertEqual(client_options["api_key"], "replacement-developer-key")
        self.assertEqual(
            client_options["http_options"].timeout,
            GEMINI_TIMEOUT_MILLISECONDS,
        )
        self.assertEqual(GEMINI_TIMEOUT_MILLISECONDS, 30_000)
        retry_options = client_options["http_options"].retry_options
        self.assertEqual(retry_options.attempts, GEMINI_RETRY_ATTEMPTS)
        self.assertEqual(GEMINI_RETRY_ATTEMPTS, 2)
        self.assertEqual(
            retry_options.http_status_codes,
            list(GEMINI_RETRYABLE_STATUS_CODES),
        )
        generate_call = client.models.generate_content.call_args
        self.assertEqual(generate_call.kwargs["model"], "gemini-flash-latest")
        generation_config = generate_call.kwargs["config"]
        self.assertTrue(generation_config.automatic_function_calling.disable)
        self.assertEqual(result.provider, ProviderName.GEMINI)
        self.assertEqual(result.request_id, "developer-response")

    def test_google_api_errors_do_not_expose_raw_provider_details(self) -> None:
        with patch("studio.providers.gemini.genai.Client") as client_class:
            client = client_class.return_value.__enter__.return_value
            client.models.generate_content.side_effect = errors.ClientError(
                403,
                {
                    "error": {
                        "message": "raw-provider-detail-must-not-render",
                        "status": "PERMISSION_DENIED",
                    }
                },
            )
            provider = GeminiLlmProvider(
                api_key="replacement-developer-key",
                model_name="gemini-flash-latest",
            )

            with self.assertRaises(ProviderRequestError) as error_context:
                provider.compose(intent="Reference intent", ontology_context="catalog")

        public_message = error_context.exception.public_message
        self.assertIn("Gemini Developer API", public_message)
        self.assertNotIn("raw-provider-detail-must-not-render", public_message)

    def test_timeout_returns_a_safe_actionable_error(self) -> None:
        with patch("studio.providers.gemini.genai.Client") as client_class:
            client = client_class.return_value.__enter__.return_value
            client.models.generate_content.side_effect = httpx.ReadTimeout(
                "raw-timeout-detail-must-not-render",
                request=httpx.Request("POST", "https://example.invalid"),
            )
            provider = GeminiLlmProvider(
                api_key="replacement-developer-key",
                model_name="gemini-flash-latest",
            )

            with self.assertRaises(ProviderRequestError) as error_context:
                provider.compose(intent="Reference intent", ontology_context="catalog")

        public_message = error_context.exception.public_message
        self.assertIn("one-minute request limit", public_message)
        self.assertIn("deterministic demo route", public_message)
        self.assertNotIn("raw-timeout-detail-must-not-render", public_message)

    def test_factory_builds_the_ai_studio_provider(self) -> None:
        provider = build_llm_provider(
            provider_name=ProviderName.GEMINI,
            ephemeral_api_key="replacement-developer-key",
            requested_model="gemini-flash-latest",
        )

        self.assertIsInstance(provider, GeminiLlmProvider)
        self.assertEqual(provider.model_name, "gemini-flash-latest")


class AnthropicProviderTests(SimpleTestCase):
    """Verify Claude Opus routing, structured output, and sanitized failures."""

    def setUp(self) -> None:
        self.draft = (
            DemoLlmProvider()
            .compose(
                intent="Reference intent",
                ontology_context="",
            )
            .draft
        )

    def test_opus_uses_structured_output_and_closes_the_client(self) -> None:
        with patch("studio.providers.anthropic.anthropic.Anthropic") as client_class:
            client = client_class.return_value.__enter__.return_value
            client.messages.parse.return_value = SimpleNamespace(
                parsed_output=self.draft,
                id="anthropic-response",
            )
            provider = AnthropicLlmProvider(
                api_key="replacement-anthropic-key",
                model_name="claude-opus-5",
            )

            result = provider.compose(intent="Reference intent", ontology_context="catalog")

        client_class.assert_called_once_with(
            api_key="replacement-anthropic-key",
            max_retries=ANTHROPIC_MAX_RETRIES,
            timeout=ANTHROPIC_TIMEOUT_SECONDS,
        )
        self.assertEqual(ANTHROPIC_MAX_RETRIES, 1)
        self.assertEqual(ANTHROPIC_TIMEOUT_SECONDS, 30.0)
        parse_call = client.messages.parse.call_args
        self.assertEqual(parse_call.kwargs["model"], "claude-opus-5")
        self.assertIs(parse_call.kwargs["output_format"], ProposalDraft)
        client_class.return_value.__exit__.assert_called_once()
        self.assertEqual(result.provider, ProviderName.ANTHROPIC)
        self.assertEqual(result.request_id, "anthropic-response")

    def test_authentication_errors_do_not_expose_raw_provider_details(self) -> None:
        with patch("studio.providers.anthropic.anthropic.Anthropic") as client_class:
            client = client_class.return_value.__enter__.return_value
            client.messages.parse.side_effect = anthropic.AuthenticationError(
                "raw-provider-detail-must-not-render",
                response=Mock(
                    status_code=401,
                    headers={"request-id": "request-test"},
                ),
                body={"error": {"message": "raw-provider-detail-must-not-render"}},
            )
            provider = AnthropicLlmProvider(
                api_key="replacement-anthropic-key",
                model_name="claude-opus-5",
            )

            with self.assertRaises(ProviderRequestError) as error_context:
                provider.compose(intent="Reference intent", ontology_context="catalog")

        public_message = error_context.exception.public_message
        self.assertIn("Anthropic rejected the API key", public_message)
        self.assertNotIn("raw-provider-detail-must-not-render", public_message)

    def test_factory_accepts_opus_five_model_id(self) -> None:
        provider = build_llm_provider(
            provider_name=ProviderName.ANTHROPIC,
            ephemeral_api_key="replacement-anthropic-key",
            requested_model="claude-opus-5",
        )

        self.assertIsInstance(provider, AnthropicLlmProvider)
        self.assertEqual(provider.model_name, "claude-opus-5")


class AuditTrailTests(TestCase):
    """Verify that domain mutations retain an authenticated audit actor."""

    def test_authenticated_proposal_creation_is_audited_without_remote_address(self) -> None:
        user = get_user_model().objects.create_user(
            username="governance-reviewer",
            password="not-used-outside-test",
        )
        self.client.force_login(user)

        response = self.client.post(
            reverse("studio:compose-proposal"),
            {
                "intent": (
                    "Help servicing analysts find insurance requirements in commercial "
                    "loan files and return citations for human review only."
                ),
                "requester_role": "Loan servicing product owner",
                "provider": "demo",
                "model_name": "deterministic-demo-v1",
                "api_key": "",
            },
        )

        self.assertEqual(response.status_code, 302)
        proposal = WorkflowProposal.objects.get()
        audit_entry = LogEntry.objects.get(
            action=LogEntry.Action.CREATE,
            content_type__app_label="studio",
            content_type__model="workflowproposal",
            object_pk=str(proposal.pk),
        )
        self.assertEqual(audit_entry.actor, user)
        self.assertIsNone(audit_entry.remote_addr)
        self.assertIsInstance(audit_entry.changes, dict)
        self.assertEqual(proposal.history.get(), audit_entry)
