# Demo shot-list — the 2 to 5 minute video

The rules require an **unedited fresh-session recall beat**: one continuous
segment where a fresh session recalls state written earlier and it changes an
onchain decision, with a live clock or commit hash visible in frame. Keep that
one take uncut. Everything else can be cut around it.

Keep a terminal clock visible the whole time:
```bash
# a live UTC clock in the corner of the terminal (or show `git rev-parse --short HEAD`)
while true; do printf "\r  %s UTC " "$(date -u +%H:%M:%S)"; sleep 1; done
```

## Beat 1 — the problem (20s, spoken over the landing page)
Open `http://127.0.0.1:8848`. Toggle the hero ticket: **Memory online → APPROVED,
0% collateral**; **Memory erased → DENIED, 150%**. "An agent that forgets has to
demand collateral from everyone. Meritor gives it a memory that changes what it
will pay."

## Beat 2 — the fresh-session recall beat  ⚠️ ONE UNCUT TAKE, clock visible
Run the demo and narrate. Every block is a separate process — say so.
```bash
make demo    # or ./demo/fresh_session_demo.sh
```
Call out on screen:
- **Session A** — 0xBETA (never seen) asks for $50 → **DENIED, 150%, memory-backed: false**.
- **Session A** — 0xALPHA asks the same $50 → **APPROVED, 0% collateral** (recalled history).
- **Session B, fresh process** — 0xBETA returns → **APPROVED, 120%**: the record written last session changed the decision. *This transition is the beat — do not cut here.*
- **Time-travel** — `as-of` shows GOLD ten days ago, PLATINUM today.

## Beat 3 — the deletion test (30s)
```bash
meritor wipe --yes
meritor request 0xALPHA 50      # same agent, same request
```
→ **DENIED, UNKNOWN, 150%.** "Same agent, same request. The only variable was
memory. No fallback quietly kept working — that's what load-bearing means."

## Beat 4 — real money on Base (30s)
Show the live EAS attestation resolving in the browser:
`https://base.easscan.org/attestation/view/0x66c791a420a61bcd3d33bf6c8ba8c6fe54b8dcdfe13852c8da7077bfdd9a0e2a`
"Meritor didn't just decide — it published 0xALPHA's tier to Base as a portable
attestation other agents can verify. The private reasoning stays in memory; the
result goes onchain."

## Beat 5 — close (15s)
Back to the desk. "Sibyl Memory for the reasoning, Base for settlement, Virtuals
ACP for the jobs that feed the record. Delete the memory and none of it works.
That's Meritor."

## Record checklist
- [ ] Terminal clock or commit hash visible during Beat 2
- [ ] Beat 2 recorded as one continuous, unedited segment
- [ ] Audio explains "separate process" at each session boundary
- [ ] Total length 2:00–5:00
