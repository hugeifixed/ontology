from django.db import migrations


def neutralize_platform_labels(apps, schema_editor):
    OntologyNode = apps.get_model("studio", "OntologyNode")
    ProofEvent = apps.get_model("studio", "ProofEvent")
    OntologyNode.objects.filter(pk=17).update(
        slug="approved-model-route",
        name="Approved model route",
        description=(
            "Target governed route for approved models, cost policy, residency, "
            "and invocation evidence."
        ),
        source_reference="Enterprise model gateway",
    )
    OntologyNode.objects.filter(pk__in=(18, 19)).update(
        source_reference="Target integration layer"
    )
    ProofEvent.objects.filter(event_type="sdlc_package_ready").update(
        actor="Delivery orchestration service (target)"
    )


class Migration(migrations.Migration):
    dependencies = [
        ("studio", "0002_seed_reference_ontology"),
    ]

    operations = [
        # This content-only cleanup intentionally remains neutral on rollback.
        migrations.RunPython(neutralize_platform_labels, migrations.RunPython.noop),
    ]
