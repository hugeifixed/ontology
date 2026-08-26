# Architecture and vendor discussion guide

## Discovery before orchestration

The application now begins with general discovery across three catalog domains: treasury management, retail banking, and commercial loan servicing. The request does not go directly to a vector store or agent. The boundary is:

```text
plain-language need
  -> simulated domain and classification filter
  -> deterministic business-concept matching over approved metadata
  -> typed graph expansion to workflow, data products, agent instance, capability
  -> reuse recommendation, access-scope stop, or metadata-gap stop
  -> optional handoff to the one implemented commercial sandbox adapter
```

Curated `search_terms` make the small reference catalog semantically useful and auditable without creating a fourth vector index. Typed relationships, not similarity alone, establish the recommended dependency path. This distinction matters: ranking can suggest a concept, but the ontology states what a workflow actually reads and uses. A real implementation can later add embedding or model reranking behind the same boundary after permissions, evaluation data, and scale justify it.

Discovery is read-only and does not persist the submitted query. Treasury and retail paths demonstrate reuse across existing domain metadata but stop before execution. Only the commercial-loan path has synthetic tools, policy, approval, orchestration, and evaluation adapters in this prototype.

## Reference journey

```text
Commercial loan servicing product owner
  -> states insurance-review intent
  -> governed model route drafts typed proposal
  -> ontology resolver checks registered slugs
  -> deterministic policy checks controls and access modes
  -> exact versioned agent manifest is exported
  -> business owner and source owner approve independently
  -> mocked orchestrator registers a sandbox instance
  -> synthetic tools carry human and agent identity through policy
  -> allowed and denied requests produce decision evidence
  -> cited findings and four evaluation results are recorded
  -> sandbox evaluation passes; the journey stops before production
```

## Three connector classes

### Model connector

The model connector receives business intent and approved ontology metadata. It does not receive loan documents, servicing records, file-share credentials, or production authority. Its output is a `ProposalDraft` Pydantic object.

The prototype supports:

- Google Gemini Developer API with `gemini-flash-latest`
- Anthropic with `claude-sonnet-5`
- A deterministic offline reference provider

### Source connectors

The proposed runtime agent would invoke governed tools rather than connect directly to sources:

- Loan Document Search -> entitled document retrieval API -> Midland file source/index
- Loan Profile Lookup -> allowlisted read-only API -> servicing database
- Policy Search -> citation-preserving retrieval -> approved policy index

The sandbox executes deterministic stand-ins for all three interfaces against synthetic records. This makes identity propagation, authorization, citation, refusal, prompt-injection handling, latency, and content hashes inspectable without implying access to an enterprise system. Real source connectors remain out of scope.

### Control and delivery connectors

The target operating path also needs institutional identity, entitlement policy, approval authority, evidence retention, issue/change management, code repositories, test/evaluation systems, and deployment controls. The demo represents those boundaries with two role-specific approvals, a mocked registration API, append-only runtime evidence, and downloadable hashed artifacts.

## What creates the agent

The LLM interprets intent; it does not create or authorize a runtime agent. Application code validates the model output against the ontology and exports a versioned manifest. Independent humans authorize sandbox use. Only then does the orchestration adapter register an instance from that exact manifest. A production design would replace the mock with the selected control-plane API while retaining the manifest, approval, policy, and evidence contracts.

## Runtime and evidence boundary

Every synthetic tool call carries a human subject and a distinct agent subject. The policy decision is made before source content is returned. An entitled loan request is allowed; a second loan is denied and returns no source payload. The permitted path produces citation-bearing findings, and the evaluation pack tests citations, write refusal, access control, and embedded prompt injection.

The evidence report contains the model route, prompt version, tokens, estimated model cost when a configured rate is known, measured latency, human reviews, orchestration identifiers, policy decisions, tool-call request and response hashes, evaluation results, and artifact hashes. A deterministic offline run truthfully reports zero model cost. Unknown live-provider pricing is left unknown rather than invented.

## Ontology scope

The graph describes governed capabilities and access paths, not customer-level knowledge. Nodes include business outcomes, roles, workflows, agent capabilities, tools, connectors, data products, systems, controls, and delivery artifacts. Edges express relationships such as `serves`, `uses`, `invokes`, `reads`, `resides_in`, `constrained_by`, and `produces`.

SQLite stores the prototype using normalized tables. A graph database should be evaluated only after real impact-analysis and multi-hop governance queries are validated.

## Platform workshop questions

1. Can the orchestration layer import or reference our ontology identifiers without becoming their system of record?
2. How are agents, models, tools, permissions, and workflow versions registered and promoted?
3. Which policy checks are native, and which call an institutional policy decision point?
4. What proof-of-work fields are captured, how are they exported, and can retention be controlled?
5. How does the orchestration layer keep user identity and agent identity together through every tool call?
6. What interface does the integration layer expose for existing APIs, file retrieval services, and event systems?
7. How are model residency, provider routing, prompt versions, token cost, and fallback policies enforced?
8. What is the promotion contract for requirements, repositories, tests, approvals, and deployments after sandbox evaluation?
9. Can one workflow be proven read-only even when another agent on the platform has write access?
10. How are emergency disablement, rollback, and downstream dependency impact represented?
