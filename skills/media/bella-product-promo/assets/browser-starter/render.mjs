#!/usr/bin/env node
// Deterministic browser frame rendering for native-html, gsap and threejs only.
import {createServer} from 'node:http';
import {readFile, mkdir, access} from 'node:fs/promises';
import {resolve, dirname, extname, sep} from 'node:path';
import {spawnSync} from 'node:child_process';

function argumentsOf(argv) {
  const opts = {project: '.', output: 'output.mp4', samples: 1, shutter: 0.5, 'frames-only': false};
  const valued = new Set(['project', 'output', 'frames', 'audio', 'samples', 'shutter', 'ffmpeg']);
  for (let i = 0; i < argv.length; i++) {
    const arg = argv[i];
    if (arg === '--help') { console.log('node render.mjs --project DIR --output FILE [--audio FILE] [--samples 1|3|4] [--shutter 0..1] [--frames DIR] [--frames-only] [--ffmpeg PATH]'); process.exit(0); }
    if (arg === '--frames-only') { opts['frames-only'] = true; continue; }
    if (!arg.startsWith('--') || !valued.has(arg.slice(2)) || !argv[i + 1] || argv[i + 1].startsWith('--')) throw new Error(`Unknown or incomplete argument: ${arg}`);
    opts[arg.slice(2)] = argv[++i];
  }
  opts.samples = Number(opts.samples); opts.shutter = Number(opts.shutter);
  if (![1, 3, 4].includes(opts.samples)) throw new Error('--samples must be 1, 3 or 4');
  if (!Number.isFinite(opts.shutter) || opts.shutter < 0 || opts.shutter > 1) throw new Error('--shutter must be between 0 and 1');
  return opts;
}

async function exists(path) { try { await access(path); return true; } catch { return false; } }
function run(command, args) {
  const result = spawnSync(command, args, {encoding: 'utf8', maxBuffer: 16 * 1024 * 1024});
  if (result.error) throw new Error(`${command}: ${result.error.message}`);
  if (result.status !== 0) throw new Error(`${command} failed: ${result.stderr || result.stdout}`);
}
function validate(brief) {
  if (brief.status !== 'authored') throw new Error('Project is unstarted: author the actual scenes before setting status=authored.');
  if (brief.schema_version !== 1 || !['native-html', 'gsap', 'threejs'].includes(brief.tech_id)) throw new Error('Only schema 1 browser projects (native-html, gsap, threejs) are supported; use the native exporter for other routes.');
  if (!Number.isInteger(brief.fps) || brief.fps < 1 || brief.fps > 120) throw new Error('fps must be an integer between 1 and 120');
  if (typeof brief.duration !== 'number' || !Number.isFinite(brief.duration) || brief.duration < 0.05 || brief.duration > 3600) throw new Error('Invalid duration');
  for (const key of ['width', 'height']) if (!Number.isInteger(brief[key]) || brief[key] < 2 || brief[key] > 8192 || brief[key] % 2) throw new Error(`${key} must be even, between 2 and 8192`);
  if (Math.abs(brief.duration * brief.fps - Math.round(brief.duration * brief.fps)) > 1e-6) throw new Error('duration * fps must be an integer');
}

