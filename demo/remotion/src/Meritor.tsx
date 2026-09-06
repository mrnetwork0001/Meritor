import React from "react";
import { AbsoluteFill, useCurrentFrame, staticFile } from "remotion";
import { loadFont as loadFraunces } from "@remotion/google-fonts/Fraunces";
import { loadFont as loadMono } from "@remotion/google-fonts/IBMPlexMono";
import { loadFont as loadSans } from "@remotion/google-fonts/IBMPlexSans";

export const FPS = 30;
export const DURATION_S = 125;

const SERIF = loadFraunces("normal", { weights: ["400", "500", "600"], subsets: ["latin"] }).fontFamily;
const MONO = loadMono("normal", { weights: ["400", "500", "600"], subsets: ["latin"] }).fontFamily;
const SANS = loadSans("normal", { weights: ["400", "500", "600"], subsets: ["latin"] }).fontFamily;

// palette
const INK = "#f2e9d9", MID = "#b9ab97", DIM = "#8a7c67";
const BRASS = "#cf9a4e", CYAN = "#63dbe6", GOOD = "#4ec38a", BAD = "#f0576e";

// ---- helpers ----
const clamp = (x: number, a = 0, b = 1) => (x < a ? a : x > b ? b : x);
const lerp = (a: number, b: number, t: number) => a + (b - a) * t;
const easeOut = (t: number) => 1 - Math.pow(1 - t, 3);
const easeInOut = (t: number) => (t < 0.5 ? 4 * t * t * t : 1 - Math.pow(-2 * t + 2, 3) / 2);
const prog = (t: number, s: number, d: number) => easeOut(clamp((t - s) / d));
// fade in over [inS,inS+inD], out over [outS,outS+outD]
const band = (t: number, inS: number, inD: number, outS: number, outD: number) =>
  clamp(Math.min(clamp((t - inS) / inD), 1 - clamp((t - outS) / outD)));
const tr = (x = 0, y = 0, s = 1) => `translate(${x}px,${y}px) scale(${s})`;

// gauge geometry
const CX = 260, CY = 250, R = 205;
const polar = (score: number): [number, number] => {
  const a = Math.PI * (1 - score / 1000);
  return [CX + R * Math.cos(a), CY - R * Math.sin(a)];
};
const arcPath = (s0: number, s1: number) => {
  const [x0, y0] = polar(s0), [x1, y1] = polar(Math.max(s1, s0 + 0.1));
  return `M ${x0.toFixed(1)} ${y0.toFixed(1)} A ${R} ${R} 0 0 1 ${x1.toFixed(1)} ${y1.toFixed(1)}`;
};
const TIERS: [number, string, string, number][] = [
  [820, "PLATINUM", CYAN, 0], [620, "GOLD", "#e3b73f", 25], [420, "SILVER", "#aab6c2", 75],
  [200, "BRONZE", "#c47a45", 120], [0, "UNKNOWN", "#7f8c9c", 150],
];
const tierOf = (score: number) => TIERS.find((t) => score >= t[0]) ?? TIERS[TIERS.length - 1];

const A: React.CSSProperties = { position: "absolute", willChange: "transform,opacity" };

