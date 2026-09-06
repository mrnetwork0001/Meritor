"""Sibyl Memory driver - the mandatory, load-bearing substrate.

Sibyl Memory is a local SQLite substrate, not a hosted service: no API key, no
base URL, no network call on the read or write path. That shapes the design in
a way worth stating plainly, because it is easy to mistake for a weakness. The
memory lives in a file the agent owns, which is precisely why deleting it is a
clean, demonstrable experiment rather than a mocked failure injection.

Meritor uses four distinct primitives rather than one key-value blob, because
each carries a different part of the credit argument:

  entities   the counterparty's current credit profile, with the tier mirrored
             into `status` so the portfolio can be swept by risk band without
             deserialising every record.
  events     an append-only journal of every credit event, which is what makes
             the score reconstructible rather than merely current.
  state      hot per-deployment state - the collateral policy version in force,
             and live exposure.
  search     FTS5 lexical search across profiles, so an underwriter can ask
             "who else has a dispute on record" without a full table scan.

The journal is the part that matters most. A credit score you cannot audit is
a number; a credit score you can replay to any past instant is a decision you
can defend to the counterparty you rejected.
"""

from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from typing import Any

from ..domain.models import CounterpartyProfile, CreditEvent
from .base import MemoryBackend, MemoryUnavailable

CATEGORY = "counterparty"
POLICY_KEY = "meritor:collateral_policy"
EXPOSURE_KEY = "meritor:exposure"


