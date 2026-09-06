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
