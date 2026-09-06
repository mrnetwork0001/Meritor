# 🛡️ MERITOR - Autonomous Dynamic Risk & Credit Memory Layer for Onchain AI Agent Fleets

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


> **Sibyl Labs Hackathon Master Blueprint ($10,000 USDC + Network School Residency)**  
> **Target Track:** Sibyl Memory (Load-Bearing Gate) + Base Stack (+15%) + Virtuals Protocol (+10%)  
> **Target Multiplier:** x1.25 Capped Maximum  
> **Registration Window:** Aug 16 – Aug 31, 2026  
> **Build Window:** Sep 1 – Sep 10, 2026  
> **License:** Apache 2.0 Open Source  
> **Author:** Ifeanyichukwu Onwo (`mrnetwork`)  

---

## 📌 Executive Summary

**Meritor** is an **Autonomous Dynamic Risk & Credit Memory Layer for Onchain AI Agent Fleets** built on **Sibyl Memory**, **Base**, and **Virtuals Protocol**.

Currently, Web3 AI agents operating on Base and Virtuals Protocol cannot extend uncollateralized execution capital, grant premium API access, or delegate high-value jobs because agents lack a persistent, load-bearing memory of counterparty reliability. Every new session forces agents to treat counterparties as unknown 0-trust entities requiring 150%+ over-collateralization.

**Meritor solves this by turning Sibyl Memory into a load-bearing risk & credit engine:**
1. **Dynamic Credit Memory (Sibyl Memory Layer):** Persists multi-session SLA completion rates, repayment velocity, dispute records, and credit scores across fresh sessions.
2. **Onchain Base Settlement (Base Stack - +15% Multiplier):** Releases onchain loan disbursements, streams x402 micropayments, and enforces smart contract vault escrows on Base.
3. **Agent Runtime Coordination (Virtuals Protocol - +10% Multiplier):** Manages Agent Communication Protocol (ACP) job dispatches and agent-native runtime execution.

---

## 🎯 Pass/Fail Gate Proof & Score Math (Targeting 1st Place)

### 🚨 The Gate: "Memory Must Be Load-Bearing" (40% of Rubric)
* **The Litmus Test:** Deleting the Sibyl Memory layer causes the core Meritor risk engine to collapse. Without Sibyl Memory, Meritor cannot calculate dynamic credit scores, forgets all repayment histories, defaults to rejecting uncollateralized loan requests, and halts the multi-agent credit economy. **Passes the gate with 40/40!**
* **Fresh Session Recall Beat:** In Session 1, Agent Alpha borrows 50 USDC on Base and repays on time. In a **fresh Session 2**, Meritor recalls Agent Alpha's flawless memory profile, upgrades them to a 0% collateral tier, and releases Base x402 funds.

### 📊 Score Math for Leaderboard Dominance
$$\text{Builder Score} = (\text{Rubric [100]} + \text{PMF Bonus [10]}) \times \text{Multiplier [1.25]} = \mathbf{126.25 \text{ Max}}$$

---

## 🏗️ System Architecture & Multi-Agent Workflow

```
                                  ┌──────────────────────────────┐
                                  │     SIBYL DYNAMIC MEMORY     │
                                  │   (Load-Bearing Risk Engine) │
                                  └──────────────┬───────────────┘
                                                 │
                                                 │ Reads/Mutates Credit State
                                                 ▼
                                 ┌───────────────────────────────┐
                                 │     Meritor Multi-Agent Fleet │
                                 └───────────────┬───────────────┘
                                                 │
                   ┌─────────────────────────────┼─────────────────────────────┐
                   │                             │                             │
                   ▼                             ▼                             ▼
       [ Agent 1: Risk Auditor ]    [ Agent 2: Virtuals ACP ]     [ Agent 3: Base Settler ]
       • Mutates Credit Scores      • ACP Job Dispatch            • Base x402 Micropayments
       • Evaluates SLA History      • Virtuals Agent Runtime      • Base Smart Contract Vaults
                   │                             │                             │
                   └─────────────────────────────┼─────────────────────────────┘
                                                 │
                                                 │ Executes Verified Multiplier Stack (x1.25)
                                                 ▼
                                 ┌───────────────────────────────┐
                                 │ Onchain Base Settlement +     │
                                 │  Fresh Session Recall Proof   │
                                 └───────────────────────────────┘
```

---

## 📋 Hackathon Submission Checklist & Answers

### 1. PROJECT NAME
`Meritor`

### 2. ELEVATOR PITCH (1–2 Sentences)
`Meritor is an autonomous dynamic risk and credit memory layer built on Sibyl Memory, Base, and Virtuals Protocol that allows AI agent fleets to build load-bearing credit scores across sessions and unlock 0% collateral Base x402 executions.`

### 3. DETAILED PROJECT DESCRIPTION
`Web3 AI agents are crippled by a lack of persistent memory. Because agents forget counterparty performance between sessions, onchain lending and job delegation require 150%+ over-collateralization. Meritor turns Sibyl Memory into a load-bearing credit engine for agent fleets on Base and Virtuals Protocol. Agent 1 (Risk Auditor) reads and mutates Sibyl Memory to calculate creditworthiness based on historical SLA completion and repayment velocity. Agent 2 (Virtuals ACP) manages agent runtime coordination. Agent 3 (Base Settler) releases onchain Base x402 micropayments and manages escrow vaults. When Sibyl Memory is deleted, Meritor forgets all credit histories and defaults to rejecting uncollateralized requests. In a fresh session, Meritor recalls a counterparty's past performance, upgrading them to zero-collateral loan tiers.`

### 4. MEMORY IMPLEMENTATION NOTE (LOAD-BEARING PROOF)
`Sibyl Memory is on Meritor's critical path:
1. Write Path: After every Base transaction or Virtuals ACP job, Meritor writes repayment timestamps, SLA scores, and dispute flags to Sibyl Memory.
2. Read Path: Upon fresh session initialization, Meritor queries Sibyl Memory for the counterparty's credit profile.
3. Deletion Test: Removing Sibyl Memory breaks Meritor's credit decision tree, forcing all requests to default to 0-trust rejection.`

### 5. TECH STACK
`Sibyl Memory API, Base Smart Contracts, Base x402 Micropayments, Virtuals Protocol ACP SDK, Python 3.11, Next.js 14, Tailwind CSS, TypeScript, Apache 2.0 License.`

---

## ⏱️ Technical Execution Plan (Sep 1 – Sep 10)

- **Phase 1 (Sep 1 – Sep 3):** Setup Sibyl Memory client (`sibyl_memory_client.py`) & define credit mutation schema.
- **Phase 2 (Sep 4 – Sep 6):** Integrate Base x402 payment contracts & Virtuals Protocol ACP agent runtime.
- **Phase 3 (Sep 7 – Sep 8):** Build Next.js 14 dashboard visualizer & test Fresh Session Recall.
- **Phase 4 (Sep 9 – Sep 10):** Record 3-minute video demo (featuring the unedited live memory deletion beat), publish social posts, and submit.
