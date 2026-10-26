# Provenance and redistribution

The bundled animation engine is adapted from [JohnHeibel/ClaudeAnimationBase](https://github.com/JohnHeibel/ClaudeAnimationBase), pinned to upstream commit `0ac8bf2b31942376cb6b8c4074715595d512acd2`. Upstream copyright is **Copyright (c) 2026 John Heibel**, under the MIT License. The original copyright and complete permission notice are preserved in the skill's `LICENSE` and `assets/animation-base/LICENSE`.

Copied upstream material: core/clawd/config/timeline/sheets JavaScript, the demo (moved to `examples/demo.js`), renderer and GPU probe, studio HTML, package manifests and lockfile, `docs/emotions.jpg`, `docs/views.jpg`, and the full guide in `references/upstream-animation-guide.md`. The runtime adapts dimensions, fonts, timeline registration, lyrics, metadata, cache validation, audio muxing and export checks. The starter scene is a clearly unimplemented placeholder; the upstream demo is opt-in reference material.

Do not distribute installed `node_modules`, `.git`, temporary outputs, generated videos/audio, or the large animated WebP reference. Dependencies retain their own licenses and are installed with the committed lockfile.

[JohnHeibel/PDoomVideo](https://github.com/JohnHeibel/PDoomVideo), inspected at `fa546a38092e75f2b079e6a86d6abc54dd525d17`, supplied conceptual workflow observations only (chapters, song-time functions, deterministic rendering and lyric-driven storytelling). No code, audio, scene scripts, storyboard, lyrics or images from that repository are bundled. Its inspected snapshot did not provide a separate license; do not infer permission from public visibility. The bundled runtime's reusable code derives from the separately MIT-licensed ClaudeAnimationBase.

Author claims about model-generated creative work in upstream READMEs are provenance statements, not independently established facts. Do not imply that the starter kit includes the original P(doom) song, authorizes third-party music, or automatically reproduces either upstream music video.
