"""Explainable semantic discovery across governed catalog metadata."""

from __future__ import annotations

import re
from dataclasses import dataclass
from enum import StrEnum

from studio.models import (
    ApprovalState,
    BusinessDomain,
    Classification,
    NodeType,
    OntologyNode,
    RelationType,
)


class DiscoveryDecision(StrEnum):
    """Recommendation produced by the discovery boundary."""

    REUSE = "reuse"
    ACCESS_MISMATCH = "access_mismatch"
    METADATA_GAP = "metadata_gap"


@dataclass(frozen=True, slots=True)
class AccessProfile:
    """Synthetic discovery scope used to demonstrate hard filters."""

    label: str
    domains: frozenset[str]
    max_classification: str


@dataclass(frozen=True, slots=True)
class CatalogMatch:
    """One ranked or graph-derived catalog match."""

    node: OntologyNode
    score: int
    reason: str


@dataclass(frozen=True, slots=True)
class DiscoveryResult:
    """Complete evidence-backed discovery response for one intent."""

    intent: str
    access_profile: AccessProfile
    decision: DiscoveryDecision
    decision_label: str
    inferred_domain: str
    inferred_domain_label: str
    workflow: CatalogMatch | None
    products: tuple[CatalogMatch, ...]
    agent: CatalogMatch | None
    capabilities: tuple[CatalogMatch, ...]
    ranked_matches: tuple[CatalogMatch, ...]
    relationship_path: tuple[str, ...]
    catalog_count: int
    eligible_count: int
    excluded_count: int
    recommendation: str
    boundary: str
    can_continue: bool


ALL_DOMAINS = frozenset(
    {
        BusinessDomain.ENTERPRISE.value,
        BusinessDomain.TREASURY.value,
        BusinessDomain.RETAIL.value,
        BusinessDomain.COMMERCIAL_LOAN.value,
    }
)

ACCESS_PROFILES = {
    "enterprise_architect": AccessProfile(
        label="Cross-domain architect",
        domains=ALL_DOMAINS,
        max_classification=Classification.RESTRICTED.value,
    ),
    "treasury_seller": AccessProfile(
        label="Treasury seller",
        domains=frozenset({BusinessDomain.ENTERPRISE.value, BusinessDomain.TREASURY.value}),
        max_classification=Classification.INTERNAL.value,
    ),
    "retail_specialist": AccessProfile(
        label="Retail specialist",
        domains=frozenset({BusinessDomain.ENTERPRISE.value, BusinessDomain.RETAIL.value}),
        max_classification=Classification.INTERNAL.value,
    ),
    "servicing_analyst": AccessProfile(
        label="Servicing analyst",
        domains=frozenset(
            {
                BusinessDomain.ENTERPRISE.value,
                BusinessDomain.COMMERCIAL_LOAN.value,
            }
        ),
        max_classification=Classification.RESTRICTED.value,
    ),
}

DOMAIN_CONCEPTS = {
    BusinessDomain.TREASURY.value: (
        "treasury",
        "cash management",
        "sales",
        "seller",
        "rfp",
        "proposal",
        "positive pay",
        "ach",
        "seismic",
        "pinnacle",
        "qvidian",
    ),
    BusinessDomain.RETAIL.value: (
        "retail",
        "care center",
        "call center",
        "customer service",
        "fee reversal",
        "branch",
        "consumer account",
        "salesforce",
        "knowledge article",
    ),
    BusinessDomain.COMMERCIAL_LOAN.value: (
        "commercial loan",
        "loan servicing",
        "insurance",
        "covenant",
        "borrower",
        "collateral",
        "flood",
        "loan agreement",
        "midland",
    ),
}

DOMAIN_LABELS = {
    BusinessDomain.ENTERPRISE.value: "Enterprise / shared",
    BusinessDomain.TREASURY.value: "Treasury management",
    BusinessDomain.RETAIL.value: "Retail banking",
    BusinessDomain.COMMERCIAL_LOAN.value: "Commercial loan servicing",
    "": "No confident domain match",
}

CLASSIFICATION_RANK = {
    Classification.PUBLIC.value: 0,
    Classification.INTERNAL.value: 1,
    Classification.CONFIDENTIAL.value: 2,
    Classification.RESTRICTED.value: 3,
}

DISCOVERABLE_NODE_TYPES = (
    NodeType.DATA_PRODUCT,
    NodeType.WORKFLOW,
    NodeType.AGENT_INSTANCE,
    NodeType.AGENT_CAPABILITY,
)

STOP_WORDS = frozenset(
    {
        "a",
        "all",
        "and",
        "for",
        "from",
        "help",
        "i",
        "in",
        "need",
        "of",
        "our",
        "the",
        "to",
        "we",
        "with",
    }
)


