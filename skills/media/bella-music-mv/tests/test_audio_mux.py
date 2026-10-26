"""Actual ffmpeg regression: an output frame cap must not truncate the audio stream.

Needs NODE, FFMPEG and FFPROBE env paths (or executables on PATH). No browser or npm dependencies.
"""
import json
import os
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest

RUNTIME = Path(__file__).resolve().parents[1] / 'assets' / 'animation-base'


def executable(name):
    value = os.environ.get(name.upper()) or shutil.which(name)
    value = shutil.which(value) or value if value else None
    return value if value and os.path.isfile(value) and os.access(value, os.X_OK) else None


class AudioMuxRegression(unittest.TestCase):
    def test_complete_video_keeps_complete_audio(self):
        node, ffmpeg, ffprobe = (executable(n) for n in ('node', 'ffmpeg', 'ffprobe'))
        if not all((node, ffmpeg, ffprobe)):
            self.skipTest('Actual audio mux test requires executable NODE, FFMPEG and FFPROBE (env or PATH).')
        with tempfile.TemporaryDirectory(prefix='bella-audio-mux-') as td:
            project = Path(td) / 'project'
            shutil.copytree(RUNTIME, project, ignore=shutil.ignore_patterns('node_modules', 'out', '.git', 'docs'))
            config = dict(status='authored', duration=2, fps=6, bpm=120, offset=0,
                          width=320, height=180, audio='song.wav', captions='off')
            (project / 'src/config.js').write_text('const PROJECT = ' + json.dumps(config) + ';', encoding='utf-8')
            (project / 'src/lyrics.js').write_text('const MV_LYRICS = [];', encoding='utf-8')
            (project / 'src/scenes/video.js').write_text('shots([[0, function noOpShot() {}]]);', encoding='utf-8')

            def run(argv):
                return subprocess.run(argv, cwd=project, check=True, capture_output=True, text=True, timeout=60)

            run([ffmpeg, '-y', '-v', 'error', '-f', 'lavfi', '-i',
                 'sine=frequency=440:duration=2', 'song.wav'])
            setup = """
import {projectConfig,sourceFingerprint,ensureManifest} from './render-utils.mjs';
import {resolve} from 'node:path';
const root=process.cwd(), p=projectConfig(root);
const identity=sourceFingerprint(root,p,{fps:p.fps,audio:resolve(p.audio),example:null,loop:null,format:'jpg',gpu:'default'});
ensureManifest('frames',{schema:1,...identity,fps:p.fps,width:p.width,height:p.height,duration:p.duration,frameCount:12,format:'jpg'});
"""
            run([node, '--input-type=module', '-e', setup])
            run([ffmpeg, '-y', '-v', 'error', '-f', 'lavfi', '-i',
                 'color=c=0x253050:s=320x180:r=6:d=2', '-frames:v', '12', '-start_number', '0',
                 'frames/f%06d.jpg'])
            run([node, 'render.mjs', '--encode', '--frames-dir=frames', '--out=out/video.mp4',
                 '--ffmpeg=' + ffmpeg, '--ffprobe=' + ffprobe])
            probe = json.loads(run([ffprobe, '-v', 'error', '-count_frames', '-show_streams', '-of', 'json',
                                    'out/video.mp4']).stdout)
            video = next(s for s in probe['streams'] if s['codec_type'] == 'video')
            audio = next(s for s in probe['streams'] if s['codec_type'] == 'audio')
            self.assertEqual(int(video['nb_read_frames']), 12)
            self.assertAlmostEqual(float(video['duration']), 2, delta=1 / 6)
            self.assertAlmostEqual(float(audio['duration']), 2, delta=0.1)
            self.assertEqual(audio['codec_name'], 'aac')
            self.assertEqual((video['width'], video['height']), (320, 180))
            metadata = json.loads((project / 'out/video.mp4.metadata.json').read_text(encoding='utf-8'))
            self.assertEqual(metadata['fps'], 6)
            self.assertGreater(metadata['verified']['audio']['duration'], 1.9)


if __name__ == '__main__':
    unittest.main()
