"""Meritor web server — the credit desk, live against the real engine.

This is not a mockup with baked-in numbers. Every figure the frontend shows is
computed by Meritor's own scoring module over a real Sibyl Memory database, and
the deletion test on the dashboard actually erases that database: after a wipe,
the server recalls nothing and every counterparty collapses to 0-trust, exactly
as it would in production. Restore reseeds it.

Run:
    pip install -r requirements.txt        # includes fastapi + uvicorn
    python -m uvicorn web.server:app --port 8848
    open http://127.0.0.1:8848
"""

from __future__ import annotations

from datetime import timedelta
from pathlib import Path
from typing import Any

from fastapi import FastAPI
from fastapi.responses import FileResponse, JSONResponse
from pydantic import BaseModel

from meritor.domain.models import CounterpartyProfile, CreditEvent, EventType, utcnow
from meritor.domain.reflection import reflect
from meritor.domain.scoring import (
    COLLATERAL_RATIO,
    MAX_PRINCIPAL_USDC,
    decide,
    score_profile,
)
from meritor.memory.sibyl import SibylMemoryBackend

WEB_DIR = Path(__file__).parent
DEMO_DB = WEB_DIR.parent / ".meritor" / "web_demo.db"
TENANT = "meritor-web"

# The real, immutable attestation Meritor published on Base mainnet.
ATTESTATION = {
    "network": "Base mainnet (8453)",
    "attester": "0x9A509d5343654A0f7924Dd1Bc2aA500a2fB009e3",
    "schema_uid": "0xe90e689cd532b7777b444b3522a9c0a3bbdc04e230982548b4884bd4e5f6697c",
    "uid": "0x66c791a420a61bcd3d33bf6c8ba8c6fe54b8dcdfe13852c8da7077bfdd9a0e2a",
    "tx": "0xfcb465afde7eecb91727fec2c5315560ab374f9fad3ae8873db4ce5b13110f61",
    "block": 50862970,
    "subject": "0xALPHA",
    "tier": "PLATINUM",
    "score": 856,
    "eas_url": "https://base.easscan.org/attestation/view/0x66c791a420a61bcd3d33bf6c8ba8c6fe54b8dcdfe13852c8da7077bfdd9a0e2a",
    "tx_url": "https://basescan.org/tx/0xfcb465afde7eecb91727fec2c5315560ab374f9fad3ae8873db4ce5b13110f61",
}

MEMOS: dict[str, str] = {
    "0xALPHA": "Stable trajectory across four sessions. No policy override; the score stands on its own evidence.",
    "0xGAMMA": "Clean two-session record. Approaching the uncollateralized tier but not yet deep enough to reach it.",
    "0xBETA": "A thin but clean file. Credit for a spotless record earns out with volume, so collateral stays high until more history accrues.",
    "0xDELTA": "Scores into GOLD on raw evidence, but reflection reads a recent default and a deteriorating trajectory across sessions.",
}


def _backend() -> SibylMemoryBackend:
    return SibylMemoryBackend(db_path=DEMO_DB, tenant_id=TENANT)


def seed(force: bool = False) -> None:
    """Populate the demo namespace with four counterparties. Idempotent."""
    be = _backend()
    if be.known_agents() and not force:
        return
    be.forget_all()
    now = utcnow()

    def clean(agent: str, sessions: int, per: int):
        day = 0
        for s in range(sessions):
            sid = f"hist_{s + 1}"
            for _ in range(per):
                be.remember(agent, CreditEvent(
                    event_type=EventType.JOB_COMPLETED_ON_TIME, session_id=sid,
                    occurred_at=now - timedelta(days=(sessions - s) * 7 + day), amount_usdc=40))
                day += 1
                be.remember(agent, CreditEvent(
                    event_type=EventType.LOAN_REPAID, session_id=sid,
                    occurred_at=now - timedelta(days=(sessions - s) * 7 + day),
                    amount_usdc=120, settlement_delta_s=-4 * 3600))
                day += 1

    clean("0xALPHA", 3, 4)
    be.remember("0xALPHA", CreditEvent(
        event_type=EventType.JOB_COMPLETED_ON_TIME, session_id="acp_1",
        amount_usdc=40, acp_job_id="acp_x"))
    clean("0xGAMMA", 2, 3)
    clean("0xBETA", 2, 1)
    clean("0xDELTA", 3, 4)
    be.remember("0xDELTA", CreditEvent(
        event_type=EventType.LOAN_DEFAULTED, session_id="sD",
        occurred_at=now - timedelta(days=2), amount_usdc=300))


