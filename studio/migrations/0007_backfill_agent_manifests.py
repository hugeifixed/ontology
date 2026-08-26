import hashlib
import json

from django.db import migrations


def canonical_json(value):
    return json.dumps(value, indent=2, sort_keys=True, separators=(",", ": ")) + "\n"


def backfill_manifests(apps, schema_editor):
    AgentManifest = apps.get_model("studio", "AgentManifest")
    ProofEvent = apps.get_model("studio", "ProofEvent")
    ProposalBinding = apps.get_model("studio", "ProposalBinding")
    WorkflowProposal = apps.get_model("studio", "WorkflowProposal")

    for proposal in WorkflowProposal.objects.all():
        if AgentManifest.objects.filter(proposal=proposal, version="1.0.0").exists():
            continue
        bindings = list(
            ProposalBinding.objects.filter(proposal=proposal).select_related("node")
        )

        def manifest_binding(binding):
            return {
                "access_mode": binding.access_mode,
                "name": binding.node.name,
                "purpose": binding.purpose,
                "slug": binding.node.slug,
            }

        payload = {
            "agent": {
                "name": proposal.agent_name,
                "purpose": proposal.business_outcome,
                "runtime": "mocked-orchestration-api",
            },
            "boundaries": {
                "allowed_actions": ["read", "retrieve", "compare", "cite", "recommend"],
                "prohibited_actions": [
                    "write to a system of record",
                    "contact a customer",
                    "make a final compliance decision",
                    "deploy to production",
                ],
                "production_eligible": False,
                "sandbox_only": True,
            },
            "connectors": [
                manifest_binding(binding)
                for binding in bindings
                if binding.node.node_type == "connector"
            ],
            "controls": [
                manifest_binding(binding)
                for binding in bindings
                if binding.binding_kind == "control"
            ],
            "data_products": [
                manifest_binding(binding)
                for binding in bindings
                if binding.binding_kind == "data"
            ],
            "evaluation_pack": [
                "citation_accuracy",
                "refusal",
                "access_control",
                "prompt_injection",
            ],
            "identity_contract": {
                "agent_identity": "registered sandbox instance identity",
                "authorization_rule": "human entitlement AND agent tool binding",
                "human_identity": "simulated servicing analyst identity",
            },
            "manifest_version": "1.0.0",
            "model_route": {
                "model": proposal.model_name,
                "prompt_version": proposal.prompt_version,
                "provider": proposal.model_provider,
            },
            "proposal_id": proposal.pk,
            "schema_version": "agent-manifest/v1",
            "tools": [
                manifest_binding(binding)
                for binding in bindings
                if binding.node.node_type == "tool"
            ],
        }
        content = canonical_json(payload)
        artifact_hash = hashlib.sha256(content.encode()).hexdigest()
        AgentManifest.objects.create(
            proposal=proposal,
            version="1.0.0",
            schema_version="agent-manifest/v1",
            prompt_version=proposal.prompt_version,
            content=content,
            artifact_hash=artifact_hash,
            size_bytes=len(content.encode()),
        )
        ProofEvent.objects.create(
            proposal=proposal,
            event_type="manifest_exported",
            actor="Manifest backfill",
            summary="Exported a sandbox-only manifest for an existing governed proposal.",
            evidence_reference=f"sha256:{artifact_hash}",
        )


def reverse_backfill(apps, schema_editor):
    AgentManifest = apps.get_model("studio", "AgentManifest")
    ProofEvent = apps.get_model("studio", "ProofEvent")
    backfill_events = ProofEvent.objects.filter(
        event_type="manifest_exported",
        actor="Manifest backfill",
    )
    artifact_hashes = [
        event.evidence_reference.removeprefix("sha256:") for event in backfill_events
    ]
    AgentManifest.objects.filter(artifact_hash__in=artifact_hashes).delete()
    backfill_events.delete()


class Migration(migrations.Migration):
    dependencies = [("studio", "0006_workflowproposal_agent_name")]

    operations = [migrations.RunPython(backfill_manifests, reverse_backfill)]
