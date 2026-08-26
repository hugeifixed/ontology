from django.db import migrations


NODES = (
    ("insurance-covenant-review", "business_outcome", "Insurance covenant review", "Identify commercial-loan insurance obligations with source evidence and accountable analyst review.", "Commercial Loan Servicing", "internal", "approved", "Reference use case"),
    ("servicing-analyst", "user_role", "Commercial loan servicing analyst", "Entitled employee who validates cited findings against source documents before acting.", "Commercial Loan Servicing", "internal", "approved", "Role catalog"),
    ("salesforce-edge", "data_product", "Salesforce Edge knowledge index", "Care-center procedures, product answers, and troubleshooting guidance from the V3 catalog.", "Retail Knowledge Team", "internal", "approved", "Salesforce Edge"),
    ("seismic-sales-content", "data_product", "Seismic sales content index", "Approved treasury sales collateral and client-ready enablement content from the V3 catalog.", "TM Sales Enablement", "internal", "approved", "Seismic"),
    ("pinnacle-product-docs", "data_product", "Pinnacle product documentation index", "Treasury product capabilities, user guides, and service descriptions from the V3 catalog.", "Treasury Product", "internal", "approved", "Pinnacle"),
    ("qvidian-proposal-library", "data_product", "Qvidian proposal library index", "Approved treasury RFP answers and reusable proposal content from the V3 catalog.", "Proposal Management", "internal", "approved", "Qvidian"),
    ("midland-loan-documents", "data_product", "Midland loan documents", "Serviced commercial loan agreements, amendments, and supporting documents exposed through governed retrieval.", "Commercial Loan Servicing", "confidential", "approved", "Midland document index"),
    ("commercial-loan-profile", "data_product", "Commercial loan servicing profile", "Allowlisted servicing attributes needed to identify the correct loan and compare review context.", "Loan Servicing Data Owner", "restricted", "conditional", "Read-only servicing view"),
    ("insurance-policy-standards", "data_product", "Insurance policy standards", "Approved servicing procedures and review standards with paragraph-level citations.", "Servicing Policy Office", "internal", "approved", "Policy knowledge index"),
    ("salesforce-edge-system", "system", "Salesforce Edge", "System of record for care-center knowledge articles.", "Retail Technology", "internal", "approved", "Enterprise application"),
    ("seismic-system", "system", "Seismic", "Enterprise sales enablement content platform.", "Sales Technology", "internal", "approved", "Enterprise application"),
    ("pinnacle-system", "system", "Pinnacle documentation", "Treasury product documentation source.", "Treasury Technology", "internal", "approved", "Enterprise application"),
    ("qvidian-system", "system", "Qvidian", "Proposal content system of record.", "Proposal Technology", "internal", "approved", "Enterprise application"),
    ("midland-file-source", "system", "Midland file source", "Controlled commercial-loan file source behind the document retrieval service.", "Commercial Loan Technology", "confidential", "approved", "File share / repository"),
    ("servicing-database", "system", "Commercial loan servicing database", "System of record for commercial-loan servicing data; not directly accessible by agents.", "Loan Servicing Technology", "restricted", "approved", "Relational database"),
    ("policy-repository", "system", "Servicing policy repository", "Authoritative repository for approved servicing policies.", "Servicing Policy Office", "internal", "approved", "Document repository"),
    ("approved-model-route", "connector", "Approved model route", "Target governed route for approved models, cost policy, residency, and invocation evidence.", "Enterprise AI Platform", "internal", "conditional", "Enterprise model gateway"),
    ("midland-document-connector", "connector", "Midland document retrieval connector", "Purpose-built interface that preserves document entitlements and citations.", "Commercial Loan Technology", "confidential", "approved", "Target integration layer"),
    ("servicing-api-connector", "connector", "Servicing profile API connector", "Allowlisted read-only facade over the servicing database; rejects arbitrary SQL.", "Loan Servicing Technology", "restricted", "conditional", "Target integration layer"),
    ("policy-index-connector", "connector", "Policy index connector", "Citation-preserving retrieval interface for approved policy content.", "Servicing Policy Office", "internal", "approved", "Enterprise search"),
    ("openwiki-code-connector", "connector", "OpenWiki code knowledge connector", "Read-only codebase and architecture knowledge for future SDLC impact analysis using OKF concepts.", "Developer Platform", "internal", "conditional", "OpenWiki / OKF"),
    ("loan-document-search", "tool", "Loan Document Search", "Search entitled loan documents and return bounded passages with source references.", "Commercial Loan Technology", "confidential", "approved", "Governed retrieval tool"),
    ("loan-profile-lookup", "tool", "Loan Profile Lookup", "Retrieve only allowlisted servicing fields for one entitled loan identifier.", "Loan Servicing Technology", "restricted", "conditional", "Read-only query tool"),
    ("policy-search", "tool", "Policy Search", "Find approved policy paragraphs and preserve citations and effective dates.", "Servicing Policy Office", "internal", "approved", "Governed retrieval tool"),
    ("azure-search-rag", "agent_capability", "Azure AI Search RAG capability", "Reusable governed retrieval capability inherited from the V3 agent registry.", "Enterprise AI Platform", "internal", "approved", "V3 agent capability"),
    ("grounded-covenant-analysis", "agent_capability", "Grounded covenant analysis", "Reusable capability that extracts obligations, compares approved context, cites evidence, and defers judgment to a human.", "Enterprise AI Platform", "confidential", "approved", "Reference agent capability"),
    ("commercial-loan-retrieval-agent", "agent_instance", "Commercial Loan Retrieval Agent", "Production retrieval instance used by the existing loan-servicing Q&A workflow.", "Commercial Loan Servicing", "confidential", "approved", "V3 agent instance"),
    ("treasury-sales-assistant", "workflow", "Treasury Management Sales assistant", "Existing production workflow over Seismic, Pinnacle, and Qvidian from the V3 catalog.", "Treasury Management", "internal", "approved", "V3 workflow"),
    ("retail-care-center-assist", "workflow", "Retail Care Center assist", "Existing production workflow over Salesforce Edge from the V3 catalog.", "Retail Banking", "internal", "approved", "V3 workflow"),
    ("commercial-loan-servicing-qa", "workflow", "Commercial Loan Servicing Q&A", "Existing read-only workflow over governed loan documents; preferred extension point for the reference use case.", "Commercial Loan Servicing", "confidential", "approved", "V3 workflow"),
    ("user-entitlement-check", "control", "User and agent entitlement", "Require both user identity and agent identity to be authorized for every retrieval.", "Identity and Access Management", "internal", "approved", "Access policy"),
    ("read-only-boundary", "control", "Read-only execution boundary", "Prohibit system-of-record updates, external communication, and autonomous decisions.", "Enterprise Architecture", "internal", "approved", "Agent action policy"),
    ("citation-required", "control", "Citation required", "Require each material finding to reference retrieved source evidence.", "AI Governance", "internal", "approved", "Grounding policy"),
    ("human-review-required", "control", "Human review required", "Keep the servicing analyst accountable for the final insurance determination.", "Commercial Loan Servicing", "internal", "approved", "Operating procedure"),
    ("data-minimization", "control", "Data minimization", "Retrieve only the documents and servicing fields necessary for the declared purpose.", "Privacy Office", "internal", "approved", "Privacy policy"),
    ("architecture-decision-record", "delivery_artifact", "Architecture decision record", "Versioned architecture rationale, boundaries, dependencies, and alternatives.", "Enterprise Architecture", "internal", "approved", "SDLC artifact"),
    ("evaluation-pack", "delivery_artifact", "Evaluation and test pack", "Golden questions, citation checks, refusal tests, and acceptance thresholds.", "AI Quality Engineering", "internal", "approved", "SDLC artifact"),
    ("access-matrix", "delivery_artifact", "Access matrix", "Roles, agent identity, sources, fields, actions, and approving owners.", "Identity and Access Management", "internal", "approved", "SDLC artifact"),
    ("evidence-manifest", "delivery_artifact", "Evidence manifest", "Required proof events, references, retention, and review responsibilities.", "AI Governance", "internal", "approved", "SDLC artifact"),
)


