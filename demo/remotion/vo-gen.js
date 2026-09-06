const fs = require("fs");
// Reads the ElevenLabs key from the environment. Set it before running:
//   export ELEVENLABS_API_KEY=...   then:  node vo-gen.js
const key = process.env.ELEVENLABS_API_KEY;
if (!key) { console.error("Set ELEVENLABS_API_KEY in your environment"); process.exit(1); }
const VOICE = "CwhRBWXzGAHq8TQ4Fs17", MODEL = "eleven_multilingual_v2";
const sections = [
  ["01", "Onchain agents can't remember who kept their word, so they demand a hundred and fifty percent collateral from everyone. Every session. Forever."],
  ["02", "Meritor changes that. It makes memory load-bearing."],
  ["03", "It records every settled obligation, recalls it in a fresh session, and lets that record set the terms."],
  ["04", "A counterparty with a clean, multi-session history is scored to the top tier, and granted credit at zero collateral."],
  ["05", "Every agent on the book is priced entirely from what Meritor remembers."],
  ["06", "Now, erase the memory. The very same request is refused. Nothing else has changed."],
  ["07", "The only variable was memory."],
  ["08", "And every decision is provable, published to Base as a portable attestation any agent can verify."],
  ["09", "Meritor. Credit that remembers."],
];
const total = sections.reduce((n, s) => n + s[1].length, 0);
console.log("total characters to generate:", total);
(async () => {
  for (const [id, text] of sections) {
    const res = await fetch(`https://api.elevenlabs.io/v1/text-to-speech/${VOICE}`, {
      method: "POST",
      headers: { "xi-api-key": key, "content-type": "application/json", accept: "audio/mpeg" },
      body: JSON.stringify({ text, model_id: MODEL, voice_settings: { stability: 0.5, similarity_boost: 0.8, style: 0.0, use_speaker_boost: true } }),
    });
    if (!res.ok) { console.error(id, "FAILED", res.status, (await res.text()).slice(0, 160)); process.exit(1); }
    const buf = Buffer.from(await res.arrayBuffer());
    fs.writeFileSync(`vo/s${id}.mp3`, buf);
    console.log(id, "ok", `${text.length} chars`, `${buf.length} bytes`);
  }
  console.log("done");
})();
