import test from 'node:test';
import assert from 'node:assert/strict';
import { mkdtempSync, mkdirSync, writeFileSync, readFileSync, rmSync, cpSync, existsSync } from 'node:fs';
import { resolve, join } from 'node:path';
import { fileURLToPath } from 'node:url';
import vm from 'node:vm';
import { spawnSync } from 'node:child_process';
import { projectConfig, registryMetadata, assertReady, frameRange, sourceFingerprint, ensureManifest, assertCompleteFrames, assertTimesCovered } from './render-utils.mjs';
const root = fileURLToPath(new URL('.', import.meta.url));
const fixture = fn => {
  mkdirSync(join(root,'out/test'),{recursive:true}); const dir=mkdtempSync(join(root,'out/test/case-'));
  try { return fn(dir); } finally { rmSync(dir,{recursive:true,force:true}); }
};
const config = {status:'authored',duration:1,fps:24,bpm:120,offset:0,width:1080,height:1920,audio:null,captions:'karaoke'};
test('fps override and portrait dimensions are the effective configuration', () => fixture(dir => {
  mkdirSync(join(dir,'src')); writeFileSync(join(dir,'src/config.js'),'const PROJECT='+JSON.stringify(config));
  const p=projectConfig(dir,30); assert.equal(p.fps,30); assert.equal(p.width,1080); assert.equal(p.height,1920);
  assert.throws(()=>projectConfig(dir,NaN),/fps/);
}));
test('frame ranges are half-open and cover non-frame-aligned duration',()=>{
  assert.deepEqual(frameRange(null,1.01,24),{first:0,end:25,start:0,duration:25/24,count:25});
  assert.equal(frameRange('0.1:0.3',1,24).first,3); assert.throws(()=>frameRange('0:2',1,24),/Invalid range/);
});
test('source bytes and package-lock invalidate cache even without mtime assumptions',()=>fixture(dir=>{
  mkdirSync(join(dir,'src')); writeFileSync(join(dir,'src/scene.js'),'a'); writeFileSync(join(dir,'package-lock.json'),'one');
  const a=sourceFingerprint(dir,config).fingerprint;
  writeFileSync(join(dir,'src/scene.js'),'b'); const b=sourceFingerprint(dir,config).fingerprint; assert.notEqual(a,b);
  writeFileSync(join(dir,'package-lock.json'),'two'); assert.notEqual(b,sourceFingerprint(dir,config).fingerprint);
  mkdirSync(join(dir,'assets')); writeFileSync(join(dir,'assets/character.svg'),'<svg/>'); const assetBefore=sourceFingerprint(dir,config).fingerprint;
  writeFileSync(join(dir,'assets/character.svg'),'<svg width="100"/>'); assert.notEqual(assetBefore,sourceFingerprint(dir,config).fingerprint);
  assert.notEqual(sourceFingerprint(dir,config).fingerprint,sourceFingerprint(dir,{...config,fps:30}).fingerprint);
}));
test('manifest rejects old frames instead of silently continuing',()=>fixture(dir=>{
  const manifest={fingerprint:'old',frameCount:24,fps:24,format:'jpg'};
  ensureManifest(dir,manifest); assert.throws(()=>ensureManifest(dir,{...manifest,fingerprint:'new'}),/Frame cache does not match/);
}));
test('template is explicitly incomplete and example is explicitly separate',()=>{
  const p=projectConfig(root), m=registryMetadata(root,p); assert.equal(m.status,'unimplemented'); assert.equal(m.timeline.valid,false); assert.throws(()=>assertReady(m),/unimplemented/);
  const example=registryMetadata(root,projectConfig(root,30,'demo'),'demo'); assert.equal(example.example,'demo'); assert.equal(example.fps,30); assert.equal(example.timeline.valid,true); assertReady(example);
});
test('chapters reject gaps, overlaps and unordered shots',()=>{
  const code=readFileSync(join(root,'src/timeline.js'),'utf8');
  for (const registration of ["chapter('a',0,.4,[[0,()=>{}]]);chapter('b',.5,1,[[.5,()=>{}]])", "chapter('a',0,.6,[[0,()=>{}]]);chapter('b',.5,1,[[.5,()=>{}]])", "chapter('a',0,1,[[0,()=>{}],[0,()=>{}]])"]) {
    const c={window:{},DUR:1}; vm.runInNewContext(code+'\n'+registration,c); assert.equal(c.window.validateTimeline().valid,false);
  }
  const c={window:{},DUR:1};vm.runInNewContext(code+"\nchapter('a',0,.5,[[0,()=>{}]]);chapter('b',.5,1,[[.5,()=>{}]])",c);
  assert.equal(c.window.validateTimeline().valid,true);assert.equal(c.window.validateTimeline().shots[1].end,1);
});
test('word timing requires an explicit exact claim and exact text',()=>{
  const code=readFileSync(join(root,'src/mv.js'),'utf8');
  const run = row => {const c={window:{},PROJECT:{duration:2},MV_LYRICS:[row]};vm.runInNewContext(code,c);return vm.runInNewContext('validateMVLyrics()',c);};
  const row={start:0,end:2,text:'你好世界',timing:'provided',source:'user timestamps',words:[{start:0,end:1,text:'你好'},{start:1,end:2,text:'世界'}]};
  const line=run(row);assert.equal(line.valid,true);assert.equal(line.rows[0].wordTiming,'none');assert.equal(line.warnings.length,1);
  assert.equal(run({...row,wordTiming:'exact'}).rows[0].wordTiming,'exact');
  assert.equal(run({...row,wordTiming:'exact',words:[{start:0,end:2,text:'错误'}]}).valid,false);
  assert.equal(run({...row,timing:'exact',words:[]}).valid,false);
});