let server, browser;
try {
  const options = argumentsOf(process.argv.slice(2));
  const project = resolve(options.project);
  const brief = JSON.parse(await readFile(resolve(project, 'brief.json'), 'utf8'));
  validate(brief);
  const entry = await readFile(resolve(project, 'engine/index.html'), 'utf8');
  if (entry.includes('BELLA_PROMO_UNAUTHORED')) throw new Error('engine/index.html is still the unmade placeholder.');
  const output = resolve(project, options.output);
  const frames = resolve(project, options.frames || `${options.output}.frames`);
  if (await exists(output)) throw new Error(`Refusing to overwrite output: ${output}`);
  if (await exists(frames)) throw new Error(`Refusing to overwrite frame directory: ${frames}`);
  const audioArg = options.audio || brief.audio;
  if (audioArg && typeof audioArg !== 'string') throw new Error('brief.audio must be a local path string or null');
  const audio = audioArg ? resolve(project, audioArg) : null;
  if (audio && !(await exists(audio))) throw new Error(`Audio file missing: ${audio}`);
  const ffmpeg = options.ffmpeg || process.env.FFMPEG || 'ffmpeg';
  if (!options['frames-only']) run(ffmpeg, ['-version']);
  const {chromium} = await import('playwright');
  const mime = {'.html': 'text/html', '.js': 'application/javascript', '.mjs': 'application/javascript', '.json': 'application/json', '.css': 'text/css', '.svg': 'image/svg+xml', '.png': 'image/png', '.jpg': 'image/jpeg', '.webp': 'image/webp', '.woff2': 'font/woff2', '.mp4': 'video/mp4'};
  server = createServer(async (request, response) => {
    try {
      const pathname = decodeURIComponent(new URL(request.url, 'http://127.0.0.1').pathname);
      if (pathname === '/favicon.ico') { response.writeHead(204); response.end(); return; }
      const path = resolve(project, '.' + (pathname === '/' ? '/engine/index.html' : pathname));
      if (path !== project && !path.startsWith(project + sep)) { response.writeHead(403); response.end(); return; }
      const body = await readFile(path);
      response.writeHead(200, {'Content-Type': mime[extname(path)] || 'application/octet-stream', 'Cache-Control': 'no-store'});
      response.end(body);
    } catch { response.writeHead(404); response.end('Not found'); }
  });
  await new Promise((res, rej) => { server.once('error', rej); server.listen(0, '127.0.0.1', res); });
  browser = await chromium.launch({headless: true});
  const context = await browser.newContext({viewport: {width: brief.width, height: brief.height}, deviceScaleFactor: 1});
  const page = await context.newPage();
  const errors = [];
  page.on('pageerror', error => errors.push(error.message));
  page.on('response', response => { if (response.status() >= 400) errors.push(`HTTP ${response.status()}: ${response.url()}`); });
  page.on('requestfailed', request => errors.push(`Request failed: ${request.url()}`));
  await page.goto(`http://127.0.0.1:${server.address().port}/engine/index.html`, {waitUntil: 'networkidle'});
  await page.waitForFunction(() => typeof window.seek === 'function', null, {timeout: 15000});
  const seek = async t => {
    await page.evaluate(async time => {
      await window.seek(time);
      await document.fonts.ready;
      await Promise.all([...document.images].map(image => image.decode()));
    }, t);
    if (errors.length) throw new Error(errors.join('\n'));
  };
  const screenshot = () => page.screenshot({type: 'png', animations: 'allow', fullPage: false});
  // Out-of-order seeks must produce exactly the same first frame.
  await seek(0); const first = await screenshot();
  await seek(Math.max(0, brief.duration - 1 / brief.fps));
  await seek(0); const repeated = await screenshot();
  if (!first.equals(repeated)) throw new Error('seek(0) changes after seeking elsewhere. Remove wall-clock playback, random state, and cumulative simulation.');
  await mkdir(frames, {recursive: true});
  let composite;
  if (options.samples > 1) {
    composite = await context.newPage();
    await composite.setContent(`<canvas id="mix" width="${brief.width}" height="${brief.height}"></canvas><style>html,body{margin:0;overflow:hidden}canvas{display:block}</style>`);
  }
  const frameCount = Math.round(brief.duration * brief.fps);
  for (let frame = 0; frame < frameCount; frame++) {
    const target = resolve(frames, `${String(frame).padStart(6, '0')}.png`);
    if (options.samples === 1) {
      await seek(frame / brief.fps);
      await page.screenshot({path: target, type: 'png', animations: 'allow', fullPage: false});
    } else {
      const samples = [];
      for (let sample = 0; sample < options.samples; sample++) {
        const offset = ((sample + 0.5) / options.samples - 0.5) * options.shutter;
        await seek(Math.min(brief.duration - 1e-8, Math.max(0, (frame + offset) / brief.fps)));
        samples.push('data:image/png;base64,' + (await screenshot()).toString('base64'));
      }
      await composite.evaluate(async sources => {
        const canvas = document.getElementById('mix'); const ctx = canvas.getContext('2d');
        ctx.clearRect(0, 0, canvas.width, canvas.height);
        ctx.globalCompositeOperation = 'lighter'; ctx.globalAlpha = 1 / sources.length;
        for (const source of sources) { const image = new Image(); image.src = source; await image.decode(); ctx.drawImage(image, 0, 0); }
        ctx.globalAlpha = 1; ctx.globalCompositeOperation = 'source-over';
      }, samples);
      await composite.locator('#mix').screenshot({path: target, type: 'png'});
    }
    if (frame === 0 || (frame + 1) % brief.fps === 0 || frame + 1 === frameCount) console.log(`Rendered ${frame + 1}/${frameCount} frames`);
  }
  if (options['frames-only']) {
    console.log(JSON.stringify({status: 'frames-only', frames: frameCount, directory: frames, note: 'Frames are not a completed video.'}));
  } else {
    await mkdir(dirname(output), {recursive: true});
    const args = ['-hide_banner', '-loglevel', 'error', '-n', '-framerate', String(brief.fps), '-start_number', '0', '-i', resolve(frames, '%06d.png')];
    if (audio) args.push('-i', audio);
    args.push('-map', '0:v:0');
    if (audio) args.push('-map', '1:a:0', '-af', `apad=whole_dur=${brief.duration}`, '-c:a', 'aac', '-b:a', '192k');
    args.push('-frames:v', String(frameCount), '-r', String(brief.fps), '-t', String(brief.duration), '-c:v', 'libx264', '-pix_fmt', 'yuv420p', '-crf', '18', '-movflags', '+faststart', output);
    run(ffmpeg, args);
    console.log(JSON.stringify({status: 'rendered-unverified', output, frames: frameCount, audio: Boolean(audio), next: 'Run promo.py verify and review frames, text and sound before delivery.'}));
  }
} catch (error) {
  console.error(error.stack || String(error)); process.exitCode = 1;
} finally {
  if (browser) await browser.close();
  if (server) await new Promise(resolve => server.close(resolve));
}
