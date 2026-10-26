// timeline.js: the shot list, standalone loops, and a brush-wipe transition.
//
// shots([[t0, fn], [t1, fn], ...]) registers shots in time order. Each fn(t, lt, dur) is called with t = video time,
// lt = time since the shot started, dur = the shot's length. It paints the WHOLE frame, background included, and must be
// a pure function of t: frames render in parallel and out of order, so nothing may carry over from one frame to the next.

const SHOTS = [];
function shots(list) { SHOTS.push(...list); SHOTS.sort((a, b) => a[0] - b[0]); }
const MV_CHAPTERS = [];
function chapter(name, start, end, list) {
  MV_CHAPTERS.push({ name, start, end, shots: list });
  MV_CHAPTERS.sort((a, b) => a.start - b.start);
}
const LOOPS = {};

// Static registry checks are available to the CLI and in Chrome's console.
window.validateTimeline = () => {
  const structuralErrors = [], coverageErrors = [], eps = 1e-6, flatShots = [];
  const checkShots = (list, a, b, label, chapterName) => {
    if (!Array.isArray(list) || !list.length) { structuralErrors.push(`${label}: no shots`); return; }
    list.forEach((s, i) => {
      if (!Array.isArray(s) || !Number.isFinite(s[0]) || typeof s[1] !== 'function') structuralErrors.push(`${label}: invalid shot ${i}`);
      else {
        if (s[0] < a - eps || s[0] >= b || (i && s[0] <= list[i - 1][0])) structuralErrors.push(`${label}: shot ${i} is out of range or unordered`);
        flatShots.push({ start: s[0], end: i + 1 < list.length ? list[i + 1][0] : b, name: s[1].name || 'anonymous', ...(chapterName ? {chapter:chapterName} : {}) });
      }
    });
    if (Math.abs(list[0][0] - a) > eps) coverageErrors.push(`${label}: uncovered ${a}..${list[0][0]}s before first shot`);
  };
  if (SHOTS.length && MV_CHAPTERS.length) structuralErrors.push('Use shots() OR chapter() on the main timeline, not both.');
  if (MV_CHAPTERS.length) {
    let cursor = 0; const names = new Set();
    for (const c of MV_CHAPTERS) {
      if (!c.name || names.has(c.name)) structuralErrors.push(`Duplicate or empty chapter name: ${c.name}`);
      names.add(c.name);
      if (!Number.isFinite(c.start) || !Number.isFinite(c.end) || c.start < 0 || c.end <= c.start || c.end > DUR + eps) structuralErrors.push(`${c.name}: invalid interval`);
      if (c.start < cursor - eps) structuralErrors.push(`${c.name}: chapter overlaps the previous chapter ending at ${cursor}s`);
      else if (c.start > cursor + eps) coverageErrors.push(`${c.name}: uncovered ${cursor}..${c.start}s`);
      checkShots(c.shots, c.start, c.end, c.name, c.name); cursor = c.end;
    }
    if (Math.abs(cursor - DUR) > eps) coverageErrors.push(`Chapters end at ${cursor}s; expected ${DUR}s.`);
  } else checkShots(SHOTS, 0, DUR, 'timeline');
  const structuralValid = structuralErrors.length === 0, coverageValid = coverageErrors.length === 0 && flatShots.length > 0;
  return { valid: structuralValid && coverageValid, structuralValid, coverageValid, structuralErrors, coverageErrors,
    errors: [...structuralErrors,...coverageErrors], warnings: coverageErrors,
    chapters: MV_CHAPTERS.map(c => ({name:c.name,start:c.start,end:c.end,shots:Array.isArray(c.shots)?c.shots.map(s=>s[0]):[]})), shots:flatShots };
};

function drawWorld(t) {
  if (window.LOOP) window.LOOP(t);
  else {
    const time = Math.min(t, DUR - 1e-9);
    const c = MV_CHAPTERS.find(c => time >= c.start && time < c.end);
    const list = c ? c.shots : MV_CHAPTERS.length ? [] : SHOTS;
    if (!list.length) { if (SHOTS.length || MV_CHAPTERS.length) throw new Error(`No registered shot covers ${t}s.`); placeholder(t); }
    else {
      let i = 0; while (i + 1 < list.length && time >= list[i + 1][0]) i++;
      if (time < list[0][0]) throw new Error(`No shot covers ${time}s.`);
      const end = i + 1 < list.length ? list[i + 1][0] : c ? c.end : DUR;
      list[i][1](t, t - list[i][0], end - list[i][0]);
      CAM = null;
    }
  }
  flushLetters();
}

function placeholder(t) {
  // Clearly incomplete studio preview. The final exporter rejects missing timeline coverage.
  letter('未实现 · UNIMPLEMENTED', W / 2, H / 2, Math.min(W, H) * .045, PAL.ink);
}

// ---------- brush wipe ----------
// A transition: fat paint strokes sweep across to cover the frame (p 0 → .5), then drag off (p .5 → 1).
// Cut to the next shot at p = .5, under full cover. Call it last in both shots, in screen space (outside a camera):
//   end of shot A:   if (lt > dur - .3) brushWipe((lt - (dur - .3)) / .6);
//   start of shot B: if (lt < .3) brushWipe(.5 + lt / .6);
function brushWipe(p, cols = [PAL.clayDk, PAL.clay]) {
  if (p <= 0 || p >= 1) return;
  const [c1, c2] = cols, n = 5, bh = (H + 420) / n + 40;
  push(); translate(W / 2, H / 2); rotate(-.1); translate(-W / 2, -H / 2);
  for (let i = 0; i < n; i++) {
    const y0 = -230 + i * (H + 420) / n, d = [0, .14, .06, .18, .1][i];
    const q = p < .5 ? easeOut(clamp((p * 2 - d) / (1 - d))) : ease(clamp(((p - .5) * 2 - d) / (1 - d)));
    const x0 = p < .5 ? -300 : lerp(-300, W + 400, q), x1 = p < .5 ? lerp(-300, W + 400, q) : W + 400;
    if (x1 - x0 < 30) continue;
    const pts = [], rag = k => 40 + 50 * hash(i * 31 + k) + jit(12);
    for (let k = 0; k <= 8; k++) pts.push([lerp(x0, x1, k / 8), y0 + Math.sin(k * .9 + i) * 14 + jit(5)]);
    for (let k = 1; k < 9; k++) pts.push([x1 + rag(k) - 40, y0 + bh * k / 9]);
    for (let k = 8; k >= 0; k--) pts.push([lerp(x0, x1, k / 8), y0 + bh + Math.sin(k * .8 + i * 2) * 14 + jit(5)]);
    if (p >= .5) for (let k = 8; k > 0; k--) pts.push([x0 - rag(k + 20) + 40, y0 + bh * k / 9]);
    paint(pts, { wash: i % 2 ? c1 : c2, washOp: 255, fill: i % 2 ? c2 : c1, fillOp: 70, bleed: .05, tex: .8, border: .6, ink: null,
      hatch: { d: 44, a: 0, o: { rand: .6, gradient: .5 }, b: 'charcoal', c: i % 2 ? c2 : PAL.cream, w: .8 } });
  }
  pop();
}
