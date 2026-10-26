# Bella Music MV runtime

This is a portable, local rendering project adapted from John Heibel's MIT-licensed ClaudeAnimationBase. Preserve LICENSE when copying it.

Copy this directory into a new project, run `npm ci`, and install Chrome, ffmpeg and ffprobe. `node render.mjs --check` intentionally rejects the untouched template. Implement `src/scenes/video.js`, synchronize `src/lyrics.js`, and set `PROJECT.status` to `authored` only when the video is actually authored.

The upstream example is explicitly separate: `node render.mjs --example=demo --sheet=0,2,5 --out=out/demo.jpg`. It is not a user's completed music video.

See the parent skill's `references/engine-api.md` and `references/provenance.md`. Dependencies and fonts are local; no generative API or ASR is included.
