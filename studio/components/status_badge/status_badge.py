"""Accessible, semantically colored status badge."""

from django_components import Component, register

_STATE_TONES = {
    "approved": "badge-success badge-soft",
    "pass": "badge-success badge-soft",
    "ready": "badge-success badge-soft",
    "low": "badge-success badge-soft",
    "conditional": "badge-warning badge-soft",
    "needs_review": "badge-warning badge-soft",
    "warning": "badge-warning badge-soft",
    "moderate": "badge-warning badge-soft",
    "blocked": "badge-error badge-soft",
    "block": "badge-error badge-soft",
    "high": "badge-error badge-soft",
    "retired": "badge-error badge-soft",
    "info": "badge-info badge-soft",
}


@register("status_badge")
class StatusBadge(Component):
    """Render a wrapping daisyUI badge without accepting arbitrary CSS classes."""

    template_file = "status_badge.html"

    class Kwargs:
        """Inputs accepted by the component template tag."""

        label: str
        state: str = "neutral"
        size: str = "medium"

    def get_template_data(self, args, kwargs: Kwargs, slots, context):
        """Map domain states to controlled semantic presentation classes."""
        size_class = "badge-sm" if kwargs.size == "small" else ""
        return {
            "label": kwargs.label,
            "size_class": size_class,
            "tone_class": _STATE_TONES.get(kwargs.state, "badge-outline"),
        }
