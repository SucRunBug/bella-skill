# Portable MV engine API

Copy `assets/animation-base/` to a new project and work in that project. Do not author user scenes inside the installed skill. Run `npm ci` using its committed lockfile. Runtime prerequisites are Node.js, Chrome/Chromium, ffmpeg and ffprobe. All JavaScript dependencies load locally; captions use installed system fonts, including Chinese font fallbacks. No CDN, remote font, AI API, ASR, music synthesis or automatic word aligner is included.

## Project contract

`src/config.js` declares `const PROJECT = {...}`. Fields:

- `status`: `unimplemented`, `draft` or `authored`. The empty template is deliberately unimplemented. Set authored only for actual authored scenes. The example is never a substitute.
- `duration`: positive seconds; `fps`: integer 1–120, default 24; `bpm`: positive number; `offset`: first downbeat in seconds.
- `width`, `height`: even pixel dimensions, default 1920×1080. Use 1080×1920 for portrait or 1080×1080 for square. `W` and `H` are these actual logical/output dimensions. Compose against `W/H`; changing size does not automatically reframe a landscape scene. The upstream reference sheets and example are landscape designs.
- `audio`: local project-relative or absolute file path, or null. `--audio` overrides it. Both `--clip` and `--encode` read this setting. The source audio must cover the configured project duration; longer audio is trimmed. Audio is muxed as AAC; it is not generated.
- `captions`: `karaoke`, `line`, `off`. `captionFont` optionally selects installed local fonts. `captionSafeBottom` defaults to 0.08 of frame height. Captions wrap within the bottom safe region, scale down to fit up to three lines, and fail if a line is still too long: split that lyric row.

`--fps=N` changes both rendering and output metadata. Frame times are `index/fps`; the half-open interval `[0,duration)` contains `ceil(duration*fps)` frames. Final MP4 duration can be up to one frame longer than the requested duration.

## Main timeline and reviewable drafts

Use **either** of these registration styles, not both:

```js
shots([[0, firstShot], [4, secondShot]]);
// or independent chapter files, loaded in studio.html before the browser load event:
chapter('verse-1', 0, 8, [[0, firstShot], [4, secondShot]]);
chapter('chorus-1', 8, PROJECT.duration, [[8, chorusShot]]);
```

A shot receives `(t, lt, dur)`: global song time, local shot time, shot duration. It paints the entire frame. Render state must be a pure function of time; workers render frames out of order. Choreograph visual transitions in scene code, using `brushWipe`, `iris`, camera transforms and matching shapes.

`window.validateTimeline()` returns `valid`, `structuralValid`, `coverageValid`, `structuralErrors`, `coverageErrors`, and flattened `shots:[{start,end,name,chapter?}]`. It detects empty registries, bad or duplicated times, overlapping chapters, mixing registration styles, and uncovered time. For a final export it requires complete `[0,PROJECT.duration)` coverage. A chapter's first shot must begin at its chapter start for full coverage.

`--draft --check` permits a nonempty partial timeline if its structure and lyrics are valid; uncovered intervals remain in the report. `--draft` image/range previews must lie entirely in registered shot intervals. Sampling an uncovered interval fails explicitly. An empty template never passes check. `--encode` always requires full frame coverage, including when used with draft.

`window.mvMetadata()` reports status, effective fps, size, duration, audio setting, example flag, timeline, and lyric timing provenance. `node render.mjs --check` prints exactly one `MV_CHECK=<JSON>` line and returns a nonzero exit code for a failed check. This is a static registry/syntax check, not a visual review; keep scene initialization pure and defer DOM/p5 drawing into shot functions. Real browser rendering also catches script errors.

## Lyrics and timing honesty

`src/lyrics.js` declares `const MV_LYRICS = [...]`:

```js
const MV_LYRICS = [
  {start:0, end:3, text:'第一句歌词', timing:'approximate', source:'weighted-active-audio-estimate'},
  {start:3, end:5, text:'你好世界', timing:'provided', source:'user verified timestamps',
   wordTiming:'exact', words:[{start:3,end:4,text:'你好'}, {start:4,end:5,text:'世界'}]},
];
```

Every line needs ordered, nonoverlapping `start/end`, nonempty `text`, `timing` and `source`. Accepted line timing labels are `provided`, `approximate`, `aligned`, `exact`. `provided` can mean trusted line timestamps; it does not claim word timestamps are exact. Only `wordTiming:'exact'` (or `timing:'exact'`) enables per-word highlighting, and then valid `words` are mandatory. Concatenated word text must reproduce line text ignoring whitespace, with ordered word intervals inside the line. Do not invent an exact claim from estimated timings.

