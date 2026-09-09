import React from "react";
import { AbsoluteFill, useCurrentFrame, staticFile, spring } from "remotion";
import { loadFont as loadFraunces } from "@remotion/google-fonts/Fraunces";
import { loadFont as loadMono } from "@remotion/google-fonts/IBMPlexMono";
import { loadFont as loadSans } from "@remotion/google-fonts/IBMPlexSans";

export const FPS = 30;
export const DURATION_S = 144;

const SERIF = loadFraunces("normal", { weights: ["400", "500", "600"], subsets: ["latin"] }).fontFamily;
const MONO = loadMono("normal", { weights: ["400", "500", "600"], subsets: ["latin"] }).fontFamily;
const SANS = loadSans("normal", { weights: ["400", "500", "600"], subsets: ["latin"] }).fontFamily;

const INK = "#f2e9d9", MID = "#b9ab97", DIM = "#8a7c67";
const BRASS = "#cf9a4e", CYAN = "#63dbe6", GOOD = "#4ec38a", BAD = "#f0576e";
const PANEL = "rgba(28,22,15,.62)", LINE = "#342b20";
const WORDMARK = staticFile("meritor-wordmark-light.png");
const MARBLE = staticFile("meritor-hero.png");

const clamp = (x: number, a = 0, b = 1) => (x < a ? a : x > b ? b : x);
const lerp = (a: number, b: number, t: number) => a + (b - a) * t;
const easeOut = (t: number) => 1 - Math.pow(1 - t, 3);
const easeInOut = (t: number) => (t < 0.5 ? 4 * t * t * t : 1 - Math.pow(-2 * t + 2, 3) / 2);
const prog = (t: number, s: number, d: number) => easeOut(clamp((t - s) / d));
const band = (t: number, inS: number, inD: number, outS: number, outD: number) =>
  clamp(Math.min(clamp((t - inS) / inD), 1 - clamp((t - outS) / outD)));
const tr = (x = 0, y = 0, s = 1) => `translate(${x}px,${y}px) scale(${s})`;

const CX = 260, CY = 250, R = 205;
const polar = (score: number): [number, number] => { const a = Math.PI * (1 - score / 1000); return [CX + R * Math.cos(a), CY - R * Math.sin(a)]; };
const arcPath = (s0: number, s1: number) => { const [x0, y0] = polar(s0), [x1, y1] = polar(Math.max(s1, s0 + 0.1)); return `M ${x0.toFixed(1)} ${y0.toFixed(1)} A ${R} ${R} 0 0 1 ${x1.toFixed(1)} ${y1.toFixed(1)}`; };
const TIERS: [number, string, string, number][] = [[820, "PLATINUM", CYAN, 0], [620, "GOLD", "#e3b73f", 25], [420, "SILVER", "#aab6c2", 75], [200, "BRONZE", "#c47a45", 120], [0, "UNKNOWN", "#7f8c9c", 150]];
const tierOf = (score: number) => TIERS.find((t) => score >= t[0]) ?? TIERS[TIERS.length - 1];

const A: React.CSSProperties = { position: "absolute", willChange: "transform,opacity" };
const CENTER: React.CSSProperties = { ...A, left: 0, width: 1920, textAlign: "center" };

