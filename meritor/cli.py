"""Meritor CLI.

Every command is a separate process invocation on purpose. The demo's claim is
that memory survives across sessions, and the only honest way to show that is
to let the process die between beats.
"""

from __future__ import annotations

import argparse
import sys

from .config import load_settings
from .domain.models import CreditEvent, EventType
from .engine import CreditSession
from .memory.base import MemoryUnavailable

RULE = "─" * 74


def _banner(session: CreditSession) -> None:
    driver = session.settings.memory_driver if session.settings else "?"
    print(RULE)
    print(f" MERITOR  ·  session {session.session_id}")
    print(f" memory driver: {driver}  ({session.memory.name})")
    print(RULE)


def cmd_status(args: argparse.Namespace) -> int:
    session = CreditSession.open(session_id=args.session_id)
    _banner(session)
    healthy = session.memory.health()
    print(f" backend reachable : {'yes' if healthy else 'NO'}")
    if not healthy:
        print("\n Memory layer is down. Every credit decision this session will")
        print(" fail closed to 0-trust rejection.")
        return 1
    agents = session.memory.known_agents()
    print(f" counterparties    : {len(agents)}")
    for agent_id in agents:
        profile = session.recall(agent_id)
        assert profile is not None
        print(f"   · {agent_id}  {len(profile.events):>3} events  "
              f"{len(profile.sessions_seen)} session(s)")
    return 0


def cmd_request(args: argparse.Namespace) -> int:
    session = CreditSession.open(session_id=args.session_id)
    _banner(session)
    print(f" {args.agent} requests ${args.amount:,.2f} USDC\n")

    decision = session.underwrite(args.agent, args.amount)

    if decision.breakdown:
        print(decision.breakdown.explain())
        print()

    verdict = "APPROVED" if decision.approved else "DENIED"
    print(f" DECISION          : {verdict}")
    print(f" tier              : {decision.tier.value}")
    print(f" principal         : ${decision.approved_usdc:,.2f}")
    print(f" collateral req'd  : ${decision.collateral_required_usdc:,.2f} "
          f"({decision.collateral_ratio:.0%})")
    print(f" memory-backed     : {decision.memory_backed}")
    print(f"\n {decision.reason}")

    if decision.approved and decision.collateral_ratio == 0.0:
        print("\n → UNCOLLATERALIZED RELEASE. This is only possible because a")
        print("   previous session's record was recalled in this fresh one.")

    if args.settle:
        print(f"\n{RULE}")
        print(" BASE SETTLEMENT")
        print(RULE)
        settlement = _settle(session, decision, args.settle, dry_run=args.dry_run)
        print(settlement.render())

    return 0 if decision.approved else 2


def _settle(session, decision, to_address: str, *, dry_run: bool):
    """Release the authorized principal on Base, then record it in memory.

    The write-back is the point. An onchain disbursement that never re-enters
    the credit record would leave the next session underwriting blind against
    money it had already lent.
    """
    from .agents.base_settler import BaseSettler
    from .config import load_settings

    cfg = session.settings or load_settings()
    settler = BaseSettler(
        rpc_url=cfg.base_rpc_url,
        chain_id=cfg.base_chain_id,
        private_key=cfg.base_private_key,
        usdc_address=cfg.usdc_address,
    )
    settlement = settler.disburse(to_address, decision.approved_usdc, dry_run=dry_run)

    if settlement.is_onchain:
        session.record(decision.agent_id, CreditEvent(
            event_type=EventType.LOAN_DISBURSED,
            session_id=session.session_id,
            amount_usdc=settlement.amount_usdc,
            tx_hash=settlement.tx_hash,
            note=f"tier={decision.tier.value} collateral={decision.collateral_ratio:.0%}",
        ))
        print("\n → Disbursement written back to memory. The next session"
              "\n   underwrites knowing this exposure is outstanding.")
    return settlement


def cmd_work(args: argparse.Namespace) -> int:
    outcome = {
        "on_time": EventType.JOB_COMPLETED_ON_TIME,
        "late": EventType.JOB_COMPLETED_LATE,
        "failed": EventType.JOB_FAILED,
    }[args.outcome]
    session = CreditSession.open(session_id=args.session_id)
    _banner(session)
    profile = session.record(
        args.agent,
        CreditEvent(
            event_type=outcome,
            session_id=session.session_id,
            amount_usdc=args.amount,
            acp_job_id=args.acp_job_id,
            note=args.note or "",
        ),
    )
    print(f" recorded {outcome.value} for {args.agent}")
    print(f" profile now holds {len(profile.events)} events across "
          f"{len(profile.sessions_seen)} session(s)")
    return 0


