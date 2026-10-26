#!/usr/bin/env node
// Local, deterministic MV renderer. See ../../references/engine-api.md for all flags.
import { spawn } from 'node:child_process';
import { createServer } from 'node:http';
import { existsSync, readFileSync, readdirSync, statSync, mkdirSync, renameSync, rmSync } from 'node:fs';
import { resolve, join, dirname, extname } from 'node:path';
import { createRequire } from 'node:module';
import { homedir } from 'node:os';
import { parseArgs, projectConfig, registryMetadata, assertReady, frameRange, sourceFingerprint, atomicWrite, frameFile, ensureManifest, assertCompleteFrames, assertTimesCovered } from './render-utils.mjs';

const args = parseArgs(process.argv.slice(2)), root = process.cwd();
const allowed = new Set(['check','draft','sheet','strip','stills','frames','clip','encode','png','range','workers','out','frames-dir','cols','w','crop','crop-at','loop','example','fps','audio','chrome','soft-gl','gpu-angle','dependency-root','ffmpeg','ffprobe','help']);
let browser, server; const children = new Set(); let aborted = false;
const childRun = (cmd, argv, capture = false) => new Promise((ok, bad) => {
  const p = spawn(cmd, argv, { stdio: capture ? ['ignore','pipe','pipe'] : ['ignore','inherit','inherit'] }); children.add(p);
  let out = '', err = ''; if (capture) { p.stdout.on('data', b => out += b); p.stderr.on('data', b => err += b); }
  p.once('error', e => { children.delete(p); bad(new Error(`${cmd}: ${e.message}`)); });
  p.once('close', (code, signal) => { children.delete(p); code === 0 ? ok(out) : bad(new Error(`${cmd} exited ${code ?? signal}: ${err.trim()}`)); });
});
async function cleanup() {
  aborted = true;
  for (const p of children) p.kill('SIGTERM');
  await browser?.close().catch(() => {});
  if (server) await new Promise(done => server.close(done));
  for (const p of children) p.kill('SIGKILL');
}
for (const signal of ['SIGINT','SIGTERM']) process.once(signal, () => { cleanup().finally(() => process.exit(signal === 'SIGINT' ? 130 : 143)); });
const jsonProbe = file => childRun(args.ffprobe || 'ffprobe', ['-v','error','-count_frames','-show_streams','-show_format','-of','json',file], true).then(JSON.parse);
const nums = text => String(text).split(',').map(Number);
function positive(value, label, max = 10000) { const n = +value; if (!Number.isInteger(n) || n < 1 || n > max) throw new Error(`${label} must be an integer from 1 to ${max}`); return n; }
function checkTimes(values, duration) { if (!values.length || values.some(t => !Number.isFinite(t) || t < 0 || t > duration)) throw new Error(`Frame times must be within 0..${duration}`); return values; }
async function main() {
  for (const name of Object.keys(args)) if (!allowed.has(name)) throw new Error(`Unknown flag --${name}`);
  if (args.help) { console.log('node render.mjs --check | --sheet=0,1 | --strip=0:1 | --stills=1 | --frames | --encode | --clip | --png\nOptions: --draft --range=a:b --frames-dir=out/frames --fps=24 --audio=assets/song.mp3 --loop=emotions --example=demo --chrome=/path --dependency-root=/local/project'); return; }
  const modes = ['check','sheet','strip','stills','frames','encode','clip','png'].filter(k => args[k] !== undefined);
  if (modes.length !== 1) throw new Error('Choose exactly one action: --check, --sheet, --strip, --stills, --frames, --encode, --clip or --png');
  const project = projectConfig(root, args.fps, args.example), fps = project.fps;
  let meta = registryMetadata(root, project, args.example);
  if(args.loop && !meta.loops?.[args.loop]) throw new Error(`Unknown loop ${args.loop}`);
  if (args.check) {
    try { assertReady(meta, !!args.draft, args.loop); }
    catch (e) { meta.errors = [e.message]; process.exitCode = 1; }
    console.log('MV_CHECK=' + JSON.stringify(meta)); return;
  }
  assertReady(meta, !!args.draft, args.loop);
  if (args.loop) {
    // Query loop duration from the same static local registry, without pretending it is a user video.
    // The renderer will obtain the authoritative loop duration from Chrome below; encode requires stored metadata.
    if (args.encode) throw new Error('Use --clip or --png for loops; --encode is reserved for the complete authored video.');
  }
  const audioSetting = args.audio === true ? (() => { throw new Error('--audio requires a path'); })() : args.audio ?? project.audio;
  const audio = args.loop || args.example ? null : audioSetting ? resolve(root, audioSetting) : null;
  if (audio && !existsSync(audio)) throw new Error(`Audio file does not exist: ${audio}`);
  if (audio && /^(https?:|data:)/i.test(audioSetting)) throw new Error('Audio must be a local path');
  let audioInfo;
  if (audio && (args.clip || args.encode)) {
    const probe = await jsonProbe(audio), stream = probe.streams.find(s => s.codec_type === 'audio');
    if (!stream) throw new Error('Selected input has no audio stream');
    audioInfo = { path: audio, duration: +(stream.duration || probe.format.duration), sampleRate: +stream.sample_rate, channels: stream.channels };
    if (!Number.isFinite(audioInfo.duration) || audioInfo.duration + 1 / fps < project.duration) throw new Error(`Audio is shorter than PROJECT.duration (${audioInfo.duration}s < ${project.duration}s); fix duration or supply the full audio.`);
  }
  const format = args.png ? 'png' : 'jpg';
  const identity = () => sourceFingerprint(root, project, { fps, audio, example: args.example || null, loop: args.loop || null, format, gpu: args['soft-gl'] ? 'software' : args['gpu-angle'] || 'default' });
  const manifestFor = duration => ({ schema: 1, ...identity(), fps, width: project.width, height: project.height, duration, frameCount: Math.ceil(duration * fps - 1e-8), format, audio: audioInfo || audio, draft: !!args.draft, loop: args.loop || null, example: args.example || null });
  const framesDir = resolve(args['frames-dir'] || (args.png ? args.out || 'out/png' : args.clip ? 'out/clip-frames' : 'out/frames'));
  async function encode(manifest, range) {
    const out = resolve(args.out || 'out/video.mp4'); mkdirSync(dirname(out), { recursive: true });
    const temp = out.replace(/\.mp4$/i, '') + '.tmp.mp4';
    await childRun(args.ffmpeg || 'ffmpeg', ['-y','-v','error','-framerate',String(fps),'-start_number',String(range.first),'-t',String(range.duration),'-i',join(framesDir,`f%06d.${manifest.format}`),
      ...(audio ? ['-ss',String(range.start),'-t',String(range.duration),'-i',audio,'-map','0:v:0','-map','1:a:0','-c:a','aac','-b:a','192k'] : []),
      '-t',String(range.duration),'-c:v','libx264','-preset','medium','-crf','18','-pix_fmt','yuv420p','-movflags','+faststart',temp]);
    try {
      const p = await jsonProbe(temp), v = p.streams.find(s => s.codec_type === 'video'), a = p.streams.find(s => s.codec_type === 'audio');
      const rate = v?.avg_frame_rate?.split('/').map(Number); const actualFps = rate ? rate[0] / rate[1] : NaN;
      if (!v || v.width !== project.width || v.height !== project.height || Math.abs(actualFps - fps) > .001 || +v.nb_read_frames !== range.count || v.pix_fmt !== 'yuv420p' || Math.abs(+v.duration - range.duration) > 1 / fps + .01) throw new Error('Encoded video failed dimension/fps/frame-count/pixel-format/duration verification');
      if (audio && (!a || a.codec_name !== 'aac' || +a.duration < range.duration - .1 || +a.sample_rate <= 0)) throw new Error('Encoded audio failed stream/codec/duration verification');
      renameSync(temp, out);
      atomicWrite(out + '.metadata.json', JSON.stringify({ ...meta, fps, renderedRange: range, audio: audioInfo, fingerprint: manifest.fingerprint, verified: { video: { width:v.width,height:v.height,fps:actualFps,frames:+v.nb_read_frames,duration:+v.duration,codec:v.codec_name }, audio:a ? {codec:a.codec_name,sampleRate:+a.sample_rate,channels:a.channels,duration:+a.duration} : null } }, null, 2) + '\n');
      console.log(`Wrote ${out} (${range.count} frames at ${fps} fps, ${project.width}×${project.height})`);
    } catch (e) { rmSync(temp, { force: true }); throw e; }
  }
  if (args.encode) {
    if (args.range) throw new Error('--encode requires the complete video; use --clip --range=a:b for a segment');
    const manifest = ensureManifest(framesDir, manifestFor(project.duration), false); assertCompleteFrames(framesDir, manifest);
    await encode(manifest, frameRange(null, project.duration, fps)); return;
  }
  const dependencyRoot = resolve(args['dependency-root'] || root), require = createRequire(join(dependencyRoot, 'package.json'));
  let puppeteer; try { puppeteer = require('puppeteer-core'); } catch { throw new Error('Local dependencies missing. Run npm ci in the copied animation-base project.'); }
  const candidates = [args.chrome, process.env.CHROME_PATH, '/Applications/Google Chrome.app/Contents/MacOS/Google Chrome','C:/Program Files/Google/Chrome/Application/chrome.exe','C:/Program Files (x86)/Google/Chrome/Application/chrome.exe','/usr/bin/google-chrome','/usr/bin/chromium','/usr/bin/chromium-browser'];
  for (const base of [join(homedir(),'.cache/ms-playwright'),join(homedir(),'Library/Caches/ms-playwright')]) if (existsSync(base)) for (const n of readdirSync(base).sort().reverse()) if (n.startsWith('chromium-')) candidates.push(join(base,n,'chrome-linux64/chrome'),join(base,n,'chrome-mac-arm64/Google Chrome for Testing.app/Contents/MacOS/Google Chrome for Testing'));
  const chrome = candidates.find(p => typeof p === 'string' && existsSync(p)); if (!chrome) throw new Error('Chrome not found. Pass --chrome=/absolute/path or set CHROME_PATH.');
  const mime = { '.html':'text/html; charset=utf-8','.js':'text/javascript; charset=utf-8','.jpg':'image/jpeg','.png':'image/png','.json':'application/json' };
  server = createServer((req, res) => {
    try {
      const name = decodeURIComponent(new URL(req.url, 'http://localhost').pathname).slice(1) || 'studio.html';
      const base = name.startsWith('node_modules/') ? dependencyRoot : root, file = resolve(base, name);
      if (!file.startsWith(base + '/') || !existsSync(file) || !statSync(file).isFile()) { res.writeHead(404); res.end(); return; }
      let body = readFileSync(file); if (name === 'src/config.js') body = Buffer.from(body.toString() + `\nObject.assign(PROJECT, ${JSON.stringify(project)});`);
      res.writeHead(200, { 'Content-Type': mime[extname(file)] || 'application/octet-stream', 'Cache-Control':'no-store' }); res.end(body);
    } catch (e) { res.writeHead(500); res.end(e.message); }
  });
  await new Promise((ok, bad) => { server.once('error', bad); server.listen(0,'127.0.0.1',ok); });
  const origin = `http://127.0.0.1:${server.address().port}`;
  const angle = { vulkan:['--use-angle=vulkan','--enable-features=Vulkan'],'gl-egl':['--use-angle=gl-egl'] };
  if (args['gpu-angle'] && !angle[args['gpu-angle']]) throw new Error('--gpu-angle must be vulkan or gl-egl');
  const gpu = args['soft-gl'] ? ['--use-angle=swiftshader','--enable-unsafe-swiftshader'] : angle[args['gpu-angle']] || (process.platform === 'darwin' ? ['--use-angle=metal'] : process.platform === 'win32' ? ['--use-angle=d3d11'] : ['--use-gl=angle']);
  browser = await puppeteer.launch({ executablePath:chrome,headless:true,protocolTimeout:120000,args:[...(process.platform==='linux'?['--no-sandbox']:[]),'--ignore-gpu-blocklist',...gpu,'--enable-gpu-rasterization','--disable-renderer-backgrounding','--disable-background-timer-throttling'] });
  async function openPage() {
    const page = await browser.newPage(); const failures = [];
    page.on('pageerror', e => failures.push(e.message));
    await page.setRequestInterception(true);
    page.on('request', r => r.url().startsWith(origin + '/') || r.url().startsWith('data:') ? r.continue() : r.abort('blockedbyclient'));
    await page.evaluateOnNewDocument(f => { window.MV_FPS = f; }, fps);
    const q = new URLSearchParams({ render:'1', ...(args.example?{example:args.example}:{}), ...(args.loop?{loop:args.loop}:{}) });
    await page.goto(origin + '/studio.html?' + q, {waitUntil:'networkidle0',timeout:60000});
    await page.waitForFunction('window.ready === true',{timeout:60000});
    if (args.loop && !(await page.evaluate(n => !!LOOPS[n],args.loop))) throw new Error(`Unknown loop ${args.loop}`);
    const checked = await page.evaluate(() => window.mvMetadata());
    assertReady(checked,!!args.draft,args.loop);
    if (failures.length) throw new Error('Browser script error: ' + failures.join('; '));
    return { page, failures };
  }
  const probe = await openPage(), duration = await probe.page.evaluate(() => window.LOOP ? window.LOOP.len : DUR);
  if (!Number.isFinite(duration) || duration <= 0) throw new Error('Loop needs a positive .len');
  const renderFrame = async (worker,t,type='image/jpeg') => {
    if (aborted) throw new Error('Render interrupted');
    const url = await worker.page.evaluate((t,type)=>window.renderAt(t,type,.94),t,type);
    if (worker.failures.length) throw new Error(worker.failures.join('; '));
    return Buffer.from(url.slice(url.indexOf(',')+1),'base64');
  };
  if (args.sheet || args.strip) {
    let ts;
    if (args.strip) { const range = frameRange(args.strip,duration,fps); ts=Array.from({length:range.count},(_,i)=>(range.first+i)/fps); }
    else ts=checkTimes(nums(args.sheet),duration);
    if (!args.loop) assertTimesCovered(meta,ts);
    const crop=args.crop?nums(args.crop):null, at=args['crop-at']?nums(args['crop-at']):null;
    for (const c of [crop,at]) if (c && (c.length!==4||c.some(v=>!Number.isFinite(v))||c[2]<=0||c[3]<=0)) throw new Error('Crop is four numbers x,y,width,height; dimensions must be positive');
    if (crop&&at) throw new Error('Choose --crop OR --crop-at');
    const result=await probe.page.evaluate((ts,cols,w,crop,at)=>window.renderSheet(ts,cols,w,crop,at),ts,positive(args.cols||(args.strip?6:3),'cols',20),positive(args.w||(args.strip?320:640),'w',8192),crop,at);
    atomicWrite(resolve(args.out||'out/sheet.jpg'),Buffer.from(result.url.split(',')[1],'base64'));
    console.log(`Wrote ${args.out||'out/sheet.jpg'} (${ts.length} frames)`); return;
  }
  if (args.stills) {
    const dir=resolve(args.out||'out/stills');
    const ts=checkTimes(nums(args.stills),duration); if(!args.loop) assertTimesCovered(meta,ts);
    for (const t of ts) atomicWrite(join(dir,`t${t.toFixed(4).replace('.','_')}.png`),await renderFrame(probe,t,'image/png'));
    console.log(`Wrote stills to ${dir}`); return;
  }
  await probe.page.close();
  const spec=args.range||(typeof args.frames==='string'?args.frames:typeof args.clip==='string'?args.clip:null), range=frameRange(spec,duration,fps);
  if(!args.loop) assertTimesCovered(meta,Array.from({length:range.count},(_,i)=>(range.first+i)/fps));
  const manifest=ensureManifest(framesDir,manifestFor(duration));
  const todo=[]; for(let i=range.first;i<range.end;i++) { const file=frameFile(framesDir,i,format); if(!existsSync(file)||statSync(file).size<4) todo.push(i); }
  let next=0,done=0;
  await Promise.all(Array.from({length:Math.min(positive(args.workers||2,'workers',16),Math.max(1,todo.length))},async()=>{
    const worker=await openPage();
    try { while(next<todo.length) { const i=todo[next++]; atomicWrite(frameFile(framesDir,i,format),await renderFrame(worker,i/fps,format==='png'?'image/png':'image/jpeg')); if(++done%24===0||done===todo.length) console.log(`Rendered ${done}/${todo.length} missing frames`); } }
    finally { await worker.page.close().catch(()=>{}); }
  }));
  if (args.clip) {
    // Every requested index must be present; ffmpeg rejects any decode or parameter failure.
    for(let i=range.first;i<range.end;i++) if(!existsSync(frameFile(framesDir,i,format))) throw new Error(`Missing clip frame ${i}`);
    await encode(manifest,range);
  } else console.log(`Frames cached in ${framesDir}; full video requires ${manifest.frameCount} consecutive frames.`);
}
try { await main(); }
catch (e) {
  if(args.check) console.log('MV_CHECK='+JSON.stringify({status:'error',timeline:{valid:false,errors:[e.message],shots:[]},errors:[e.message]}));
  else console.error('Render failed:',e.message);
  process.exitCode=1;
} finally { await cleanup(); }
