const fs = require("fs");
const key = process.env.ELEVENLABS_API_KEY;
if (!key) { console.error("Set ELEVENLABS_API_KEY"); process.exit(1); }
const VOICE="CwhRBWXzGAHq8TQ4Fs17", MODEL="eleven_multilingual_v2";
const lines = [
 ["l01","What if an agent could remember who kept its word?"],
 ["l02","Onchain, they can't. Between sessions, every counterparty is a stranger again."],
 ["l03","So agents demand a hundred and fifty percent collateral from everyone, every session, forever. And real credit between them never happens."],
 ["l04","Meritor changes that. It makes memory load-bearing."],
 ["l05","Here's how. First, it persists. After every job and every settlement, Meritor appends a signed credit event to a journal in Sibyl Memory."],
 ["l06","The outcome, the repayment timing, the dispute flags, and the onchain proof. An append-only record of who did what."],
 ["l07","Then it recalls. A fresh session holds nothing in memory."],
 ["l08","On a credit request, it replays the entire journal into an explainable score, from zero to a thousand."],
 ["l09","Finally, it decides. The score sets a collateral tier, and the tier sets the terms."],
 ["l10","A clean, multi-session history reaches the top tier, and unlocks credit at zero collateral. Credit that could not exist without memory."],
 ["l11","Every counterparty is priced the same way. Gold, silver, and a recent default, remembered and held to a lower tier."],
 ["l12","Now, the test that matters. Erase the memory."],
 ["l13","The very same agent, the very same request, is refused. Zero-trust, a hundred and fifty percent collateral."],
 ["l14","The only variable was memory. No fallback quietly kept working. Meritor fails closed, by design."],
 ["l15","And every decision is provable. The recalled tier is published to Base mainnet as an attestation any agent can verify, and Meritor is registered on Virtuals ACP."],
 ["l16","Thirty-nine tests green. Six memory primitives. Reproducible from a clean clone."],
 ["l17","Meritor. Credit that remembers."],
];
console.log("chars:", lines.reduce((n,l)=>n+l[1].length,0));
(async()=>{ for(const [id,text] of lines){
  const r=await fetch(`https://api.elevenlabs.io/v1/text-to-speech/${VOICE}`,{method:"POST",headers:{"xi-api-key":key,"content-type":"application/json",accept:"audio/mpeg"},body:JSON.stringify({text,model_id:MODEL,voice_settings:{stability:0.5,similarity_boost:0.8,style:0.0,use_speaker_boost:true}})});
  if(!r.ok){console.error(id,"FAIL",r.status,(await r.text()).slice(0,140));process.exit(1);}
  fs.writeFileSync(`vo3/${id}.mp3`,Buffer.from(await r.arrayBuffer())); console.log(id,"ok",text.length);
} console.log("done"); })();
