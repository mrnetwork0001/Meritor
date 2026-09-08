import React from "react";
import { AbsoluteFill, useCurrentFrame, staticFile, spring } from "remotion";
import { loadFont as loadFraunces } from "@remotion/google-fonts/Fraunces";
import { loadFont as loadMono } from "@remotion/google-fonts/IBMPlexMono";
import { loadFont as loadSans } from "@remotion/google-fonts/IBMPlexSans";

export const FPS = 30;
export const DURATION_S = 88;

const SERIF = loadFraunces("normal", { weights: ["400", "500", "600"], subsets: ["latin"] }).fontFamily;
const MONO = loadMono("normal", { weights: ["400", "500", "600"], subsets: ["latin"] }).fontFamily;
const SANS = loadSans("normal", { weights: ["400", "500", "600"], subsets: ["latin"] }).fontFamily;

const INK = "#f2e9d9", MID = "#b9ab97", DIM = "#8a7c67";
const BRASS = "#cf9a4e", CYAN = "#63dbe6", GOOD = "#4ec38a", BAD = "#f0576e";
const WORDMARK = staticFile("meritor-wordmark-light.png");
const MARBLE = staticFile("meritor-hero.png");

const clamp = (x: number, a = 0, b = 1) => (x < a ? a : x > b ? b : x);
const lerp = (a: number, b: number, t: number) => a + (b - a) * t;
const easeOut = (t: number) => 1 - Math.pow(1 - t, 3);
const easeInOut = (t: number) => (t < 0.5 ? 4 * t * t * t : 1 - Math.pow(-2 * t + 2, 3) / 2);
const prog = (t: number, s: number, d: number) => easeOut(clamp((t - s) / d));
// fade in then out
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
const CENTER: React.CSSProperties = { ...A, left: 0, width: 1920, textAlign: "center" };

