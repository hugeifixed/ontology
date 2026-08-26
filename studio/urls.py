"""Namespaced routes for the studio."""

from django.urls import path

from studio import views

app_name = "studio"

urlpatterns = [
    path("", views.dashboard, name="dashboard"),
    path("catalog/discover", views.discover, name="discover"),
    path("proposals/compose", views.compose_proposal, name="compose-proposal"),
    path("proposals/<int:proposal_id>", views.proposal_detail, name="proposal-detail"),
    path(
        "proposals/<int:proposal_id>/approve",
        views.approve_proposal,
        name="approve-proposal",
    ),
    path(
        "proposals/<int:proposal_id>/manifest",
        views.download_manifest,
        name="download-manifest",
    ),
    path(
        "proposals/<int:proposal_id>/sandbox/register",
        views.register_sandbox,
        name="register-sandbox",
    ),
    path(
        "proposals/<int:proposal_id>/sandbox/evaluate",
        views.evaluate_sandbox,
        name="evaluate-sandbox",
    ),
    path(
        "proposals/<int:proposal_id>/evidence/<str:artifact_type>",
        views.download_evidence,
        name="download-evidence",
    ),
]
