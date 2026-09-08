const fs = require("fs");
const key = process.env.ELEVENLABS_API_KEY;
if (!key) { console.error("Set ELEVENLABS_API_KEY"); process.exit(1); }
const VOICE="CwhRBWXzGAHq8TQ4Fs17", MODEL="eleven_multilingual_v2";
const lines = [
 ["n01","What if an agent could remember who kept its word?"],
 ["n02","Onchain, they can't. So they demand a hundred and fifty percent collateral from everyone. Every session. Forever."],
 ["n03","Meritor changes that. It makes memory load-bearing."],
 ["n04","The kind you can remove, and watch everything break."],
 ["n05","It records every settled obligation, recalls it in a fresh session, and lets that record set the terms."],
 ["n06","A clean, multi-session history is scored to the top tier, and granted credit at zero collateral."],
 ["n07","Credit that could not exist without memory."],
 ["n08","Every counterparty is priced from what Meritor remembers. Gold, silver, even a single default."],
 ["n09","Now erase the memory. The very same request is refused. Nothing else changed."],
 ["n10","The only variable was memory."],
 ["n11","And every decision is provable, published to Base as an attestation any agent can verify."],
 ["n12","Meritor. Credit that remembers."],
];
console.log("chars:", lines.reduce((n,l)=>n+l[1].length,0));
(async()=>{ for(const [id,text] of lines){
  const r=await fetch(`https://api.elevenlabs.io/v1/text-to-speech/${VOICE}`,{method:"POST",headers:{"xi-api-key":key,"content-type":"application/json",accept:"audio/mpeg"},body:JSON.stringify({text,model_id:MODEL,voice_settings:{stability:0.5,similarity_boost:0.8,style:0.0,use_speaker_boost:true}})});
  if(!r.ok){console.error(id,"FAIL",r.status,(await r.text()).slice(0,140));process.exit(1);}
  fs.writeFileSync(`vo2/${id}.mp3`,Buffer.from(await r.arrayBuffer())); console.log(id,"ok",text.length);
} console.log("done"); })();