def discover_catalog(*, intent: str, access_profile: str) -> DiscoveryResult:
    """Filter, rank, and graph-expand governed metadata for one business intent."""
    profile = ACCESS_PROFILES[access_profile]
    catalog = list(
        OntologyNode.objects.filter(
            node_type__in=DISCOVERABLE_NODE_TYPES,
            approval_state__in=(ApprovalState.APPROVED, ApprovalState.CONDITIONAL),
        ).prefetch_related("outgoing_edges__target")
    )
    inferred_domain = _infer_domain(intent)
    eligible = [node for node in catalog if _is_eligible(node, profile)]

    if inferred_domain and inferred_domain not in profile.domains:
        return _empty_result(
            intent=intent,
            profile=profile,
            decision=DiscoveryDecision.ACCESS_MISMATCH,
            inferred_domain=inferred_domain,
            catalog_count=len(catalog),
            eligible_count=len(eligible),
            recommendation=(
                "The intent maps to a domain outside this simulated discovery scope. "
                "Request the domain-owner path instead of broadening source access here."
            ),
            boundary=(
                "No catalog objects were ranked after the hard domain filter. "
                "This is a metadata-scope demonstration, not a production entitlement decision."
            ),
        )

    if not inferred_domain:
        return _empty_result(
            intent=intent,
            profile=profile,
            decision=DiscoveryDecision.METADATA_GAP,
            inferred_domain="",
            catalog_count=len(catalog),
            eligible_count=len(eligible),
            recommendation=(
                "No governed business-domain concept matched with enough confidence. "
                "Capture an owner, source, workflow, and access policy before proposing an agent."
            ),
            boundary=(
                "A model should not invent missing catalog objects. This request stops at "
                "discovery until metadata is registered and approved."
            ),
        )

    domain_nodes = [
        node
        for node in eligible
        if _enum_value(node.business_domain) in {inferred_domain, BusinessDomain.ENTERPRISE.value}
    ]
    ranked = tuple(
        sorted(
            (_score_node(node, intent, inferred_domain) for node in domain_nodes),
            key=lambda match: (-match.score, match.node.name),
        )[:8]
    )
    workflow = next(
        (
            match
            for match in ranked
            if match.node.node_type == NodeType.WORKFLOW and match.score >= 55
        ),
        None,
    )
    if workflow is None:
        return _empty_result(
            intent=intent,
            profile=profile,
            decision=DiscoveryDecision.METADATA_GAP,
            inferred_domain=inferred_domain,
            catalog_count=len(catalog),
            eligible_count=len(eligible),
            ranked_matches=ranked,
            recommendation=(
                "Relevant catalog metadata exists, but no approved workflow anchors the "
                "request. Define the workflow boundary before creating an agent instance."
            ),
            boundary="Discovery found concepts, not an executable workflow contract.",
        )

    products = _linked_matches(workflow.node, RelationType.READS, NodeType.DATA_PRODUCT)
    agents = _linked_matches(workflow.node, RelationType.USES, NodeType.AGENT_INSTANCE)
    agent = agents[0] if agents else None
    capabilities = (
        _linked_matches(agent.node, RelationType.INSTANCE_OF, NodeType.AGENT_CAPABILITY)
        if agent
        else ()
    )
    relationship_path = _relationship_path(workflow, products, agent, capabilities)
    is_runnable_reference = inferred_domain == BusinessDomain.COMMERCIAL_LOAN.value
    boundary = (
        "This catalog path can continue into the synthetic commercial-loan sandbox. "
        "Separate business and source-owner approvals are still required."
        if is_runnable_reference
        else (
            "Discovery is complete, but this domain has no runnable adapter in the demo. "
            "The result is not an agent deployment or production approval."
        )
    )
    return DiscoveryResult(
        intent=intent,
        access_profile=profile,
        decision=DiscoveryDecision.REUSE,
        decision_label="Reuse an existing governed workflow",
        inferred_domain=inferred_domain,
        inferred_domain_label=DOMAIN_LABELS[inferred_domain],
        workflow=workflow,
        products=products,
        agent=agent,
        capabilities=capabilities,
        ranked_matches=ranked,
        relationship_path=relationship_path,
        catalog_count=len(catalog),
        eligible_count=len(eligible),
        excluded_count=len(catalog) - len(eligible),
        recommendation=(
            f"Start with {workflow.node.name}; reuse its registered data products and "
            "agent boundary before proposing anything new."
        ),
        boundary=boundary,
        can_continue=is_runnable_reference,
    )


