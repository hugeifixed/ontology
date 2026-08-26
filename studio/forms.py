"""Forms for creating and approving governed workflow proposals."""

from django import forms
from django.conf import settings

from studio.models import ReviewRole
from studio.types import ProviderName

PROVIDER_CHOICES = (
    (ProviderName.DEMO.value, "Deterministic demo, no key required"),
    (ProviderName.GEMINI.value, "Google Gemini — AI Studio"),
    (ProviderName.ANTHROPIC.value, "Anthropic Claude"),
)

DISCOVERY_PROFILE_CHOICES = (
    (
        "enterprise_architect",
        "Cross-domain architect — all catalog metadata",
    ),
    (
        "treasury_seller",
        "Treasury seller — internal treasury metadata",
    ),
    (
        "retail_specialist",
        "Retail specialist — internal retail metadata",
    ),
    (
        "servicing_analyst",
        "Servicing analyst — commercial-loan metadata",
    ),
)

DISCOVERY_REFERENCE_INTENT = (
    "Help commercial loan servicing analysts find insurance requirements and return "
    "cited findings for human review."
)


class DiscoveryForm(forms.Form):
    """Capture an intent and simulated access profile for catalog discovery."""

    intent = forms.CharField(
        min_length=8,
        max_length=1000,
        initial=DISCOVERY_REFERENCE_INTENT,
        widget=forms.Textarea(
            attrs={
                "id": "id_discovery_intent",
                "class": "textarea w-full min-h-28",
                "placeholder": "What business question or workflow do you need to support?",
                "aria-describedby": "discovery-intent-help",
            }
        ),
    )
    access_profile = forms.ChoiceField(
        choices=DISCOVERY_PROFILE_CHOICES,
        initial="enterprise_architect",
        widget=forms.Select(
            attrs={
                "id": "id_discovery_profile",
                "class": "select w-full",
                "aria-describedby": "discovery-profile-help",
            }
        ),
    )


class ProposalForm(forms.Form):
    """Capture intent and an optional ephemeral model credential."""

    intent = forms.CharField(
        min_length=20,
        max_length=2000,
        widget=forms.Textarea(
            attrs={
                "class": "textarea textarea-lg w-full min-h-36",
                "placeholder": "Describe the outcome, users, and operating limits",
                "aria-describedby": "intent-help",
            }
        ),
    )
    requester_role = forms.CharField(
        min_length=3,
        max_length=160,
        initial="Commercial loan servicing product owner",
        widget=forms.TextInput(attrs={"class": "input w-full"}),
    )
    provider = forms.ChoiceField(
        choices=PROVIDER_CHOICES,
        initial=ProviderName.DEMO.value,
        widget=forms.Select(attrs={"class": "select w-full", "x-model": "provider"}),
    )
    model_name = forms.CharField(
        required=False,
        max_length=100,
        initial=settings.GEMINI_MODEL,
        widget=forms.TextInput(
            attrs={
                "class": "input w-full font-mono text-sm",
                "autocomplete": "off",
            }
        ),
    )
    api_key = forms.CharField(
        required=False,
        max_length=300,
        strip=True,
        widget=forms.PasswordInput(
            render_value=False,
            attrs={
                "class": "input w-full font-mono text-sm",
                "autocomplete": "off",
                "placeholder": "Used only when this form is submitted",
                "aria-describedby": "api-key-help",
            },
        ),
    )

    def clean_provider(self) -> ProviderName:
        """Normalize the selected provider to a typed value."""
        return ProviderName(self.cleaned_data["provider"])


class ApprovalForm(forms.Form):
    """Capture the accountable human decision for sandbox approval."""

    review_role = forms.TypedChoiceField(
        choices=ReviewRole.choices,
        coerce=ReviewRole,
        widget=forms.HiddenInput(),
    )

    approver = forms.CharField(
        min_length=3,
        max_length=120,
        initial="AI Governance Review Board",
        widget=forms.TextInput(attrs={"class": "input w-full"}),
    )
    note = forms.CharField(
        required=False,
        max_length=500,
        widget=forms.Textarea(
            attrs={"class": "textarea w-full", "placeholder": "Optional approval note"}
        ),
    )
