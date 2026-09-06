---
name: meritor-sibyl
description: Architecture, guidelines, Sibyl Memory specs, Base x402 integration, and Virtuals Protocol ACP rules for Meritor (Autonomous Dynamic Risk & Credit Memory Layer) built for the Sibyl Labs Hackathon.
---

# 🛡️ Meritor — Sibyl Labs Hackathon Skill & Execution Guide

Use this skill whenever working on, reviewing, or developing **Meritor** — the Autonomous Dynamic Risk & Credit Memory Layer for the Sibyl Labs Hackathon.

## 📌 Project Overview & Prize Targets
- **Target Event:** Sibyl Labs Hackathon
- **Registration Deadline:** Aug 31, 2026 (23:59 UTC)
- **Build Window:** Sep 1 – Sep 10, 2026
- **Prize Targets:** 1st Place ($4,000 USDC on Base + Network School Residency)
- **Core Stack:** Sibyl Memory (Load-Bearing Gate) + Base Stack (+15%) + Virtuals Protocol (+10%) = **x1.25 Multiplier Cap**

## 🏗️ Technical Architecture Rules

### 1. Sibyl Memory (Mandatory Load-Bearing Gate)
- Sibyl Memory MUST be on Meritor's critical path.
- Deleting the memory layer MUST cause the credit decision engine to fail.
- Implement fresh-session recall where state written in Session 1 dynamically alters onchain loan tiers in Session 2.

### 2. Base Partner Stack (+15% Multiplier)
- Execute onchain Base transactions: x402 micropayments, wallet operations, or smart contract vault escrows.

### 3. Virtuals Protocol Partner Stack (+10% Multiplier)
- Implement Virtuals ACP (Agent Communication Protocol) job dispatch and agent-native runtime execution.

## 🚨 Submission Checklist
- Public GitHub repo under OSI-approved license (Apache 2.0 / MIT).
- 2 to 5 minute demo video featuring the unedited fresh-session recall beat.
- `README.md` with memory implementation note and partner stack documentation.
- Two public posts tagging `@sibylcap`, `@base`, and `@virtuals_io`.
