"""The memory backend contract.

Meritor is designed to fail closed. There is deliberately no graceful
degradation path around this interface: if the backend cannot be reached,
callers get an exception, not an empty profile that quietly reads as
"new counterparty with a clean record". That distinction is the whole
load-bearing argument — a memory layer you can remove without noticing
was never load-bearing.
"""

from __future__ import annotations

from abc import ABC, abstractmethod

from ..domain.models import CounterpartyProfile, CreditEvent


class MemoryUnavailable(RuntimeError):
    """The memory layer could not be reached, authenticated, or read.

    Never caught-and-defaulted inside the credit path. It propagates to the
    decision boundary, where it becomes an explicit 0-trust rejection.
    """


class MemoryBackend(ABC):
    """Persistent credit memory, namespaced per lender deployment."""

    @property
    @abstractmethod
    def name(self) -> str:
        """Human-readable backend name, shown in decision provenance."""

    @abstractmethod
    def health(self) -> bool:
        """True if the backend is reachable and authenticated right now."""

    @abstractmethod
    def recall(self, agent_id: str) -> CounterpartyProfile | None:
        """Read a counterparty's full credit profile.

        Returns None for a genuinely unseen counterparty.
        Raises MemoryUnavailable if the backend cannot answer.
        """

    @abstractmethod
    def remember(self, agent_id: str, event: CreditEvent) -> CounterpartyProfile:
        """Append one credit event and persist the updated profile."""

    @abstractmethod
    def forget(self, agent_id: str) -> None:
        """Erase one counterparty's memory. Used by the deletion test."""

    @abstractmethod
    def forget_all(self) -> int:
        """Erase the entire namespace. Returns the number of profiles removed.

        This is the demo's destructive beat: after calling it, every
        subsequent credit decision must collapse to 0-trust rejection.
        """

    @abstractmethod
    def known_agents(self) -> list[str]:
        """All agent ids with a profile in this namespace."""