export const Meritor: React.FC = () => {
  const frame = useCurrentFrame();
  const t = frame / FPS;
  // spring helper (overshoot entrance)
  const sp = (startS: number, damping = 14) =>
    spring({ frame: frame - startS * FPS, fps: FPS, config: { damping, mass: 0.9 } });

  // scene opacity with cross-fade
  const sceneOp = (s: number, e: number, f = 0.55) => band(t, s, f, e - f, f);

  // ---- shared gauge score across approve + deletion ----
  let score = 0, gaugeOn = false;
  if (t >= 35.4 && t < 49.6) { gaugeOn = true; score = t < 40 ? lerp(0, 849, easeOut(clamp((t - 36) / 3.4))) : 849; }
  else if (t >= 59.4 && t < 73.2) { gaugeOn = true; score = t < 63 ? 849 : lerp(849, 0, easeInOut(clamp((t - 63) / 3.2))); }
  const [, tname, tcol, tcollat] = tierOf(score);
  const [kx, ky] = polar(Math.max(score, 0.2));
  const gaugeOp = t < 55 ? sceneOp(35.4, 49.6) : sceneOp(59.4, 73.2);

  const roster = [
    { id: "0xALPHA", score: 849, tier: "PLATINUM", col: CYAN, sub: "4 sessions · 0% collateral" },
    { id: "0xGAMMA", score: 757, tier: "GOLD", col: "#e3b73f", sub: "2 sessions · 25% collateral" },
    { id: "0xBETA", score: 518, tier: "SILVER", col: "#aab6c2", sub: "thin file · 75% collateral" },
    { id: "0xDELTA", score: 676, tier: "SILVER", col: "#aab6c2", sub: "capped from GOLD · a recent default" },
  ];

  // ambient background drift
  const glowX = 60 + 9 * Math.sin(t * 0.5);
  const glowY = 34 + 6 * Math.cos(t * 0.37);
  const gridShift = (t * 7) % 46;

  return (
    <AbsoluteFill style={{ background: "#0e0b07", fontFamily: SANS, color: INK, overflow: "hidden" }}>
      {/* ambient layers */}
      <AbsoluteFill style={{ background: `radial-gradient(1500px 1000px at ${glowX}% ${glowY}%, #201a12 0%, #140f09 45%, #0b0805 100%)` }} />
      <AbsoluteFill style={{
        backgroundImage: `radial-gradient(circle, rgba(207,154,78,.05) 1.4px, transparent 1.5px)`,
        backgroundSize: "46px 46px", transform: `translate(${-gridShift}px, ${-gridShift * 0.5}px)`, opacity: 0.7,
      }} />
      <AbsoluteFill style={{ boxShadow: "inset 0 0 360px 80px rgba(0,0,0,.62)", pointerEvents: "none" }} />

      {/* persistent corner wordmark during content (6-83) */}
      <img src={WORDMARK} style={{ ...A, left: 64, top: 56, height: 34, opacity: band(t, 6.2, 0.8, 82.5, 0.7) * 0.55 }} />

      {/* ================= S1 BRAND (0-6) ================= */}
      {t < 6.6 && (() => {
        const op = sceneOp(0, 6.2, 0.5);
        const s = lerp(0.86, 1, clamp(sp(0.3)));
        return (
          <>
            <img src={MARBLE} style={{ ...A, right: 90, top: "50%", width: 640, height: 860, objectFit: "cover", borderRadius: 18, transform: `translateY(-50%) translateX(${(1 - clamp(sp(0.3))) * 50}px)`, opacity: op * 0.42 }} />
            <div style={{ ...A, right: 90, top: "50%", width: 640, height: 860, transform: "translateY(-50%)", borderRadius: 18, background: "linear-gradient(90deg,#0e0b07 8%, rgba(14,11,7,.3) 46%, transparent 74%)", opacity: op }} />
            <img src={WORDMARK} style={{ ...A, left: 210, top: 430, height: 150, transform: tr(0, (1 - clamp(sp(0.4))) * 20, s), transformOrigin: "left center", opacity: op }} />
            <div style={{ ...A, left: 216, top: 604, width: 560, height: 2, transformOrigin: "left", transform: `scaleX(${prog(t, 1.1, 1.0)})`, background: `linear-gradient(90deg,${BRASS},rgba(207,154,78,.06))`, opacity: op }} />
            <div style={{ ...A, left: 218, top: 626, fontFamily: SERIF, fontSize: 27, color: MID, opacity: band(t, 1.4, 0.8, 6.0, 0.5), transform: tr(0, (1 - prog(t, 1.4, 0.9)) * 12) }}>
              A load-bearing credit memory for autonomous agents.
            </div>
            <div style={{ ...A, left: 210, top: 384, fontFamily: MONO, fontSize: 19, letterSpacing: "0.28em", textTransform: "uppercase", color: BRASS, opacity: op, transform: tr(0, (1 - clamp(sp(0.2))) * 10) }}>
              Sibyl Memory · Base · Virtuals
            </div>
          </>
        );
      })()}

      {/* ================= S2 PROBLEM (6-16) ================= */}
      {t >= 5.8 && t < 16.4 && (() => {
        return (
          <>
            <div style={{ ...A, left: 210, top: 300, fontFamily: SERIF, fontSize: 78, color: INK, opacity: band(t, 6.2, 0.6, 15.6, 0.6), transform: tr((1 - clamp(sp(6.2))) * -30) }}>
              An agent that forgets
            </div>
            <div style={{ ...A, left: 210, top: 398, fontFamily: SERIF, fontSize: 78, color: MID, opacity: band(t, 6.7, 0.6, 15.6, 0.6), transform: tr((1 - clamp(sp(6.7))) * -30) }}>
              over-collateralizes everyone.
            </div>
            <div style={{ ...A, left: 210, top: 566, fontFamily: SERIF, fontWeight: 600, fontSize: 184, color: BAD, transformOrigin: "left bottom", opacity: band(t, 9.0, 0.5, 15.6, 0.6), transform: tr(0, 0, lerp(0.8, 1, clamp(sp(9.0, 11)))) }}>
              150%+
            </div>
            <div style={{ ...A, left: 222, top: 800, fontFamily: MONO, fontSize: 22, color: DIM, letterSpacing: "0.04em", opacity: band(t, 10.0, 0.6, 15.6, 0.6), transform: tr(0, (1 - prog(t, 10.0, 0.8)) * 12) }}>
              every counterparty · every session · forever
            </div>
          </>
        );
      })()}

      {/* ================= S3 THESIS (16-24) ================= */}
      {t >= 15.8 && t < 24.4 && (
        <div style={{ ...CENTER, top: 400, fontFamily: SERIF, fontSize: 88, opacity: sceneOp(16.0, 24.0), transform: tr(0, (1 - clamp(sp(16.2))) * 22) }}>
          Meritor makes memory<br /><span style={{ fontStyle: "italic", color: BRASS }}>load-bearing.</span>
        </div>
      )}

      {/* ================= S4 HOW (24-35) ================= */}
      {t >= 23.8 && t < 35.4 && (() => {
        const steps: [string, string, string, number][] = [
          ["01", "Persist", "every settled obligation", 250],
          ["02", "Recall", "in a fresh session", 780],
          ["03", "Decide", "tier · collateral · settle", 1290],
        ];
        return (
          <>
            <div style={{ ...CENTER, top: 250, fontFamily: SERIF, fontSize: 58, opacity: band(t, 24.1, 0.6, 34.8, 0.6), transform: tr(0, (1 - prog(t, 24.1, 0.8)) * -12) }}>
              Memory becomes a tier. The tier becomes money.
            </div>
            <div style={{ ...A, left: 250, top: 560, width: 1420, height: 2, background: `linear-gradient(90deg,transparent,${BRASS}88,transparent)`, transformOrigin: "center", transform: `scaleX(${prog(t, 25.0, 1.4)})`, opacity: band(t, 25.0, 0.6, 34.8, 0.6) }} />
            {steps.map(([n, l, d, x], i) => (
              <div key={i} style={{ ...A, left: x, top: 490, width: 360, opacity: band(t, 25.2 + i * 0.55, 0.5, 34.8, 0.6), transform: tr(0, (1 - clamp(sp(25.2 + i * 0.55, 12))) * 26) }}>
                <div style={{ fontFamily: MONO, color: BRASS, fontSize: 22, letterSpacing: "0.14em", marginBottom: 10 }}>{n}</div>
                <div style={{ fontFamily: MONO, fontSize: 42, letterSpacing: "0.1em", textTransform: "uppercase" }}>{l}</div>
                <div style={{ fontFamily: SANS, fontSize: 17, color: DIM, marginTop: 12 }}>{d}</div>
              </div>
            ))}
          </>
        );
      })()}

      {/* ================= GAUGE INSTRUMENT (approve 35-49 + deletion 59-73) ================= */}
      {gaugeOn && (() => {
        const denied = t >= 66;
        const rOp = t < 55 ? band(t, 35.8, 0.6, 49.4, 0.6) : band(t, 59.8, 0.6, 73.0, 0.6);
        return (
          <>
            <div style={{ ...A, left: 240, top: 300, width: 520, opacity: gaugeOp, transform: tr(0, (1 - clamp(sp(t < 55 ? 35.6 : 59.6, 13))) * 20) }}>
              <svg viewBox="0 0 520 330" style={{ width: 520, height: 330, display: "block" }}>
                <path d={arcPath(0, 1000)} fill="none" stroke="#2c2519" strokeWidth={16} strokeLinecap="round" />
                <path d={arcPath(0, Math.max(score, 0.2))} fill="none" stroke={tcol} strokeWidth={16} strokeLinecap="round" style={{ filter: `drop-shadow(0 0 10px ${tcol}66)` }} />
                <circle cx={kx} cy={ky} r={13} fill={tcol} stroke="#0e0b07" strokeWidth={4} style={{ opacity: score > 2 ? 1 : 0 }} />
              </svg>
              <div style={{ ...A, left: 0, top: 148, width: 520, textAlign: "center", fontFamily: SERIF, fontWeight: 600, fontSize: 96, letterSpacing: "-0.03em", color: tcol }}>{Math.round(score)}</div>
              <div style={{ ...A, left: 0, top: 262, width: 520, textAlign: "center", fontFamily: MONO, fontSize: 20, color: DIM }}>/ 1000</div>
              <div style={{ ...A, left: 0, top: 300, width: 520, textAlign: "center", fontFamily: SERIF, fontWeight: 600, fontSize: 32, letterSpacing: "0.06em", color: tcol }}>{tname}</div>
            </div>
            <div style={{ ...A, left: 840, top: 350, width: 560, opacity: rOp }}>
              <div style={{ fontFamily: MONO, fontSize: 32 }}>0xALPHA</div>
              <div style={{ fontFamily: SANS, fontSize: 20, color: MID, marginTop: 10 }}>
                {denied ? "Memory erased. No history to recall." : "Recalled 25 credit events across 4 sessions."}
              </div>
              <div style={{
                fontFamily: SERIF, fontWeight: 600, fontSize: 66, marginTop: 32,
                color: !denied ? GOOD : BAD,
                opacity: !denied ? band(t, 40.2, 0.5, 49.4, 0.4) : band(t, 66.8, 0.5, 73.0, 0.5),
                transform: tr(0, 0, !denied ? lerp(0.9, 1, clamp(sp(40.2, 12))) : 1),
              }}>
                {!denied ? "APPROVED" : "DENIED"}
              </div>
              <div style={{ fontFamily: MONO, fontSize: 26, color: MID, marginTop: 22, opacity: band(t, t < 55 ? 38.0 : 61.0, 0.6, 73.0, 0.6) }}>
                collateral &nbsp; <b style={{ fontSize: 42, color: tcollat === 0 ? GOOD : tcollat >= 120 ? BAD : INK }}>{tcollat}%</b>
              </div>
            </div>
          </>
        );
      })()}

      {/* approve caption */}
      {t >= 42 && t < 49.6 && (
        <div style={{ ...CENTER, top: 900, fontFamily: SERIF, fontSize: 38, color: MID, opacity: band(t, 42.5, 0.6, 49.2, 0.5) }}>
          Uncollateralized credit, earned across sessions.
        </div>
      )}

      {/* ================= S6 ROSTER (49-60) ================= */}
      {t >= 48.8 && t < 60.4 && (
        <>
          <div style={{ ...CENTER, top: 210, fontFamily: SERIF, fontSize: 56, opacity: band(t, 49.2, 0.6, 59.6, 0.6), transform: tr(0, (1 - prog(t, 49.2, 0.8)) * -12) }}>
            The whole book, priced from memory.
          </div>
          {roster.map((r, i) => {
            const x = 210 + i * 385;
            const op = band(t, 49.9 + i * 0.45, 0.55, 59.6, 0.6);
            return (
              <div key={r.id} style={{ ...A, left: x, top: 380, width: 340, height: 300, borderRadius: 18, border: "1px solid #342b20", background: "rgba(28,22,15,.6)", padding: "26px 24px", opacity: op, transform: tr(0, (1 - clamp(sp(49.9 + i * 0.45, 13))) * 30) }}>
                <div style={{ fontFamily: MONO, fontSize: 26 }}>{r.id}</div>
                <div style={{ fontFamily: SERIF, fontWeight: 600, fontSize: 74, letterSpacing: "-0.03em", color: r.col, marginTop: 10 }}>{r.score}</div>
                <div style={{ display: "inline-block", marginTop: 8, fontFamily: MONO, fontSize: 16, fontWeight: 600, letterSpacing: "0.06em", color: r.col, border: `1px solid ${r.col}`, borderRadius: 8, padding: "5px 11px" }}>{r.tier}</div>
                <div style={{ fontFamily: SANS, fontSize: 15.5, color: DIM, marginTop: 16, lineHeight: 1.4 }}>{r.sub}</div>
              </div>
            );
          })}
        </>
      )}

      {/* ================= DELETION cues (59-73) ================= */}
      {t >= 59.8 && t < 63.4 && (
        <div style={{ ...CENTER, top: 120, fontFamily: MONO, fontSize: 30, color: BAD, letterSpacing: "0.12em", textTransform: "uppercase", opacity: band(t, 60.0, 0.4, 63.0, 0.4) }}>
          Erase the memory
        </div>
      )}
      <AbsoluteFill style={{ background: BAD, mixBlendMode: "screen", opacity: band(t, 63.0, 0.1, 63.25, 0.5) * 0.5, pointerEvents: "none" }} />
      {t >= 67.5 && t < 73.4 && (
        <div style={{ ...CENTER, top: 892, fontFamily: SERIF, fontSize: 50, opacity: band(t, 67.8, 0.7, 73.0, 0.6), transform: tr(0, (1 - prog(t, 67.8, 0.9)) * 16) }}>
          The only variable was memory.
        </div>
      )}

      {/* ================= S8 ONCHAIN (73-83) ================= */}
      {t >= 72.8 && t < 83.4 && (
        <>
          <div style={{ ...A, left: 210, top: 350, width: 560, fontFamily: SERIF, fontSize: 60, opacity: band(t, 73.2, 0.6, 82.6, 0.6), transform: tr((1 - clamp(sp(73.2))) * -22) }}>
            Every decision, provable on Base.
          </div>
          <div style={{ ...A, left: 212, top: 552, width: 520, fontFamily: SANS, fontSize: 20, color: MID, opacity: band(t, 73.8, 0.6, 82.6, 0.6) }}>
            The recalled tier is published to Base mainnet as a portable EAS attestation any agent can verify.
          </div>
          <div style={{ ...A, left: 800, top: 300, width: 660, borderRadius: 20, border: "1px solid #3a3226", background: "rgba(20,16,11,.76)", padding: "34px 36px", opacity: band(t, 74.0, 0.6, 82.6, 0.6), transform: tr((1 - clamp(sp(74.0, 13))) * 44) }}>
            <div style={{ display: "inline-flex", alignItems: "center", gap: 10, fontFamily: MONO, fontSize: 15, color: CYAN, background: "rgba(99,219,230,.1)", padding: "7px 14px", borderRadius: 999, marginBottom: 22 }}>
              <span style={{ width: 9, height: 9, borderRadius: 999, background: CYAN, display: "inline-block" }} /> Base mainnet · confirmed
            </div>
            {[["Claim", "0xALPHA → PLATINUM (856)", CYAN], ["Attestation", "0x66c791…9a0e2a", INK], ["Transaction", "0xfcb465…13110f61", INK], ["Block", "50,862,970", INK]].map(([k, v, c], i) => (
              <div key={i} style={{ display: "flex", justifyContent: "space-between", gap: 20, padding: "12px 0", borderBottom: i < 3 ? "1px solid #2a2419" : "none", fontSize: 18 }}>
                <span style={{ color: DIM }}>{k}</span><span style={{ fontFamily: MONO, color: c as string }}>{v}</span>
              </div>
            ))}
          </div>
        </>
      )}

      {/* ================= S9 CLOSE (83-88) ================= */}
      {t >= 82.8 && (() => {
        const op = band(t, 83.2, 0.8, 88, 1.2);
        return (
          <>
            <img src={MARBLE} style={{ ...A, left: "50%", top: "50%", width: 620, height: 820, objectFit: "cover", borderRadius: 18, transform: "translate(-50%,-50%)", opacity: op * 0.16 }} />
            <img src={WORDMARK} style={{ ...A, left: "50%", top: 392, height: 132, transform: `translateX(-50%) translateY(${(1 - clamp(sp(83.2))) * 16}px)`, opacity: op }} />
            <div style={{ ...CENTER, top: 566, fontFamily: SERIF, fontSize: 42, color: MID, opacity: band(t, 83.9, 0.8, 88, 1.2) }}>Credit that remembers.</div>
            <div style={{ ...CENTER, top: 660, fontFamily: MONO, fontSize: 20, color: DIM, letterSpacing: "0.18em", textTransform: "uppercase", opacity: band(t, 84.3, 0.8, 88, 1.2) }}>Sibyl Memory · Base · Virtuals</div>
          </>
        );
      })()}
    </AbsoluteFill>
  );
};
