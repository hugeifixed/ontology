"""Safe, provider-neutral failures that can be shown to a requester."""


class ProviderRequestError(RuntimeError):
    """Report an external-provider failure without exposing its raw response."""

    def __init__(self, public_message: str) -> None:
        self.public_message = public_message
        super().__init__(public_message)
