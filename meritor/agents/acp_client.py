"""Virtuals ACP driver - job dispatch as a source of credit events.

Meritor is a credit layer for an agent economy, and Virtuals ACP is where that
economy actually transacts. Every ACP job a counterparty completes or fails is a
data point about its reliability, so ACP is not a bolt-on multiplier here - it is
where Meritor's SLA history comes from.

The integration is a thin subprocess wrapper around @virtuals-protocol/acp-cli,
run with --json. The Python ACP SDK is abandoned (pinned below Python 3.13 and
built on a primitive ACP v2 removed), so the maintained CLI is the honest path.

`mock=True` runs the whole lifecycle without the network or a funded wallet, so
the credit-event mapping is testable and the demo runs offline. A real run swaps
the mock for the CLI once `acp configure` has authenticated.
"""

from __future__ import annotations

import json
import shutil
import subprocess
from dataclasses import dataclass, field
from enum import Enum
from typing import Any

from ..domain.models import CreditEvent, EventType


# Meritor's live ACP registration (Virtuals). Registered on ERC-8004 on Base
# mainnet as agent #84921; exposes the `meritor_credit_report` offering. This is
# the real identity the CLI operates as once `acp configure` has authenticated.
REGISTERED_AGENT = {
    "name": "Meritor",
    "acp_agent_id": "01a075bc-bf93-73e3-a1bd-cc0904791ab3",
    "wallet": "0xcd1e56694767cb4ab26ca87abcce5e964c41a196",
    "erc8004_id_base": 84921,
    "offering": "meritor_credit_report",
}


class JobPhase(str, Enum):
    """ACP v2 on-chain states, plus the CLI's terminal branches."""

    OPEN = "open"
    BUDGET_SET = "budget_set"
    FUNDED = "funded"
    SUBMITTED = "submitted"
    COMPLETED = "completed"
    REJECTED = "rejected"
    EXPIRED = "expired"


# How a finished ACP job becomes a credit event. This mapping is the whole point
# of the integration: reliability observed on ACP feeds the credit score that
# gates money on Base.
PHASE_TO_EVENT: dict[JobPhase, EventType | None] = {
    JobPhase.COMPLETED: EventType.JOB_COMPLETED_ON_TIME,
    JobPhase.REJECTED: EventType.JOB_FAILED,
    JobPhase.EXPIRED: EventType.JOB_FAILED,
    JobPhase.OPEN: None,
    JobPhase.BUDGET_SET: None,
    JobPhase.FUNDED: None,
    JobPhase.SUBMITTED: None,
}


@dataclass
class JobResult:
    job_id: str
    phase: JobPhase
    provider: str | None = None
    amount_usdc: float = 0.0
    raw: dict[str, Any] = field(default_factory=dict)

    def to_credit_event(self, session_id: str, *, late: bool = False) -> CreditEvent | None:
        """Translate a terminal ACP job into a credit event, or None if pending."""
        event_type = PHASE_TO_EVENT.get(self.phase)
        if event_type is None:
            return None
        if event_type is EventType.JOB_COMPLETED_ON_TIME and late:
            event_type = EventType.JOB_COMPLETED_LATE
        return CreditEvent(
            event_type=event_type,
            session_id=session_id,
            amount_usdc=self.amount_usdc,
            acp_job_id=self.job_id,
            note=f"ACP job {self.job_id} -> {self.phase.value}",
        )


class ACPError(RuntimeError):
    pass


class ACPClient:
    """Dispatches ACP jobs and reports terminal outcomes as credit signals."""

    def __init__(
        self,
        testnet: bool = True,
        mock: bool = False,
        cli: str = "acp",
        timeout_s: int = 180,
    ) -> None:
        self.testnet = testnet
        self.mock = mock
        self.cli = cli
        self.timeout_s = timeout_s

    # --- availability -----------------------------------------------------

    def available(self) -> tuple[bool, str]:
        if self.mock:
            return True, "mock mode"
        if shutil.which(self.cli) is None and shutil.which("npx") is None:
            return False, "neither 'acp' nor 'npx' is on PATH"
        return True, "cli present (authentication checked at call time)"

    def _run(self, *args: str) -> dict[str, Any]:
        """Run an acp CLI subcommand with --json and parse the result."""
        if shutil.which(self.cli):
            cmd = [self.cli, *args, "--json"]
        else:
            cmd = ["npx", "--no-install", self.cli, *args, "--json"]
        env_note = "IS_TESTNET=true " if self.testnet else ""
        try:
            proc = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=self.timeout_s,
                env={**_environ(), "IS_TESTNET": "true" if self.testnet else "false"},
            )
        except subprocess.TimeoutExpired as exc:
            raise ACPError(f"{env_note}{' '.join(cmd)} timed out after {self.timeout_s}s") from exc
        if proc.returncode != 0:
            raise ACPError(f"{env_note}{' '.join(cmd)} failed: {proc.stderr.strip() or proc.stdout.strip()}")
        try:
            return json.loads(proc.stdout)
        except json.JSONDecodeError as exc:
            raise ACPError(f"non-JSON output from {' '.join(cmd)}: {proc.stdout[:200]}") from exc

    # --- discovery + dispatch --------------------------------------------

    def whoami(self) -> dict[str, Any]:
        """Return the live registered ACP identity (read-only). Mock-safe."""
        if self.mock:
            return dict(REGISTERED_AGENT, mock=True)
        return self._run("agent", "whoami")

    def browse(self, query: str, top_k: int = 5) -> list[dict[str, Any]]:
        if self.mock:
            return [{"id": "0xPROVIDER_MOCK", "name": f"mock provider for {query}", "successRate": 0.97}]
        result = self._run("browse", query, "--top-k", str(top_k))
        if isinstance(result, dict):
            return result.get("agents") or result.get("results") or []
        return result or []

    def dispatch(self, provider: str, offering: str, budget_usdc: float) -> JobResult:
        """Create + fund an ACP job. In mock mode, resolves to COMPLETED."""
        if self.mock:
            return JobResult(
                job_id=f"mock_job_{abs(hash((provider, offering))) % 100000}",
                phase=JobPhase.COMPLETED,
                provider=provider,
                amount_usdc=budget_usdc,
                raw={"mock": True},
            )
        created = self._run("client", "create-job", "--provider", provider,
                            "--offering", offering, "--budget", str(budget_usdc))
        job_id = str(created.get("jobId") or created.get("id") or "")
        if not job_id:
            raise ACPError(f"create-job returned no job id: {created}")
        self._run("client", "fund", "--job-id", job_id)
        return JobResult(job_id=job_id, phase=JobPhase.FUNDED, provider=provider,
                         amount_usdc=budget_usdc, raw=created)

    def job_status(self, job_id: str) -> JobResult:
        if self.mock:
            return JobResult(job_id=job_id, phase=JobPhase.COMPLETED, amount_usdc=0.0, raw={"mock": True})
        hist = self._run("job", "history", "--job-id", job_id)
        phase_raw = str(hist.get("status") or hist.get("phase") or "open").lower()
        try:
            phase = JobPhase(phase_raw)
        except ValueError:
            phase = JobPhase.OPEN
        return JobResult(
            job_id=job_id,
            phase=phase,
            provider=hist.get("provider"),
            amount_usdc=float(hist.get("budget") or hist.get("amount") or 0.0),
            raw=hist,
        )


def _environ() -> dict[str, str]:
    import os

    return dict(os.environ)