class SibylMemoryBackend(MemoryBackend):
    """Credit memory on Sibyl Memory."""

    def __init__(
        self,
        db_path: str | Path = "~/.sibyl-memory/memory.db",
        tenant_id: str = "meritor-credit",
    ) -> None:
        try:
            from sibyl_memory_client import MemoryClient
        except ImportError as exc:  # pragma: no cover - dependency is declared
            raise MemoryUnavailable(
                "sibyl-memory-client is not installed. Meritor's credit engine "
                "has no memory substrate without it: pip install "
                "'sibyl-memory-client==0.8.0'"
            ) from exc

        self._db_path = Path(db_path).expanduser()
        self._tenant_id = tenant_id
        try:
            self._client = MemoryClient.local(str(self._db_path), tenant_id=tenant_id)
        except Exception as exc:
            raise MemoryUnavailable(f"could not open Sibyl Memory at {self._db_path}: {exc}") from exc

    @property
    def name(self) -> str:
        return f"sibyl-memory[{self._db_path}, tenant={self._tenant_id}]"

    # --- error translation ------------------------------------------------

    @staticmethod
    def _not_found_type():
        from sibyl_memory_client import NotFoundError

        return NotFoundError

    def _guard(self, op: str, fn, *args, **kwargs):
        """Run an SDK call, translating substrate failure into MemoryUnavailable.

        NotFoundError is deliberately *not* translated - "this counterparty has
        no record" and "the memory layer is gone" are different facts, and
        collapsing them is exactly the bug that would make an outage look like
        a clean slate.
        """
        try:
            return fn(*args, **kwargs)
        except self._not_found_type():
            raise
        except Exception as exc:
            raise MemoryUnavailable(f"Sibyl Memory {op} failed: {exc}") from exc

    # --- MemoryBackend ----------------------------------------------------

    def health(self) -> bool:
        try:
            self._guard("health check", self._client.get_tenant)
            return True
        except MemoryUnavailable:
            return False

    def recall(self, agent_id: str) -> CounterpartyProfile | None:
        try:
            record = self._guard("get_entity", self._client.get_entity, CATEGORY, agent_id)
        except self._not_found_type():
            return None
        body = record.get("body")
        if not body:
            return None
        return CounterpartyProfile.model_validate(body)

    def remember(self, agent_id: str, event: CreditEvent) -> CounterpartyProfile:
        profile = self.recall(agent_id) or CounterpartyProfile(agent_id=agent_id)
        profile.record(event)

        # Late import keeps the domain layer free of scoring concerns here.
        from ..domain.scoring import score_profile

        tier = score_profile(profile).tier

        self._guard(
            "set_entity",
            self._client.set_entity,
            CATEGORY,
            agent_id,
            json.loads(profile.model_dump_json()),
            status=tier.value,
        )

        # The append-only journal. `acted` reads back as a human-legible line in
        # the event stream; `extra` carries the machine-readable payload used to
        # replay the score at a past instant.
        self._guard(
            "write_event",
            self._client.write_event,
            acted=[
                f"{event.event_type.value} · {agent_id} · ${event.amount_usdc:,.2f} USDC"
            ],
            evaluated=[f"tier={tier.value} after {len(profile.events)} events"],
            extra={
                "agent_id": agent_id,
                "session_id": event.session_id,
                "event": json.loads(event.model_dump_json()),
                "tier_after": tier.value,
            },
            ts=event.occurred_at.isoformat(),
        )
        return profile

    def forget(self, agent_id: str) -> None:
        self._guard("delete_entity", self._client.delete_entity, CATEGORY, agent_id)

    def forget_all(self) -> int:
        rows = self._guard(
            "list_entities", self._client.list_entities, CATEGORY, limit=10_000
        )
        n = 0
        for row in rows:
            if self._guard("delete_entity", self._client.delete_entity, CATEGORY, row["name"]):
                n += 1
        return n

    def known_agents(self) -> list[str]:
        rows = self._guard(
            "list_entities", self._client.list_entities, CATEGORY, limit=10_000
        )
        return sorted(r["name"] for r in rows)

    # --- Primitives beyond the base contract ------------------------------

    def by_tier(self, tier: str) -> list[str]:
        """Sweep the portfolio by risk band, using the mirrored entity status."""
        rows = self._guard(
            "list_entities", self._client.list_entities, CATEGORY, status=tier, limit=10_000
        )
        return sorted(r["name"] for r in rows)

    def search_counterparties(self, query: str, limit: int = 20) -> list[dict[str, Any]]:
        """Lexical (FTS5) search across stored credit profiles."""
        results = self._guard(
            "search_entities", self._client.search_entities, query, limit=limit, category=CATEGORY
        )
        return list(results)

    def journal(
        self, since: datetime | None = None, until: datetime | None = None, limit: int = 500
    ) -> list[dict[str, Any]]:
        """Read the append-only credit journal over a time window."""
        return self._guard(
            "read_events",
            self._client.read_events,
            limit=limit,
            since=since.isoformat() if since else None,
            until=until.isoformat() if until else None,
        )

    def profile_as_of(self, agent_id: str, instant: datetime) -> CounterpartyProfile | None:
        """Reconstruct a counterparty's profile as it stood at `instant`.

        Time-travel over the journal rather than the current record. This is
        what turns the score from a number into a defensible decision: when a
        counterparty disputes a rejection, Meritor can show the exact evidence
        it held at the moment it decided, not the evidence it holds now.
        """
        rows = self.journal(until=instant, limit=10_000)
        profile = CounterpartyProfile(agent_id=agent_id)
        seen = False
        for row in rows:
            extra = row.get("extra") or {}
            if isinstance(extra, str):
                try:
                    extra = json.loads(extra)
                except json.JSONDecodeError:
                    continue
            if extra.get("agent_id") != agent_id:
                continue
            raw_event = extra.get("event")
            if not raw_event:
                continue
            profile.record(CreditEvent.model_validate(raw_event))
            seen = True
        return profile if seen else None

    def set_policy(self, policy: dict[str, Any]) -> None:
        self._guard("set_state", self._client.set_state, POLICY_KEY, policy)

    def get_policy(self) -> dict[str, Any] | None:
        row = self._guard("get_state", self._client.get_state, POLICY_KEY)
        return row.get("body") if row else None

    def free_tier_status(self) -> dict[str, Any]:
        return self._guard("free_tier_status", self._client.free_tier_status)

    # --- Reflection memos (reference storage; free-tier) ------------------

    def save_memo(self, memo) -> None:
        self._guard(
            "set_reference", self._client.set_reference,
            f"credit_memo:{memo.agent_id}", json.loads(memo.model_dump_json()),
        )

    def load_memo(self, agent_id: str):
        from ..domain.reflection import CreditMemo

        row = self._guard("get_reference", self._client.get_reference, f"credit_memo:{agent_id}")
        if not row:
            return None
        body = row.get("body")
        if isinstance(body, str):
            try:
                body = json.loads(body)
            except json.JSONDecodeError:
                return None
        return CreditMemo.model_validate(body) if body else None