export const Meritor: React.FC = () => {
  const frame = useCurrentFrame();
  const t = frame / FPS;

  // gauge score across instrument + deletion phases
  const gaugeScore = (): number => {
    if (t < 47) return 0;
    if (t < 51) return lerp(0, 849, easeOut(clamp((t - 47) / 3.6)));
    if (t < 84) return 849;
    if (t < 88.5) return lerp(849, 0, easeInOut(clamp((t - 85) / 3.5)));
    return 0;
  };
  const sc = gaugeScore();
  const [, tname, tcol, tcollat] = tierOf(sc);
  const [kx, ky] = polar(Math.max(sc, 0.2));

  const roster = [
    { id: "0xALPHA", score: 849, tier: "PLATINUM", col: CYAN, sub: "4 sessions · 0% collateral" },
    { id: "0xGAMMA", score: 757, tier: "GOLD", col: "#e3b73f", sub: "2 sessions · 25% collateral" },
    { id: "0xBETA", score: 518, tier: "SILVER", col: "#aab6c2", sub: "thin file · 75% collateral" },
    { id: "0xDELTA", score: 676, tier: "SILVER", col: "#aab6c2", sub: "capped from GOLD · recent default" },
  ];

  return (
    <AbsoluteFill
      style={{
        background: "radial-gradient(1400px 900px at 66% 34%, #1c1710 0%, #140f09 46%, #0b0805 100%)",
        fontFamily: SANS, color: INK,
      }}
    >
      {/* vignette */}
      <AbsoluteFill style={{ boxShadow: "inset 0 0 360px 70px rgba(0,0,0,.62)", pointerEvents: "none" }} />

      {/* marble atmosphere (brand + close) */}
      <img
        src={staticFile("meritor-hero.png")}
        style={{
          ...A, right: 70, top: "50%", width: 720, height: 940, objectFit: "cover", borderRadius: 18,
          transform: `translateY(-50%) translateX(${(1 - prog(t, 0.3, 2)) * 60}px)`,
          opacity: (t < 9 ? band(t, 0.3, 1.5, 7.6, 1.0) * 0.5 : t > 117 ? band(t, 117.6, 1.2, 125, 1.4) * 0.26 : 0),
          filter: "saturate(.92) contrast(1.02)",
        }}
      />
      <div style={{
        ...A, right: 70, top: "50%", width: 720, height: 940, transform: "translateY(-50%)", borderRadius: 18,
        background: "linear-gradient(90deg,#120f0a 6%, rgba(18,15,10,.25) 44%, transparent 72%)",
        opacity: (t < 9 ? band(t, 0.3, 1.5, 7.6, 1.0) : t > 117 ? band(t, 117.6, 1.2, 125, 1.4) : 0),
      }} />

      {/* ---------- S1 BRAND (0-9) ---------- */}
      <div style={{ ...A, left: 210, top: 386, fontFamily: MONO, fontSize: 21, letterSpacing: "0.28em", textTransform: "uppercase", color: BRASS, fontWeight: 500, opacity: band(t, 0.6, 0.8, 7.8, 0.7), transform: tr(0, (1 - prog(t, 0.6, 0.9)) * 14) }}>
        Sibyl Memory · Base · Virtuals
      </div>
      <div style={{ ...A, left: 205, top: 414, fontFamily: SERIF, fontWeight: 600, fontSize: 158, letterSpacing: "-0.02em", opacity: band(t, 0.8, 1.0, 7.8, 0.7), transform: tr(0, (1 - prog(t, 0.8, 1.1)) * 26) }}>
        Meritor
      </div>
      <div style={{ ...A, left: 214, top: 604, width: 520, height: 2, transformOrigin: "left center", transform: `scaleX(${prog(t, 1.6, 1.1)})`, background: `linear-gradient(90deg,${BRASS},rgba(207,154,78,.1))`, opacity: band(t, 1.6, 0.6, 7.8, 0.7) }} />
      <div style={{ ...A, left: 216, top: 622, fontFamily: SERIF, fontSize: 27, color: MID, opacity: band(t, 1.9, 0.9, 7.8, 0.7), transform: tr(0, (1 - prog(t, 1.9, 1.0)) * 12) }}>
        A load-bearing credit memory for autonomous agents.
      </div>

      {/* ---------- S2 PROBLEM (9-21) ---------- */}
      <div style={{ ...A, left: 210, top: 300, fontFamily: SERIF, fontSize: 76, color: INK, opacity: band(t, 9.4, 0.7, 20.2, 0.7), transform: tr((1 - prog(t, 9.4, 0.9)) * -22) }}>
        An agent that forgets
      </div>
      <div style={{ ...A, left: 210, top: 396, fontFamily: SERIF, fontSize: 76, color: MID, opacity: band(t, 10.0, 0.7, 20.2, 0.7), transform: tr((1 - prog(t, 10.0, 0.9)) * -22) }}>
        must over-collateralize everyone.
      </div>
      <div style={{ ...A, left: 210, top: 566, fontFamily: SERIF, fontSize: 176, fontWeight: 600, color: BAD, opacity: band(t, 12.4, 0.6, 20.2, 0.7), transform: tr(0, 0, lerp(0.86, 1, prog(t, 12.4, 0.7))) , transformOrigin: "left bottom" }}>
        150%+
      </div>
      <div style={{ ...A, left: 222, top: 792, fontFamily: MONO, fontSize: 23, color: DIM, letterSpacing: "0.04em", opacity: band(t, 13.4, 0.7, 20.2, 0.7), transform: tr(0, (1 - prog(t, 13.4, 0.9)) * 12) }}>
        collateral demanded of every counterparty, every session, forever
      </div>

      {/* ---------- S3 THESIS (21-31) ---------- */}
      <div style={{ ...A, left: 0, width: 1920, textAlign: "center", top: 380, fontFamily: SERIF, fontSize: 82, opacity: band(t, 21.6, 0.9, 30.0, 0.8), transform: tr(0, (1 - prog(t, 21.6, 1.1)) * 16) }}>
        Meritor makes memory<br /><span style={{ fontStyle: "italic", color: BRASS }}>load-bearing.</span>
      </div>

      {/* ---------- S4 HOW: persist / recall / decide (31-45) ---------- */}
      <div style={{ ...A, left: 0, width: 1920, textAlign: "center", top: 250, fontFamily: SERIF, fontSize: 60, opacity: band(t, 31.4, 0.7, 44.0, 0.7), transform: tr(0, (1 - prog(t, 31.4, 0.9)) * -12) }}>
        Memory becomes a tier. The tier becomes money.
      </div>
      {[["01", "Persist", "every settled obligation", 300], ["02", "Recall", "in a fresh session", 800], ["03", "Decide", "tier · collateral · settle", 1250]].map(([n, l, d, x], i) => (
        <div key={i} style={{ ...A, left: x as number, top: 500, opacity: band(t, 32.6 + i * 0.6, 0.6, 44.0, 0.7), transform: tr(0, (1 - prog(t, 32.6 + i * 0.6, 0.9)) * 24) }}>
          <div style={{ fontFamily: MONO, color: BRASS, fontSize: 22, letterSpacing: "0.14em", marginBottom: 10 }}>{n}</div>
          <div style={{ fontFamily: MONO, fontSize: 40, letterSpacing: "0.1em", textTransform: "uppercase", color: INK }}>{l}</div>
          <div style={{ fontFamily: SANS, fontSize: 17, color: DIM, marginTop: 12 }}>{d}</div>
        </div>
      ))}

      {/* ---------- GAUGE INSTRUMENT (45-64 approve, 84-89 collapse) ---------- */}
      {(t >= 44.8 && t < 64.5) || (t >= 78.5 && t < 96.6) ? (() => {
        const inApprove = t < 70;
        const gOp = inApprove ? band(t, 45.0, 0.8, 63.6, 0.8) : band(t, 79.0, 0.8, 96.0, 0.8);
        const denied = t >= 85.6;
        return (
          <>
            <div style={{ ...A, left: 240, top: 300, width: 520, opacity: gOp }}>
              <svg viewBox="0 0 520 330" style={{ width: 520, height: 330, display: "block" }}>
                <path d={arcPath(0, 1000)} fill="none" stroke="#2c2519" strokeWidth={16} strokeLinecap="round" />
                <path d={arcPath(0, Math.max(sc, 0.2))} fill="none" stroke={tcol} strokeWidth={16} strokeLinecap="round" />
                <circle cx={kx} cy={ky} r={12} fill={tcol} stroke="#120f0a" strokeWidth={4} style={{ opacity: sc > 2 ? 1 : 0 }} />
              </svg>
              <div style={{ ...A, left: 0, top: 150, width: 520, textAlign: "center", fontFamily: SERIF, fontWeight: 600, fontSize: 92, letterSpacing: "-0.03em", color: tcol }}>{Math.round(sc)}</div>
              <div style={{ ...A, left: 0, top: 258, width: 520, textAlign: "center", fontFamily: MONO, fontSize: 20, color: DIM }}>/ 1000</div>
              <div style={{ ...A, left: 0, top: 296, width: 520, textAlign: "center", fontFamily: SERIF, fontWeight: 600, fontSize: 30, letterSpacing: "0.06em", color: tcol }}>{tname}</div>
            </div>
            <div style={{ ...A, left: 830, top: 360, width: 560, opacity: inApprove ? band(t, 45.8, 0.7, 63.6, 0.8) : band(t, 79.6, 0.7, 96.0, 0.8) }}>
              <div style={{ fontFamily: MONO, fontSize: 32, color: INK }}>0xALPHA</div>
              <div style={{ fontFamily: SANS, fontSize: 20, color: MID, marginTop: 10 }}>
                {denied ? "Memory erased - no history to recall." : "Recalled 25 credit events across 4 sessions."}
              </div>
              <div style={{ fontFamily: SERIF, fontWeight: 600, fontSize: 62, marginTop: 34, color: (t >= 51 && t < 84.5) ? GOOD : BAD, opacity: (t >= 51 && t < 84.5) ? band(t, 51.0, 0.5, 84.2, 0.4) : (t >= 86.6 ? band(t, 86.6, 0.5, 96.0, 0.6) : 0) }}>
                {(t >= 51 && t < 84.5) ? "APPROVED" : "DENIED"}
              </div>
              <div style={{ fontFamily: MONO, fontSize: 26, color: MID, marginTop: 22, opacity: inApprove ? band(t, 48.0, 0.6, 63.6, 0.6) : band(t, 80.0, 0.6, 96.0, 0.6) }}>
                collateral required &nbsp; <b style={{ fontSize: 40, color: tcollat === 0 ? GOOD : tcollat >= 120 ? BAD : INK }}>{tcollat}%</b>
              </div>
            </div>
          </>
        );
      })() : null}

      {/* approve caption */}
      <div style={{ ...A, left: 0, width: 1920, textAlign: "center", top: 900, fontFamily: SERIF, fontSize: 40, color: MID, opacity: band(t, 55.0, 0.8, 63.6, 0.7) }}>
        Uncollateralized credit, earned across sessions.
      </div>

      {/* ---------- S6 ROSTER (64-79) ---------- */}
      <div style={{ ...A, left: 0, width: 1920, textAlign: "center", top: 190, fontFamily: SERIF, fontSize: 58, opacity: band(t, 64.6, 0.7, 78.4, 0.7), transform: tr(0, (1 - prog(t, 64.6, 0.9)) * -12) }}>
        The book is priced entirely from memory.
      </div>
      {roster.map((r, i) => {
        const x = 210 + i * 385;
        const op = band(t, 65.6 + i * 0.5, 0.7, 78.4, 0.7);
        return (
          <div key={r.id} style={{ ...A, left: x, top: 360, width: 340, height: 300, borderRadius: 18, border: "1px solid #342b20", background: "rgba(28,22,15,.6)", padding: "26px 24px", opacity: op, transform: tr(0, (1 - prog(t, 65.6 + i * 0.5, 0.9)) * 26) }}>
            <div style={{ fontFamily: MONO, fontSize: 26, color: INK }}>{r.id}</div>
            <div style={{ fontFamily: SERIF, fontWeight: 600, fontSize: 72, letterSpacing: "-0.03em", color: r.col, marginTop: 12 }}>{r.score}</div>
            <div style={{ display: "inline-block", marginTop: 8, fontFamily: MONO, fontSize: 16, fontWeight: 600, letterSpacing: "0.06em", color: r.col, border: `1px solid ${r.col}`, borderRadius: 8, padding: "5px 11px" }}>{r.tier}</div>
            <div style={{ fontFamily: SANS, fontSize: 15.5, color: DIM, marginTop: 16, lineHeight: 1.4 }}>{r.sub}</div>
          </div>
        );
      })}

      {/* ---------- DELETION cue (79-97) ---------- */}
      <div style={{ ...A, left: 0, width: 1920, textAlign: "center", top: 120, fontFamily: MONO, fontSize: 30, color: BAD, letterSpacing: "0.12em", textTransform: "uppercase", opacity: band(t, 80.4, 0.4, 84.8, 0.5) }}>
        Erase the memory
      </div>
      <AbsoluteFill style={{ background: BAD, mixBlendMode: "screen", opacity: band(t, 84.9, 0.12, 85.2, 0.55) * 0.5, pointerEvents: "none" }} />
      <div style={{ ...A, left: 0, width: 1920, textAlign: "center", top: 892, fontFamily: SERIF, fontSize: 50, color: INK, opacity: band(t, 90.0, 0.9, 102.4, 0.9), transform: tr(0, (1 - prog(t, 90.0, 1.1)) * 16) }}>
        The only variable was memory.
      </div>

      {/* ---------- S9 ONCHAIN (103-117) ---------- */}
      <div style={{ ...A, left: 210, top: 350, width: 560, fontFamily: SERIF, fontSize: 62, opacity: band(t, 103.4, 0.7, 116.2, 0.7), transform: tr((1 - prog(t, 103.4, 0.9)) * -20) }}>
        Every decision, provable on Base.
      </div>
      <div style={{ ...A, left: 212, top: 560, width: 520, fontFamily: SANS, fontSize: 20, color: MID, opacity: band(t, 104.0, 0.7, 116.2, 0.7) }}>
        Meritor publishes the recalled tier to Base mainnet as a portable EAS attestation other agents can verify.
      </div>
      <div style={{ ...A, left: 800, top: 300, width: 660, borderRadius: 20, border: "1px solid #3a3226", background: "rgba(20,16,11,.74)", padding: "34px 36px", opacity: band(t, 104.4, 0.8, 116.2, 0.7), transform: tr((1 - prog(t, 104.4, 1.0)) * 40) }}>
        <div style={{ display: "inline-flex", alignItems: "center", gap: 10, fontFamily: MONO, fontSize: 15, color: CYAN, background: "rgba(99,219,230,.1)", padding: "7px 14px", borderRadius: 999, marginBottom: 22 }}>
          <span style={{ width: 9, height: 9, borderRadius: 999, background: CYAN, display: "inline-block" }} /> Base mainnet · confirmed
        </div>
        {[["Claim", "0xALPHA → PLATINUM (856)", CYAN], ["Attestation", "0x66c791…9a0e2a", INK], ["Transaction", "0xfcb465…13110f61", INK], ["Block", "50,862,970", INK]].map(([k, v, c], i) => (
          <div key={i} style={{ display: "flex", justifyContent: "space-between", gap: 20, padding: "12px 0", borderBottom: i < 3 ? "1px solid #2a2419" : "none", fontSize: 18 }}>
            <span style={{ color: DIM }}>{k}</span><span style={{ fontFamily: MONO, color: c as string }}>{v}</span>
          </div>
        ))}
      </div>

      {/* ---------- S10 CLOSE (117-125) ---------- */}
      <div style={{ ...A, left: 0, width: 1920, textAlign: "center", top: 392, fontFamily: SERIF, fontWeight: 600, fontSize: 160, letterSpacing: "-0.02em", opacity: band(t, 117.9, 0.9, 125, 1.4), transform: tr(0, (1 - prog(t, 117.9, 1.1)) * 18) }}>
        Meritor
      </div>
      <div style={{ ...A, left: 0, width: 1920, textAlign: "center", top: 580, fontFamily: SERIF, fontSize: 40, color: MID, opacity: band(t, 118.7, 0.9, 125, 1.4) }}>
        Credit that remembers.
      </div>
      <div style={{ ...A, left: 0, width: 1920, textAlign: "center", top: 668, fontFamily: MONO, fontSize: 20, color: DIM, letterSpacing: "0.18em", textTransform: "uppercase", opacity: band(t, 119.2, 0.9, 125, 1.4) }}>
        Sibyl Memory · Base · Virtuals
      </div>
    </AbsoluteFill>
  );
};
