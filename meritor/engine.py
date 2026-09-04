"""The credit engine facade — where memory becomes an onchain decision.

A `CreditSession` is deliberately scoped to one process run. Nothing is cached
between sessions in memory-the-RAM-sense; everything a session knows about a
counterparty it learned by calling out to the memory layer. That is what makes
the fresh-session demo honest rather than staged.
"""

from __future__ import annotations

import os
import uuid
from dataclasses import dataclass, field

from .config import Settings, load_settings
from .domain.models import CounterpartyProfile, CreditDecision, CreditEvent
from .domain.scoring import decide, score_profile
from .memory.base import MemoryBackend, MemoryUnavailable


def new_session_id() -> str:
    """Resolve this run's logical session id.

    A logical session is a unit of the *narrative* — "the agent came back a
    week later" — not a unit of process lifetime. Several CLI invocations can
    belong to one logical session, and one logical session must never be split
    across process boundaries by accident, because `sessions_seen` feeds both
    the maturity score and the cross-session guardrail on uncollateralized
    credit. Making the boundary explicit is what keeps that evidence honest.
    """
    explicit = os.getenv("MERITOR_SESSION_ID")
    return explicit if explicit else f"sess_{uuid.uuid4().hex[:12]}"


def build_backend(settings: Settings) -> MemoryBackend:
    """Construct the configured memory driver. Never falls back."""
    if settings.memory_driver == "sibyl":
        from .memory.sibyl import SibylMemoryBackend

        return SibylMemoryBackend(
            db_path=settings.sibyl_db_path,
            tenant_id=settings.sibyl_tenant_id,
        )
    if settings.memory_driver == "local":
        from .memory.local import LocalFileBackend

        return LocalFileBackend(settings.local_memory_path, settings.sibyl_tenant_id)
    raise RuntimeError(f"unknown memory driver {settings.memory_driver!r}")


@dataclass
class CreditSession:
    """One underwriting session against a live memory backend."""

    memory: MemoryBackend
    session_id: str = field(default_factory=new_session_id)
    settings: Settings | None = None

    @classmethod
    def open(
        cls, settings: Settings | None = None, session_id: str | None = None
    ) -> "CreditSession":
        settings = settings or load_settings()
        return cls(
            memory=build_backend(settings),
            session_id=session_id or new_session_id(),
            settings=settings,
        )

    # --- read path -------------------------------------------------------

    def recall(self, agent_id: str) -> CounterpartyProfile | None:
        """Read a counterparty's history. Propagates MemoryUnavailable."""
        return self.memory.recall(agent_id)

    def underwrite(self, agent_id: str, requested_usdc: float) -> CreditDecision:
        """Price a credit request against recalled memory.

        The only place a MemoryUnavailable is converted into an answer instead
        of an exception — and the answer is always a rejection.
        """
        try:
            profile = self.memory.recall(agent_id)
        except MemoryUnavailable:
            return decide(
                None,
                agent_id=agent_id,
                session_id=self.session_id,
                requested_usdc=requested_usdc,
                memory_available=False,
            )
        memo = None
        if hasattr(self.memory, "load_memo"):
            try:
                memo = self.memory.load_memo(agent_id)
            except Exception:
                memo = None
        return decide(
            profile,
            agent_id=agent_id,
            session_id=self.session_id,
            requested_usdc=requested_usdc,
            memory_available=True,
            tier_cap=memo.tier_cap if memo else None,
        )

    # --- write path ------------------------------------------------------

    def record(self, agent_id: str, event: CreditEvent) -> CounterpartyProfile:
        """Persist one credit event, stamped with this session's id."""
        event.session_id = self.session_id
        return self.memory.remember(agent_id, event)

    def reflect(self, agent_id: str):
        """Consolidate the counterparty's journal into a durable credit memo.

        Returns the memo, or None if there is nothing to reflect on. Persists it
        so the next session's underwriting reads the trend without recomputing.
        """
        from .domain.reflection import reflect as run_reflect

        profile = self.memory.recall(agent_id)
        if profile is None or not profile.events:
            return None
        memo = run_reflect(profile)
        if hasattr(self.memory, "save_memo"):
            self.memory.save_memo(memo)
        return memo

    # --- introspection ---------------------------------------------------

    def explain(self, agent_id: str) -> str:
        profile = self.memory.recall(agent_id)
        if profile is None:
            return f"{agent_id}: no credit memory in this namespace."
        return score_profile(profile).explain()