def cmd_repay(args: argparse.Namespace) -> int:
    session = CreditSession.open(session_id=args.session_id)
    _banner(session)
    profile = session.record(
        args.agent,
        CreditEvent(
            event_type=EventType.LOAN_DEFAULTED if args.default else EventType.LOAN_REPAID,
            session_id=session.session_id,
            amount_usdc=args.amount,
            settlement_delta_s=-args.early_hours * 3600.0,
            tx_hash=args.tx_hash,
        ),
    )
    what = "DEFAULT" if args.default else "repayment"
    print(f" recorded {what} of ${args.amount:,.2f} for {args.agent}")
    print(f" profile now holds {len(profile.events)} events across "
          f"{len(profile.sessions_seen)} session(s)")
    return 0


def cmd_explain(args: argparse.Namespace) -> int:
    session = CreditSession.open(session_id=args.session_id)
    _banner(session)
    print(session.explain(args.agent))
    return 0


def cmd_seed(args: argparse.Namespace) -> int:
    """Replay prior operating history for a counterparty.

    A deployed Meritor would already hold weeks of settlement data. Rather than
    pretend a two-minute demo accumulates that live, this command replays it
    explicitly: backdated events, distinct historical session ids, printed as
    it writes so nothing is smuggled in. The live session boundary in the demo
    is still crossed for real.
    """
    from datetime import timedelta

    from .domain.models import utcnow

    session = CreditSession.open(session_id=args.session_id)
    _banner(session)
    print(f" replaying {args.sessions} historical session(s) of settled activity"
          f" for {args.agent}\n")

    now = utcnow()
    written = 0
    for s_idx in range(args.sessions):
        hist_session = f"hist_{s_idx + 1:02d}"
        days_ago = (args.sessions - s_idx) * 7
        for j in range(args.per_session):
            offset = timedelta(days=days_ago, hours=j * 3)
            session.memory.remember(args.agent, CreditEvent(
                event_type=EventType.JOB_COMPLETED_ON_TIME,
                session_id=hist_session,
                occurred_at=now - offset,
                amount_usdc=40.0,
                acp_job_id=f"acp_hist_{s_idx+1}_{j+1}",
            ))
            session.memory.remember(args.agent, CreditEvent(
                event_type=EventType.LOAN_REPAID,
                session_id=hist_session,
                occurred_at=now - offset + timedelta(hours=1),
                amount_usdc=120.0,
                settlement_delta_s=-4.0 * 3600.0,
            ))
            written += 2
        print(f"   {hist_session}: {args.per_session} jobs + {args.per_session} "
              f"repayments, ~{days_ago}d ago")

    print(f"\n wrote {written} backdated events across {args.sessions} historical sessions")
    print(" (decay is applied at scoring time, so older sessions count for less)")
    return 0


def cmd_reflect(args: argparse.Namespace) -> int:
    """Consolidate a counterparty's journal into a durable credit memo."""
    session = CreditSession.open(session_id=args.session_id)
    _banner(session)
    memo = session.reflect(args.agent)
    if memo is None:
        print(f" no credit memory for {args.agent} - nothing to reflect on.")
        return 2
    print(f" reflection over {memo.consolidated_events} events for {args.agent}\n")
    print(f" trend            : {memo.trend}")
    print(f" volatility       : ±{memo.volatility_hours:.1f}h settlement timing")
    print(f" recent default   : {memo.recent_default}")
    print(f" tier cap         : {memo.tier_cap.value if memo.tier_cap else 'none'}")
    print(f"\n {memo.summary}")
    if memo.tier_cap:
        print("\n → This memo is durable. The next fresh session will underwrite")
        print("   under this cap without recomputing the trend.")
    return 0


def cmd_attest(args: argparse.Namespace) -> int:
    """Publish a counterparty's recalled credit tier to Base as an EAS attestation.

    The private reasoning stays in Sibyl Memory; the result becomes a portable,
    verifiable onchain claim other agents can consume. The attestation UID is
    written back to memory as provenance.
    """
    from datetime import timezone

    from .agents.eas_attester import EASAttester
    from .config import load_settings
    from .domain.scoring import score_profile

    session = CreditSession.open(session_id=args.session_id)
    _banner(session)
    profile = session.recall(args.agent)
    if profile is None or not profile.events:
        print(f" no credit memory for {args.agent} - nothing to attest.")
        return 2
    b = score_profile(profile)
    print(f" attesting: {args.agent} → {b.tier.value} ({b.score:.0f}/1000)\n")

    cfg = session.settings or load_settings()
    attester = EASAttester(
        rpc_url=cfg.base_rpc_url, chain_id=cfg.base_chain_id,
        private_key=cfg.base_private_key,
    )
    assessed_at = int(b.computed_at.replace(tzinfo=timezone.utc).timestamp())
    att = attester.attest_credit(
        args.agent, int(round(b.score)), b.tier.value, b.evidence_events,
        b.sessions_observed, assessed_at,
        recipient=args.agent if args.agent.startswith("0x") and len(args.agent) == 42 else None,
        dry_run=args.dry_run,
    )
    print(att.render())

    if att.is_onchain:
        session.record(args.agent, CreditEvent(
            event_type=EventType.LOAN_DISBURSED, session_id=session.session_id,
            amount_usdc=0.0, tx_hash=att.tx_hash,
            note=f"EAS attestation {att.uid} tier={att.tier}"))
        print("\n → Attestation UID written back to memory as provenance.")
    return 0