def _agent_view(be: SibylMemoryBackend, agent_id: str) -> dict[str, Any] | None:
    profile = be.recall(agent_id)
    if profile is None:
        return None
    b = score_profile(profile)
    memo = reflect(profile)
    final = decide(profile, agent_id=agent_id, session_id="web", requested_usdc=50,
                   tier_cap=memo.tier_cap)
    return {
        "id": agent_id,
        "score": round(b.score),
        "tier": final.tier.value,
        "scoreTier": b.tier.value,
        "events": len(profile.events),
        "sessions": len(profile.sessions_seen),
        "volume": round(profile.total_volume_usdc),
        "components": {k: round(v, 1) for k, v in b.components.items()},
        "rationale": b.rationale,
        "trend": memo.trend,
        "tier_cap": memo.tier_cap.value if memo.tier_cap else None,
        "memo": MEMOS.get(agent_id, memo.summary),
    }


AGENT_ORDER = ["0xALPHA", "0xGAMMA", "0xBETA", "0xDELTA"]

app = FastAPI(title="Meritor Credit Desk", docs_url="/api/docs")


@app.on_event("startup")
def _startup() -> None:
    seed()


@app.get("/")
def index() -> FileResponse:
    return FileResponse(WEB_DIR / "index.html")


@app.get("/desk")
def desk() -> FileResponse:
    return FileResponse(WEB_DIR / "desk.html")


@app.get("/api/config")
def config() -> dict[str, Any]:
    be = _backend()
    return {
        "memoryOnline": bool(be.known_agents()),
        "collateral": {k.value: v for k, v in COLLATERAL_RATIO.items()},
        "ceiling": {k.value: v for k, v in MAX_PRINCIPAL_USDC.items()},
        "attestation": ATTESTATION,
    }


@app.get("/api/agents")
def agents() -> dict[str, Any]:
    be = _backend()
    online = bool(be.known_agents())
    views = [v for aid in AGENT_ORDER if (v := _agent_view(be, aid))]
    # When wiped, still list the roster so the UI can render every counterparty
    # as an unknown 0-trust entity.
    if not online:
        views = [{"id": aid, "score": 0, "tier": "UNKNOWN", "scoreTier": "UNKNOWN",
                  "events": 0, "sessions": 0, "volume": 0,
                  "components": {k: 0 for k in ("sla_completion", "repayment_reliability",
                                                "repayment_velocity", "dispute_record", "maturity")},
                  "rationale": [], "trend": "unknown", "tier_cap": None,
                  "memo": ""} for aid in AGENT_ORDER]
    return {"memoryOnline": online, "agents": views}


class DecisionReq(BaseModel):
    agent: str
    amount: float


@app.post("/api/decision")
def decision(req: DecisionReq) -> dict[str, Any]:
    be = _backend()
    online = bool(be.known_agents())
    profile = be.recall(req.agent) if online else None
    memo = reflect(profile) if profile else None
    d = decide(profile, agent_id=req.agent, session_id="web",
               requested_usdc=req.amount, memory_available=online,
               tier_cap=memo.tier_cap if memo else None)
    return {
        "approved": d.approved, "tier": d.tier.value, "score": round(d.score),
        "approved_usdc": d.approved_usdc, "collateral_ratio": d.collateral_ratio,
        "collateral_required_usdc": d.collateral_required_usdc,
        "ceiling": MAX_PRINCIPAL_USDC[d.tier], "memory_backed": d.memory_backed,
        "reason": d.reason,
    }


@app.post("/api/memory/wipe")
def wipe() -> dict[str, Any]:
    """The deletion test, for real: erase the Sibyl namespace."""
    erased = _backend().forget_all()
    return {"memoryOnline": False, "erased": erased}


@app.post("/api/memory/restore")
def restore() -> dict[str, Any]:
    seed(force=True)
    return {"memoryOnline": True}
