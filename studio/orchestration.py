"""Mocked orchestration boundary for sandbox-only agent registration."""

from dataclasses import dataclass
from hashlib import sha256


@dataclass(frozen=True)
class OrchestrationReceipt:
    """Non-production identifiers returned by the orchestration adapter."""

    agent_id: str
    request_id: str
    environment: str


class MockOrchestrationClient:
    """Register a manifest without calling or impersonating a real platform."""

    environment = "synthetic-sandbox"

    def register(self, *, manifest_hash: str, manifest_version: str) -> OrchestrationReceipt:
        """Return deterministic identifiers for an idempotent demo registration."""
        registration_key = f"{manifest_hash}:{manifest_version}:{self.environment}"
        digest = sha256(registration_key.encode()).hexdigest()
        return OrchestrationReceipt(
            agent_id=f"sandbox-agent-{digest[:12]}",
            request_id=f"mock-orch-{digest[12:28]}",
            environment=self.environment,
        )
