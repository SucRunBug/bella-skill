// Authored lyric timing in seconds on the project's audio timeline; no ASR is run by this kit.
// words require wordTiming:'exact' (or timing:'exact') and start/end/text fields. Approximate timing only animates whole-line progress.
// Record the provenance in source (e.g. supplied LRC, manual transcription); never claim estimated words are exact.
const MV_LYRICS = [
  // { start: 0, end: 3, text: '你的第一句歌词', timing: 'approximate', source: 'manual estimate' },
  // { start: 3, end: 5, text: '你好世界', timing: 'provided', wordTiming: 'exact', source: 'user verified word timing',
  //   words: [{ start: 3, end: 4, text: '你好' }, { start: 4, end: 5, text: '世界' }] },
];
