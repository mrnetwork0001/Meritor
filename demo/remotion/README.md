# Meritor teaser (Remotion)

A ~2:05 motion-graphics teaser for Meritor, built with [Remotion](https://remotion.dev).

```bash
cd demo/remotion
npm install
npm run render        # copies brand assets into public/, renders out/meritor.mp4 (1080p, 30fps)
npm run studio        # live preview / edit
```

`src/Meritor.tsx` is the whole timeline (frame-driven). Brand assets are copied
from `web/assets/` by the `setup` script. The rendered `out/` and copied
`public/*.png` are gitignored; a compressed 720p cut lives at
`demo/meritor-teaser-720.mp4`.

## Voiceover

`vo-gen.js` generates the narration with ElevenLabs (one clip per beat), then
ffmpeg places each at its timecode and mixes it onto the render:

```bash
export ELEVENLABS_API_KEY=...
node vo-gen.js                       # writes vo/s01..s09.mp3 (~720 characters)
# then mux with the adelay/amix ffmpeg command (see project notes)
```

`demo/meritor-teaser-narrated-720.mp4` is the narrated cut.
