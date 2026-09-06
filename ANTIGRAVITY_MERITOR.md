# 🛡️ ANTIGRAVITY_MERITOR - Persistent Project Context Directive

> **⚠️ SUPERSEDED PLANNING DOC (authored 2026-08-20).** The source of truth is
> now [README.md](README.md), the code under [`meritor/`](meritor/), and
> [`docs/`](docs/). Three claims below were wrong on contact with the real
> stack and are corrected in code, not here:
> 1. **Sibyl Memory is not a hosted API.** It is a local SQLite SDK
>    (`sibyl-memory-client`) - no API key, no base URL, no network. Any mention
>    of `SIBYL_API_KEY` / credentials below is void.
> 2. **The multiplier is ordinal (+15% first stack, +10% second, cap x1.25), not
>    per-partner.** The max Builder Score is `110 × 1.25 = 137.5`, not 126.25.
> 3. **The gate is pass/fail and awards no points.** "40/40 on the gate" conflates
>    the pass/fail gate with the separately-scored 40% memory criterion.
> Kept in-repo, unedited below this line, as an honest record of the plan.

---


> **Project Name:** MERITOR  
> **Target Hackathon:** Sibyl Labs Hackathon ($10,000 USDC + Network School Residency)  
> **Registration Window:** Aug 16 – Aug 31, 2026  
> **Build Window:** Sep 1 – Sep 10, 2026  
> **Core Memory Layer:** Sibyl Memory (Load-Bearing 40% Gate)  
> **Verified Partner Stack 1:** Base (+15% Multiplier - x402 & Smart Contracts)  
> **Verified Partner Stack 2:** Virtuals Protocol (+10% Multiplier - ACP Agent Runtime)  
> **Target Multiplier:** x1.25 Capped Maximum  

---

## 📌 Core Directives for Meritor Development

1. **Master Spec Source of Truth:**  
   Always consult [MERITOR_PROJECT_SPEC.md](file:///Users/mrnetwork/Meritor/MERITOR_PROJECT_SPEC.md).

2. **Technical Architecture Guidelines:**
   - **Sibyl Memory (Load-Bearing Gate):** Must be on the critical path. Deleting Sibyl Memory MUST cause the credit decision engine to fail.
   - **Fresh Session Recall:** The demo video and codebase must showcase a fresh session reading state written in a prior session to change an onchain decision.
   - **Base Stack Integration:** Execute Base onchain wallet operations, smart contract escrows, or x402 micropayments.
   - **Virtuals Protocol Integration:** Coordinate agent runtimes using Virtuals ACP (Agent Communication Protocol).

3. **Submission Requirements Checklist:**
   - Public GitHub repository with Apache 2.0 or MIT License.
   - `README.md` with complete setup instructions + memory implementation note.
   - 2 to 5 minute demo video featuring the unedited fresh-session recall beat.
   - Two public posts tagging `@sibylcap`, `@base`, and `@virtuals_io`.

4. **Repository Key Files:**
   - Master Blueprint: `MERITOR_PROJECT_SPEC.md`
   - Directive File: `ANTIGRAVITY_MERITOR.md`
   - Skill Instructions: `.agents/skills/meritor-sibyl/SKILL.md`