test('drafts may cover part of the song but previews cannot land in gaps',()=>{
  const c={window:{},DUR:2}; vm.runInNewContext(readFileSync(join(root,'src/timeline.js'),'utf8')+"\nchapter('first',0,1,[[0,()=>{}]])",c);
  const timeline=c.window.validateTimeline(), meta={status:'draft',duration:2,timeline,lyrics:{valid:true}};
  assert.equal(timeline.structuralValid,true); assert.equal(timeline.coverageValid,false);
  assert.doesNotThrow(()=>assertReady(meta,true)); assert.throws(()=>assertReady(meta,false),/draft/);
  assert.doesNotThrow(()=>assertTimesCovered(meta,[0,.9])); assert.throws(()=>assertTimesCovered(meta,[1.1]),/No registered shot/);
});
test('encoding rejects missing or corrupt frames',()=>fixture(dir=>{
  const manifest={frameCount:2,format:'jpg'};
  writeFileSync(join(dir,'f000000.jpg'),Buffer.from([255,216,0,255,217]));
  assert.throws(()=>assertCompleteFrames(dir,manifest),/Missing or empty frame 1/);
  writeFileSync(join(dir,'f000001.jpg'),Buffer.from([0,0,0,0]));
  assert.throws(()=>assertCompleteFrames(dir,manifest),/Corrupt JPEG/);
}));

test('failed encoder exits nonzero and does not publish a final MP4',()=>fixture(dir=>{
  cpSync(join(root,'src'),join(dir,'src'),{recursive:true});
  for(const name of ['studio.html','render.mjs','render-utils.mjs','package.json','package-lock.json']) cpSync(join(root,name),join(dir,name));
  const p={...config,duration:1/24,width:16,height:16,captions:'off'};
  writeFileSync(join(dir,'src/config.js'),'const PROJECT='+JSON.stringify(p));
  writeFileSync(join(dir,'src/lyrics.js'),'const MV_LYRICS=[];');
  writeFileSync(join(dir,'src/scenes/video.js'),'shots([[0,function testShot(){}]]);');
  const frameDir=join(dir,'frames'), effective=projectConfig(dir);
  const fp=sourceFingerprint(dir,effective,{fps:24,audio:null,example:null,loop:null,format:'jpg',gpu:'default'});
  ensureManifest(frameDir,{...fp,frameCount:1,fps:24,format:'jpg'});
  writeFileSync(join(frameDir,'f000000.jpg'),Buffer.from([255,216,0,255,217]));
  const out=join(dir,'final.mp4');
  const run=spawnSync(process.execPath,[join(dir,'render.mjs'),'--encode','--frames-dir='+frameDir,'--out='+out,'--ffmpeg='+join(dir,'missing-ffmpeg')],{cwd:dir,encoding:'utf8',timeout:10000});
  assert.equal(run.status,1);assert.match(run.stderr,/Render failed.*ENOENT/);assert.equal(existsSync(out),false);
}));
