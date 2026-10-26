// Lyric overlay and inspectable metadata. This file contains no ASR or generative API calls.
function validateMVLyrics() {
  const errors = [], warnings = [];
  if (!Array.isArray(MV_LYRICS)) return { valid: false, errors: ['MV_LYRICS must be an array'], warnings, rows: [] };
  const rows = MV_LYRICS.map((row, i) => {
    const exact = row.wordTiming === 'exact' || row.timing === 'exact';
    if (!Number.isFinite(row.start) || !Number.isFinite(row.end) || row.start < 0 || row.end <= row.start || row.end > PROJECT.duration + 1e-6) errors.push(`lyric ${i}: invalid interval`);
    if (i && row.start < MV_LYRICS[i - 1].end - 1e-6) errors.push(`lyric ${i}: overlapping or unordered rows`);
    if (typeof row.text !== 'string' || !row.text.trim()) errors.push(`lyric ${i}: text is required`);
    if (!['provided', 'approximate', 'aligned', 'exact'].includes(row.timing)) errors.push(`lyric ${i}: timing must be provided, approximate, aligned or exact`);
    if (typeof row.source !== 'string' || !row.source.trim()) errors.push(`lyric ${i}: record a timing source`);
    if (row.words != null && !Array.isArray(row.words)) errors.push(`lyric ${i}: words must be an array`);
    if (exact) {
      if (!Array.isArray(row.words) || !row.words.length) errors.push(`lyric ${i}: exact word timing requires words`);
      else {
        row.words.forEach((w, j) => {
          if (!Number.isFinite(w.start) || !Number.isFinite(w.end) || w.start < row.start || w.end > row.end + 1e-6 || w.end <= w.start || (j && w.start < row.words[j - 1].end - 1e-6)) errors.push(`lyric ${i}, word ${j}: invalid interval`);
          if (typeof w.text !== 'string' || !w.text.trim()) errors.push(`lyric ${i}, word ${j}: text is required`);
        });
        if (row.words.map(w => w.text).join('').replace(/\s/g, '') !== String(row.text).replace(/\s/g, '')) errors.push(`lyric ${i}: word text must reproduce line text (ignoring whitespace)`);
      }
    } else if (row.words?.length) warnings.push(`lyric ${i}: words ignored without exact word timing; whole-line progress is used`);
    return { start: row.start, end: row.end, timing: row.timing, wordTiming: exact ? 'exact' : 'none', source: row.source };
  });
  return { valid: errors.length === 0, errors, warnings, rows };
}

window.mvMetadata = () => ({
  status: PROJECT.status || 'unimplemented',
  width: W, height: H, fps: window.MV_FPS || PROJECT.fps || 24, duration: DUR,
  audio: PROJECT.audio || null, captions: PROJECT.captions || 'off',
  example: window.MV_EXAMPLE ? 'demo' : null,
  loops: Object.fromEntries(Object.entries(LOOPS).map(([name, fn]) => [name, {duration:fn.len}])),
  video: window.MV_VIDEO || null,
  timeline: window.validateTimeline(), lyrics: validateMVLyrics(),
});

function drawMVLyrics(c, t) {
  if (PROJECT.captions === 'off') return;
  const row = MV_LYRICS.find(r => t >= r.start && t < r.end);
  if (!row) return;
  const exact = (row.wordTiming === 'exact' || row.timing === 'exact') && row.words?.length;
  const maxWidth = W * .86;
  let fontSize = Math.round(Math.min(W, H) * .047), lines;
  const chars = Array.from(row.text), font = PROJECT.captionFont || 'system-ui, "PingFang SC", "Microsoft YaHei", sans-serif';
  const wrap = () => {
    c.font = `600 ${fontSize}px ${font}`;
    const result = [[]]; let width = 0;
    for (let i = 0; i < chars.length; i++) {
      const w = c.measureText(chars[i]).width;
      if (width + w > maxWidth && result.at(-1).length) { result.push([]); width = 0; }
      result.at(-1).push({ char: chars[i], index: i, width: w }); width += w;
    }
    return result;
  };
  do { lines = wrap(); if (lines.length <= 3) break; fontSize -= 2; } while (fontSize >= 16);
  if (lines.length > 3) throw new Error('Lyric line is too long for the caption safe area; split the lyric row.');
  const lineHeight = fontSize * 1.4, safe = H * (PROJECT.captionSafeBottom ?? .08);
  const boxH = lines.length * lineHeight + fontSize * .6, top = H - safe - boxH;
  const lineProgress = clamp((t - row.start) / (row.end - row.start));
  const total = lines.flat().reduce((n, item) => n + item.width, 0);
  // Each exact word owns a contiguous group of non-whitespace characters.
  const wordByChar = new Map();
  if (exact) {
    let ci = 0;
    row.words.forEach(w => {
      for (const wc of Array.from(w.text).filter(ch => !/\s/.test(ch))) {
        while (ci < chars.length && /\s/.test(chars[ci])) ci++;
        if (chars[ci] !== wc) throw new Error('Exact word text does not match lyric text.');
        wordByChar.set(ci++, w);
      }
    });
  }
  const wordWidths = new Map(), wordOffsets = new Map();
  for (const item of lines.flat()) { const w = wordByChar.get(item.index); if (w) wordWidths.set(w, (wordWidths.get(w) || 0) + item.width); }
  c.save(); c.globalAlpha = 1; c.globalCompositeOperation = 'source-over';
  c.fillStyle = 'rgba(25,20,32,.82)';
  c.beginPath(); c.roundRect(W * .045, top, W * .91, boxH, fontSize * .25); c.fill();
  c.font = `600 ${fontSize}px ${font}`; c.textAlign = 'left'; c.textBaseline = 'middle';
  let globalOffset = 0;
  lines.forEach((line, li) => {
    let x = (W - line.reduce((sum, item) => sum + item.width, 0)) / 2;
    const y = top + fontSize * .3 + lineHeight * (li + .5);
    for (const item of line) {
      c.fillStyle = '#FFF5E2'; c.fillText(item.char, x, y);
      let fraction = 0;
      if (PROJECT.captions === 'karaoke') {
        if (exact) {
          const w = wordByChar.get(item.index);
          if (w) {
            const offset = wordOffsets.get(w) || 0;
            fraction = clamp((clamp((t - w.start) / (w.end - w.start)) * wordWidths.get(w) - offset) / (item.width || 1));
            wordOffsets.set(w, offset + item.width);
          }
        } else fraction = clamp((lineProgress * total - globalOffset) / (item.width || 1));
        if (fraction > 0) {
          c.save(); c.beginPath(); c.rect(x - 1, y - lineHeight / 2, item.width * fraction + 1, lineHeight); c.clip();
          c.fillStyle = '#FFD061'; c.fillText(item.char, x, y); c.restore();
        }
      }
      x += item.width; globalOffset += item.width;
    }
  });
  c.restore();
}