def cmd_acp_job(args: argparse.Namespace) -> int:
    """Dispatch a Virtuals ACP job and record its outcome as a credit event.

    This is where Meritor's SLA history comes from: reliability observed on the
    Agent Commerce Protocol feeds the credit score that gates money on Base.
    """
    from .agents.acp_client import ACPClient

    session = CreditSession.open(session_id=args.session_id)
    _banner(session)
    client = ACPClient(testnet=not args.mainnet, mock=args.mock)
    ok, why = client.available()
    if not ok:
        print(f" ACP unavailable: {why}")
        return 1
    mode = "MOCK" if args.mock else ("mainnet" if args.mainnet else "testnet")
    print(f" ACP mode: {mode}\n")

    if args.provider:
        provider = args.provider
    else:
        print(f" browsing ACP for '{args.offering}'...")
        found = client.browse(args.offering, top_k=5)
        if not found:
            print(" no providers found for that offering.")
            return 2
        provider = found[0].get("id") or found[0].get("address")
        print(f" selected provider: {provider}")

    print(f" dispatching job to {provider} (budget ${args.budget:,.2f})...")
    job = client.dispatch(provider, args.offering, args.budget)
    print(f" job {job.job_id} -> {job.phase.value}")

    event = job.to_credit_event(session.session_id, late=args.late)
    if event is None:
        print(" job is not in a terminal state yet; no credit event recorded.")
        return 0
    profile = session.record(args.counterparty, event)
    print(f"\n recorded {event.event_type.value} for {args.counterparty}")
    print(f" profile now holds {len(profile.events)} events across "
          f"{len(profile.sessions_seen)} session(s)")
    return 0


def cmd_as_of(args: argparse.Namespace) -> int:
    """Replay the credit score to a past instant from the journal."""
    from datetime import timedelta

    from .domain.models import utcnow
    from .domain.scoring import score_profile

    session = CreditSession.open(session_id=args.session_id)
    _banner(session)
    backend = session.memory
    if not hasattr(backend, "profile_as_of"):
        print(" time-travel requires the Sibyl driver (MEMORY_DRIVER=sibyl)")
        return 1

    instant = utcnow() - timedelta(days=args.days_ago)
    print(f" replaying {args.agent}'s record as it stood {args.days_ago} day(s) ago"
          f"  ({instant:%Y-%m-%d %H:%M UTC})\n")

    past = backend.profile_as_of(args.agent, instant)
    if past is None:
        print(" no record existed at that instant.")
        return 0
    print(score_profile(past, now=instant).explain())

    now_profile = backend.recall(args.agent)
    if now_profile:
        then = score_profile(past, now=instant)
        current = score_profile(now_profile)
        print(f"\n then: {then.score:>6.0f}/1000  {then.tier.value}")
        print(f" now : {current.score:>6.0f}/1000  {current.tier.value}")
        if then.tier is not current.tier:
            print("\n → The decision Meritor would have made then is not the one it")
            print("   makes now. Both are defensible, because both are reconstructible.")
    return 0


def cmd_journal(args: argparse.Namespace) -> int:
    """Print the append-only credit journal."""
    from datetime import timedelta

    from .domain.models import utcnow

    session = CreditSession.open(session_id=args.session_id)
    _banner(session)
    backend = session.memory
    if not hasattr(backend, "journal"):
        print(" the journal requires the Sibyl driver (MEMORY_DRIVER=sibyl)")
        return 1
    since = utcnow() - timedelta(days=args.days) if args.days else None
    rows = backend.journal(since=since, limit=args.limit)
    print(f" {len(rows)} journal entr{'y' if len(rows) == 1 else 'ies'}\n")
    for row in rows:
        acted = row.get("acted") or []
        ts = row.get("ts") or row.get("created_at") or ""
        for line in (acted if isinstance(acted, list) else [acted]):
            print(f"   {str(ts)[:19]}  {line}")
    return 0