export const Meritor: React.FC = () => {
  const frame = useCurrentFrame();
  const t = frame / FPS;
  const sp = (startS: number, damping = 14) => spring({ frame: frame - startS * FPS, fps: FPS, config: { damping, mass: 0.9 } });
  const sceneOp = (s: number, e: number, f = 0.6) => band(t, s, f, e - f, f);

  // gauge score across recall(fill+hold), decide(hold), deletion(collapse)
  let score = 0, gaugeOn = false;
  if (t >= 51 && t < 84) { gaugeOn = true; score = t < 56 ? lerp(0, 849, easeOut(clamp((t - 52) / 3.6))) : 849; }
  else if (t >= 99 && t < 114.4) { gaugeOn = true; score = t < 104 ? 849 : lerp(849, 0, easeInOut(clamp((t - 104) / 3.2))); }
  const [, tname, tcol, tcollat] = tierOf(score);
  const [kx, ky] = polar(Math.max(score, 0.2));

  const roster = [
    { id: "0xALPHA", score: 849, tier: "PLATINUM", col: CYAN, sub: "4 sessions · 0% collateral" },
    { id: "0xGAMMA", score: 757, tier: "GOLD", col: "#e3b73f", sub: "2 sessions · 25% collateral" },
    { id: "0xBETA", score: 518, tier: "SILVER", col: "#aab6c2", sub: "thin file · 75% collateral" },
    { id: "0xDELTA", score: 676, tier: "SILVER", col: "#aab6c2", sub: "capped from GOLD · a recent default" },
  ];
  const events = [
    ["JOB_COMPLETED_ON_TIME", "+ SLA", GOOD],
    ["LOAN_REPAID", "$120 · 4h early", GOOD],
    ["ATTESTATION", "Base tx 0xfcb4…", CYAN],
    ["DISPUTE", "none on record", MID],
  ];
  const ladder = [["PLATINUM", CYAN, "0%"], ["GOLD", "#e3b73f", "25%"], ["SILVER", "#aab6c2", "75%"], ["BRONZE", "#c47a45", "120%"], ["UNKNOWN", "#7f8c9c", "150%"]];

  const glowX = 60 + 9 * Math.sin(t * 0.45), glowY = 34 + 6 * Math.cos(t * 0.33), gridShift = (t * 7) % 46;

  // which "how" step badge
  let step = "";
  if (t >= 34 && t < 52) step = "01 · PERSIST";
  else if (t >= 52 && t < 70) step = "02 · RECALL";
  else if (t >= 70 && t < 88) step = "03 · DECIDE";

  return (
    <AbsoluteFill style={{ background: "#0e0b07", fontFamily: SANS, color: INK, overflow: "hidden" }}>
      <AbsoluteFill style={{ background: `radial-gradient(1500px 1000px at ${glowX}% ${glowY}%, #201a12 0%, #140f09 45%, #0b0805 100%)` }} />
      <AbsoluteFill style={{ backgroundImage: `radial-gradient(circle, rgba(207,154,78,.05) 1.4px, transparent 1.5px)`, backgroundSize: "46px 46px", transform: `translate(${-gridShift}px, ${-gridShift * 0.5}px)`, opacity: 0.7 }} />
      <AbsoluteFill style={{ boxShadow: "inset 0 0 360px 80px rgba(0,0,0,.62)", pointerEvents: "none" }} />

      {/* persistent chrome: corner logo + step badge + progress bar */}
      <img src={WORDMARK} style={{ ...A, left: 64, top: 54, height: 34, opacity: band(t, 7.0, 0.8, 138.5, 0.7) * 0.5 }} />
      {step && (
        <div style={{ ...A, right: 64, top: 58, fontFamily: MONO, fontSize: 15, letterSpacing: "0.16em", color: BRASS, opacity: band(t, 34.2, 0.6, 87.6, 0.6) }}>{step}</div>
      )}
      <div style={{ ...A, left: 0, bottom: 0, height: 4, width: `${clamp(t / DURATION_S) * 100}%`, background: `linear-gradient(90deg,${BRASS},${CYAN})`, opacity: 0.5 }} />

      {/* ===== BRAND (0-7) ===== */}
      {t < 7.6 && (() => {
        const op = sceneOp(0, 7.0, 0.5), s = lerp(0.86, 1, clamp(sp(0.3)));
        return (<>
          <img src={MARBLE} style={{ ...A, right: 90, top: "50%", width: 640, height: 860, objectFit: "cover", borderRadius: 18, transform: `translateY(-50%) translateX(${(1 - clamp(sp(0.3))) * 50}px)`, opacity: op * 0.42 }} />
          <div style={{ ...A, right: 90, top: "50%", width: 640, height: 860, transform: "translateY(-50%)", borderRadius: 18, background: "linear-gradient(90deg,#0e0b07 8%, rgba(14,11,7,.3) 46%, transparent 74%)", opacity: op }} />
          <div style={{ ...A, left: 210, top: 388, fontFamily: MONO, fontSize: 19, letterSpacing: "0.28em", textTransform: "uppercase", color: BRASS, opacity: op, transform: tr(0, (1 - clamp(sp(0.2))) * 10) }}>Sibyl Memory · Base · Virtuals</div>
          <img src={WORDMARK} style={{ ...A, left: 210, top: 432, height: 152, transformOrigin: "left center", transform: tr(0, (1 - clamp(sp(0.4))) * 20, s), opacity: op }} />
          <div style={{ ...A, left: 216, top: 606, width: 560, height: 2, transformOrigin: "left", transform: `scaleX(${prog(t, 1.1, 1.0)})`, background: `linear-gradient(90deg,${BRASS},rgba(207,154,78,.06))`, opacity: op }} />
          <div style={{ ...A, left: 218, top: 628, fontFamily: SERIF, fontSize: 27, color: MID, opacity: band(t, 1.4, 0.8, 7.0, 0.5) }}>A load-bearing credit memory for autonomous agents.</div>
        </>);
      })()}

      {/* ===== PROBLEM (7-23) ===== */}
      {t >= 6.8 && t < 23.4 && (<>
        <div style={{ ...A, left: 210, top: 250, fontFamily: SERIF, fontSize: 76, color: INK, opacity: band(t, 7.2, 0.6, 22.6, 0.6), transform: tr((1 - clamp(sp(7.2))) * -28) }}>Agents can't remember</div>
        <div style={{ ...A, left: 210, top: 344, fontFamily: SERIF, fontSize: 76, color: MID, opacity: band(t, 7.8, 0.6, 22.6, 0.6), transform: tr((1 - clamp(sp(7.8))) * -28) }}>who kept their word.</div>
        <div style={{ ...A, left: 210, top: 520, fontFamily: SERIF, fontWeight: 600, fontSize: 170, color: BAD, transformOrigin: "left bottom", opacity: band(t, 12.5, 0.5, 22.6, 0.6), transform: tr(0, 0, lerp(0.82, 1, clamp(sp(12.5, 11)))) }}>150%+</div>
        <div style={{ ...A, left: 222, top: 742, width: 900, fontFamily: SANS, fontSize: 23, color: MID, lineHeight: 1.5, opacity: band(t, 13.6, 0.6, 22.6, 0.6) }}>So every counterparty is a stranger every session, and lending falls back on over-collateralizing everyone. An entire class of agent-to-agent credit never happens.</div>
      </>)}

      {/* ===== IDEA (23-34) ===== */}
      {t >= 22.8 && t < 34.4 && (
        <div style={{ ...CENTER, top: 400, fontFamily: SERIF, fontSize: 82, opacity: sceneOp(23.0, 34.0), transform: tr(0, (1 - clamp(sp(23.2))) * 20) }}>
          Meritor makes memory<br /><span style={{ fontStyle: "italic", color: BRASS }}>load-bearing.</span>
        </div>
      )}

      {/* ===== PERSIST (34-52): the journal builds ===== */}
      {t >= 33.8 && t < 52.4 && (<>
        <div style={{ ...A, left: 210, top: 250, fontFamily: SERIF, fontSize: 60, opacity: band(t, 34.2, 0.6, 51.6, 0.6), transform: tr(0, (1 - prog(t, 34.2, 0.8)) * -10) }}>Every obligation, written to memory.</div>
        <div style={{ ...A, left: 212, top: 340, width: 640, fontFamily: SANS, fontSize: 20, color: MID, lineHeight: 1.5, opacity: band(t, 34.8, 0.6, 51.6, 0.6) }}>After each ACP job and Base settlement, Meritor appends a signed credit event to a journal in Sibyl Memory: the outcome, the timing, the onchain proof.</div>
        {events.map(([name, meta, c], i) => {
          const enter = 36.4 + i * 0.9;
          const p = clamp(sp(enter, 13));
          return (
            <div key={i} style={{ ...A, left: 1050, top: 300 + i * 118, width: 620, borderRadius: 12, border: `1px solid ${LINE}`, background: PANEL, padding: "16px 20px", display: "flex", justifyContent: "space-between", alignItems: "center", opacity: band(t, enter, 0.5, 51.6, 0.6), transform: tr((1 - p) * 90) }}>
              <span style={{ fontFamily: MONO, fontSize: 19, color: INK }}>{name}</span>
              <span style={{ fontFamily: MONO, fontSize: 16, color: c as string }}>{meta}</span>
            </div>
          );
        })}
      </>)}

      {/* ===== GAUGE (recall 51-84 + deletion 99-114) ===== */}
      {gaugeOn && (() => {
        const inLive = t < 90, denied = t >= 105.6;
        const gOp = inLive ? band(t, 51.2, 0.7, 83.6, 0.7) : band(t, 99.4, 0.7, 114.0, 0.7);
        const rOp = inLive ? band(t, 53.0, 0.7, 83.6, 0.7) : band(t, 99.8, 0.7, 114.0, 0.7);
        return (<>
          <div style={{ ...A, left: 240, top: 330, width: 520, opacity: gOp, transform: tr(0, (1 - clamp(sp(inLive ? 51.0 : 99.2, 13))) * 18) }}>
            <svg viewBox="0 0 520 330" style={{ width: 520, height: 330, display: "block" }}>
              <path d={arcPath(0, 1000)} fill="none" stroke="#2c2519" strokeWidth={16} strokeLinecap="round" />
              <path d={arcPath(0, Math.max(score, 0.2))} fill="none" stroke={tcol} strokeWidth={16} strokeLinecap="round" style={{ filter: `drop-shadow(0 0 10px ${tcol}66)` }} />
              <circle cx={kx} cy={ky} r={13} fill={tcol} stroke="#0e0b07" strokeWidth={4} style={{ opacity: score > 2 ? 1 : 0 }} />
            </svg>
            <div style={{ ...A, left: 0, top: 148, width: 520, textAlign: "center", fontFamily: SERIF, fontWeight: 600, fontSize: 96, letterSpacing: "-0.03em", color: tcol }}>{Math.round(score)}</div>
            <div style={{ ...A, left: 0, top: 262, width: 520, textAlign: "center", fontFamily: MONO, fontSize: 20, color: DIM }}>/ 1000</div>
            <div style={{ ...A, left: 0, top: 300, width: 520, textAlign: "center", fontFamily: SERIF, fontWeight: 600, fontSize: 32, letterSpacing: "0.06em", color: tcol }}>{tname}</div>
          </div>
          <div style={{ ...A, left: 840, top: 388, width: 560, opacity: rOp }}>
            <div style={{ fontFamily: MONO, fontSize: 32 }}>0xALPHA</div>
            <div style={{ fontFamily: SANS, fontSize: 20, color: MID, marginTop: 10 }}>{denied ? "Memory erased. No history to recall." : "Recalled 25 credit events across 4 sessions."}</div>
            <div style={{ fontFamily: SERIF, fontWeight: 600, fontSize: 66, marginTop: 30, color: !denied ? GOOD : BAD, opacity: !denied ? band(t, 70.4, 0.5, 83.6, 0.4) : band(t, 106.6, 0.5, 114.0, 0.5) }}>{!denied ? "APPROVED" : "DENIED"}</div>
            <div style={{ fontFamily: MONO, fontSize: 26, color: MID, marginTop: 22, opacity: band(t, inLive ? 70.4 : 100.4, 0.6, 114.0, 0.6) }}>collateral &nbsp; <b style={{ fontSize: 42, color: tcollat === 0 ? GOOD : tcollat >= 120 ? BAD : INK }}>{tcollat}%</b></div>
          </div>
        </>);
      })()}

      {/* RECALL caption */}
      {t >= 52.5 && t < 66 && (<>
        <div style={{ ...CENTER, top: 120, fontFamily: SERIF, fontSize: 46, opacity: band(t, 53.0, 0.6, 65.4, 0.6) }}>A fresh session recalls the whole history.</div>
        <div style={{ ...CENTER, top: 900, fontFamily: SANS, fontSize: 21, color: MID, opacity: band(t, 54.0, 0.6, 65.4, 0.6) }}>A new process holds nothing in RAM. It replays the journal into an explainable score.</div>
      </>)}

      {/* DECIDE: collateral ladder */}
      {t >= 70 && t < 84 && (<>
        <div style={{ ...CENTER, top: 116, fontFamily: SERIF, fontSize: 46, opacity: band(t, 70.4, 0.6, 83.4, 0.6) }}>The tier sets the terms.</div>
        <div style={{ ...A, left: 640, top: 880, width: 640, display: "flex", gap: 10, justifyContent: "center", opacity: band(t, 72.0, 0.6, 83.4, 0.6) }}>
          {ladder.map(([nm, c, pc], i) => (
            <div key={i} style={{ fontFamily: MONO, fontSize: 15, fontWeight: 600, color: c as string, border: `1px solid ${c}`, borderRadius: 8, padding: "8px 10px", textAlign: "center", opacity: nm === "PLATINUM" ? 1 : 0.4, boxShadow: nm === "PLATINUM" ? `0 0 0 2px ${c}55` : "none" }}>{nm}<br />{pc}</div>
          ))}
        </div>
      </>)}

      {/* ===== BOOK / roster (88-102) ===== */}
      {t >= 87.8 && t < 102.4 && (<>
        <div style={{ ...CENTER, top: 210, fontFamily: SERIF, fontSize: 56, opacity: band(t, 88.2, 0.6, 101.6, 0.6), transform: tr(0, (1 - prog(t, 88.2, 0.8)) * -12) }}>The whole book, priced from memory.</div>
        {roster.map((r, i) => {
          const x = 210 + i * 385, op = band(t, 88.9 + i * 0.45, 0.55, 101.6, 0.6);
          return (
            <div key={r.id} style={{ ...A, left: x, top: 380, width: 340, height: 300, borderRadius: 18, border: `1px solid ${LINE}`, background: PANEL, padding: "26px 24px", opacity: op, transform: tr(0, (1 - clamp(sp(88.9 + i * 0.45, 13))) * 30) }}>
              <div style={{ fontFamily: MONO, fontSize: 26 }}>{r.id}</div>
              <div style={{ fontFamily: SERIF, fontWeight: 600, fontSize: 74, letterSpacing: "-0.03em", color: r.col, marginTop: 10 }}>{r.score}</div>
              <div style={{ display: "inline-block", marginTop: 8, fontFamily: MONO, fontSize: 16, fontWeight: 600, letterSpacing: "0.06em", color: r.col, border: `1px solid ${r.col}`, borderRadius: 8, padding: "5px 11px" }}>{r.tier}</div>
              <div style={{ fontFamily: SANS, fontSize: 15.5, color: DIM, marginTop: 16, lineHeight: 1.4 }}>{r.sub}</div>
            </div>
          );
        })}
      </>)}

      {/* ===== DELETION (96-118) ===== */}
      {t >= 96 && t < 100 && (
        <div style={{ ...CENTER, top: 470, fontFamily: MONO, fontSize: 34, color: BAD, letterSpacing: "0.12em", textTransform: "uppercase", opacity: band(t, 96.4, 0.5, 99.4, 0.5) }}>Erase the memory</div>
      )}
      <AbsoluteFill style={{ background: BAD, mixBlendMode: "screen", opacity: band(t, 104.0, 0.1, 104.25, 0.5) * 0.5, pointerEvents: "none" }} />
      {t >= 108 && t < 118.4 && (<>
        <div style={{ ...CENTER, top: 880, fontFamily: SERIF, fontSize: 50, opacity: band(t, 108.4, 0.7, 117.6, 0.6), transform: tr(0, (1 - prog(t, 108.4, 0.9)) * 16) }}>The only variable was memory.</div>
        <div style={{ ...CENTER, top: 962, fontFamily: SANS, fontSize: 20, color: MID, opacity: band(t, 109.0, 0.7, 117.6, 0.6) }}>No fallback quietly kept working. Fail-closed, by design.</div>
      </>)}

      {/* ===== ONCHAIN (118-132) ===== */}
      {t >= 117.8 && t < 132.4 && (<>
        <div style={{ ...A, left: 210, top: 350, width: 560, fontFamily: SERIF, fontSize: 58, opacity: band(t, 118.2, 0.6, 131.6, 0.6), transform: tr((1 - clamp(sp(118.2))) * -20) }}>Every decision, provable on Base.</div>
        <div style={{ ...A, left: 212, top: 548, width: 520, fontFamily: SANS, fontSize: 20, color: MID, lineHeight: 1.5, opacity: band(t, 118.8, 0.6, 131.6, 0.6) }}>The recalled tier is published to Base mainnet as an EAS attestation, and Meritor is a registered agent on Virtuals ACP.</div>
        <div style={{ ...A, left: 800, top: 300, width: 660, borderRadius: 20, border: `1px solid #3a3226`, background: "rgba(20,16,11,.78)", padding: "34px 36px", opacity: band(t, 119.0, 0.6, 131.6, 0.6), transform: tr((1 - clamp(sp(119.0, 13))) * 44) }}>
          <div style={{ display: "inline-flex", alignItems: "center", gap: 10, fontFamily: MONO, fontSize: 15, color: CYAN, background: "rgba(99,219,230,.1)", padding: "7px 14px", borderRadius: 999, marginBottom: 22 }}><span style={{ width: 9, height: 9, borderRadius: 999, background: CYAN, display: "inline-block" }} /> Base mainnet · confirmed</div>
          {[["Claim", "0xALPHA → PLATINUM (856)", CYAN], ["Attestation", "0x66c791…9a0e2a", INK], ["Transaction", "0xfcb465…13110f61", INK], ["Block", "50,862,970", INK], ["ACP identity", "ERC-8004 #84921", INK]].map(([k, v, c], i) => (
            <div key={i} style={{ display: "flex", justifyContent: "space-between", gap: 20, padding: "11px 0", borderBottom: i < 4 ? `1px solid #2a2419` : "none", fontSize: 18 }}>
              <span style={{ color: DIM }}>{k}</span><span style={{ fontFamily: MONO, color: c as string }}>{v}</span>
            </div>
          ))}
        </div>
      </>)}

      {/* ===== TESTS / STACKS strip (131-139) ===== */}
      {t >= 130.8 && t < 139.4 && (<>
        <div style={{ ...CENTER, top: 320, fontFamily: SERIF, fontSize: 52, opacity: band(t, 131.2, 0.6, 138.6, 0.6) }}>Verifiable, not vibes.</div>
        <div style={{ ...A, left: 360, top: 470, width: 1200, display: "flex", justifyContent: "space-between", opacity: band(t, 131.8, 0.6, 138.6, 0.6) }}>
          {[["39", "tests green"], ["6", "memory primitives"], ["make", "reproduce"], ["x1.25", "verified stacks"]].map(([n, l], i) => (
            <div key={i} style={{ textAlign: "center", transform: tr(0, (1 - clamp(sp(131.8 + i * 0.25, 13))) * 18) }}>
              <div style={{ fontFamily: SERIF, fontWeight: 600, fontSize: 60, color: INK }}>{n}</div>
              <div style={{ fontFamily: MONO, fontSize: 15, color: DIM, marginTop: 8, letterSpacing: "0.05em" }}>{l}</div>
            </div>
          ))}
        </div>
      </>)}

      {/* ===== CLOSE (139-144) ===== */}
      {t >= 138.8 && (() => {
        const op = band(t, 139.2, 0.8, 144, 1.4);
        return (<>
          <img src={MARBLE} style={{ ...A, left: "50%", top: "50%", width: 620, height: 820, objectFit: "cover", borderRadius: 18, transform: "translate(-50%,-50%)", opacity: op * 0.16 }} />
          <img src={WORDMARK} style={{ ...A, left: "50%", top: 400, height: 130, transform: `translateX(-50%) translateY(${(1 - clamp(sp(139.2))) * 16}px)`, opacity: op }} />
          <div style={{ ...CENTER, top: 572, fontFamily: SERIF, fontSize: 42, color: MID, opacity: band(t, 139.9, 0.8, 144, 1.4) }}>Credit that remembers.</div>
          <div style={{ ...CENTER, top: 664, fontFamily: MONO, fontSize: 20, color: DIM, letterSpacing: "0.18em", textTransform: "uppercase", opacity: band(t, 140.3, 0.8, 144, 1.4) }}>Sibyl Memory · Base · Virtuals</div>
        </>);
      })()}
    </AbsoluteFill>
  );
};