Karaoke without exact words advances continuously across the whole line's duration. `line` shows a static active line; `off` removes the overlay. Timing sources stay in metadata and project records; the finished video does not print uncertainty labels. Exact timestamps are supplied or verified by the author; this runtime does not obtain them from audio.

## Character and drawing tools

The MIT Clawd model includes five drawn views (eight directions with mirroring), 31 animated emotion presets, acted emotion changes, hats, arm hooks, smear trails and dance loops. Use `feel(name,t)`, `emotions(t,keys)`, `turn(t,t0,t1,a0,a1)`, `move(style,t)`, `jump`, `take`, `stroll`, `arcPt`, `spring` and `ring`. The 31 presets combine face, body motion and optional tint/emote; they are not a general action planner. Different character anatomy requires code and model-sheet work.

Use `boilSeed(stableKey)` for each independent drawn element and `boilKey` for characters whose call order can change. `paint()` and p5.brush create watercolour/ink shapes; `camBegin/camEnd` control a 2D camera. `docs/emotions.jpg` and `docs/views.jpg` are upstream reference assets. The full inherited API/style guide is [upstream-animation-guide.md](upstream-animation-guide.md); this skill's explicit caption and music-video requirements supersede that guide's default no-text rule.

## Commands

```sh
node render.mjs --check
node render.mjs --draft --check
node render.mjs --draft --sheet=0,1,2 --out=out/check/verse.jpg
node render.mjs --draft --strip=1:1.5 --cols=6 --w=320 --out=out/check/motion.jpg
node render.mjs --draft --sheet=1,1.2 --crop=700,300,400,400 --out=out/check/face.jpg
node render.mjs --draft --strip=1:1.5 --crop-at=960,780,500,400 --out=out/check/contact.jpg
node render.mjs --stills=1,3 --out=out/stills
node render.mjs --frames --workers=2 --frames-dir=out/frames
node render.mjs --encode --frames-dir=out/frames --out=out/video.mp4
node render.mjs --clip --range=0:3 --workers=2 --out=out/preview.mp4
node render.mjs --example=demo --sheet=0,2,5 --out=out/reference.jpg
node render.mjs --loop=emotions --png --out=out/loop-png
```

`--strip=a:b` is half-open and includes every frame on the configured fps grid. `--crop` uses screen coordinates; `--crop-at` follows a fixed numeric world point through the last active camera. Both accept four numeric values only. `--sheet` and `--stills` accept comma-separated seconds. Contact sheets have timestamp labels for QA. Loops are declared as `LOOPS.name=t=>{...}; LOOPS.name.len=4`; use `--clip` or `--png` to export them, with no lyrics/audio overlay. `--example=demo` deliberately sets the upstream landscape example's 11-second duration and disables captions/audio.

Other options: `--chrome=/absolute/path`, `CHROME_PATH`, `--soft-gl`, `--gpu-angle=vulkan|gl-egl`, `--ffmpeg=/path`, `--ffprobe=/path`, `--fps=N`, `--audio=local/file`, `--frames-dir=local/path`. `--dependency-root=/local/installed/project` is an optional development/review escape hatch to reuse an existing *local* dependency installation; normal projects use their own `npm ci`. It does not copy node_modules into the skill. Chrome makes requests only to an ephemeral localhost server; nonlocal network requests are blocked.

Skill repository maintenance checks run from the skill directory: `node --test tests/test_engine.mjs`. They are separate from authoring a copied project.

## Cache and export integrity

Cached JPEG frames use `f000000.jpg` and a `manifest.json`. Its SHA-256 identity covers all files in `src/`, `examples/`, `assets/` and `fonts/` (when present), `studio.html`, package metadata and lockfile, renderer code, effective configuration/fps, source audio content and render selection. Modifying source or configuration rejects old frames rather than mixing shots. Use a new `--frames-dir` or explicitly clear your own old output directory. Partial `--frames --range=a:b` runs can fill the same matching cache; `--encode` refuses missing, empty, corrupt-signature or unexpected frames.

ffmpeg failures return nonzero; child processes, browser and server are cleaned up. Before renaming a temporary MP4 to the requested destination, ffprobe verifies video dimensions, fps, decoded frame count, duration and pixel format, plus AAC/audio duration when audio is supplied. `<video.mp4>.metadata.json` records the effective settings, source fingerprint and verified stream parameters. This checks technical export integrity; contact sheets, motion strips and listening are still needed to review timing, composition and audio/visual meaning.
