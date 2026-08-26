"""Controlled icon set for the primary navigation."""

from django_components import Component, register

_ICON_NAMES = frozenset(
    {
        "catalog",
        "connections",
        "ontology",
        "overview",
        "proposals",
        "workflow",
    }
)


@register("menu_icon")
class MenuIcon(Component):
    """Render one decorative icon from the workbench navigation set."""

    template_file = "menu_icon.html"

    class Kwargs:
        """Inputs accepted by the component template tag."""

        name: str

    def get_template_data(self, args, kwargs: Kwargs, slots, context):
        """Reject unknown names so navigation cannot silently show the wrong icon."""
        if kwargs.name not in _ICON_NAMES:
            message = f"Unknown menu icon: {kwargs.name}"
            raise ValueError(message)
        return {"name": kwargs.name}