EDGES = (
    ("commercial-loan-servicing-qa", "serves", "insurance-covenant-review", "The existing servicing workflow is the preferred extension point for this business outcome."),
    ("commercial-loan-servicing-qa", "used_by", "servicing-analyst", "Entitled servicing analysts use the workflow and remain accountable for conclusions."),
    ("commercial-loan-servicing-qa", "uses", "commercial-loan-retrieval-agent", "The workflow delegates governed retrieval to the registered agent instance."),
    ("commercial-loan-retrieval-agent", "instance_of", "grounded-covenant-analysis", "The instance inherits the approved grounded-analysis capability contract."),
    ("grounded-covenant-analysis", "invokes", "loan-document-search", "The capability searches documents only through the governed tool."),
    ("grounded-covenant-analysis", "invokes", "loan-profile-lookup", "The capability uses an allowlisted servicing lookup rather than direct SQL."),
    ("grounded-covenant-analysis", "invokes", "policy-search", "The capability retrieves effective policy evidence with citations."),
    ("loan-document-search", "uses", "midland-document-connector", "The tool delegates source access and entitlement enforcement to the connector."),
    ("loan-profile-lookup", "uses", "servicing-api-connector", "The tool calls a read-only facade with bounded fields."),
    ("policy-search", "uses", "policy-index-connector", "The tool uses the approved policy retrieval service."),
    ("midland-document-connector", "exposes", "midland-loan-documents", "The connector exposes governed retrieval, not raw file-share credentials."),
    ("servicing-api-connector", "exposes", "commercial-loan-profile", "The connector exposes only allowlisted servicing attributes."),
    ("policy-index-connector", "exposes", "insurance-policy-standards", "The connector exposes approved policy passages and metadata."),
    ("midland-loan-documents", "resides_in", "midland-file-source", "The data product describes governed content held in the Midland source."),
    ("commercial-loan-profile", "resides_in", "servicing-database", "The data product is a governed projection over the servicing system of record."),
    ("insurance-policy-standards", "resides_in", "policy-repository", "The indexed policy product derives from the authoritative repository."),
    ("salesforce-edge", "resides_in", "salesforce-edge-system", "Catalog product to source-system lineage from V3."),
    ("seismic-sales-content", "resides_in", "seismic-system", "Catalog product to source-system lineage from V3."),
    ("pinnacle-product-docs", "resides_in", "pinnacle-system", "Catalog product to source-system lineage from V3."),
    ("qvidian-proposal-library", "resides_in", "qvidian-system", "Catalog product to source-system lineage from V3."),
    ("treasury-sales-assistant", "reads", "seismic-sales-content", "The existing sales workflow retrieves approved Seismic content."),
    ("treasury-sales-assistant", "reads", "pinnacle-product-docs", "The existing sales workflow retrieves approved product documentation."),
    ("treasury-sales-assistant", "reads", "qvidian-proposal-library", "The existing sales workflow retrieves approved proposal answers."),
    ("retail-care-center-assist", "reads", "salesforce-edge", "The care-center workflow retrieves approved knowledge procedures."),
    ("commercial-loan-servicing-qa", "reads", "midland-loan-documents", "The existing servicing workflow retrieves governed loan documents."),
    ("commercial-loan-servicing-qa", "constrained_by", "user-entitlement-check", "Source access must preserve user and agent authorization."),
    ("commercial-loan-servicing-qa", "constrained_by", "read-only-boundary", "The reference use case may not change a system of record."),
    ("commercial-loan-servicing-qa", "constrained_by", "citation-required", "Every material finding must remain traceable to source evidence."),
    ("commercial-loan-servicing-qa", "constrained_by", "human-review-required", "The analyst owns the final decision."),
    ("commercial-loan-servicing-qa", "constrained_by", "data-minimization", "Only purpose-necessary documents and fields may be retrieved."),
    ("commercial-loan-servicing-qa", "produces", "architecture-decision-record", "An approved extension produces a versioned architecture decision."),
    ("commercial-loan-servicing-qa", "produces", "evaluation-pack", "The workflow cannot enter sandbox without defined evaluations."),
    ("commercial-loan-servicing-qa", "produces", "access-matrix", "The implementation handoff declares identity and source scopes."),
    ("commercial-loan-servicing-qa", "produces", "evidence-manifest", "The handoff defines proof and retention expectations."),
)


def seed_reference_ontology(apps, schema_editor):
    OntologyNode = apps.get_model("studio", "OntologyNode")
    OntologyEdge = apps.get_model("studio", "OntologyEdge")
    nodes = {}
    for slug, node_type, name, description, owner, classification, approval_state, source_reference in NODES:
        nodes[slug] = OntologyNode.objects.create(
            slug=slug,
            node_type=node_type,
            name=name,
            description=description,
            owner=owner,
            classification=classification,
            approval_state=approval_state,
            source_reference=source_reference,
        )
    for source, relation, target, rationale in EDGES:
        OntologyEdge.objects.create(
            source=nodes[source],
            relation=relation,
            target=nodes[target],
            rationale=rationale,
        )


def remove_reference_ontology(apps, schema_editor):
    OntologyNode = apps.get_model("studio", "OntologyNode")
    OntologyNode.objects.filter(slug__in=[node[0] for node in NODES]).delete()


class Migration(migrations.Migration):

    dependencies = [
        ("studio", "0001_initial"),
    ]

    operations = [
        migrations.RunPython(seed_reference_ontology, remove_reference_ontology),
    ]