def cmd_wipe(args: argparse.Namespace) -> int:
    """The deletion test."""
    session = CreditSession.open(session_id=args.session_id)
    _banner(session)
    if not args.yes:
        print(" refusing to wipe without --yes")
        return 1
    n = session.memory.forget_all()
    print(f" ERASED {n} counterparty profile(s) from the memory layer.")
    print("\n Meritor now has no basis to price risk for anyone. Re-run the")
    print(" same credit request to see the engine collapse to 0-trust.")
    return 0


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="meritor", description=__doc__)
    p.add_argument(
        "--session-id",
        default=None,
        help="logical session id; also read from MERITOR_SESSION_ID. Several "
             "commands sharing one id count as one session in the credit record.",
    )
    sub = p.add_subparsers(dest="command", required=True)

    sub.add_parser("status", help="backend health and known counterparties").set_defaults(func=cmd_status)

    r = sub.add_parser("request", help="underwrite a credit request")
    r.add_argument("agent")
    r.add_argument("amount", type=float)
    r.add_argument("--settle", metavar="ADDRESS", default=None,
                   help="release the approved principal to this Base address")
    r.add_argument("--dry-run", action="store_true",
                   help="price and route the settlement without broadcasting")
    r.set_defaults(func=cmd_request)

    w = sub.add_parser("work", help="record an ACP job outcome")
    w.add_argument("agent")
    w.add_argument("--outcome", choices=["on_time", "late", "failed"], default="on_time")
    w.add_argument("--amount", type=float, default=0.0)
    w.add_argument("--acp-job-id", default=None)
    w.add_argument("--note", default=None)
    w.set_defaults(func=cmd_work)

    rp = sub.add_parser("repay", help="record a loan settlement")
    rp.add_argument("agent")
    rp.add_argument("amount", type=float)
    rp.add_argument("--early-hours", type=float, default=0.0)
    rp.add_argument("--default", action="store_true", help="record a default instead")
    rp.add_argument("--tx-hash", default=None)
    rp.set_defaults(func=cmd_repay)

    e = sub.add_parser("explain", help="show a counterparty's score breakdown")
    e.add_argument("agent")
    e.set_defaults(func=cmd_explain)

    rf = sub.add_parser("reflect", help="consolidate the journal into a credit memo")
    rf.add_argument("agent")
    rf.set_defaults(func=cmd_reflect)

    at = sub.add_parser("attest", help="publish a recalled tier to Base via EAS")
    at.add_argument("agent")
    at.add_argument("--dry-run", action="store_true", help="show the payload without broadcasting")
    at.set_defaults(func=cmd_attest)

    aj = sub.add_parser("acp-job", help="dispatch a Virtuals ACP job -> credit event")
    aj.add_argument("counterparty", help="the agent whose credit record this job updates")
    aj.add_argument("--offering", default="risk-audit")
    aj.add_argument("--provider", default=None, help="skip browse and dispatch to this provider")
    aj.add_argument("--budget", type=float, default=10.0)
    aj.add_argument("--late", action="store_true", help="record completion as late")
    aj.add_argument("--mock", action="store_true", help="run the lifecycle offline")
    aj.add_argument("--mainnet", action="store_true", help="use ACP mainnet instead of testnet")
    aj.set_defaults(func=cmd_acp_job)

    ao = sub.add_parser("as-of", help="replay a counterparty's score to a past instant")
    ao.add_argument("agent")
    ao.add_argument("--days-ago", type=float, default=3.0)
    ao.set_defaults(func=cmd_as_of)

    jl = sub.add_parser("journal", help="print the append-only credit journal")
    jl.add_argument("--days", type=float, default=None)
    jl.add_argument("--limit", type=int, default=100)
    jl.set_defaults(func=cmd_journal)

    sd = sub.add_parser("seed", help="replay backdated operating history")
    sd.add_argument("agent")
    sd.add_argument("--sessions", type=int, default=3)
    sd.add_argument("--per-session", type=int, default=4)
    sd.set_defaults(func=cmd_seed)

    wp = sub.add_parser("wipe", help="erase the memory namespace (deletion test)")
    wp.add_argument("--yes", action="store_true")
    wp.set_defaults(func=cmd_wipe)

    return p


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        return args.func(args)
    except MemoryUnavailable as exc:
        print(f"\n MEMORY UNAVAILABLE: {exc}", file=sys.stderr)
        print(" Meritor fails closed - no credit can be extended.", file=sys.stderr)
        return 3
    except RuntimeError as exc:
        print(f"\n CONFIG ERROR: {exc}", file=sys.stderr)
        return 4


if __name__ == "__main__":
    raise SystemExit(main())
