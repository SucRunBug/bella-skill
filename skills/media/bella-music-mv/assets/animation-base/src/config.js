// Project settings. Author scene coordinates against W/H; portrait is a layout, not an automatic crop.
const PROJECT = {
  status: 'unimplemented',    // unimplemented | draft | authored; only authored is a final deliverable
  duration: 15,
  fps: 24,
  bpm: 120,
  offset: 0,
  width: 1920,                 // landscape 1920×1080; portrait 1080×1920; square 1080×1080
  height: 1080,
  audio: null,                 // local project-relative path; --audio overrides it
  captions: 'karaoke',         // karaoke | line | off
  captionFont: 'system-ui, "PingFang SC", "Microsoft YaHei", sans-serif',
  captionSafeBottom: 0.08,      // fraction of H, leave room for player controls
};
