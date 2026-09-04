"""Core domain models for Meritor's credit memory layer.

Everything in this module is a plain data structure. The credit state that
matters lives in Sibyl Memory; these types are the shape it takes in and out.
"""

from __future__ import annotations

from datetime import datetime, timezone
from enum import Enum
from typing import Any, Literal

from pydantic import BaseModel, Field


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


class EventType(str, Enum):
    """Append-only credit events. Each one mutates a counterparty's profile."""

    JOB_COMPLETED_ON_TIME = "job_completed_on_time"
    JOB_COMPLETED_LATE = "job_completed_late"
    JOB_FAILED = "job_failed"
    LOAN_DISBURSED = "loan_disbursed"
    LOAN_REPAID = "loan_repaid"
    LOAN_DEFAULTED = "loan_defaulted"
    DISPUTE_OPENED = "dispute_opened"
    DISPUTE_RESOLVED_FOR = "dispute_resolved_for"
    DISPUTE_RESOLVED_AGAINST = "dispute_resolved_against"


class Tier(str, Enum):
    """Collateral tiers. The tier is what turns memory into an onchain decision."""

    UNKNOWN = "UNKNOWN"
    BRONZE = "BRONZE"
    SILVER = "SILVER"
    GOLD = "GOLD"
    PLATINUM = "PLATINUM"


class CreditEvent(BaseModel):
    """One thing that happened to a counterparty, in one session.

    `session_id` is what makes fresh-session recall demonstrable: an event
    written in session A is read back and acted on in session B.
    """

    event_type: EventType
    session_id: str
    occurred_at: datetime = Field(default_factory=utcnow)

    amount_usdc: float = 0.0
    # Seconds relative to the deadline. Negative = early, positive = late.
    settlement_delta_s: float | None = None

    # Provenance: the onchain or ACP artifact that proves this event happened.
    tx_hash: str | None = None
    acp_job_id: str | None = None
    note: str = ""

    def signed_amount(self) -> float:
        return self.amount_usdc


class CounterpartyProfile(BaseModel):
    """The full credit memory for one agent counterparty.

    This is the object persisted to and recalled from Sibyl Memory. If it
    cannot be recalled, Meritor has no basis to extend credit and must reject.
    """

    agent_id: str
    first_seen_at: datetime = Field(default_factory=utcnow)
    last_seen_at: datetime = Field(default_factory=utcnow)
    sessions_seen: list[str] = Field(default_factory=list)
    events: list[CreditEvent] = Field(default_factory=list)

    def record(self, event: CreditEvent) -> None:
        self.events.append(event)
        self.last_seen_at = event.occurred_at
        if event.session_id not in self.sessions_seen:
            self.sessions_seen.append(event.session_id)

    # --- Derived counters -------------------------------------------------

    def _count(self, *types: EventType) -> int:
        return sum(1 for e in self.events if e.event_type in types)

    @property
    def jobs_on_time(self) -> int:
        return self._count(EventType.JOB_COMPLETED_ON_TIME)

    @property
    def jobs_late(self) -> int:
        return self._count(EventType.JOB_COMPLETED_LATE)

    @property
    def jobs_failed(self) -> int:
        return self._count(EventType.JOB_FAILED)

    @property
    def jobs_total(self) -> int:
        return self.jobs_on_time + self.jobs_late + self.jobs_failed

    @property
    def loans_repaid(self) -> int:
        return self._count(EventType.LOAN_REPAID)

    @property
    def loans_defaulted(self) -> int:
        return self._count(EventType.LOAN_DEFAULTED)

    @property
    def loans_settled(self) -> int:
        return self.loans_repaid + self.loans_defaulted

    @property
    def disputes_against(self) -> int:
        return self._count(EventType.DISPUTE_RESOLVED_AGAINST)

    @property
    def disputes_open(self) -> int:
        return self._count(EventType.DISPUTE_OPENED) - self._count(
            EventType.DISPUTE_RESOLVED_FOR, EventType.DISPUTE_RESOLVED_AGAINST
        )

    @property
    def total_volume_usdc(self) -> float:
        return sum(
            e.amount_usdc
            for e in self.events
            if e.event_type in (EventType.LOAN_REPAID, EventType.LOAN_DISBURSED)
        )

    @property
    def is_returning(self) -> bool:
        """True once this counterparty has been seen in more than one session.

        This is the flag the demo hinges on: it can only ever be true if
        memory survived a session boundary.
        """
        return len(self.sessions_seen) > 1


class ScoreBreakdown(BaseModel):
    """An explainable score. Judges (and counterparties) can audit every point."""

    agent_id: str
    score: float
    tier: Tier
    components: dict[str, float]
    rationale: list[str]
    evidence_events: int
    sessions_observed: int
    computed_at: datetime = Field(default_factory=utcnow)

    def explain(self) -> str:
        lines = [f"Credit score for {self.agent_id}: {self.score:.0f}/1000 → {self.tier.value}"]
        for name, value in self.components.items():
            lines.append(f"  {name:.<28} {value:+.1f}")
        lines.append(f"  {'evidence':.<28} {self.evidence_events} events across {self.sessions_observed} session(s)")
        lines.extend(f"  · {r}" for r in self.rationale)
        return "\n".join(lines)


class CreditDecision(BaseModel):
    """The output that actually gates money movement on Base."""

    agent_id: str
    session_id: str
    requested_usdc: float
    approved: bool
    approved_usdc: float
    collateral_required_usdc: float
    collateral_ratio: float
    tier: Tier
    score: float
    reason: str
    memory_backed: bool = Field(
        description="False when the decision was made with no recalled memory. "
        "A False here must never accompany an uncollateralized approval."
    )
    breakdown: ScoreBreakdown | None = None
