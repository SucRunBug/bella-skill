// Bella's portable render checks. Only Node built-ins are needed for --check and manifest tests.
import { readFileSync, readdirSync, statSync, existsSync, writeFileSync, renameSync, mkdirSync } from 'node:fs';
import { resolve, join, relative, dirname } from 'node:path';
import { createHash } from 'node:crypto';
import vm from 'node:vm';

export function parseArgs(argv) {
  const args = {};
  for (const arg of argv) {
    if (!arg.startsWith('--')) throw new Error(`Expected --flag or --flag=value: ${arg}`);
    const at = arg.indexOf('='), key = arg.slice(2, at < 0 ? undefined : at);
    if (key in args) throw new Error(`Repeated flag --${key}`);
    args[key] = at < 0 ? true : arg.slice(at + 1);
  }
  return args;
}
export function projectConfig(root, fpsOverride, example) {
  const p = vm.runInNewContext(readFileSync(join(root, 'src/config.js'), 'utf8') + '\nJSON.parse(JSON.stringify(PROJECT))', {}, { timeout: 2000 });
  if (example) { if (example !== 'demo') throw new Error('Only --example=demo is available'); Object.assign(p, { duration: 11, status: 'authored', width: 1920, height: 1080, captions: 'off', audio: null }); }
  p.fps = +(fpsOverride ?? p.fps ?? 24); p.width ??= 1920; p.height ??= 1080;
  if (!Number.isFinite(p.duration) || p.duration <= 0) throw new Error('PROJECT.duration must be a positive number');
  if (!Number.isInteger(p.fps) || p.fps < 1 || p.fps > 120) throw new Error('fps must be an integer from 1 to 120');
  for (const key of ['width', 'height']) if (!Number.isInteger(p[key]) || p[key] < 16 || p[key] > 8192 || p[key] % 2) throw new Error(`${key} must be an even integer from 16 to 8192`);
  if (!Number.isFinite(p.bpm) || p.bpm <= 0 || !Number.isFinite(p.offset ?? 0)) throw new Error('Set positive bpm and a finite offset');
  if (!['karaoke', 'line', 'off'].includes(p.captions)) throw new Error('PROJECT.captions must be karaoke, line or off');
  if (!['unimplemented', 'draft', 'authored'].includes(p.status)) throw new Error('PROJECT.status must be unimplemented, draft or authored');
  if (p.captionSafeBottom != null && (!Number.isFinite(p.captionSafeBottom) || p.captionSafeBottom < 0 || p.captionSafeBottom > .35)) throw new Error('captionSafeBottom must be a fraction from 0 to .35');
  if (p.audio != null && (typeof p.audio !== 'string' || /^(https?:|data:|\/\/)/i.test(p.audio))) throw new Error('PROJECT.audio must be a local file path or null');
  return p;
}
export function registryMetadata(root, project, example) {
  root = resolve(root);
  const context = vm.createContext({ window: { MV_FPS: project.fps, MV_EXAMPLE: !!example }, console, URLSearchParams, location: { search: '?render' } });
  const html = readFileSync(join(root, 'studio.html'), 'utf8');
  const sources = [...html.matchAll(/<script\b[^>]*\bsrc=["']([^"']+)["'][^>]*>/gi)].map(m => m[1]).filter(s => !s.startsWith('node_modules/'));
  sources.push(example ? 'examples/demo.js' : 'src/scenes/video.js');
  for (const name of [...new Set(sources)]) {
    if (/^(https?:|\/\/)/i.test(name) || !resolve(root, name).startsWith(root + '/')) throw new Error(`Nonlocal script: ${name}`);
    vm.runInContext(readFileSync(resolve(root, name), 'utf8'), context, { filename: name, timeout: 5000 });
    if (name === 'src/config.js') vm.runInContext(`Object.assign(PROJECT, ${JSON.stringify(project)})`, context);
  }
  const metadata = vm.runInContext('JSON.stringify(window.mvMetadata())', context, { timeout: 2000 });
  return JSON.parse(metadata);
}
export function assertReady(meta, draft = false, loop = null) {
  if (loop) return;
  if (!draft && meta.status !== 'authored') throw new Error(`Video is ${meta.status}; implement the scenes and set PROJECT.status='authored', or use --draft for an explicit preview.`);
  if (!(draft ? meta.timeline?.structuralValid : meta.timeline?.valid)) throw new Error('Invalid timeline: ' + (draft ? meta.timeline?.structuralErrors || meta.timeline?.errors || [] : meta.timeline?.errors || []).join('; '));
  if (!meta.lyrics?.valid) throw new Error('Invalid lyrics: ' + (meta.lyrics?.errors || []).join('; '));
}
export function frameRange(spec, duration, fps) {
  const a = spec ? String(spec).split(':').map(Number) : [0, duration];
  if (a.length !== 2 || a.some(x => !Number.isFinite(x)) || a[0] < 0 || a[1] <= a[0] || a[1] > duration + 1e-6) throw new Error(`Invalid range: ${spec}; expected 0 <= start < end <= ${duration}`);
  const first = Math.max(0, Math.ceil(a[0] * fps - 1e-8)), end = Math.min(Math.ceil(duration * fps - 1e-8), Math.ceil(a[1] * fps - 1e-8));
  if (end <= first) throw new Error('Range does not contain any frames at this fps');
  return { first, end, start: first / fps, duration: (end - first) / fps, count: end - first };
}
export function sourceFingerprint(root, project, selection = {}) {
  const hash = createHash('sha256'), files = [];
  const visit = dir => {
    for (const name of readdirSync(dir).sort()) {
      const full = join(dir, name), st = statSync(full);
      if (st.isDirectory()) visit(full); else files.push(relative(root, full));
    }
  };
  for (const dir of ['src', 'examples', 'assets', 'fonts']) if (existsSync(join(root, dir))) visit(join(root, dir));
  for (const name of ['studio.html', 'package.json', 'package-lock.json', 'render.mjs', 'render-utils.mjs']) if (existsSync(join(root, name))) files.push(name);
  for (const name of files.sort()) { hash.update(name + '\0'); hash.update(readFileSync(join(root, name))); hash.update('\0'); }
  hash.update(JSON.stringify(project)); hash.update(JSON.stringify(selection));
  // Audio is part of a project's identity even if it lives outside src/.
  if (selection.audio) { hash.update(resolve(root, selection.audio)); hash.update(readFileSync(resolve(root, selection.audio))); }
  return { fingerprint: hash.digest('hex'), files };
}
export function atomicWrite(file, data) {
  mkdirSync(dirname(file), { recursive: true }); writeFileSync(file + '.tmp', data); renameSync(file + '.tmp', file);
}
export function frameFile(dir, index, extension = 'jpg') { return join(dir, `f${String(index).padStart(6, '0')}.${extension}`); }
export function ensureManifest(dir, expected, create = true) {
  const path = join(dir, 'manifest.json'); mkdirSync(dir, { recursive: true });
  if (existsSync(path)) {
    const old = JSON.parse(readFileSync(path, 'utf8'));
    if (old.fingerprint !== expected.fingerprint || old.frameCount !== expected.frameCount || old.fps !== expected.fps || old.format !== expected.format) throw new Error(`Frame cache does not match source/config/fps. Use a new --frames-dir or remove ${dir} explicitly; stale frames were not reused.`);
    return old;
  }
  if (!create) throw new Error(`Missing ${path}. Render --frames first.`);
  if (readdirSync(dir).some(n => /^f\d+\.(jpg|png)$/.test(n))) throw new Error(`Untracked old frames in ${dir}; use a new --frames-dir or clear it explicitly.`);
  atomicWrite(path, JSON.stringify(expected, null, 2) + '\n'); return expected;
}
export function assertCompleteFrames(dir, manifest) {
  const expected = new Set();
  for (let i = 0; i < manifest.frameCount; i++) {
    const file = frameFile(dir, i, manifest.format); expected.add(file.split('/').at(-1));
    if (!existsSync(file) || statSync(file).size < 4) throw new Error(`Missing or empty frame ${i}: ${file}. Complete the full timeline before --encode.`);
    const b = readFileSync(file);
    if (manifest.format === 'jpg' && (b[0] !== 255 || b[1] !== 216 || b[b.length - 2] !== 255 || b.at(-1) !== 217)) throw new Error(`Corrupt JPEG: ${file}`);
    if (manifest.format === 'png' && !b.subarray(0, 8).equals(Buffer.from([137,80,78,71,13,10,26,10]))) throw new Error(`Corrupt PNG: ${file}`);
  }
  const extra = readdirSync(dir).filter(n => /^f\d+\.(jpg|png)$/.test(n) && !expected.has(n));
  if (extra.length) throw new Error(`Unexpected frames in ${dir}: ${extra.slice(0, 3).join(', ')}`);
}

export function assertTimesCovered(meta, times) {
  for (const t of times) {
    const time = Math.min(t, meta.duration - 1e-9);
    if (!meta.timeline.shots.some(s => time >= s.start - 1e-8 && time < s.end)) throw new Error(`No registered shot covers ${t}s. Draft previews may only use authored intervals.`);
  }
}