def _empty_result(
    *,
    intent: str,
    profile: AccessProfile,
    decision: DiscoveryDecision,
    inferred_domain: str,
    catalog_count: int,
    eligible_count: int,
    recommendation: str,
    boundary: str,
    ranked_matches: tuple[CatalogMatch, ...] = (),
) -> DiscoveryResult:
    labels = {
        DiscoveryDecision.ACCESS_MISMATCH: "Outside the selected discovery scope",
        DiscoveryDecision.METADATA_GAP: "Catalog metadata gap",
        DiscoveryDecision.REUSE: "Reuse an existing governed workflow",
    }
    return DiscoveryResult(
        intent=intent,
        access_profile=profile,
        decision=decision,
        decision_label=labels[decision],
        inferred_domain=inferred_domain,
        inferred_domain_label=DOMAIN_LABELS[inferred_domain],
        workflow=None,
        products=(),
        agent=None,
        capabilities=(),
        ranked_matches=ranked_matches,
        relationship_path=(),
        catalog_count=catalog_count,
        eligible_count=eligible_count,
        excluded_count=catalog_count - eligible_count,
        recommendation=recommendation,
        boundary=boundary,
        can_continue=False,
    )


def _infer_domain(intent: str) -> str:
    normalized = " ".join(_tokenize(intent))
    scores: dict[str, int] = {}
    for domain, concepts in DOMAIN_CONCEPTS.items():
        score = 0
        for concept in concepts:
            concept_tokens = _tokenize(concept)
            if concept in intent.lower():
                score += 4 if len(concept_tokens) > 1 else 2
            else:
                score += len(set(concept_tokens) & set(normalized.split()))
        scores[domain] = score
    domain, score = max(scores.items(), key=lambda item: item[1])
    return domain if score >= 2 else ""


def _is_eligible(node: OntologyNode, profile: AccessProfile) -> bool:
    domain = _enum_value(node.business_domain)
    classification = _enum_value(node.classification)
    return (
        domain in profile.domains
        and CLASSIFICATION_RANK[classification] <= CLASSIFICATION_RANK[profile.max_classification]
    )


def _score_node(
    node: OntologyNode,
    intent: str,
    inferred_domain: str,
) -> CatalogMatch:
    query_tokens = set(_tokenize(intent)) - STOP_WORDS
    document = " ".join(
        (
            node.name,
            node.slug.replace("-", " "),
            node.description,
            node.owner,
            node.source_reference,
            node.search_terms,
        )
    )
    document_tokens = set(_tokenize(document)) - STOP_WORDS
    direct_matches = sorted(query_tokens & document_tokens)
    semantic_tokens: set[str] = set()
    for concept in DOMAIN_CONCEPTS[inferred_domain]:
        concept_tokens = set(_tokenize(concept))
        if concept in intent.lower() or concept_tokens & query_tokens:
            semantic_tokens.update(concept_tokens)
    semantic_matches = sorted(semantic_tokens & document_tokens)
    domain_bonus = 32 if _enum_value(node.business_domain) == inferred_domain else 4
    type_bonus = {
        NodeType.WORKFLOW: 12,
        NodeType.DATA_PRODUCT: 8,
        NodeType.AGENT_INSTANCE: 7,
        NodeType.AGENT_CAPABILITY: 5,
    }[node.node_type]
    score = min(
        100, domain_bonus + type_bonus + len(direct_matches) * 9 + len(semantic_matches) * 2
    )
    if direct_matches:
        reason = f"Matched intent terms: {', '.join(direct_matches[:3])}."
    else:
        reason = f"Registered in the inferred {DOMAIN_LABELS[inferred_domain]} domain."
    return CatalogMatch(node=node, score=score, reason=reason)


def _linked_matches(
    source: OntologyNode,
    relation: RelationType,
    target_type: NodeType,
) -> tuple[CatalogMatch, ...]:
    matches = []
    for edge in source.outgoing_edges.all():
        if edge.relation == relation and edge.target.node_type == target_type:
            matches.append(
                CatalogMatch(
                    node=edge.target,
                    score=100,
                    reason=f"Linked by the governed “{edge.get_relation_display()}” relationship.",
                )
            )
    return tuple(sorted(matches, key=lambda match: match.node.name))


def _relationship_path(
    workflow: CatalogMatch,
    products: tuple[CatalogMatch, ...],
    agent: CatalogMatch | None,
    capabilities: tuple[CatalogMatch, ...],
) -> tuple[str, ...]:
    path = [f"Workflow · {workflow.node.name}"]
    if agent:
        path.append(f"uses agent instance · {agent.node.name}")
    for capability in capabilities:
        path.append(f"instance of · {capability.node.name}")
    for product in products:
        path.append(f"reads data product · {product.node.name}")
    return tuple(path)


def _tokenize(value: str) -> tuple[str, ...]:
    return tuple(re.findall(r"[a-z0-9]+", value.lower()))


def _enum_value(value: object) -> str:
    return str(getattr(value, "value", value))
